#!/usr/bin/env python
"""
Performance Optimization Suite Main Module

This module provides the main entry point for integrating all performance
optimization components into the Inner Architect application.
"""

import logging
import os
import sys
from typing import Dict, Any, Optional, List, Tuple

from flask import Flask

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("performance.main")


def setup_performance_optimization(app: Flask, config: Optional[Dict[str, Any]] = None) -> None:
    """
    Set up and integrate all performance optimization components.
    
    This is the main entry point for integrating performance optimization with
    the Inner Architect application.
    
    Args:
        app: Flask application instance
        config: Optional configuration dictionary
    """
    # Check dependencies
    from performance.performance_integrator import check_performance_dependencies
    all_installed, missing = check_performance_dependencies()
    
    if not all_installed:
        logger.warning(
            f"Some performance optimization dependencies are missing: {', '.join(missing)}\n"
            "Full functionality may not be available."
        )
    
    # Initialize core components
    try:
        # Import the performance integrator
        from performance.performance_integrator import initialize_performance
        
        # Initialize all performance components
        integrator = initialize_performance(app, config)
        
        if integrator:
            logger.info("Performance optimization suite successfully initialized")
        else:
            logger.warning("Performance optimization is disabled in configuration")
    
    except Exception as e:
        logger.error(f"Error setting up performance optimization: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


def optimize_existing_code_paths(app: Flask) -> None:
    """
    Apply performance optimizations to existing code paths in the application.
    
    This function identifies critical code paths in the application and applies
    appropriate performance optimizations such as caching and query optimization.
    
    Args:
        app: Flask application instance
    """
    try:
        # Import optimization decorators
        from performance.performance_suite import optimize_query, profile_performance
        
        # Apply optimizations to database models
        logger.info("Applying database query optimization to critical code paths...")
        
        # Check if SQLAlchemy is being used
        if 'sqlalchemy' in app.extensions:
            # Try to optimize common model query methods
            try:
                from models import User, Session, Technique
                
                # Apply caching to frequently used queries
                if hasattr(User, 'get_by_id'):
                    User.get_by_id = optimize_query(expire=300)(User.get_by_id)
                    logger.info("Optimized User.get_by_id with query caching")
                
                if hasattr(Session, 'get_recent'):
                    Session.get_recent = optimize_query(expire=60)(Session.get_recent)
                    logger.info("Optimized Session.get_recent with query caching")
                
                if hasattr(Technique, 'get_all'):
                    Technique.get_all = optimize_query(expire=3600)(Technique.get_all)
                    logger.info("Optimized Technique.get_all with query caching")
            
            except (ImportError, AttributeError) as e:
                logger.warning(f"Could not optimize model queries: {str(e)}")
        
        # Optimize route handlers for frequently accessed pages
        from flask import current_app
        for endpoint, view_func in current_app.view_functions.items():
            # Skip static and admin endpoints
            if endpoint.startswith('static') or endpoint.startswith('admin'):
                continue
            
            # Apply performance profiling to view functions
            current_app.view_functions[endpoint] = profile_performance()(view_func)
        
        logger.info("Applied performance profiling to route handlers")
    
    except Exception as e:
        logger.error(f"Error optimizing existing code paths: {str(e)}")


def create_performance_dashboard_template() -> None:
    """Create the performance dashboard template if it doesn't exist."""
    # Template directory path
    template_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "templates",
        "admin",
        "performance"
    )
    
    # Create directory if it doesn't exist
    os.makedirs(template_dir, exist_ok=True)
    
    # Check if dashboard template exists
    dashboard_path = os.path.join(template_dir, "dashboard.html")
    if os.path.exists(dashboard_path):
        return
    
    # Create dashboard template
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
                    <h5 class="card-title mb-0">Performance Overview</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-3">
                            <div class="card bg-light">
                                <div class="card-body text-center">
                                    <h3 id="avgResponseTime">--</h3>
                                    <p class="text-muted mb-0">Avg. Response Time</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="card bg-light">
                                <div class="card-body text-center">
                                    <h3 id="cacheHitRate">--</h3>
                                    <p class="text-muted mb-0">Cache Hit Rate</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="card bg-light">
                                <div class="card-body text-center">
                                    <h3 id="memoryUsage">--</h3>
                                    <p class="text-muted mb-0">Memory Usage</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="card bg-light">
                                <div class="card-body text-center">
                                    <h3 id="activeConnections">--</h3>
                                    <p class="text-muted mb-0">Active Connections</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
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
        .then(data => {
            updateRequestChart(data);
            
            // Update overview stats
            if (data.summary && data.summary.avg_time_ms) {
                document.getElementById('avgResponseTime').textContent = 
                    data.summary.avg_time_ms.toFixed(2) + ' ms';
            }
            
            if (data.summary && data.summary.active_connections) {
                document.getElementById('activeConnections').textContent = 
                    data.summary.active_connections;
            }
        })
        .catch(error => console.error('Error loading request metrics:', error));
    
    // Load memory metrics
    fetch('/api/performance/memory')
        .then(response => response.json())
        .then(data => {
            updateMemoryChart(data);
            
            // Update overview stats
            if (data.current && data.current.rss_mb) {
                document.getElementById('memoryUsage').textContent = 
                    data.current.rss_mb.toFixed(2) + ' MB';
            }
        })
        .catch(error => console.error('Error loading memory metrics:', error));
    
    // Load query metrics
    fetch('/api/performance/queries')
        .then(response => response.json())
        .then(data => {
            updateQueryChart(data);
            
            // Update overview stats
            if (data.summary && data.summary.hit_rate) {
                document.getElementById('cacheHitRate').textContent = 
                    (data.summary.hit_rate * 100).toFixed(1) + '%';
            }
        })
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
        const date = new Date(point.timestamp * 1000);
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
    if (!data.system) return;
    
    const system = data.system;
    
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


if __name__ == "__main__":
    print("Performance Optimization Suite for Inner Architect")
    print("")
    print("This module provides the main entry point for integrating all performance")
    print("optimization components into the Inner Architect application.")
    print("")
    print("To use in your Flask application:")
    print("")
    print("  from performance.main import setup_performance_optimization")
    print("")
    print("  # Initialize Flask app")
    print("  app = Flask(__name__)")
    print("")
    print("  # Set up performance optimization")
    print("  setup_performance_optimization(app)")
    
    # Create performance dashboard template
    create_performance_dashboard_template()