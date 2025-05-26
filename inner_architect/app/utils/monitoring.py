"""
Monitoring utilities for InnerArchitect.

This module provides utilities for monitoring application health, API usage,
and performance metrics.
"""
import time
import logging
import threading
import functools
from typing import Dict, Any, List, Optional, Callable, Tuple
from collections import deque, defaultdict
from datetime import datetime, timedelta

# Setup logger
logger = logging.getLogger('inner_architect.monitoring')

# Singleton class for metrics collection
class MetricsCollector:
    """
    Singleton class for collecting and reporting application metrics.
    Tracks API call performance, error rates, and resource usage.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MetricsCollector, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if self._initialized:
            return
            
        # Initialize metrics storage
        self._api_calls = deque(maxlen=1000)  # Store last 1000 API calls
        self._errors = deque(maxlen=500)  # Store last 500 errors
        self._api_response_times = defaultdict(lambda: deque(maxlen=100))  # Store last 100 response times per endpoint
        
        # Provider availability tracking
        self._provider_availability = {
            'claude': {
                'available': True,
                'last_check': datetime.now(),
                'success_count': 0,
                'failure_count': 0,
                'response_times': deque(maxlen=100)
            },
            'openai': {
                'available': True,
                'last_check': datetime.now(),
                'success_count': 0,
                'failure_count': 0,
                'response_times': deque(maxlen=100)
            }
        }
        
        # Performance metrics
        self._memory_usage = deque(maxlen=100)  # Store last 100 memory usage measurements
        self._cpu_usage = deque(maxlen=100)  # Store last 100 CPU usage measurements
        
        # Start background monitoring thread
        self._stop_thread = threading.Event()
        self._monitoring_thread = threading.Thread(target=self._collect_system_metrics)
        self._monitoring_thread.daemon = True
        self._monitoring_thread.start()
        
        self._initialized = True
        logger.info("Metrics collector initialized")
    
    def __del__(self):
        # Stop background thread on shutdown
        if hasattr(self, '_stop_thread'):
            self._stop_thread.set()
            if hasattr(self, '_monitoring_thread') and self._monitoring_thread.is_alive():
                self._monitoring_thread.join(timeout=1)
    
    def _collect_system_metrics(self):
        """Background thread to collect system metrics periodically."""
        try:
            import psutil
        except ImportError:
            logger.warning("psutil not installed, system metrics collection disabled")
            return
            
        while not self._stop_thread.is_set():
            try:
                # Collect memory usage
                memory = psutil.virtual_memory()
                self._memory_usage.append({
                    'timestamp': datetime.now(),
                    'percent': memory.percent,
                    'used': memory.used,
                    'total': memory.total
                })
                
                # Collect CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self._cpu_usage.append({
                    'timestamp': datetime.now(),
                    'percent': cpu_percent
                })
                
                # Sleep for 15 seconds before next collection
                self._stop_thread.wait(15)
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
                self._stop_thread.wait(30)  # Longer wait on error
    
    def record_api_call(self, provider: str, endpoint: str, duration: float, success: bool, 
                       error: Optional[Exception] = None, **kwargs) -> None:
        """
        Record an API call for metrics tracking.
        
        Args:
            provider: API provider name (e.g., 'claude', 'openai')
            endpoint: API endpoint called
            duration: Duration of the call in seconds
            success: Whether the call was successful
            error: Error if the call failed
            **kwargs: Additional metadata about the call
        """
        timestamp = datetime.now()
        
        # Record the API call
        call_record = {
            'timestamp': timestamp,
            'provider': provider,
            'endpoint': endpoint,
            'duration': duration,
            'success': success,
            'error': str(error) if error else None,
            'metadata': kwargs
        }
        self._api_calls.append(call_record)
        
        # Update provider availability metrics
        if provider in self._provider_availability:
            provider_metrics = self._provider_availability[provider]
            provider_metrics['last_check'] = timestamp
            
            if success:
                provider_metrics['success_count'] += 1
                provider_metrics['response_times'].append(duration)
            else:
                provider_metrics['failure_count'] += 1
                provider_metrics['available'] = provider_metrics['failure_count'] < 3  # Mark as unavailable after 3 consecutive failures
                
                # Record error
                error_record = {
                    'timestamp': timestamp,
                    'provider': provider,
                    'endpoint': endpoint,
                    'error': str(error) if error else 'Unknown error',
                    'error_type': type(error).__name__ if error else 'Unknown',
                    'metadata': kwargs
                }
                self._errors.append(error_record)
        
        # Record response time for this endpoint
        endpoint_key = f"{provider}_{endpoint}"
        self._api_response_times[endpoint_key].append(duration)
    
    def record_error(self, source: str, error: Exception, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Record an application error for metrics tracking.
        
        Args:
            source: Source of the error (e.g., module name)
            error: The exception that occurred
            metadata: Additional metadata about the error
        """
        error_record = {
            'timestamp': datetime.now(),
            'source': source,
            'error': str(error),
            'error_type': type(error).__name__,
            'metadata': metadata or {}
        }
        self._errors.append(error_record)
    
    def get_api_metrics(self, time_range: Optional[timedelta] = None) -> Dict[str, Any]:
        """
        Get API call metrics for the specified time range.
        
        Args:
            time_range: Time range to get metrics for (defaults to all available data)
            
        Returns:
            Dictionary with API metrics
        """
        # Filter API calls by time range if specified
        if time_range:
            start_time = datetime.now() - time_range
            api_calls = [call for call in self._api_calls if call['timestamp'] >= start_time]
        else:
            api_calls = list(self._api_calls)
        
        # Calculate metrics
        total_calls = len(api_calls)
        successful_calls = sum(1 for call in api_calls if call['success'])
        failed_calls = total_calls - successful_calls
        
        # Success rate
        success_rate = (successful_calls / total_calls) * 100 if total_calls > 0 else 0
        
        # Average response time overall
        avg_response_time = sum(call['duration'] for call in api_calls) / total_calls if total_calls > 0 else 0
        
        # Response times by provider
        provider_metrics = defaultdict(lambda: {'calls': 0, 'successful': 0, 'failed': 0, 'total_time': 0})
        
        for call in api_calls:
            provider = call['provider']
            provider_metrics[provider]['calls'] += 1
            if call['success']:
                provider_metrics[provider]['successful'] += 1
            else:
                provider_metrics[provider]['failed'] += 1
            provider_metrics[provider]['total_time'] += call['duration']
        
        # Calculate average response times and success rates by provider
        for provider, metrics in provider_metrics.items():
            metrics['avg_response_time'] = metrics['total_time'] / metrics['calls'] if metrics['calls'] > 0 else 0
            metrics['success_rate'] = (metrics['successful'] / metrics['calls']) * 100 if metrics['calls'] > 0 else 0
        
        # Response times by endpoint
        endpoint_metrics = defaultdict(lambda: {'calls': 0, 'successful': 0, 'failed': 0, 'total_time': 0})
        
        for call in api_calls:
            endpoint = call['endpoint']
            endpoint_metrics[endpoint]['calls'] += 1
            if call['success']:
                endpoint_metrics[endpoint]['successful'] += 1
            else:
                endpoint_metrics[endpoint]['failed'] += 1
            endpoint_metrics[endpoint]['total_time'] += call['duration']
        
        # Calculate average response times and success rates by endpoint
        for endpoint, metrics in endpoint_metrics.items():
            metrics['avg_response_time'] = metrics['total_time'] / metrics['calls'] if metrics['calls'] > 0 else 0
            metrics['success_rate'] = (metrics['successful'] / metrics['calls']) * 100 if metrics['calls'] > 0 else 0
        
        return {
            'total_calls': total_calls,
            'successful_calls': successful_calls,
            'failed_calls': failed_calls,
            'success_rate': success_rate,
            'avg_response_time': avg_response_time,
            'provider_metrics': dict(provider_metrics),
            'endpoint_metrics': dict(endpoint_metrics),
            'time_range': str(time_range) if time_range else 'all'
        }
    
    def get_error_metrics(self, time_range: Optional[timedelta] = None) -> Dict[str, Any]:
        """
        Get error metrics for the specified time range.
        
        Args:
            time_range: Time range to get metrics for (defaults to all available data)
            
        Returns:
            Dictionary with error metrics
        """
        # Filter errors by time range if specified
        if time_range:
            start_time = datetime.now() - time_range
            errors = [error for error in self._errors if error['timestamp'] >= start_time]
        else:
            errors = list(self._errors)
        
        # Calculate metrics
        total_errors = len(errors)
        
        # Errors by source
        source_counts = defaultdict(int)
        for error in errors:
            source_counts[error.get('source', 'unknown')] += 1
        
        # Errors by type
        type_counts = defaultdict(int)
        for error in errors:
            type_counts[error.get('error_type', 'unknown')] += 1
        
        # Errors by provider (for API errors)
        provider_counts = defaultdict(int)
        for error in errors:
            if 'provider' in error:
                provider_counts[error['provider']] += 1
        
        return {
            'total_errors': total_errors,
            'errors_by_source': dict(source_counts),
            'errors_by_type': dict(type_counts),
            'errors_by_provider': dict(provider_counts),
            'recent_errors': [error for error in list(errors)[-10:]],  # Last 10 errors
            'time_range': str(time_range) if time_range else 'all'
        }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get system resource usage metrics.
        
        Returns:
            Dictionary with system metrics
        """
        # Current memory usage
        current_memory = self._memory_usage[-1] if self._memory_usage else {
            'timestamp': datetime.now(),
            'percent': 0,
            'used': 0,
            'total': 0
        }
        
        # Current CPU usage
        current_cpu = self._cpu_usage[-1] if self._cpu_usage else {
            'timestamp': datetime.now(),
            'percent': 0
        }
        
        # Memory usage over time
        memory_history = [
            {'timestamp': m['timestamp'].strftime('%H:%M:%S'), 'percent': m['percent']}
            for m in list(self._memory_usage)[-20:]  # Last 20 readings
        ]
        
        # CPU usage over time
        cpu_history = [
            {'timestamp': c['timestamp'].strftime('%H:%M:%S'), 'percent': c['percent']}
            for c in list(self._cpu_usage)[-20:]  # Last 20 readings
        ]
        
        return {
            'current_memory': current_memory,
            'current_cpu': current_cpu,
            'memory_history': memory_history,
            'cpu_history': cpu_history
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall application health status.
        
        Returns:
            Dictionary with health status indicators
        """
        # Check API provider availability
        providers_available = all(p['available'] for p in self._provider_availability.values())
        
        # Check recent error rate (last 5 minutes)
        recent_api_calls = [
            call for call in self._api_calls 
            if call['timestamp'] >= datetime.now() - timedelta(minutes=5)
        ]
        
        total_recent_calls = len(recent_api_calls)
        recent_success_rate = (
            sum(1 for call in recent_api_calls if call['success']) / total_recent_calls * 100
            if total_recent_calls > 0 else 100
        )
        
        # Check system resource usage
        system_ok = True
        if self._memory_usage and self._memory_usage[-1]['percent'] > 90:
            system_ok = False
        if self._cpu_usage and self._cpu_usage[-1]['percent'] > 90:
            system_ok = False
        
        # Overall health status
        health_status = 'healthy'
        if not providers_available:
            health_status = 'degraded'
        if recent_success_rate < 70 or not system_ok:
            health_status = 'unhealthy'
        
        return {
            'status': health_status,
            'providers_available': providers_available,
            'api_success_rate': recent_success_rate,
            'system_ok': system_ok,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'uptime': None,  # Would come from app.config in a real implementation
            'version': '0.1.0'  # Would come from app.config in a real implementation
        }

# Create singleton instance
metrics_collector = MetricsCollector()

def track_api_call(f):
    """
    Decorator to track API calls and record metrics.
    
    Args:
        f: Function to decorate
        
    Returns:
        Decorated function
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        provider = kwargs.get('provider', 'unknown')
        endpoint = f.__name__
        
        start_time = time.time()
        success = False
        error = None
        
        try:
            result = f(*args, **kwargs)
            success = True
            return result
        except Exception as e:
            error = e
            raise
        finally:
            duration = time.time() - start_time
            metrics_collector.record_api_call(
                provider=provider,
                endpoint=endpoint,
                duration=duration,
                success=success,
                error=error,
                args_count=len(args),
                kwargs_keys=list(kwargs.keys())
            )
    
    return wrapper

def health_check() -> Dict[str, Any]:
    """
    Perform a health check of the application.
    
    Returns:
        Dictionary with health status information
    """
    return metrics_collector.get_health_status()

def get_api_metrics(hours: int = 24) -> Dict[str, Any]:
    """
    Get API metrics for the specified time range.
    
    Args:
        hours: Number of hours to get metrics for
        
    Returns:
        Dictionary with API metrics
    """
    return metrics_collector.get_api_metrics(timedelta(hours=hours))

def get_error_metrics(hours: int = 24) -> Dict[str, Any]:
    """
    Get error metrics for the specified time range.
    
    Args:
        hours: Number of hours to get metrics for
        
    Returns:
        Dictionary with error metrics
    """
    return metrics_collector.get_error_metrics(timedelta(hours=hours))

def get_system_metrics() -> Dict[str, Any]:
    """
    Get system resource usage metrics.
    
    Returns:
        Dictionary with system metrics
    """
    return metrics_collector.get_system_metrics()