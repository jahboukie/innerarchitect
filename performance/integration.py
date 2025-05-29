#!/usr/bin/env python
"""
Performance Optimization Suite Integration for Inner Architect

This module provides a simple way to integrate the Performance Optimization
Suite with the Inner Architect application.
"""

import logging
import os
from typing import Dict, Any, Optional

from flask import Flask, Blueprint, render_template, jsonify, current_app, request

from performance import init_performance_suite, PerformanceOptimizationSuite

# Configure logging
logger = logging.getLogger("performance.integration")

# Create blueprint for performance admin UI
perf_blueprint = Blueprint(
    "performance", 
    __name__, 
    url_prefix="/admin/performance",
    template_folder="templates"
)


def init_performance(app: Flask, config: Optional[Dict[str, Any]] = None) -> PerformanceOptimizationSuite:
    """
    Initialize performance optimization for the application.
    
    Args:
        app: Flask application instance
        config: Configuration dictionary (optional)
        
    Returns:
        Configured performance suite instance
    """
    # Set default configuration
    app.config.setdefault("PERF_ASSET_OPTIMIZATION", True)
    app.config.setdefault("PERF_QUERY_CACHE", True)
    app.config.setdefault("PERF_MEMORY_PROFILING", True)
    app.config.setdefault("PERF_MONITORING", True)
    app.config.setdefault("PERF_RESPONSE_COMPRESSION", True)
    app.config.setdefault("PERF_FRONTEND_OPTIMIZATION", True)
    
    # Initialize performance suite
    suite = init_performance_suite(app, config)
    
    # Register admin blueprint if enabled
    if app.config.get("PERF_ADMIN_UI", True):
        app.register_blueprint(perf_blueprint)
    
    # Run asset optimization if in production
    if not app.debug and app.config.get("PERF_OPTIMIZE_ASSETS_ON_STARTUP", True):
        @app.before_first_request
        def optimize_assets():
            logger.info("Running asset optimization on startup...")
            suite.optimize_assets()
    
    # Add custom headers for performance monitoring
    @app.after_request
    def add_performance_headers(response):
        response.headers["X-Performance-Enabled"] = "true"
        
        # Add Server-Timing header if available
        if hasattr(request, "start_time") and hasattr(current_app, "extensions") and "performance_monitor" in current_app.extensions:
            perf_monitor = current_app.extensions["performance_monitor"]
            if hasattr(perf_monitor, "_generate_server_timing_header"):
                import time
                elapsed_ms = (time.time() - request.start_time) * 1000
                response.headers["Server-Timing"] = perf_monitor._generate_server_timing_header(elapsed_ms)
        
        return response
    
    logger.info("Performance optimization suite initialized")
    
    return suite


# Performance admin UI routes
@perf_blueprint.route("/")
def performance_dashboard():
    """Admin dashboard for performance monitoring."""
    # Check if user has admin permission
    if not _check_admin_permission():
        return render_template("error.html", message="Unauthorized"), 403
    
    return render_template(
        "admin/performance/dashboard.html",
        title="Performance Dashboard"
    )


@perf_blueprint.route("/optimize")
def run_optimization():
    """Run performance optimization tasks."""
    # Check if user has admin permission
    if not _check_admin_permission():
        return jsonify({"error": "Unauthorized"}), 403
    
    # Get suite from app extensions
    suite = current_app.extensions.get("performance_suite")
    if not suite:
        return jsonify({"error": "Performance suite not initialized"}), 500
    
    # Run asset optimization
    manifest = suite.optimize_assets()
    
    return jsonify({
        "success": True,
        "message": f"Optimization completed. {len(manifest)} assets processed.",
        "manifest": manifest
    })


@perf_blueprint.route("/clear-caches")
def clear_caches():
    """Clear all performance-related caches."""
    # Check if user has admin permission
    if not _check_admin_permission():
        return jsonify({"error": "Unauthorized"}), 403
    
    # Get suite from app extensions
    suite = current_app.extensions.get("performance_suite")
    if not suite:
        return jsonify({"error": "Performance suite not initialized"}), 500
    
    # Clear caches
    suite.clear_caches()
    
    return jsonify({
        "success": True,
        "message": "All caches cleared successfully."
    })


def _check_admin_permission() -> bool:
    """
    Check if the current user has admin permission.
    
    Returns:
        True if user has permission, False otherwise
    """
    # Check if testing
    if current_app.config.get("TESTING", False):
        return True
    
    # Check if user is authenticated and has admin role
    from flask import g
    if hasattr(g, "user") and hasattr(g.user, "is_admin"):
        return g.user.is_admin
    
    return False


# Create admin UI templates if they don't exist
def ensure_admin_templates():
    """Ensure admin UI templates exist."""
    # Get template directory
    template_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "templates",
        "admin",
        "performance"
    )
    
    # Create directory if it doesn't exist
    os.makedirs(template_dir, exist_ok=True)
    
    # Create dashboard template if it doesn't exist
    dashboard_path = os.path.join(template_dir, "dashboard.html")
    if not os.path.exists(dashboard_path):
        with open(dashboard_path, "w") as f:
            f.write("""
{% extends "base.html" %}

{% block title %}Performance Dashboard{% endblock %}

{% block content %}
<div class="container py-4">
    <h1 class="mb-4">Performance Dashboard</h1>
    
    <div class="row mb-4">
        <div class="col">
            <div class="card shadow-sm">
                <div class="card-header">
                    <h5 class="card-title mb-0">Performance Tools</h5>
                </div>
                <div class="card-body">
                    <div class="d-flex justify-content-between mb-3">
                        <button id="optimizeAssetsBtn" class="btn btn-primary">
                            <i class="fas fa-rocket me-1"></i> Optimize Assets
                        </button>
                        <button id="clearCachesBtn" class="btn btn-warning">
                            <i class="fas fa-broom me-1"></i> Clear Caches
                        </button>
                    </div>
                    <div id="toolsResult" class="alert alert-info d-none"></div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="row mb-4">
        <div class="col-md-6">
            <div class="card shadow-sm h-100">
                <div class="card-header">
                    <h5 class="card-title mb-0">Request Performance</h5>
                </div>
                <div class="card-body">
                    <div id="requestChart" style="height: 300px;"></div>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card shadow-sm h-100">
                <div class="card-header">
                    <h5 class="card-title mb-0">Memory Usage</h5>
                </div>
                <div class="card-body">
                    <div id="memoryChart" style="height: 300px;"></div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="row">
        <div class="col-md-6">
            <div class="card shadow-sm h-100">
                <div class="card-header">
                    <h5 class="card-title mb-0">Database Queries</h5>
                </div>
                <div class="card-body">
                    <div id="queryChart" style="height: 300px;"></div>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card shadow-sm h-100">
                <div class="card-header">
                    <h5 class="card-title mb-0">System Resources</h5>
                </div>
                <div class="card-body">
                    <div id="systemChart" style="height: 300px;"></div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="https://cdn.jsdelivr.net/npm/chart.js@3.7.1/dist/chart.min.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts
    initCharts();
    
    // Set up button handlers
    document.getElementById('optimizeAssetsBtn').addEventListener('click', optimizeAssets);
    document.getElementById('clearCachesBtn').addEventListener('click', clearCaches);
    
    // Load initial data
    loadPerformanceData();
    
    // Refresh data every 30 seconds
    setInterval(loadPerformanceData, 30000);
});

function initCharts() {
    // Request chart
    window.requestChart = new Chart(
        document.getElementById('requestChart').getContext('2d'),
        {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Avg. Response Time (ms)',
                    data: [],
                    backgroundColor: 'rgba(99, 91, 255, 0.5)',
                    borderColor: 'rgb(99, 91, 255)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        }
    );
    
    // Memory chart
    window.memoryChart = new Chart(
        document.getElementById('memoryChart').getContext('2d'),
        {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Memory Usage (MB)',
                    data: [],
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    borderColor: 'rgb(255, 99, 132)',
                    borderWidth: 1,
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        }
    );
    
    // Query chart
    window.queryChart = new Chart(
        document.getElementById('queryChart').getContext('2d'),
        {
            type: 'pie',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        'rgba(99, 91, 255, 0.5)',
                        'rgba(255, 99, 132, 0.5)',
                        'rgba(255, 205, 86, 0.5)',
                        'rgba(75, 192, 192, 0.5)',
                        'rgba(54, 162, 235, 0.5)'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        }
    );
    
    // System chart
    window.systemChart = new Chart(
        document.getElementById('systemChart').getContext('2d'),
        {
            type: 'doughnut',
            data: {
                labels: ['CPU', 'Memory', 'Disk'],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.5)',
                        'rgba(54, 162, 235, 0.5)',
                        'rgba(255, 205, 86, 0.5)'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        }
    );
}

function loadPerformanceData() {
    // Load request metrics
    fetch('/api/performance/requests')
        .then(response => response.json())
        .then(data => updateRequestChart(data))
        .catch(error => console.error('Error loading request metrics:', error));
    
    // Load memory metrics
    fetch('/api/performance/memory')
        .then(response => response.json())
        .then(data => updateMemoryChart(data))
        .catch(error => console.error('Error loading memory metrics:', error));
    
    // Load query metrics
    fetch('/api/performance/queries')
        .then(response => response.json())
        .then(data => updateQueryChart(data))
        .catch(error => console.error('Error loading query metrics:', error));
    
    // Load system metrics
    fetch('/api/performance/system')
        .then(response => response.json())
        .then(data => updateSystemChart(data))
        .catch(error => console.error('Error loading system metrics:', error));
}

function updateRequestChart(data) {
    const endpoints = data.endpoints;
    const labels = [];
    const avgTimes = [];
    
    // Get top 10 endpoints by count
    const sortedEndpoints = Object.entries(endpoints)
        .sort((a, b) => b[1].count - a[1].count)
        .slice(0, 10);
    
    for (const [endpoint, stats] of sortedEndpoints) {
        labels.push(endpoint);
        avgTimes.push(stats.avg_time_ms);
    }
    
    // Update chart
    window.requestChart.data.labels = labels;
    window.requestChart.data.datasets[0].data = avgTimes;
    window.requestChart.update();
}

function updateMemoryChart(data) {
    if (!data.timeline) return;
    
    const timeline = data.timeline;
    const labels = [];
    const memoryData = [];
    
    for (const point of timeline) {
        // Format timestamp as HH:MM:SS
        const date = new Date(point.timestamp);
        const timeStr = date.toLocaleTimeString();
        
        labels.push(timeStr);
        memoryData.push(point.rss_mb);
    }
    
    // Update chart
    window.memoryChart.data.labels = labels;
    window.memoryChart.data.datasets[0].data = memoryData;
    window.memoryChart.update();
}

function updateQueryChart(data) {
    const queries = data.queries;
    const labels = [];
    const counts = [];
    
    for (const [queryType, stats] of Object.entries(queries)) {
        labels.push(queryType);
        counts.push(stats.count);
    }
    
    // Update chart
    window.queryChart.data.labels = labels;
    window.queryChart.data.datasets[0].data = counts;
    window.queryChart.update();
}

function updateSystemChart(data) {
    if (!data.system || !data.system.system) return;
    
    const system = data.system.system;
    
    // Update chart data
    window.systemChart.data.datasets[0].data = [
        system.cpu_percent,
        system.memory_percent,
        system.disk_percent
    ];
    window.systemChart.update();
}

function optimizeAssets() {
    const btn = document.getElementById('optimizeAssetsBtn');
    const result = document.getElementById('toolsResult');
    
    // Disable button and show loading state
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Optimizing...';
    
    // Call API
    fetch('/admin/performance/optimize')
        .then(response => response.json())
        .then(data => {
            // Show result
            result.textContent = data.message;
            result.classList.remove('d-none', 'alert-danger');
            result.classList.add('alert-success');
        })
        .catch(error => {
            // Show error
            result.textContent = 'Error: ' + error.message;
            result.classList.remove('d-none', 'alert-success');
            result.classList.add('alert-danger');
        })
        .finally(() => {
            // Restore button state
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-rocket me-1"></i> Optimize Assets';
        });
}

function clearCaches() {
    const btn = document.getElementById('clearCachesBtn');
    const result = document.getElementById('toolsResult');
    
    // Disable button and show loading state
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Clearing...';
    
    // Call API
    fetch('/admin/performance/clear-caches')
        .then(response => response.json())
        .then(data => {
            // Show result
            result.textContent = data.message;
            result.classList.remove('d-none', 'alert-danger');
            result.classList.add('alert-success');
        })
        .catch(error => {
            // Show error
            result.textContent = 'Error: ' + error.message;
            result.classList.remove('d-none', 'alert-success');
            result.classList.add('alert-danger');
        })
        .finally(() => {
            // Restore button state
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-broom me-1"></i> Clear Caches';
        });
}
</script>
{% endblock %}
            """)


# Ensure admin templates exist
ensure_admin_templates()


if __name__ == "__main__":
    # Example usage
    print("This module provides integration for the Performance Optimization Suite.")
    print("Example usage:")
    print("")
    print("  from performance.integration import init_performance")
    print("")
    print("  # Initialize with Flask app")
    print("  init_performance(app)")