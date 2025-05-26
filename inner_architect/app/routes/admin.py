"""
Admin routes for InnerArchitect.

This module provides routes for administrative functions, including error monitoring,
log viewing, and API status monitoring.
"""
import os
import json
import csv
import logging
import datetime
from io import StringIO
from functools import wraps
from collections import defaultdict
from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    jsonify, current_app, send_file, abort, Response
)
from flask_login import login_required, current_user

from ..services.ai_client_factory import ai_client_factory
from ..utils.logging_setup import get_logger

# Create admin blueprint
admin = Blueprint('admin', __name__, url_prefix='/admin')

# Get logger
logger = get_logger('admin')

def admin_required(f):
    """
    Decorator to require admin privileges for a route.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/')
@login_required
@admin_required
def index():
    """Admin dashboard index page."""
    return redirect(url_for('admin.error_dashboard'))

@admin.route('/error-dashboard')
@login_required
@admin_required
def error_dashboard():
    """Error monitoring dashboard."""
    # Get time range from request args
    time_range = request.args.get('time_range', '24h')
    
    # Convert time range to timedelta
    if time_range == '1h':
        delta = datetime.timedelta(hours=1)
        time_label = 'Last hour'
    elif time_range == '6h':
        delta = datetime.timedelta(hours=6)
        time_label = 'Last 6 hours'
    elif time_range == '7d':
        delta = datetime.timedelta(days=7)
        time_label = 'Last 7 days'
    elif time_range == '30d':
        delta = datetime.timedelta(days=30)
        time_label = 'Last 30 days'
    else:  # Default to 24h
        delta = datetime.timedelta(days=1)
        time_label = 'Last 24 hours'
    
    # Calculate start time
    start_time = datetime.datetime.now() - delta
    
    # In a real implementation, we would load actual log data from the database
    # For demo purposes, we'll create sample data
    error_logs = _get_sample_logs(10, start_time, 'ERROR')
    
    # Calculate metrics
    error_count = len(error_logs)
    api_error_count = sum(1 for log in error_logs if 'api' in log.get('source', '').lower())
    
    # Provider status
    provider_status = {
        'claude': {
            'available': ai_client_factory.providers.get('claude', {}).get('available', False),
            'success_rate': '98.2%',
            'avg_response_time': '245 ms',
            'failed_calls': 5,
            'last_failure': '2h ago'
        },
        'openai': {
            'available': ai_client_factory.providers.get('openai', {}).get('available', False),
            'success_rate': '99.5%',
            'avg_response_time': '180 ms',
            'failed_calls': 2,
            'last_failure': '4h ago'
        }
    }
    
    # API performance data (for chart)
    api_performance_data = {
        'labels': ['00:00', '06:00', '12:00', '18:00', '00:00'],
        'claude': [230, 245, 280, 260, 240],
        'openai': [170, 185, 210, 195, 180]
    }
    
    # Error distribution (for chart)
    error_distribution = [25, 15, 40, 10, 10]  # Timeout, Connection, Response, Server, Authentication
    
    return render_template(
        'admin/error_dashboard.html',
        time_range=time_label,
        error_logs=error_logs,
        error_count=error_count,
        api_error_count=api_error_count,
        error_count_change=+12,  # Simulated increase from previous period
        api_error_count_change=-5,  # Simulated decrease from previous period
        avg_response_time='210 ms',
        avg_response_time_change=+3,
        availability='98.8%',
        availability_change=-0.5,
        provider_status=provider_status,
        api_performance_data=api_performance_data,
        error_distribution=error_distribution
    )

@admin.route('/error-logs')
@login_required
@admin_required
def error_logs():
    """Detailed error logs view with filtering."""
    # Get time range from request args
    time_range = request.args.get('time_range', '24h')
    
    # Convert time range to timedelta
    if time_range == '1h':
        delta = datetime.timedelta(hours=1)
        time_label = 'Last hour'
    elif time_range == '6h':
        delta = datetime.timedelta(hours=6)
        time_label = 'Last 6 hours'
    elif time_range == '7d':
        delta = datetime.timedelta(days=7)
        time_label = 'Last 7 days'
    elif time_range == '30d':
        delta = datetime.timedelta(days=30)
        time_label = 'Last 30 days'
    else:  # Default to 24h
        delta = datetime.timedelta(days=1)
        time_label = 'Last 24 hours'
    
    # Calculate start time
    start_time = datetime.datetime.now() - delta
    
    # Get filter parameters
    selected_levels = request.args.getlist('level[]')
    selected_sources = request.args.getlist('source[]')
    selected_providers = request.args.getlist('provider[]')
    search_query = request.args.get('search', '')
    
    # Get pagination parameters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 25))
    
    # In a real implementation, we would load and filter actual log data from the database
    # For demo purposes, we'll create sample data
    all_logs = []
    
    # If no filters are selected, include all levels by default
    if not selected_levels:
        all_logs.extend(_get_sample_logs(20, start_time, 'ERROR'))
        all_logs.extend(_get_sample_logs(15, start_time, 'WARNING'))
        all_logs.extend(_get_sample_logs(10, start_time, 'INFO'))
        all_logs.extend(_get_sample_logs(5, start_time, 'DEBUG'))
    else:
        for level in selected_levels:
            all_logs.extend(_get_sample_logs(10, start_time, level))
    
    # Apply source filter
    if selected_sources:
        all_logs = [log for log in all_logs if any(source.lower() in log.get('source', '').lower() for source in selected_sources)]
    
    # Apply provider filter
    if selected_providers:
        all_logs = [log for log in all_logs if log.get('provider') in selected_providers]
    
    # Apply search filter
    if search_query:
        all_logs = [log for log in all_logs if search_query.lower() in log.get('message', '').lower()]
    
    # Sort logs by timestamp (newest first)
    all_logs.sort(key=lambda x: x.get('timestamp_obj', 0), reverse=True)
    
    # Calculate total pages
    total_logs = len(all_logs)
    total_pages = (total_logs + per_page - 1) // per_page
    
    # Paginate logs
    logs = all_logs[(page - 1) * per_page:page * per_page]
    
    return render_template(
        'admin/error_logs.html',
        logs=logs,
        total_logs=total_logs,
        page=page,
        pages=total_pages,
        time_range=time_label,
        selected_levels=selected_levels,
        selected_sources=selected_sources,
        selected_providers=selected_providers,
        search_query=search_query
    )

@admin.route('/export-logs')
@login_required
@admin_required
def export_logs():
    """Export logs in various formats."""
    # Get filter parameters
    time_range = request.args.get('time_range', '24h')
    selected_levels = request.args.getlist('level[]')
    selected_sources = request.args.getlist('source[]')
    selected_providers = request.args.getlist('provider[]')
    search_query = request.args.get('search', '')
    export_format = request.args.get('format', 'csv')
    
    # Convert time range to timedelta
    if time_range == '1h':
        delta = datetime.timedelta(hours=1)
    elif time_range == '6h':
        delta = datetime.timedelta(hours=6)
    elif time_range == '7d':
        delta = datetime.timedelta(days=7)
    elif time_range == '30d':
        delta = datetime.timedelta(days=30)
    else:  # Default to 24h
        delta = datetime.timedelta(days=1)
    
    # Calculate start time
    start_time = datetime.datetime.now() - delta
    
    # In a real implementation, we would load and filter actual log data from the database
    # For demo purposes, we'll create sample data
    all_logs = []
    
    # If no filters are selected, include all levels by default
    if not selected_levels:
        all_logs.extend(_get_sample_logs(20, start_time, 'ERROR'))
        all_logs.extend(_get_sample_logs(15, start_time, 'WARNING'))
        all_logs.extend(_get_sample_logs(10, start_time, 'INFO'))
        all_logs.extend(_get_sample_logs(5, start_time, 'DEBUG'))
    else:
        for level in selected_levels:
            all_logs.extend(_get_sample_logs(10, start_time, level))
    
    # Apply source filter
    if selected_sources:
        all_logs = [log for log in all_logs if any(source.lower() in log.get('source', '').lower() for source in selected_sources)]
    
    # Apply provider filter
    if selected_providers:
        all_logs = [log for log in all_logs if log.get('provider') in selected_providers]
    
    # Apply search filter
    if search_query:
        all_logs = [log for log in all_logs if search_query.lower() in log.get('message', '').lower()]
    
    # Sort logs by timestamp (newest first)
    all_logs.sort(key=lambda x: x.get('timestamp_obj', 0), reverse=True)
    
    # Export logs in requested format
    if export_format == 'csv':
        return _export_logs_csv(all_logs)
    elif export_format == 'json':
        return _export_logs_json(all_logs)
    elif export_format == 'txt':
        return _export_logs_txt(all_logs)
    else:
        abort(400, f"Unsupported export format: {export_format}")

@admin.route('/log-detail/<log_id>')
@login_required
@admin_required
def log_detail(log_id):
    """API endpoint to get detailed information about a specific log entry."""
    # In a real implementation, we would load the log details from the database
    # For demo purposes, we'll create sample data
    log_detail = {
        'id': log_id,
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'level': 'ERROR',
        'source': 'api_client.py:243',
        'message': 'API call to claude/chat_completion failed after 2 retries: Connection refused',
        'context': {
            'provider': 'claude',
            'endpoint': 'chat_completion',
            'duration': 3.245,
            'success': False,
            'error_type': 'connection',
            'retry_count': 2,
            'request_id': 'req_123456789',
            'user_id': 'user_123',
            'ip_address': '192.168.1.1'
        },
        'request': {
            'url': '/chat/message',
            'method': 'POST',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        },
        'stacktrace': """Traceback (most recent call last):
  File "/workspace/InnerArchitect/inner_architect/app/services/claude_client.py", line 243, in chat_completion
    response = self.client_factory.chat_completion(
  File "/workspace/InnerArchitect/inner_architect/app/services/ai_client_factory.py", line 312, in chat_completion
    return _chat_completion(
  File "/workspace/InnerArchitect/inner_architect/app/services/ai_client_factory.py", line 245, in _chat_completion
    response = client.messages.create(
  File "/usr/local/lib/python3.9/site-packages/anthropic/resources/messages.py", line 237, in create
    return self._post(
  File "/usr/local/lib/python3.9/site-packages/anthropic/resources/messages.py", line 45, in _post
    return make_request_with_retry(
  File "/usr/local/lib/python3.9/site-packages/anthropic/lib/api_response.py", line 124, in make_request_with_retry
    response = _make_request(
  File "/usr/local/lib/python3.9/site-packages/anthropic/lib/api_response.py", line 113, in _make_request
    response = client.session.request(
  File "/usr/local/lib/python3.9/site-packages/requests/sessions.py", line 587, in request
    resp = self.send(prep, **send_kwargs)
  File "/usr/local/lib/python3.9/site-packages/requests/sessions.py", line 701, in send
    r = adapter.send(request, **kwargs)
  File "/usr/local/lib/python3.9/site-packages/requests/adapters.py", line 547, in send
    raise ConnectionError(err, request=request)
requests.exceptions.ConnectionError: Connection refused"""
    }
    
    return jsonify(log_detail)

@admin.route('/api-provider-status')
@login_required
@admin_required
def api_provider_status():
    """API endpoint to get the current status of all API providers."""
    providers = ai_client_factory.providers.copy()
    
    # Create simplified response
    provider_status = {}
    for name, info in providers.items():
        provider_status[name] = {
            'available': info.get('available', False),
            'priority': info.get('priority', 0),
            'failure_count': info.get('failure_count', 0),
            'last_failure_time': info.get('last_failure_time', 0),
            'cooldown_period': info.get('cooldown_period', 0),
            'max_failures': info.get('max_failures', 0)
        }
    
    # Add success rates and response times (simulated)
    provider_status['claude']['success_rate'] = '98.2%'
    provider_status['claude']['avg_response_time'] = '245 ms'
    provider_status['claude']['failed_calls'] = 5
    provider_status['claude']['last_failure'] = '2h ago'
    
    provider_status['openai']['success_rate'] = '99.5%'
    provider_status['openai']['avg_response_time'] = '180 ms'
    provider_status['openai']['failed_calls'] = 2
    provider_status['openai']['last_failure'] = '4h ago'
    
    return jsonify({
        'active_provider': ai_client_factory.active_provider,
        'providers': provider_status
    })

@admin.route('/reset-provider/<provider_name>', methods=['POST'])
@login_required
@admin_required
def reset_provider(provider_name):
    """Reset a provider's failure count and availability."""
    if provider_name not in ai_client_factory.providers:
        abort(404, f"Provider not found: {provider_name}")
    
    # Reset provider status
    provider = ai_client_factory.providers[provider_name]
    provider['available'] = True
    provider['failure_count'] = 0
    provider['last_failure_time'] = 0
    
    # Re-evaluate active provider
    ai_client_factory._set_active_provider()
    
    logger.info(f"Provider {provider_name} reset by admin user {current_user.id}")
    
    return jsonify({
        'success': True,
        'message': f"Provider {provider_name} reset successfully",
        'active_provider': ai_client_factory.active_provider
    })

# Helper functions for generating sample data
def _get_sample_logs(count, start_time, level):
    """Generate sample log entries for demo purposes."""
    logs = []
    
    for i in range(count):
        # Generate random timestamp between start_time and now
        time_offset = datetime.timedelta(
            seconds=int((datetime.datetime.now() - start_time).total_seconds() * i / count)
        )
        timestamp = start_time + time_offset
        
        # Sample sources and messages based on level
        if level == 'ERROR':
            sources = ['api_client.py:243', 'ai_client_factory.py:312', 'claude_client.py:156', 'app.py:87']
            messages = [
                'API call to claude/chat_completion failed after 2 retries: Connection refused',
                'Failed to create chat completion: HTTPError 429 Too Many Requests',
                'Error processing user message: KeyError: "technique_id"',
                'Database error: IntegrityError: UNIQUE constraint failed'
            ]
            providers = ['claude', 'openai', None, None]
        elif level == 'WARNING':
            sources = ['api_client.py:187', 'api_fallback.py:75', 'subscription.py:124', 'auth.py:219']
            messages = [
                'API timeout detected, retrying (attempt 1/3)',
                'Switching to fallback provider openai due to claude availability issue',
                'User approaching API usage limit (95%)',
                'Multiple failed login attempts detected for user_456'
            ]
            providers = ['claude', 'claude', None, None]
        elif level == 'INFO':
            sources = ['app.py:42', 'api_client.py:132', 'routes.py:87', 'chat.py:156']
            messages = [
                'Application started successfully',
                'API call to claude/chat_completion succeeded in 0.87s',
                'User user_123 logged in successfully',
                'New conversation created: conv_789'
            ]
            providers = [None, 'claude', None, None]
        else:  # DEBUG
            sources = ['app.py:138', 'utils.py:45', 'models.py:87', 'services.py:129']
            messages = [
                'Loading configuration from environment',
                'Processing technique selection for message',
                'User preferences updated: {"theme": "dark"}',
                'Cache hit for conversation context'
            ]
            providers = [None, None, None, None]
        
        # Create log entry
        log = {
            'id': f"log_{i}_{level.lower()}",
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'timestamp_obj': timestamp,
            'level': level,
            'source': sources[i % len(sources)],
            'message': messages[i % len(messages)],
            'user_id': f"user_{i % 5 + 1}",
            'provider': providers[i % len(providers)]
        }
        
        logs.append(log)
    
    return logs

def _export_logs_csv(logs):
    """Export logs in CSV format."""
    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Timestamp', 'Level', 'Source', 'Message', 'User ID', 'Provider'])
    
    # Write data
    for log in logs:
        writer.writerow([
            log.get('timestamp', ''),
            log.get('level', ''),
            log.get('source', ''),
            log.get('message', ''),
            log.get('user_id', ''),
            log.get('provider', '')
        ])
    
    # Prepare response
    output.seek(0)
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=inner_architect_logs_{timestamp}.csv'
        }
    )

def _export_logs_json(logs):
    """Export logs in JSON format."""
    # Clean logs for JSON export (remove non-serializable objects)
    clean_logs = []
    for log in logs:
        clean_log = log.copy()
        clean_log.pop('timestamp_obj', None)
        clean_logs.append(clean_log)
    
    # Prepare response
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    return Response(
        json.dumps(clean_logs, indent=2),
        mimetype='application/json',
        headers={
            'Content-Disposition': f'attachment; filename=inner_architect_logs_{timestamp}.json'
        }
    )

def _export_logs_txt(logs):
    """Export logs in plain text format."""
    # Create text file in memory
    output = StringIO()
    
    # Write logs
    for log in logs:
        output.write(f"[{log.get('timestamp', '')}] {log.get('level', '')} in {log.get('source', '')}: {log.get('message', '')}\n")
        if log.get('user_id'):
            output.write(f"  User: {log.get('user_id')}\n")
        if log.get('provider'):
            output.write(f"  Provider: {log.get('provider')}\n")
        output.write("\n")
    
    # Prepare response
    output.seek(0)
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    return Response(
        output.getvalue(),
        mimetype='text/plain',
        headers={
            'Content-Disposition': f'attachment; filename=inner_architect_logs_{timestamp}.txt'
        }
    )