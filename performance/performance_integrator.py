#!/usr/bin/env python
"""
Performance Optimization Integrator for Inner Architect

This module provides the main integration point between the Performance Optimization
Suite and the Inner Architect application. It handles the integration of all performance
components with the Flask application.
"""

import logging
import importlib
import os
import sys
from typing import Dict, Any, Optional, List, Set, Tuple, Union

from flask import Flask, request, g, current_app
import time

# Configure logging
logger = logging.getLogger("performance.integrator")


class PerformanceIntegrator:
    """Central integration point for all performance optimization components."""
    
    def __init__(
        self,
        app: Optional[Flask] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the performance integrator.
        
        Args:
            app: Flask application instance
            config: Configuration dictionary
        """
        self.config = config or {}
        self.components = []
        self._initialized = False
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask) -> None:
        """
        Initialize with a Flask application.
        
        Args:
            app: Flask application instance
        """
        if self._initialized:
            logger.warning("Performance integrator already initialized")
            return
        
        # Initialize performance suite
        self._init_performance_suite(app)
        
        # Register performance middleware
        self._register_performance_middleware(app)
        
        # Register CLI commands
        self._register_cli_commands(app)
        
        # Register performance API endpoints
        self._register_api_endpoints(app)
        
        # Store integrator in app extensions
        app.extensions["performance_integrator"] = self
        
        self._initialized = True
        logger.info("Performance integrator initialized")
    
    def _init_performance_suite(self, app: Flask) -> None:
        """
        Initialize the performance optimization suite.
        
        Args:
            app: Flask application instance
        """
        # Import here to avoid circular imports
        from performance.integration import init_performance
        
        # Initialize the performance suite
        performance_suite = init_performance(app, self.config)
        self.components.append(("performance_suite", performance_suite))
        
        logger.info("Performance suite initialized")
    
    def _register_performance_middleware(self, app: Flask) -> None:
        """
        Register performance middleware with the Flask app.
        
        Args:
            app: Flask application instance
        """
        # Add request timing middleware
        @app.before_request
        def before_request():
            # Store start time for request timing
            request.start_time = time.time()
            
            # Store original path for tracking
            request.original_path = request.path
        
        # Add response timing middleware
        @app.after_request
        def after_request(response):
            # Calculate request duration
            if hasattr(request, 'start_time'):
                duration = time.time() - request.start_time
                
                # Log slow requests
                if duration > app.config.get('PERF_SLOW_REQUEST_THRESHOLD', 0.5):
                    logger.warning(
                        f"Slow request: {request.method} {request.original_path} "
                        f"({duration:.3f}s)"
                    )
                
                # Add timing header if enabled
                if app.config.get('PERF_ADD_TIMING_HEADERS', True):
                    response.headers['X-Request-Time'] = f"{duration:.3f}"
            
            return response
        
        logger.info("Performance middleware registered")
    
    def _register_cli_commands(self, app: Flask) -> None:
        """
        Register performance CLI commands with the Flask app.
        
        Args:
            app: Flask application instance
        """
        @app.cli.group('perf')
        def perf_cli():
            """Performance optimization commands."""
            pass
        
        @perf_cli.command('optimize')
        def optimize_cmd():
            """Run asset optimization."""
            from flask import current_app
            suite = current_app.extensions.get('performance_suite')
            if suite:
                suite.optimize_assets()
                print("Asset optimization completed")
            else:
                print("Performance suite not initialized")
        
        @perf_cli.command('clear-caches')
        def clear_caches_cmd():
            """Clear all caches."""
            from flask import current_app
            suite = current_app.extensions.get('performance_suite')
            if suite:
                suite.clear_caches()
                print("Caches cleared")
            else:
                print("Performance suite not initialized")
        
        logger.info("Performance CLI commands registered")
    
    def _register_api_endpoints(self, app: Flask) -> None:
        """
        Register performance API endpoints with the Flask app.
        
        Args:
            app: Flask application instance
        """
        # Import here to avoid circular imports
        from flask import jsonify
        
        @app.route('/api/performance/client', methods=['POST'])
        def client_performance():
            """Handle client-side performance metrics."""
            # Get performance monitor
            performance_monitor = None
            if hasattr(app, 'extensions') and 'performance_monitor' in app.extensions:
                performance_monitor = app.extensions['performance_monitor']
            
            if not performance_monitor:
                return jsonify({'error': 'Performance monitoring not enabled'}), 501
            
            # Record client metrics
            try:
                metrics = request.json
                performance_monitor.record_client_metrics(metrics)
                return jsonify({'success': True})
            except Exception as e:
                logger.error(f"Error recording client metrics: {str(e)}")
                return jsonify({'error': str(e)}), 500
        
        # Add endpoints for monitoring data
        if app.config.get('PERF_API_ENDPOINTS', True):
            self._register_monitoring_endpoints(app)
        
        logger.info("Performance API endpoints registered")
    
    def _register_monitoring_endpoints(self, app: Flask) -> None:
        """
        Register monitoring data endpoints.
        
        Args:
            app: Flask application instance
        """
        # Import here to avoid circular imports
        from flask import jsonify
        
        # Monitoring data endpoints
        @app.route('/api/performance/requests')
        def api_performance_requests():
            """Get request performance data."""
            # Check if user has admin permission
            if not self._check_admin_permission():
                return jsonify({'error': 'Unauthorized'}), 403
            
            # Get performance monitor
            if 'performance_monitor' in app.extensions:
                perf_monitor = app.extensions['performance_monitor']
                data = perf_monitor.get_request_metrics()
                return jsonify(data)
            
            return jsonify({'error': 'Performance monitoring not enabled'}), 501
        
        @app.route('/api/performance/memory')
        def api_performance_memory():
            """Get memory usage data."""
            # Check if user has admin permission
            if not self._check_admin_permission():
                return jsonify({'error': 'Unauthorized'}), 403
            
            # Get memory profiler
            if 'memory_profiler' in app.extensions:
                memory_profiler = app.extensions['memory_profiler']
                data = memory_profiler.get_memory_metrics()
                return jsonify(data)
            
            return jsonify({'error': 'Memory profiling not enabled'}), 501
        
        @app.route('/api/performance/queries')
        def api_performance_queries():
            """Get query performance data."""
            # Check if user has admin permission
            if not self._check_admin_permission():
                return jsonify({'error': 'Unauthorized'}), 403
            
            # Get query cache
            if 'query_cache' in app.extensions:
                query_cache = app.extensions['query_cache']
                data = query_cache.get_query_metrics()
                return jsonify(data)
            
            return jsonify({'error': 'Query caching not enabled'}), 501
        
        @app.route('/api/performance/system')
        def api_performance_system():
            """Get system performance data."""
            # Check if user has admin permission
            if not self._check_admin_permission():
                return jsonify({'error': 'Unauthorized'}), 403
            
            # Get performance monitor
            if 'performance_monitor' in app.extensions:
                perf_monitor = app.extensions['performance_monitor']
                data = perf_monitor.get_system_metrics()
                return jsonify(data)
            
            return jsonify({'error': 'Performance monitoring not enabled'}), 501
    
    def _check_admin_permission(self) -> bool:
        """
        Check if the current user has admin permission.
        
        Returns:
            True if user has permission, False otherwise
        """
        # Check if testing
        if current_app.config.get('TESTING', False):
            return True
        
        # Check if user is authenticated and has admin role
        if hasattr(g, 'user') and hasattr(g.user, 'is_admin'):
            return g.user.is_admin
        
        return False


def initialize_performance(app: Flask, config: Optional[Dict[str, Any]] = None) -> PerformanceIntegrator:
    """
    Initialize all performance optimization components with the Flask app.
    
    This is the main entry point for integrating performance optimization with
    the Inner Architect application.
    
    Args:
        app: Flask application instance
        config: Configuration dictionary
        
    Returns:
        Configured performance integrator instance
    """
    # Set default configuration
    app.config.setdefault('PERF_ENABLED', True)
    app.config.setdefault('PERF_SLOW_REQUEST_THRESHOLD', 0.5)
    app.config.setdefault('PERF_ADD_TIMING_HEADERS', True)
    app.config.setdefault('PERF_API_ENDPOINTS', True)
    
    # Skip initialization if performance is disabled
    if not app.config.get('PERF_ENABLED'):
        logger.info("Performance optimization disabled")
        return None
    
    # Create and initialize integrator
    integrator = PerformanceIntegrator(app, config)
    
    return integrator


def check_performance_dependencies() -> Tuple[bool, List[str]]:
    """
    Check if all performance optimization dependencies are installed.
    
    Returns:
        Tuple of (all_installed, missing_packages)
    """
    required_packages = [
        'redis',         # For Redis cache backend
        'pymemcache',    # For Memcached cache backend
        'psutil',        # For system resource monitoring
        'cssmin',        # For CSS minification
        'jsmin',         # For JavaScript minification
        'pillow',        # For image optimization
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
        except ImportError:
            missing_packages.append(package)
    
    return len(missing_packages) == 0, missing_packages


if __name__ == "__main__":
    # Example usage
    print("This module provides integration for the Performance Optimization Suite.")
    print("Example usage:")
    print("")
    print("  from performance.performance_integrator import initialize_performance")
    print("")
    print("  # Initialize with Flask app")
    print("  initialize_performance(app)")