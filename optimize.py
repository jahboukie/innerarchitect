#!/usr/bin/env python
"""
Performance Optimization CLI for Inner Architect

This script provides command-line tools for performance optimization tasks:
- Asset optimization
- Cache management
- Memory profiling
- Performance analysis
"""

import argparse
import logging
import os
import sys
import time
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("optimize")


def create_app():
    """Create Flask application instance."""
    # Add the parent directory to sys.path
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    # Import the app creation function
    try:
        from app import create_app as app_factory
        return app_factory()
    except ImportError:
        logger.error("Could not import app. Make sure app.py exists and defines create_app().")
        sys.exit(1)


def optimize_assets(args):
    """Optimize static assets."""
    logger.info("Optimizing static assets...")
    
    # Create app instance
    app = create_app()
    
    # Initialize performance suite if not already
    if "performance_suite" not in app.extensions:
        from performance import init_performance_suite
        suite = init_performance_suite(app)
    else:
        suite = app.extensions["performance_suite"]
    
    # Optimize assets
    start_time = time.time()
    manifest = suite.optimize_assets()
    duration = time.time() - start_time
    
    # Print results
    logger.info(f"Asset optimization completed in {duration:.2f}s")
    logger.info(f"Processed {len(manifest)} assets")
    
    if args.verbose:
        for orig, optimized in manifest.items():
            logger.info(f"{orig} -> {optimized}")


def clear_caches(args):
    """Clear application caches."""
    logger.info("Clearing application caches...")
    
    # Create app instance
    app = create_app()
    
    # Initialize performance suite if not already
    if "performance_suite" not in app.extensions:
        from performance import init_performance_suite
        suite = init_performance_suite(app)
    else:
        suite = app.extensions["performance_suite"]
    
    # Clear caches
    suite.clear_caches()
    
    logger.info("Caches cleared successfully")


def analyze_memory(args):
    """Analyze application memory usage."""
    logger.info("Analyzing memory usage...")
    
    # Create app instance
    app = create_app()
    
    # Initialize memory profiler
    from performance.memory_profiler import MemoryProfiler
    profiler = MemoryProfiler(app)
    
    # Take a memory snapshot
    snapshot = profiler.take_snapshot("cli_request")
    
    # Get memory metrics
    memory_mb = snapshot.get_rss_mb()
    total_objects = snapshot.python_stats["total_objects"]
    
    # Print results
    logger.info(f"Current memory usage: {memory_mb:.2f}MB")
    logger.info(f"Total Python objects: {total_objects}")
    
    # Print top object types
    logger.info("Top object types by count:")
    for obj_type, count in list(snapshot.python_stats["type_counts"].items())[:10]:
        logger.info(f"  {obj_type}: {count}")
    
    # Run leak detection if requested
    if args.leak_detection:
        logger.info("Running memory leak detection...")
        leak_info = profiler.detect_leaks()
        
        logger.info(f"Memory after GC: {leak_info['after_gc_memory_mb']:.2f}MB")
        logger.info(f"Object count after GC: {leak_info['object_count_after']}")
        
        if leak_info["uncollectable_objects"] > 0:
            logger.warning(f"Found {leak_info['uncollectable_objects']} uncollectable objects")
        
        if leak_info["circular_references"]:
            logger.warning(f"Found {len(leak_info['circular_references'])} potential circular references")
            
            for i, ref in enumerate(leak_info["circular_references"][:5]):
                logger.warning(f"  {i+1}. {ref['type']} - {ref['cycle_type']}")


def profile_endpoint(args):
    """Profile a specific API endpoint."""
    logger.info(f"Profiling endpoint: {args.endpoint}")
    
    # Create app instance
    app = create_app()
    
    # Initialize performance monitor
    from performance.performance_monitor import PerformanceMonitor
    monitor = PerformanceMonitor(app)
    
    # Create test client
    client = app.test_client()
    
    # Send requests to endpoint
    num_requests = args.requests
    total_time = 0
    
    logger.info(f"Sending {num_requests} requests to {args.endpoint}...")
    
    for i in range(num_requests):
        start_time = time.time()
        response = client.get(args.endpoint)
        duration = time.time() - start_time
        total_time += duration
        
        # Log request
        logger.debug(f"Request {i+1}/{num_requests}: {response.status_code} in {duration:.4f}s")
    
    # Calculate statistics
    avg_time = total_time / num_requests
    
    # Print results
    logger.info(f"Profiling complete:")
    logger.info(f"  Total requests: {num_requests}")
    logger.info(f"  Total time: {total_time:.2f}s")
    logger.info(f"  Average time: {avg_time:.4f}s")
    logger.info(f"  Requests per second: {num_requests / total_time:.2f}")


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Performance Optimization CLI for Inner Architect")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Assets command
    assets_parser = subparsers.add_parser("assets", help="Optimize static assets")
    assets_parser.add_argument("-v", "--verbose", action="store_true", help="Show verbose output")
    assets_parser.set_defaults(func=optimize_assets)
    
    # Cache command
    cache_parser = subparsers.add_parser("cache", help="Manage application caches")
    cache_parser.add_argument("--clear", action="store_true", help="Clear all caches", default=True)
    cache_parser.set_defaults(func=clear_caches)
    
    # Memory command
    memory_parser = subparsers.add_parser("memory", help="Analyze memory usage")
    memory_parser.add_argument("--leak-detection", action="store_true", help="Run leak detection")
    memory_parser.set_defaults(func=analyze_memory)
    
    # Profile command
    profile_parser = subparsers.add_parser("profile", help="Profile application performance")
    profile_parser.add_argument("endpoint", help="Endpoint to profile (e.g., /api/health)")
    profile_parser.add_argument("-r", "--requests", type=int, default=100, help="Number of requests to send")
    profile_parser.set_defaults(func=profile_endpoint)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Run command
    if args.command is None:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == "__main__":
    main()