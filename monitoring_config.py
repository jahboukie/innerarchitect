#!/usr/bin/env python
"""
Configuration for application monitoring and alerting.
This helps track application health, errors, and performance.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from logging_config import get_logger, info, error, warning

# Initialize logger
logger = get_logger("monitoring")

# Health check configuration
HEALTH_CHECK_ENDPOINTS = {
    "api": "/api/health",
    "database": "/api/health/db",
    "auth": "/api/health/auth",
    "stripe": "/api/health/stripe",
}

# Alerting thresholds
ALERT_THRESHOLDS = {
    "api_error_rate": 0.05,  # 5% error rate
    "response_time_ms": 2000,  # 2 seconds
    "database_connection_errors": 5,  # 5 consecutive failures
    "memory_usage_percent": 85,  # 85% memory usage
    "disk_usage_percent": 80,  # 80% disk usage
    "concurrent_users": 100,  # Alert if more than 100 concurrent users
}

# Metrics to collect
METRICS = [
    "requests_per_minute",
    "average_response_time",
    "error_rate",
    "database_query_time",
    "active_users",
    "memory_usage",
    "disk_usage",
    "api_calls_by_endpoint",
    "login_success_rate",
    "subscription_conversion_rate",
]

# Performance monitoring
SLOW_QUERY_THRESHOLD_MS = 500  # Log queries taking longer than 500ms
SLOW_REQUEST_THRESHOLD_MS = 1000  # Log requests taking longer than 1s

class HealthStatus:
    """Represents the health status of a component."""
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

def check_database_health() -> Tuple[str, str]:
    """
    Check the health of the database connection.
    
    Returns:
        Tuple of (status, message) where status is one of HealthStatus values
    """
    from app import db
    try:
        # Execute a simple query to check database connectivity
        result = db.session.execute("SELECT 1").scalar()
        
        if result == 1:
            return HealthStatus.OK, "Database connection is healthy"
        else:
            return HealthStatus.WARNING, "Database returned unexpected result"
    except Exception as e:
        error(f"Database health check failed: {str(e)}")
        return HealthStatus.CRITICAL, f"Database connection failed: {str(e)}"

def check_api_health() -> Dict[str, Any]:
    """
    Check the health of external API dependencies (OpenAI, Stripe, SendGrid).
    
    Returns:
        Dictionary with health status for each API
    """
    results = {}
    
    # Check OpenAI API
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            # Simple model list call to check API access
            models = client.models.list()
            results["openai"] = {
                "status": HealthStatus.OK,
                "message": "OpenAI API connection successful"
            }
        except Exception as e:
            error(f"OpenAI API health check failed: {str(e)}")
            results["openai"] = {
                "status": HealthStatus.CRITICAL,
                "message": f"OpenAI API error: {str(e)}"
            }
    else:
        results["openai"] = {
            "status": HealthStatus.UNKNOWN,
            "message": "OpenAI API key not configured"
        }
    
    # Check Stripe API
    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    if stripe_key:
        try:
            import stripe
            stripe.api_key = stripe_key
            # Simple API call to check connectivity
            stripe.Balance.retrieve()
            results["stripe"] = {
                "status": HealthStatus.OK,
                "message": "Stripe API connection successful"
            }
        except Exception as e:
            error(f"Stripe API health check failed: {str(e)}")
            results["stripe"] = {
                "status": HealthStatus.CRITICAL,
                "message": f"Stripe API error: {str(e)}"
            }
    else:
        results["stripe"] = {
            "status": HealthStatus.UNKNOWN,
            "message": "Stripe API key not configured"
        }
    
    # Check SendGrid API
    sendgrid_key = os.environ.get("SENDGRID_API_KEY")
    if sendgrid_key:
        try:
            from sendgrid import SendGridAPIClient
            sg = SendGridAPIClient(sendgrid_key)
            # Check API key validity
            response = sg.client.api_keys._(sendgrid_key).get()
            if response.status_code == 200:
                results["sendgrid"] = {
                    "status": HealthStatus.OK,
                    "message": "SendGrid API connection successful"
                }
            else:
                results["sendgrid"] = {
                    "status": HealthStatus.WARNING,
                    "message": f"SendGrid API returned status {response.status_code}"
                }
        except Exception as e:
            error(f"SendGrid API health check failed: {str(e)}")
            results["sendgrid"] = {
                "status": HealthStatus.CRITICAL,
                "message": f"SendGrid API error: {str(e)}"
            }
    else:
        results["sendgrid"] = {
            "status": HealthStatus.UNKNOWN,
            "message": "SendGrid API key not configured"
        }
    
    return results

def check_auth_services() -> Dict[str, Any]:
    """
    Check the health of authentication services.
    
    Returns:
        Dictionary with health status for auth services
    """
    results = {}
    
    # Check Replit Auth
    try:
        repl_id = os.environ.get("REPL_ID")
        if repl_id:
            results["replit_auth"] = {
                "status": HealthStatus.OK,
                "message": "Replit Auth configuration found"
            }
        else:
            results["replit_auth"] = {
                "status": HealthStatus.WARNING,
                "message": "REPL_ID not configured, Replit Auth may not work"
            }
    except Exception as e:
        error(f"Replit Auth health check failed: {str(e)}")
        results["replit_auth"] = {
            "status": HealthStatus.WARNING,
            "message": f"Replit Auth check error: {str(e)}"
        }
    
    # Check Email verification capability
    if os.environ.get("SENDGRID_API_KEY"):
        results["email_auth"] = {
            "status": HealthStatus.OK,
            "message": "Email authentication configuration found"
        }
    else:
        results["email_auth"] = {
            "status": HealthStatus.WARNING,
            "message": "SendGrid API key missing, email verification won't work"
        }
    
    return results

def collect_system_metrics() -> Dict[str, Any]:
    """
    Collect system-level metrics.
    
    Returns:
        Dictionary of system metrics
    """
    import psutil
    
    metrics = {}
    
    # Memory usage
    memory = psutil.virtual_memory()
    metrics["memory_total_mb"] = memory.total / (1024 * 1024)
    metrics["memory_available_mb"] = memory.available / (1024 * 1024)
    metrics["memory_used_percent"] = memory.percent
    
    # CPU usage
    metrics["cpu_percent"] = psutil.cpu_percent(interval=1)
    
    # Disk usage
    disk = psutil.disk_usage('/')
    metrics["disk_total_gb"] = disk.total / (1024 * 1024 * 1024)
    metrics["disk_free_gb"] = disk.free / (1024 * 1024 * 1024)
    metrics["disk_used_percent"] = disk.percent
    
    # Network IO
    net_io = psutil.net_io_counters()
    metrics["net_bytes_sent"] = net_io.bytes_sent
    metrics["net_bytes_recv"] = net_io.bytes_recv
    
    return metrics

def get_overall_health() -> Dict[str, Any]:
    """
    Get a complete health check of all system components.
    
    Returns:
        Dictionary with health status for all monitored components
    """
    db_status, db_message = check_database_health()
    api_health = check_api_health()
    auth_health = check_auth_services()
    system_metrics = collect_system_metrics()
    
    # Determine overall status based on component status
    if db_status == HealthStatus.CRITICAL or HealthStatus.CRITICAL in [
        api_health.get("openai", {}).get("status"),
        api_health.get("stripe", {}).get("status")
    ]:
        overall_status = HealthStatus.CRITICAL
    elif db_status == HealthStatus.WARNING or HealthStatus.WARNING in [
        api_health.get("openai", {}).get("status"),
        api_health.get("stripe", {}).get("status"),
        auth_health.get("replit_auth", {}).get("status"),
        auth_health.get("email_auth", {}).get("status")
    ]:
        overall_status = HealthStatus.WARNING
    else:
        overall_status = HealthStatus.OK
    
    # Check if any metrics exceed alert thresholds
    if system_metrics["memory_used_percent"] > ALERT_THRESHOLDS["memory_usage_percent"]:
        overall_status = HealthStatus.WARNING
        warning(f"Memory usage at {system_metrics['memory_used_percent']}%, exceeding threshold of {ALERT_THRESHOLDS['memory_usage_percent']}%")
    
    if system_metrics["disk_used_percent"] > ALERT_THRESHOLDS["disk_usage_percent"]:
        overall_status = HealthStatus.WARNING
        warning(f"Disk usage at {system_metrics['disk_used_percent']}%, exceeding threshold of {ALERT_THRESHOLDS['disk_usage_percent']}%")
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "status": overall_status,
        "database": {
            "status": db_status,
            "message": db_message
        },
        "apis": api_health,
        "auth": auth_health,
        "system": system_metrics
    }

def setup_monitoring_endpoints(app):
    """
    Set up health check and monitoring endpoints in the Flask app.
    
    Args:
        app: Flask application instance
    """
    from flask import jsonify, request
    
    @app.route("/api/health")
    def health_check():
        """Overall health check endpoint."""
        # Simple response for basic health check
        return jsonify({"status": "ok"})
    
    @app.route("/api/health/detailed")
    def detailed_health_check():
        """Detailed health check with all components."""
        health_data = get_overall_health()
        return jsonify(health_data)
    
    @app.route("/api/health/db")
    def db_health_check():
        """Database-specific health check."""
        status, message = check_database_health()
        return jsonify({
            "status": status,
            "message": message
        })
    
    @app.route("/api/health/auth")
    def auth_health_check():
        """Authentication services health check."""
        return jsonify(check_auth_services())
    
    @app.route("/api/health/apis")
    def api_health_check():
        """External API dependencies health check."""
        return jsonify(check_api_health())
    
    @app.route("/api/health/system")
    def system_health_check():
        """System metrics health check."""
        return jsonify(collect_system_metrics())
    
    # Register before_request handler to monitor response times
    @app.before_request
    def before_request():
        request.start_time = datetime.utcnow()
    
    # Register after_request handler to log slow requests
    @app.after_request
    def after_request(response):
        if hasattr(request, 'start_time'):
            elapsed = datetime.utcnow() - request.start_time
            elapsed_ms = elapsed.total_seconds() * 1000
            
            # Log slow requests
            if elapsed_ms > SLOW_REQUEST_THRESHOLD_MS:
                warning(f"Slow request: {request.method} {request.path} took {elapsed_ms:.2f}ms")
            
            # Add timing header for debugging
            response.headers['X-Response-Time'] = f"{elapsed_ms:.2f}ms"
        
        return response

if __name__ == "__main__":
    # When run directly, perform a health check
    print("Performing health check...")
    health = get_overall_health()
    
    # Pretty print the results
    import json
    print(json.dumps(health, indent=2))