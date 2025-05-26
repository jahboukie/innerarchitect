"""
Logging configuration for InnerArchitect.

This module sets up comprehensive logging for the application, including:
- Console logging for development
- File logging for production
- Error monitoring and reporting via Sentry (optional)
- Custom formatters and handlers for different environments
"""
import os
import logging
import json
import time
import traceback
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from flask import request, has_request_context, current_app, g

# Optional Sentry integration
try:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

# Default log directory
LOG_DIR = os.environ.get('LOG_DIR', 'logs')

# Log levels
LOG_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
}

class RequestFormatter(logging.Formatter):
    """
    Custom formatter that adds request information to log records.
    """
    def format(self, record):
        if has_request_context():
            record.url = request.url
            record.method = request.method
            record.path = request.path
            record.ip = request.remote_addr
            record.user_agent = request.user_agent.string
            # Add user ID if available
            if hasattr(g, 'user') and hasattr(g.user, 'id'):
                record.user_id = g.user.id
            else:
                record.user_id = 'anonymous'
        else:
            record.url = None
            record.method = None
            record.path = None
            record.ip = None
            record.user_agent = None
            record.user_id = None
            
        return super().format(record)

class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after gathering all the log record attributes
    """
    def format(self, record):
        logobj = {}
        
        # Add standard record attributes
        logobj['time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created))
        logobj['name'] = record.name
        logobj['level'] = record.levelname
        logobj['message'] = record.getMessage()
        
        # Add request context if available
        if hasattr(record, 'url') and record.url is not None:
            logobj['url'] = record.url
            logobj['method'] = record.method
            logobj['path'] = record.path
            logobj['ip'] = record.ip
            logobj['user_agent'] = record.user_agent
            logobj['user_id'] = record.user_id
        
        # Add exception info if available
        if record.exc_info:
            logobj['exception'] = {
                'type': str(record.exc_info[0].__name__),
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add any custom attributes
        for key, value in record.__dict__.items():
            if key not in ['args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
                          'funcName', 'id', 'levelname', 'levelno', 'lineno', 'module',
                          'msecs', 'message', 'msg', 'name', 'pathname', 'process',
                          'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName',
                          'url', 'method', 'path', 'ip', 'user_agent', 'user_id']:
                try:
                    # Try to serialize to JSON, skip if not serializable
                    json.dumps({key: value})
                    logobj[key] = value
                except (TypeError, OverflowError):
                    pass
        
        return json.dumps(logobj)

def configure_logging(app, config=None):
    """
    Configure logging for the application.
    
    Args:
        app: Flask application instance
        config: Optional configuration dictionary
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    
    # Default configuration
    log_config = {
        'level': os.environ.get('LOG_LEVEL', 'info'),
        'format': os.environ.get('LOG_FORMAT', 'standard'),  # 'standard' or 'json'
        'file_logging': os.environ.get('FILE_LOGGING', 'true').lower() == 'true',
        'console_logging': os.environ.get('CONSOLE_LOGGING', 'true').lower() == 'true',
        'sentry_dsn': os.environ.get('SENTRY_DSN'),
        'sentry_environment': os.environ.get('SENTRY_ENVIRONMENT', 'production'),
        'sentry_traces_sample_rate': float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
    }
    
    # Override with provided config
    if config:
        log_config.update(config)
    
    # Set root logger level
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVELS.get(log_config['level'].lower(), logging.INFO))
    
    # Clear existing handlers to avoid duplicates
    if root_logger.handlers:
        root_logger.handlers.clear()
        
    # Create app logger
    logger = logging.getLogger('inner_architect')
    logger.setLevel(LOG_LEVELS.get(log_config['level'].lower(), logging.INFO))
    
    # Create formatters
    if log_config['format'].lower() == 'json':
        formatter = JSONFormatter()
    else:
        formatter = RequestFormatter(
            '[%(asctime)s] %(levelname)s in %(module)s [%(user_id)s] [%(path)s]: %(message)s'
        )
    
    # Configure console logging
    if log_config['console_logging']:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(LOG_LEVELS.get(log_config['level'].lower(), logging.INFO))
        logger.addHandler(console_handler)
        app.logger.addHandler(console_handler)
    
    # Configure file logging
    if log_config['file_logging']:
        # Standard log file with rotation by size
        file_handler = RotatingFileHandler(
            os.path.join(LOG_DIR, 'inner_architect.log'),
            maxBytes=10485760,  # 10 MB
            backupCount=10
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(LOG_LEVELS.get(log_config['level'].lower(), logging.INFO))
        logger.addHandler(file_handler)
        app.logger.addHandler(file_handler)
        
        # Error log file with daily rotation
        error_handler = TimedRotatingFileHandler(
            os.path.join(LOG_DIR, 'error.log'),
            when='midnight',
            interval=1,
            backupCount=30
        )
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        logger.addHandler(error_handler)
        app.logger.addHandler(error_handler)
        
        # Access log for requests
        access_handler = TimedRotatingFileHandler(
            os.path.join(LOG_DIR, 'access.log'),
            when='midnight',
            interval=1,
            backupCount=30
        )
        access_handler.setFormatter(formatter)
        logger.addHandler(access_handler)
        
        # API call log for external API calls
        api_handler = RotatingFileHandler(
            os.path.join(LOG_DIR, 'api_calls.log'),
            maxBytes=10485760,  # 10 MB
            backupCount=10
        )
        api_handler.setFormatter(formatter)
        api_logger = logging.getLogger('inner_architect.api')
        api_logger.addHandler(api_handler)
        
        app.logger.info("File logging configured successfully")
    
    # Configure Sentry for error monitoring
    if SENTRY_AVAILABLE and log_config.get('sentry_dsn'):
        # Configure Sentry logging integration
        sentry_logging = LoggingIntegration(
            level=logging.INFO,        # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors as events
        )
        
        # Initialize Sentry SDK
        sentry_sdk.init(
            dsn=log_config['sentry_dsn'],
            integrations=[FlaskIntegration(), sentry_logging],
            environment=log_config['sentry_environment'],
            traces_sample_rate=log_config['sentry_traces_sample_rate'],
            
            # Associate users with errors
            send_default_pii=True
        )
        
        app.logger.info("Sentry error monitoring configured successfully")
    
    return logger

def log_api_call(provider, endpoint, duration, success, error=None, **kwargs):
    """
    Log an API call to the API call log.
    
    Args:
        provider: API provider name (e.g., 'claude', 'openai')
        endpoint: API endpoint called
        duration: Duration of the call in seconds
        success: Whether the call was successful
        error: Error message if the call failed
        **kwargs: Additional data to log
    """
    logger = logging.getLogger('inner_architect.api')
    
    log_data = {
        'provider': provider,
        'endpoint': endpoint,
        'duration': duration,
        'success': success
    }
    
    # Add error information if available
    if error:
        log_data['error'] = str(error)
        log_data['error_type'] = error.__class__.__name__ if hasattr(error, '__class__') else 'Unknown'
    
    # Add additional keyword arguments
    log_data.update(kwargs)
    
    # Log at appropriate level
    if success:
        logger.info(f"API call to {provider}/{endpoint} completed in {duration:.2f}s", extra=log_data)
    else:
        logger.error(f"API call to {provider}/{endpoint} failed after {duration:.2f}s: {error}", extra=log_data)
    
    # Log to Sentry if available and it's an error
    if not success and SENTRY_AVAILABLE and sentry_sdk.Hub.current.client:
        with sentry_sdk.push_scope() as scope:
            # Add context to the error
            scope.set_tag('provider', provider)
            scope.set_tag('endpoint', endpoint)
            scope.set_context('api_call', log_data)
            
            # Capture the exception if it exists, or create a new one
            if isinstance(error, Exception):
                sentry_sdk.capture_exception(error)
            else:
                sentry_sdk.capture_message(f"API call to {provider}/{endpoint} failed", level='error')

def get_logger(name=None):
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (defaults to 'inner_architect')
        
    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f'inner_architect.{name}')
    else:
        return logging.getLogger('inner_architect')

def setup_request_logging(app):
    """
    Set up request logging middleware for the Flask application.
    
    Args:
        app: Flask application instance
    """
    @app.before_request
    def log_request_start():
        request.start_time = time.time()
    
    @app.after_request
    def log_request(response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            # Skip logging for static files
            if not request.path.startswith('/static/'):
                log_data = {
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'duration': round(duration * 1000, 2),  # Convert to milliseconds
                    'ip': request.remote_addr,
                    'user_agent': request.user_agent.string if request.user_agent else None,
                    'content_length': response.content_length
                }
                
                # Add user ID if available
                if hasattr(g, 'user') and hasattr(g.user, 'id'):
                    log_data['user_id'] = g.user.id
                
                # Log at appropriate level based on status code
                logger = get_logger('access')
                if response.status_code >= 500:
                    logger.error(f"{request.method} {request.path} {response.status_code} ({duration:.2f}s)", extra=log_data)
                elif response.status_code >= 400:
                    logger.warning(f"{request.method} {request.path} {response.status_code} ({duration:.2f}s)", extra=log_data)
                else:
                    logger.info(f"{request.method} {request.path} {response.status_code} ({duration:.2f}s)", extra=log_data)
        
        return response
    
    @app.teardown_request
    def log_request_exception(exception):
        if exception:
            app.logger.error(f"Request failed: {str(exception)}", exc_info=exception)
            
            # Log to Sentry if available
            if SENTRY_AVAILABLE and sentry_sdk.Hub.current.client:
                sentry_sdk.capture_exception(exception)