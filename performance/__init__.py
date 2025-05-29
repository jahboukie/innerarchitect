#!/usr/bin/env python
"""
Performance Optimization Suite for Inner Architect

This package provides comprehensive performance optimization tools including:
- Asset optimization (minification, bundling, caching)
- Database query caching
- Memory profiling and leak detection
- Performance monitoring and metrics
- Image optimization
- Frontend code splitting
- Response compression
"""

from typing import Dict, Any, Optional, Callable

from flask import Flask

from performance.performance_suite import (
    PerformanceOptimizationSuite,
    create_suite,
    optimize_query,
    profile_performance,
    profile_memory
)

from performance.asset_optimizer import AssetOptimizer, register_asset_helper
from performance.query_cache import setup_query_cache, cache_query
from performance.memory_profiler import MemoryProfiler, profile_memory
from performance.performance_monitor import PerformanceMonitor, profile

# Version
__version__ = "1.0.0"


def init_performance_suite(app: Flask, config: Optional[Dict[str, Any]] = None) -> PerformanceOptimizationSuite:
    """
    Initialize the performance optimization suite with a Flask application.
    
    Args:
        app: Flask application instance
        config: Configuration dictionary (optional)
        
    Returns:
        Configured performance suite instance
    """
    # Create and initialize suite
    suite = create_suite(app)
    
    # Apply custom configuration if provided
    if config:
        for key, value in config.items():
            setattr(suite, key, value)
    
    return suite


__all__ = [
    "PerformanceOptimizationSuite",
    "AssetOptimizer",
    "MemoryProfiler",
    "PerformanceMonitor",
    "init_performance_suite",
    "create_suite",
    "optimize_query",
    "profile_performance",
    "profile_memory",
    "cache_query",
    "profile",
    "__version__",
]