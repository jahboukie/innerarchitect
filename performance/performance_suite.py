#!/usr/bin/env python
"""
Performance Optimization Suite for Inner Architect

This module integrates all performance optimization components:
- Asset optimization (CSS/JS bundling, minification)
- Database query caching
- Memory profiling and leak detection
- Performance monitoring and metrics
- Image optimization
- Frontend code splitting
- Response compression
"""

import logging
import os
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from flask import Flask, g, request, Response, jsonify

# Import optimization components
from performance.asset_optimizer import AssetOptimizer, register_asset_helper
from performance.query_cache import setup_query_cache
from performance.memory_profiler import MemoryProfiler
from performance.performance_monitor import PerformanceMonitor

# Configure logging
logger = logging.getLogger("performance_suite")


class PerformanceOptimizationSuite:
    """Complete performance optimization suite for Flask applications."""
    
    def __init__(
        self,
        app: Optional[Flask] = None,
        config: Optional[Dict[str, Any]] = None,
        enable_asset_optimization: bool = True,
        enable_query_cache: bool = True,
        enable_memory_profiling: bool = True,
        enable_performance_monitoring: bool = True,
        enable_response_compression: bool = True,
        enable_frontend_optimization: bool = True
    ):
        """
        Initialize performance suite.
        
        Args:
            app: Flask application instance
            config: Configuration dictionary
            enable_asset_optimization: Whether to enable asset optimization
            enable_query_cache: Whether to enable database query caching
            enable_memory_profiling: Whether to enable memory profiling
            enable_performance_monitoring: Whether to enable performance monitoring
            enable_response_compression: Whether to enable response compression
            enable_frontend_optimization: Whether to enable frontend optimization
        """
        self.config = config or {}
        self.enable_asset_optimization = enable_asset_optimization
        self.enable_query_cache = enable_query_cache
        self.enable_memory_profiling = enable_memory_profiling
        self.enable_performance_monitoring = enable_performance_monitoring
        self.enable_response_compression = enable_response_compression
        self.enable_frontend_optimization = enable_frontend_optimization
        
        # Initialize components
        self.asset_optimizer = None
        self.query_cache = None
        self.memory_profiler = None
        self.performance_monitor = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask) -> None:
        """
        Initialize with a Flask application.
        
        Args:
            app: Flask application instance
        """
        # Configure from app config
        self._configure_from_app(app)
        
        # Register extension with Flask
        app.extensions["performance_suite"] = self
        
        # Initialize components
        self._init_components(app)
        
        # Set up frontend optimization
        if self.enable_frontend_optimization:
            self._setup_frontend_optimization(app)
        
        # Set up response compression
        if self.enable_response_compression:
            self._setup_response_compression(app)
        
        # Register suite route
        self._register_suite_endpoint(app)
        
        logger.info("Performance Optimization Suite initialized")
    
    def _configure_from_app(self, app: Flask) -> None:
        """
        Configure suite from Flask application config.
        
        Args:
            app: Flask application instance
        """
        # Read configuration from app config
        if app.config.get("PERF_ASSET_OPTIMIZATION") is not None:
            self.enable_asset_optimization = app.config.get("PERF_ASSET_OPTIMIZATION")
        
        if app.config.get("PERF_QUERY_CACHE") is not None:
            self.enable_query_cache = app.config.get("PERF_QUERY_CACHE")
        
        if app.config.get("PERF_MEMORY_PROFILING") is not None:
            self.enable_memory_profiling = app.config.get("PERF_MEMORY_PROFILING")
        
        if app.config.get("PERF_MONITORING") is not None:
            self.enable_performance_monitoring = app.config.get("PERF_MONITORING")
        
        if app.config.get("PERF_RESPONSE_COMPRESSION") is not None:
            self.enable_response_compression = app.config.get("PERF_RESPONSE_COMPRESSION")
        
        if app.config.get("PERF_FRONTEND_OPTIMIZATION") is not None:
            self.enable_frontend_optimization = app.config.get("PERF_FRONTEND_OPTIMIZATION")
        
        # Read component-specific configurations
        self.config.update({
            k.replace("PERF_", "").lower(): v
            for k, v in app.config.items()
            if k.startswith("PERF_")
        })
    
    def _init_components(self, app: Flask) -> None:
        """
        Initialize optimization components.
        
        Args:
            app: Flask application instance
        """
        # Initialize asset optimization
        if self.enable_asset_optimization:
            # Create asset optimizer
            self.asset_optimizer = AssetOptimizer(
                static_dir=app.config.get("STATIC_FOLDER", app.static_folder),
                dist_dir=os.path.join(
                    app.config.get("STATIC_FOLDER", app.static_folder),
                    "dist"
                ),
                create_source_maps=self.config.get("asset_source_maps", True),
                manifest_file=os.path.join(
                    app.config.get("STATIC_FOLDER", app.static_folder),
                    "dist",
                    "asset-manifest.json"
                )
            )
            
            # Register asset helper with Jinja
            register_asset_helper(app)
            
            logger.info("Asset optimization initialized")
        
        # Initialize query cache
        if self.enable_query_cache:
            # Get Redis client if configured
            redis_client = None
            if "REDIS_URL" in app.config:
                try:
                    import redis
                    redis_client = redis.from_url(app.config["REDIS_URL"])
                except (ImportError, Exception) as e:
                    logger.warning(f"Failed to initialize Redis client: {str(e)}")
            
            # Set up query cache
            self.query_cache = setup_query_cache(
                app, 
                app.extensions.get("sqlalchemy").db, 
                redis_client=redis_client
            )
            
            logger.info("Query cache initialized")
        
        # Initialize memory profiling
        if self.enable_memory_profiling:
            # Create memory profiler
            self.memory_profiler = MemoryProfiler(app)
            
            logger.info("Memory profiling initialized")
        
        # Initialize performance monitoring
        if self.enable_performance_monitoring:
            # Create performance monitor
            self.performance_monitor = PerformanceMonitor(app)
            
            logger.info("Performance monitoring initialized")
    
    def _setup_frontend_optimization(self, app: Flask) -> None:
        """
        Set up frontend optimization.
        
        Args:
            app: Flask application instance
        """
        # Add JavaScript optimization scripts to context
        @app.context_processor
        def inject_optimization_scripts():
            return {
                "optimization_scripts": self._get_optimization_scripts()
            }
        
        # Add JavaScript preload headers for critical resources
        @app.after_request
        def add_preload_headers(response: Response) -> Response:
            # Only add preload headers for HTML responses
            if response.content_type and "text/html" in response.content_type:
                # Add preload headers for critical resources
                critical_resources = [
                    # Main JS files
                    "/static/js/code-splitter.js",
                    "/static/js/image-optimizer.js",
                    
                    # Main CSS files
                    "/static/style.css",
                    "/static/css/premium.css"
                ]
                
                for resource in critical_resources:
                    # Determine resource type
                    if resource.endswith(".js"):
                        resource_type = "script"
                    elif resource.endswith(".css"):
                        resource_type = "style"
                    else:
                        continue
                    
                    # Add preload header
                    response.headers.add(
                        "Link",
                        f"<{resource}>; rel=preload; as={resource_type}"
                    )
            
            return response
        
        logger.info("Frontend optimization initialized")
    
    def _setup_response_compression(self, app: Flask) -> None:
        """
        Set up response compression.
        
        Args:
            app: Flask application instance
        """
        # Try to use Flask-Compress if available
        try:
            from flask_compress import Compress
            compress = Compress()
            compress.init_app(app)
            logger.info("Response compression initialized using Flask-Compress")
            return
        except ImportError:
            pass
        
        # Fallback: Use gzip compression via after_request
        @app.after_request
        def compress_response(response: Response) -> Response:
            # Check if client accepts gzip
            if (
                response.status_code < 200 or
                response.status_code >= 300 or
                "Content-Encoding" in response.headers or
                not self._client_accepts_gzip()
            ):
                return response
            
            # Check if content should be compressed
            content_type = response.headers.get("Content-Type", "")
            if not self._should_compress_content_type(content_type):
                return response
            
            # Compress response if larger than threshold
            response_data = response.get_data()
            if len(response_data) < 500:  # Skip small responses
                return response
            
            try:
                import gzip
                gzipped_data = gzip.compress(response_data)
                
                # Only use compressed data if it's smaller
                if len(gzipped_data) < len(response_data):
                    response.set_data(gzipped_data)
                    response.headers["Content-Encoding"] = "gzip"
                    response.headers["Content-Length"] = str(len(gzipped_data))
                    response.headers["Vary"] = "Accept-Encoding"
            except Exception as e:
                logger.warning(f"Error compressing response: {str(e)}")
            
            return response
        
        logger.info("Response compression initialized using gzip")
    
    def _client_accepts_gzip(self) -> bool:
        """
        Check if client accepts gzip encoding.
        
        Returns:
            True if client accepts gzip, False otherwise
        """
        accept_encoding = request.headers.get("Accept-Encoding", "")
        return "gzip" in accept_encoding
    
    def _should_compress_content_type(self, content_type: str) -> bool:
        """
        Check if content type should be compressed.
        
        Args:
            content_type: HTTP Content-Type header
            
        Returns:
            True if content should be compressed, False otherwise
        """
        compressible_types = {
            "text/",
            "application/json",
            "application/javascript",
            "application/xml",
            "application/xhtml+xml",
            "image/svg+xml",
            "application/rss+xml",
            "application/atom+xml"
        }
        
        return any(ct in content_type for ct in compressible_types)
    
    def _get_optimization_scripts(self) -> str:
        """
        Get JavaScript optimization scripts for frontend.
        
        Returns:
            HTML string with script tags
        """
        scripts = []
        
        # Add code splitter script
        scripts.append(
            '<script src="/static/js/code-splitter.js" async></script>'
        )
        
        # Add image optimizer script
        scripts.append(
            '<script src="/static/js/image-optimizer.js" async></script>'
        )
        
        # Add client-side performance monitoring
        if self.enable_performance_monitoring:
            scripts.append("""
            <script>
            // Initialize performance monitoring
            window.addEventListener('load', function() {
                // Record basic timing metrics
                if (window.performance) {
                    setTimeout(function() {
                        var timing = window.performance.timing;
                        var navigationStart = timing.navigationStart;
                        
                        var metrics = {
                            page: window.location.pathname,
                            load_time: timing.loadEventEnd - navigationStart,
                            dom_ready: timing.domInteractive - navigationStart,
                            ttfb: timing.responseStart - navigationStart,
                            resources: []
                        };
                        
                        // Get resource timing
                        if (window.performance.getEntriesByType) {
                            var resources = window.performance.getEntriesByType('resource');
                            if (resources && resources.length > 0) {
                                // Just track the count and total time for general metrics
                                metrics.resource_count = resources.length;
                                metrics.total_resource_time = resources.reduce(function(total, r) {
                                    return total + r.duration;
                                }, 0);
                            }
                        }
                        
                        // Send metrics to server
                        fetch('/api/performance/client', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify(metrics)
                        }).catch(function(error) {
                            console.error('Error sending performance metrics:', error);
                        });
                    }, 1000);
                }
            });
            </script>
            """)
        
        return "\n".join(scripts)
    
    def _register_suite_endpoint(self, app: Flask) -> None:
        """
        Register performance suite endpoint.
        
        Args:
            app: Flask application instance
        """
        @app.route("/api/performance/status")
        def performance_status():
            # Check if user has admin permission
            if not self._check_admin_permission():
                return jsonify({"error": "Unauthorized"}), 403
            
            # Return suite status
            status = {
                "components": {
                    "asset_optimization": self.enable_asset_optimization,
                    "query_cache": self.enable_query_cache,
                    "memory_profiling": self.enable_memory_profiling,
                    "performance_monitoring": self.enable_performance_monitoring,
                    "response_compression": self.enable_response_compression,
                    "frontend_optimization": self.enable_frontend_optimization
                },
                "settings": self.config
            }
            
            return jsonify(status)
    
    def _check_admin_permission(self) -> bool:
        """
        Check if the current user has admin permission.
        
        Returns:
            True if user has permission, False otherwise
        """
        # Check if testing
        from flask import current_app
        if current_app.config.get("TESTING", False):
            return True
        
        # Check if user is authenticated and has admin role
        if hasattr(g, "user") and hasattr(g.user, "is_admin"):
            return g.user.is_admin
        
        return False
    
    def optimize_assets(self) -> Dict[str, str]:
        """
        Run asset optimization process.
        
        Returns:
            Asset manifest dictionary
        """
        if not self.enable_asset_optimization or not self.asset_optimizer:
            logger.warning("Asset optimization is disabled")
            return {}
        
        logger.info("Running asset optimization...")
        start_time = time.time()
        
        # Run optimization
        manifest = self.asset_optimizer.optimize_all()
        
        duration = time.time() - start_time
        logger.info(f"Asset optimization completed in {duration:.2f}s")
        
        return manifest
    
    def clear_caches(self) -> None:
        """Clear all caches (query cache, asset cache, etc.)"""
        # Clear query cache
        if self.enable_query_cache and self.query_cache:
            self.query_cache.clear()
            logger.info("Query cache cleared")
        
        # Clear memory snapshots
        if self.enable_memory_profiling and self.memory_profiler:
            self.memory_profiler.clear_snapshots()
            logger.info("Memory snapshots cleared")


def optimize_query(
    expire: Optional[int] = None,
    key_prefix: Optional[str] = None
) -> Callable:
    """
    Decorator to optimize database queries with caching.
    
    Args:
        expire: Cache expiration time in seconds
        key_prefix: Cache key prefix
        
    Returns:
        Decorator function
    """
    from performance.query_cache import cache_query
    return cache_query(expire=expire, key_prefix=key_prefix)


def profile_performance(name: Optional[str] = None) -> Callable:
    """
    Decorator to profile function performance.
    
    Args:
        name: Profile name
        
    Returns:
        Decorator function
    """
    from performance.performance_monitor import profile
    return profile(name=name)


def profile_memory(func: Optional[Callable] = None) -> Callable:
    """
    Decorator to profile function memory usage.
    
    Args:
        func: Function to profile
        
    Returns:
        Decorated function
    """
    from performance.memory_profiler import profile_memory
    
    if func is None:
        return profile_memory
    
    return profile_memory(func)


def create_suite(app: Flask) -> PerformanceOptimizationSuite:
    """
    Create and initialize performance suite for a Flask app.
    
    Args:
        app: Flask application instance
        
    Returns:
        Performance optimization suite instance
    """
    suite = PerformanceOptimizationSuite(app)
    return suite


if __name__ == "__main__":
    # Example usage
    print("This module provides a complete performance optimization suite.")
    print("Example usage:")
    print("")
    print("  from performance.performance_suite import create_suite, optimize_query")
    print("")
    print("  # Initialize with Flask app")
    print("  performance_suite = create_suite(app)")
    print("")
    print("  # Optimize a database query function")
    print("  @optimize_query(expire=300)")
    print("  def get_user_data(user_id):")
    print("      # Database query here")
    print("      return result")