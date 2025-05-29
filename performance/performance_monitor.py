#!/usr/bin/env python
"""
Performance Monitoring for Inner Architect

This module provides tools for monitoring and profiling application performance:
- Request timing and profiling
- Memory usage tracking
- Database query analysis
- Resource utilization metrics
- Client-side performance tracking
"""

import functools
import gc
import inspect
import json
import logging
import os
import re
import sys
import threading
import time
import traceback
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from flask import Flask, g, jsonify, request, Response, current_app
import psutil

# Set up logging
logger = logging.getLogger("performance_monitor")

# Performance thresholds
DEFAULT_THRESHOLDS = {
    "slow_request_ms": 500,
    "very_slow_request_ms": 2000,
    "slow_query_ms": 100,
    "very_slow_query_ms": 500,
    "high_memory_mb": 500,
    "critical_memory_mb": 800,
    "high_cpu_percent": 80,
    "critical_cpu_percent": 95,
}

# Global state for tracking metrics
_metrics_data = {
    "requests": {},
    "queries": {},
    "memory": {},
    "endpoints": {},
    "clients": {}
}

# Thread local storage for request data
_thread_local = threading.local()


class PerformanceMonitor:
    """Performance monitoring and profiling for Flask applications."""
    
    def __init__(
        self,
        app: Optional[Flask] = None,
        thresholds: Optional[Dict[str, Any]] = None,
        log_slow_requests: bool = True,
        log_slow_queries: bool = True,
        track_memory: bool = True,
        track_sql_queries: bool = True,
        track_client_metrics: bool = True,
        enable_endpoints: bool = True
    ):
        """
        Initialize performance monitor.
        
        Args:
            app: Flask application instance
            thresholds: Performance threshold settings
            log_slow_requests: Whether to log slow requests
            log_slow_queries: Whether to log slow queries
            track_memory: Whether to track memory usage
            track_sql_queries: Whether to track SQL queries
            track_client_metrics: Whether to track client-side metrics
            enable_endpoints: Whether to enable monitoring endpoints
        """
        self.thresholds = thresholds or DEFAULT_THRESHOLDS
        self.log_slow_requests = log_slow_requests
        self.log_slow_queries = log_slow_queries
        self.track_memory = track_memory
        self.track_sql_queries = track_sql_queries
        self.track_client_metrics = track_client_metrics
        self.enable_endpoints = enable_endpoints
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask) -> None:
        """
        Initialize with a Flask application.
        
        Args:
            app: Flask application instance
        """
        # Register extension with Flask
        app.extensions["performance_monitor"] = self
        
        # Configure from app config
        self.log_slow_requests = app.config.get(
            "PERF_LOG_SLOW_REQUESTS", self.log_slow_requests
        )
        self.log_slow_queries = app.config.get(
            "PERF_LOG_SLOW_QUERIES", self.log_slow_queries
        )
        self.track_memory = app.config.get(
            "PERF_TRACK_MEMORY", self.track_memory
        )
        self.track_sql_queries = app.config.get(
            "PERF_TRACK_SQL_QUERIES", self.track_sql_queries
        )
        self.track_client_metrics = app.config.get(
            "PERF_TRACK_CLIENT_METRICS", self.track_client_metrics
        )
        self.enable_endpoints = app.config.get(
            "PERF_ENABLE_ENDPOINTS", self.enable_endpoints
        )
        
        # Load thresholds from app config
        config_thresholds = {
            k.replace("PERF_THRESHOLD_", "").lower(): v
            for k, v in app.config.items()
            if k.startswith("PERF_THRESHOLD_")
        }
        if config_thresholds:
            self.thresholds.update(config_thresholds)
        
        # Register request handlers
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        app.teardown_request(self._teardown_request)
        
        # Enable SQL query tracking if requested
        if self.track_sql_queries:
            try:
                from flask_sqlalchemy import SQLAlchemy
                from sqlalchemy import event
                
                # Get SQLAlchemy instance from app extensions
                db = None
                for ext_name, ext in app.extensions.items():
                    if isinstance(ext, SQLAlchemy):
                        db = ext
                        break
                
                if db is not None:
                    # Set up query tracking
                    engine = db.engine
                    event.listen(engine, "before_cursor_execute", self._before_cursor_execute)
                    event.listen(engine, "after_cursor_execute", self._after_cursor_execute)
                else:
                    logger.warning(
                        "SQLAlchemy not found in app extensions, "
                        "disabling SQL query tracking"
                    )
                    self.track_sql_queries = False
            except ImportError:
                logger.warning(
                    "Flask-SQLAlchemy not installed, disabling SQL query tracking"
                )
                self.track_sql_queries = False
        
        # Register monitoring endpoints if requested
        if self.enable_endpoints:
            self._register_endpoints(app)
        
        # Set up client-side tracking if requested
        if self.track_client_metrics:
            self._setup_client_tracking(app)
    
    def _before_request(self) -> None:
        """Record data before handling a request."""
        # Store start time
        _thread_local.start_time = time.time()
        _thread_local.sql_queries = []
        
        if self.track_memory:
            # Record initial memory usage
            _thread_local.start_memory = self._get_memory_usage()
    
    def _after_request(self, response: Response) -> Response:
        """
        Process request data and add timing headers.
        
        Args:
            response: Flask response object
            
        Returns:
            Modified response
        """
        if not hasattr(_thread_local, "start_time"):
            return response
        
        # Calculate request duration
        duration_ms = (time.time() - _thread_local.start_time) * 1000
        
        # Add timing header
        response.headers["X-Request-Time-Ms"] = str(int(duration_ms))
        
        # Add query timing header if available
        if hasattr(_thread_local, "sql_queries"):
            total_query_time = sum(q["duration_ms"] for q in _thread_local.sql_queries)
            response.headers["X-Query-Time-Ms"] = str(int(total_query_time))
            response.headers["X-Query-Count"] = str(len(_thread_local.sql_queries))
        
        # Add performance tracking headers
        response.headers["Server-Timing"] = self._generate_server_timing_header(duration_ms)
        
        # Check if this was a slow request
        endpoint = request.endpoint or "unknown"
        if self.log_slow_requests and duration_ms > self.thresholds["slow_request_ms"]:
            severity = "WARNING"
            if duration_ms > self.thresholds["very_slow_request_ms"]:
                severity = "ERROR"
            
            logger.log(
                logging.WARNING if severity == "WARNING" else logging.ERROR,
                f"Slow request ({severity}): {request.method} {request.path} - "
                f"{duration_ms:.1f}ms - Endpoint: {endpoint}"
            )
        
        # Track endpoint performance
        if endpoint not in _metrics_data["endpoints"]:
            _metrics_data["endpoints"][endpoint] = {
                "count": 0,
                "total_time_ms": 0,
                "max_time_ms": 0,
                "min_time_ms": float("inf"),
                "avg_time_ms": 0,
                "p95_time_ms": 0,
                "slow_count": 0,
                "times": []  # Last 100 requests for percentile calculation
            }
        
        stats = _metrics_data["endpoints"][endpoint]
        stats["count"] += 1
        stats["total_time_ms"] += duration_ms
        stats["max_time_ms"] = max(stats["max_time_ms"], duration_ms)
        stats["min_time_ms"] = min(stats["min_time_ms"], duration_ms)
        stats["avg_time_ms"] = stats["total_time_ms"] / stats["count"]
        
        if duration_ms > self.thresholds["slow_request_ms"]:
            stats["slow_count"] += 1
        
        # Keep last 100 request times for percentile calculation
        stats["times"].append(duration_ms)
        if len(stats["times"]) > 100:
            stats["times"].pop(0)
        
        if len(stats["times"]) >= 20:  # Only calculate p95 with enough samples
            stats["p95_time_ms"] = sorted(stats["times"])[int(len(stats["times"]) * 0.95)]
        
        return response
    
    def _teardown_request(self, exception: Optional[Exception]) -> None:
        """
        Clean up request data.
        
        Args:
            exception: Exception raised during request handling, if any
        """
        # Check memory usage if tracking enabled
        if self.track_memory and hasattr(_thread_local, "start_memory"):
            end_memory = self._get_memory_usage()
            memory_diff = end_memory - _thread_local.start_memory
            
            # Log high memory usage
            if memory_diff > self.thresholds["high_memory_mb"]:
                severity = "WARNING"
                if memory_diff > self.thresholds["critical_memory_mb"]:
                    severity = "ERROR"
                
                endpoint = request.endpoint or "unknown"
                logger.log(
                    logging.WARNING if severity == "WARNING" else logging.ERROR,
                    f"High memory usage ({severity}): {request.method} {request.path} - "
                    f"{memory_diff:.1f}MB - Endpoint: {endpoint}"
                )
            
            # Track memory usage by endpoint
            endpoint = request.endpoint or "unknown"
            if endpoint not in _metrics_data["memory"]:
                _metrics_data["memory"][endpoint] = {
                    "count": 0,
                    "total_mb": 0,
                    "max_mb": 0,
                    "avg_mb": 0
                }
            
            mem_stats = _metrics_data["memory"][endpoint]
            mem_stats["count"] += 1
            mem_stats["total_mb"] += memory_diff
            mem_stats["max_mb"] = max(mem_stats["max_mb"], memory_diff)
            mem_stats["avg_mb"] = mem_stats["total_mb"] / mem_stats["count"]
        
        # Clear thread local data
        for attr in ["start_time", "sql_queries", "start_memory"]:
            if hasattr(_thread_local, attr):
                delattr(_thread_local, attr)
    
    def _before_cursor_execute(
        self, conn, cursor, statement, parameters, context, executemany
    ) -> None:
        """
        Record data before executing a database query.
        
        Args:
            conn: Database connection
            cursor: Database cursor
            statement: SQL statement
            parameters: Query parameters
            context: Execution context
            executemany: Whether this is an executemany call
        """
        if not self.track_sql_queries:
            return
        
        # Store query start time
        setattr(conn, "query_start_time", time.time())
    
    def _after_cursor_execute(
        self, conn, cursor, statement, parameters, context, executemany
    ) -> None:
        """
        Record data after executing a database query.
        
        Args:
            conn: Database connection
            cursor: Database cursor
            statement: SQL statement
            parameters: Query parameters
            context: Execution context
            executemany: Whether this is an executemany call
        """
        if not self.track_sql_queries or not hasattr(conn, "query_start_time"):
            return
        
        # Calculate query duration
        duration_ms = (time.time() - conn.query_start_time) * 1000
        
        # Clean up statement for logging
        statement = statement.strip()
        
        # Record query data
        query_data = {
            "statement": statement,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat(),
        }
        
        # Log slow queries
        if self.log_slow_queries and duration_ms > self.thresholds["slow_query_ms"]:
            severity = "WARNING"
            if duration_ms > self.thresholds["very_slow_query_ms"]:
                severity = "ERROR"
            
            # Truncate long queries for logging
            log_statement = statement
            if len(log_statement) > 100:
                log_statement = log_statement[:97] + "..."
            
            logger.log(
                logging.WARNING if severity == "WARNING" else logging.ERROR,
                f"Slow query ({severity}): {log_statement} - {duration_ms:.1f}ms"
            )
        
        # Track query statistics
        query_type = self._get_query_type(statement)
        if query_type not in _metrics_data["queries"]:
            _metrics_data["queries"][query_type] = {
                "count": 0,
                "total_time_ms": 0,
                "max_time_ms": 0,
                "min_time_ms": float("inf"),
                "avg_time_ms": 0,
                "slow_count": 0
            }
        
        stats = _metrics_data["queries"][query_type]
        stats["count"] += 1
        stats["total_time_ms"] += duration_ms
        stats["max_time_ms"] = max(stats["max_time_ms"], duration_ms)
        stats["min_time_ms"] = min(stats["min_time_ms"], duration_ms)
        stats["avg_time_ms"] = stats["total_time_ms"] / stats["count"]
        
        if duration_ms > self.thresholds["slow_query_ms"]:
            stats["slow_count"] += 1
        
        # Add to thread-local for request tracking
        if hasattr(_thread_local, "sql_queries"):
            _thread_local.sql_queries.append(query_data)
    
    def _generate_server_timing_header(self, total_ms: float) -> str:
        """
        Generate Server-Timing header for Chrome DevTools.
        
        Args:
            total_ms: Total request time in milliseconds
            
        Returns:
            Server-Timing header value
        """
        parts = [f"total;dur={total_ms:.1f};desc=\"Total\""]
        
        # Add query timing if available
        if hasattr(_thread_local, "sql_queries"):
            query_time = sum(q["duration_ms"] for q in _thread_local.sql_queries)
            query_count = len(_thread_local.sql_queries)
            if query_count > 0:
                parts.append(
                    f"db;dur={query_time:.1f};desc=\"DB ({query_count} queries)\""
                )
        
        # Add app time (total - query)
        if hasattr(_thread_local, "sql_queries"):
            query_time = sum(q["duration_ms"] for q in _thread_local.sql_queries)
            app_time = total_ms - query_time
            parts.append(f"app;dur={app_time:.1f};desc=\"App\"")
        
        return ", ".join(parts)
    
    def _get_query_type(self, statement: str) -> str:
        """
        Determine the type of SQL query from the statement.
        
        Args:
            statement: SQL statement
            
        Returns:
            Query type (SELECT, INSERT, UPDATE, DELETE, or OTHER)
        """
        statement = statement.strip().upper()
        
        if statement.startswith("SELECT"):
            return "SELECT"
        elif statement.startswith("INSERT"):
            return "INSERT"
        elif statement.startswith("UPDATE"):
            return "UPDATE"
        elif statement.startswith("DELETE"):
            return "DELETE"
        else:
            return "OTHER"
    
    def _get_memory_usage(self) -> float:
        """
        Get current memory usage in MB.
        
        Returns:
            Memory usage in MB
        """
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return memory_info.rss / (1024 * 1024)  # Convert to MB
    
    def _register_endpoints(self, app: Flask) -> None:
        """
        Register performance monitoring endpoints.
        
        Args:
            app: Flask application instance
        """
        # Register API endpoints for metrics
        @app.route("/api/performance/metrics")
        def performance_metrics():
            # Check if user has permission
            if not self._check_admin_permission():
                return jsonify({"error": "Unauthorized"}), 403
            
            # Return current metrics
            return jsonify({
                "endpoints": _metrics_data["endpoints"],
                "queries": _metrics_data["queries"],
                "memory": _metrics_data["memory"],
                "system": self._get_system_metrics(),
                "timestamp": datetime.now().isoformat()
            })
        
        @app.route("/api/performance/requests")
        def performance_requests():
            # Check if user has permission
            if not self._check_admin_permission():
                return jsonify({"error": "Unauthorized"}), 403
            
            # Return endpoint performance data
            return jsonify({
                "endpoints": _metrics_data["endpoints"],
                "timestamp": datetime.now().isoformat()
            })
        
        @app.route("/api/performance/queries")
        def performance_queries():
            # Check if user has permission
            if not self._check_admin_permission():
                return jsonify({"error": "Unauthorized"}), 403
            
            # Return query performance data
            return jsonify({
                "queries": _metrics_data["queries"],
                "timestamp": datetime.now().isoformat()
            })
        
        @app.route("/api/performance/memory")
        def performance_memory():
            # Check if user has permission
            if not self._check_admin_permission():
                return jsonify({"error": "Unauthorized"}), 403
            
            # Return memory usage data
            memory_data = {
                "endpoints": _metrics_data["memory"],
                "current": self._get_memory_usage(),
                "system": self._get_memory_system_metrics(),
                "timestamp": datetime.now().isoformat()
            }
            
            return jsonify(memory_data)
        
        @app.route("/api/performance/system")
        def performance_system():
            # Check if user has permission
            if not self._check_admin_permission():
                return jsonify({"error": "Unauthorized"}), 403
            
            # Return system metrics
            return jsonify({
                "system": self._get_system_metrics(),
                "timestamp": datetime.now().isoformat()
            })
        
        @app.route("/api/performance/client", methods=["POST"])
        def performance_client():
            # Store client-side metrics
            if not self.track_client_metrics:
                return jsonify({"status": "disabled"}), 200
            
            try:
                metrics = request.json
                if not metrics:
                    return jsonify({"error": "No metrics provided"}), 400
                
                # Generate a unique key for this client report
                client_id = metrics.get("clientId", "unknown")
                timestamp = datetime.now().isoformat()
                key = f"{client_id}-{timestamp}"
                
                # Store metrics
                _metrics_data["clients"][key] = {
                    "timestamp": timestamp,
                    "metrics": metrics
                }
                
                # Keep only the last 1000 client reports
                if len(_metrics_data["clients"]) > 1000:
                    oldest_key = min(
                        _metrics_data["clients"].keys(),
                        key=lambda k: _metrics_data["clients"][k]["timestamp"]
                    )
                    del _metrics_data["clients"][oldest_key]
                
                return jsonify({"status": "success"}), 200
            except Exception as e:
                logger.error(f"Error processing client metrics: {str(e)}")
                return jsonify({"error": "Internal server error"}), 500
        
        @app.route("/api/performance/client/metrics")
        def performance_client_metrics():
            # Check if user has permission
            if not self._check_admin_permission():
                return jsonify({"error": "Unauthorized"}), 403
            
            # Return client-side metrics
            return jsonify({
                "clients": _metrics_data["clients"],
                "timestamp": datetime.now().isoformat()
            })
    
    def _setup_client_tracking(self, app: Flask) -> None:
        """
        Set up client-side performance tracking.
        
        Args:
            app: Flask application instance
        """
        # Add template context processor for client-side tracking
        @app.context_processor
        def inject_performance_tracking():
            if not self.track_client_metrics:
                return {}
            
            # Return tracking script to be included in templates
            return {
                "performance_tracking_script": self._get_client_tracking_script()
            }
    
    def _get_client_tracking_script(self) -> str:
        """
        Get JavaScript code for client-side performance tracking.
        
        Returns:
            JavaScript code snippet
        """
        return """
        <script>
        // Performance monitoring script
        document.addEventListener('DOMContentLoaded', function() {
            // Generate a random client ID if not already present
            if (!localStorage.getItem('perfClientId')) {
                localStorage.setItem('perfClientId', Math.random().toString(36).substring(2, 15));
            }
            
            // Collect performance metrics when page is fully loaded
            window.addEventListener('load', function() {
                setTimeout(function() {
                    // Collect performance data
                    var perfData = collectPerformanceData();
                    
                    // Send to server
                    sendPerformanceData(perfData);
                }, 1000);
            });
            
            // Collect performance metrics
            function collectPerformanceData() {
                var performance = window.performance || window.mozPerformance || window.msPerformance || window.webkitPerformance || {};
                var timing = performance.timing || {};
                var navigation = performance.navigation || {};
                
                // Basic timing metrics
                var metrics = {
                    clientId: localStorage.getItem('perfClientId'),
                    url: window.location.pathname,
                    userAgent: navigator.userAgent,
                    screenWidth: window.screen.width,
                    screenHeight: window.screen.height,
                    timestamp: new Date().toISOString()
                };
                
                // Navigation type
                if (navigation.type !== undefined) {
                    metrics.navigationType = [
                        'navigate',
                        'reload',
                        'back_forward',
                        'prerender'
                    ][navigation.type] || 'unknown';
                }
                
                // Add timing data if available
                if (timing.navigationStart) {
                    var navigationStart = timing.navigationStart;
                    
                    metrics.timing = {
                        // Time to first byte
                        ttfb: timing.responseStart - navigationStart,
                        
                        // DOM loading time
                        domLoading: timing.domLoading - navigationStart,
                        
                        // DOM interactive time
                        domInteractive: timing.domInteractive - navigationStart,
                        
                        // DOM complete time
                        domComplete: timing.domComplete - navigationStart,
                        
                        // Load event time
                        loadEvent: timing.loadEventEnd - navigationStart,
                        
                        // DNS time
                        dns: timing.domainLookupEnd - timing.domainLookupStart,
                        
                        // Connection time
                        connect: timing.connectEnd - timing.connectStart,
                        
                        // Request time
                        request: timing.responseEnd - timing.requestStart,
                        
                        // Response time
                        response: timing.responseEnd - timing.responseStart,
                        
                        // DOM processing time
                        domProcessing: timing.domComplete - timing.domLoading,
                        
                        // Load event processing time
                        loadEventProcessing: timing.loadEventEnd - timing.loadEventStart
                    };
                }
                
                // Add performance entries if available
                if (performance.getEntriesByType) {
                    // Resource timing
                    var resources = performance.getEntriesByType('resource');
                    if (resources && resources.length > 0) {
                        metrics.resources = {
                            count: resources.length,
                            totalSize: 0,
                            totalTime: 0,
                            byType: {}
                        };
                        
                        resources.forEach(function(resource) {
                            // Extract resource type
                            var type = 'other';
                            var url = resource.name || '';
                            
                            if (url.match(/\\.(?:js)(?:\\?|$)/i)) type = 'script';
                            else if (url.match(/\\.(?:css)(?:\\?|$)/i)) type = 'style';
                            else if (url.match(/\\.(?:png|jpg|jpeg|gif|webp|svg)(?:\\?|$)/i)) type = 'image';
                            else if (url.match(/\\.(?:woff|woff2|ttf|otf|eot)(?:\\?|$)/i)) type = 'font';
                            else if (url.match(/\\/api\\//i)) type = 'api';
                            
                            // Initialize type if not exists
                            if (!metrics.resources.byType[type]) {
                                metrics.resources.byType[type] = {
                                    count: 0,
                                    totalSize: 0,
                                    totalTime: 0
                                };
                            }
                            
                            // Add resource data
                            metrics.resources.byType[type].count++;
                            metrics.resources.byType[type].totalTime += resource.duration || 0;
                            
                            // Add to totals
                            metrics.resources.totalTime += resource.duration || 0;
                            
                            // Try to get transferred size if available
                            if (resource.transferSize) {
                                metrics.resources.totalSize += resource.transferSize;
                                metrics.resources.byType[type].totalSize += resource.transferSize;
                            }
                        });
                    }
                    
                    // Paint timing
                    var paints = performance.getEntriesByType('paint');
                    if (paints && paints.length > 0) {
                        metrics.paint = {};
                        
                        paints.forEach(function(paint) {
                            if (paint.name === 'first-paint') {
                                metrics.paint.firstPaint = paint.startTime;
                            } else if (paint.name === 'first-contentful-paint') {
                                metrics.paint.firstContentfulPaint = paint.startTime;
                            }
                        });
                    }
                }
                
                // Add memory info if available
                if (performance.memory) {
                    metrics.memory = {
                        jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
                        totalJSHeapSize: performance.memory.totalJSHeapSize,
                        usedJSHeapSize: performance.memory.usedJSHeapSize
                    };
                }
                
                return metrics;
            }
            
            // Send performance data to server
            function sendPerformanceData(data) {
                fetch('/api/performance/client', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                }).catch(function(error) {
                    console.error('Error sending performance data:', error);
                });
            }
        });
        </script>
        """
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """
        Get system metrics (CPU, memory, disk, etc.)
        
        Returns:
            Dictionary of system metrics
        """
        try:
            process = psutil.Process(os.getpid())
            
            # Basic process info
            process_info = {
                "pid": process.pid,
                "cpu_percent": process.cpu_percent(interval=0.1),
                "memory_percent": process.memory_percent(),
                "memory_mb": process.memory_info().rss / (1024 * 1024),
                "threads": process.num_threads(),
                "uptime": time.time() - process.create_time()
            }
            
            # System-wide metrics
            system_info = {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "memory_available_mb": psutil.virtual_memory().available / (1024 * 1024),
                "disk_percent": psutil.disk_usage('/').percent,
                "disk_free_gb": psutil.disk_usage('/').free / (1024 * 1024 * 1024)
            }
            
            return {
                "process": process_info,
                "system": system_info,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {str(e)}")
            return {"error": str(e)}
    
    def _get_memory_system_metrics(self) -> Dict[str, Any]:
        """
        Get detailed memory metrics for the system and process.
        
        Returns:
            Dictionary of memory metrics
        """
        try:
            process = psutil.Process(os.getpid())
            
            # Get process memory info
            process_memory = process.memory_info()
            
            # Get system memory info
            system_memory = psutil.virtual_memory()
            
            # Get Python interpreter memory info
            gc.collect()
            python_objects = gc.get_objects()
            object_counts = {}
            
            for obj in python_objects:
                obj_type = type(obj).__name__
                if obj_type not in object_counts:
                    object_counts[obj_type] = 0
                object_counts[obj_type] += 1
            
            # Get top object types by count
            top_objects = sorted(
                object_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:20]
            
            return {
                "process": {
                    "rss_mb": process_memory.rss / (1024 * 1024),
                    "vms_mb": process_memory.vms / (1024 * 1024),
                    "percent": process.memory_percent()
                },
                "system": {
                    "total_mb": system_memory.total / (1024 * 1024),
                    "available_mb": system_memory.available / (1024 * 1024),
                    "used_mb": system_memory.used / (1024 * 1024),
                    "percent": system_memory.percent
                },
                "python": {
                    "total_objects": len(python_objects),
                    "top_objects": dict(top_objects)
                }
            }
        except Exception as e:
            logger.error(f"Error getting memory metrics: {str(e)}")
            return {"error": str(e)}
    
    def _check_admin_permission(self) -> bool:
        """
        Check if the current user has admin permission.
        
        Returns:
            True if user has permission, False otherwise
        """
        # Simple implementation for now, should be replaced with proper auth check
        if current_app.config.get("TESTING", False):
            return True
        
        # Check if user is authenticated and has admin role
        if hasattr(g, "user") and hasattr(g.user, "is_admin"):
            return g.user.is_admin
        
        return False


def profile(func: Optional[Callable] = None, name: Optional[str] = None) -> Callable:
    """
    Decorator to profile a function's execution time.
    
    Args:
        func: Function to profile
        name: Custom name for the profile
        
    Returns:
        Decorated function
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            # Get function name if not provided
            profile_name = name or f.__name__
            
            # Start timer
            start_time = time.time()
            
            try:
                # Execute the function
                result = f(*args, **kwargs)
                return result
            finally:
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Log execution time
                logger.debug(f"Profile {profile_name}: {duration_ms:.2f}ms")
                
                # Add to metrics for tracking
                if profile_name not in _metrics_data["requests"]:
                    _metrics_data["requests"][profile_name] = {
                        "count": 0,
                        "total_time_ms": 0,
                        "max_time_ms": 0,
                        "min_time_ms": float("inf"),
                        "avg_time_ms": 0
                    }
                
                stats = _metrics_data["requests"][profile_name]
                stats["count"] += 1
                stats["total_time_ms"] += duration_ms
                stats["max_time_ms"] = max(stats["max_time_ms"], duration_ms)
                stats["min_time_ms"] = min(stats["min_time_ms"], duration_ms)
                stats["avg_time_ms"] = stats["total_time_ms"] / stats["count"]
        
        return wrapper
    
    if func is None:
        return decorator
    else:
        return decorator(func)


def memory_profile(func: Callable) -> Callable:
    """
    Decorator to profile a function's memory usage.
    
    Args:
        func: Function to profile
        
    Returns:
        Decorated function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss / (1024 * 1024)
        
        # Run garbage collection to get accurate measurements
        gc.collect()
        
        try:
            # Execute the function
            result = func(*args, **kwargs)
            return result
        finally:
            # Run garbage collection again
            gc.collect()
            
            # Calculate memory usage
            end_memory = process.memory_info().rss / (1024 * 1024)
            memory_diff = end_memory - start_memory
            
            # Log memory usage
            logger.debug(f"Memory {func.__name__}: {memory_diff:.2f}MB")
    
    return wrapper


if __name__ == "__main__":
    # Example usage
    print("This module provides performance monitoring for Flask applications.")
    print("Example usage:")
    print("")
    print("  from performance.performance_monitor import PerformanceMonitor, profile")
    print("")
    print("  # Initialize with Flask app")
    print("  perf_monitor = PerformanceMonitor(app)")
    print("")
    print("  # Profile a function")
    print("  @profile")
    print("  def expensive_operation():")
    print("      # Do something expensive")
    print("      return result")