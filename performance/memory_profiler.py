#!/usr/bin/env python
"""
Memory Profiler for Inner Architect

This module provides tools for memory profiling and analysis to help identify
memory leaks, track object lifetimes, and optimize memory usage.

Features:
- Object reference tracking
- Memory leak detection
- Heap dumping and analysis
- Memory usage timeline
- Per-request memory profiling
"""

import gc
import inspect
import io
import linecache
import os
import sys
import threading
import time
import traceback
from collections import defaultdict, deque
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union

import psutil

try:
    import objgraph
    OBJGRAPH_AVAILABLE = True
except ImportError:
    OBJGRAPH_AVAILABLE = False

try:
    import pympler.tracker
    PYMPLER_AVAILABLE = True
except ImportError:
    PYMPLER_AVAILABLE = False

# Set up logging
import logging
logger = logging.getLogger("memory_profiler")

# Thread-local storage
_thread_local = threading.local()

# Memory snapshots for tracking
_memory_snapshots = []
_snapshot_lock = threading.Lock()

# Maximum number of snapshots to keep
MAX_SNAPSHOTS = 100

# Memory tracking settings
TRACK_TOP_OBJECTS = 50
SNAPSHOT_INTERVAL_SECONDS = 300  # 5 minutes


class MemorySnapshot:
    """Snapshot of memory usage at a specific point in time."""
    
    def __init__(self, trigger: str = "manual"):
        """
        Create a memory snapshot.
        
        Args:
            trigger: What triggered this snapshot
        """
        self.timestamp = datetime.now()
        self.trigger = trigger
        
        # Process info
        process = psutil.Process(os.getpid())
        self.process_info = {
            "pid": process.pid,
            "memory_info": dict(process.memory_info()._asdict()),
            "memory_percent": process.memory_percent(),
            "memory_maps": None,  # Too detailed for regular snapshots
            "num_threads": process.num_threads(),
            "num_fds": process.num_fds() if hasattr(process, "num_fds") else None,
            "cpu_percent": process.cpu_percent(interval=0.1)
        }
        
        # System memory info
        vm = psutil.virtual_memory()
        self.system_info = {
            "total": vm.total,
            "available": vm.available,
            "percent": vm.percent,
            "used": vm.used,
            "free": vm.free
        }
        
        # Python object stats
        self.python_stats = self._get_python_stats()
        
        # Call stack if requested
        self.stack_trace = None
        if trigger in ["leak_suspected", "high_memory", "explicit"]:
            self.stack_trace = traceback.format_stack()
    
    def _get_python_stats(self) -> Dict[str, Any]:
        """
        Get statistics about Python objects.
        
        Returns:
            Dictionary of Python object statistics
        """
        gc.collect()
        
        # Count objects by type
        type_counts = defaultdict(int)
        type_sizes = defaultdict(int)
        
        for obj in gc.get_objects():
            obj_type = type(obj).__name__
            type_counts[obj_type] += 1
            
            # Estimate size if pympler is available
            if PYMPLER_AVAILABLE:
                try:
                    size = pympler.asizeof.asizeof(obj)
                    type_sizes[obj_type] += size
                except:
                    pass
        
        # Get top types by count
        top_types_by_count = sorted(
            type_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:TRACK_TOP_OBJECTS]
        
        # Get top types by size if available
        top_types_by_size = []
        if type_sizes:
            top_types_by_size = sorted(
                type_sizes.items(),
                key=lambda x: x[1],
                reverse=True
            )[:TRACK_TOP_OBJECTS]
        
        # Get garbage collector stats
        gc_stats = {
            "garbage": len(gc.garbage),
            "collections": [gc.get_count()[i] for i in range(3)],
            "thresholds": [gc.get_threshold()[i] for i in range(3)]
        }
        
        # Get detailed object graphs if objgraph is available
        growth_stats = {}
        if OBJGRAPH_AVAILABLE:
            try:
                # Get top growing types
                growth_stats["growth"] = objgraph.growth(limit=20)
            except:
                pass
        
        return {
            "total_objects": sum(type_counts.values()),
            "type_counts": dict(top_types_by_count),
            "type_sizes": dict(top_types_by_size) if top_types_by_size else None,
            "gc_stats": gc_stats,
            "growth_stats": growth_stats if growth_stats else None
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert snapshot to dictionary for serialization.
        
        Returns:
            Dictionary representation of the snapshot
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "trigger": self.trigger,
            "process_info": self.process_info,
            "system_info": self.system_info,
            "python_stats": self.python_stats,
            "stack_trace": self.stack_trace
        }
    
    def get_rss_mb(self) -> float:
        """
        Get resident set size in MB.
        
        Returns:
            RSS in MB
        """
        return self.process_info["memory_info"]["rss"] / (1024 * 1024)
    
    def get_growth_since(self, previous: 'MemorySnapshot') -> Dict[str, Any]:
        """
        Calculate memory growth since a previous snapshot.
        
        Args:
            previous: Previous memory snapshot
            
        Returns:
            Dictionary with growth information
        """
        # Calculate basic growth
        rss_diff = (
            self.process_info["memory_info"]["rss"] - 
            previous.process_info["memory_info"]["rss"]
        )
        rss_diff_mb = rss_diff / (1024 * 1024)
        
        # Calculate percentage growth
        prev_rss = previous.process_info["memory_info"]["rss"]
        rss_percent = (rss_diff / prev_rss) * 100 if prev_rss > 0 else 0
        
        # Calculate time difference
        time_diff = self.timestamp - previous.timestamp
        minutes = time_diff.total_seconds() / 60
        
        # Calculate growth rate (MB per hour)
        growth_rate = (rss_diff_mb / time_diff.total_seconds()) * 3600
        
        # Calculate object count changes
        curr_obj_count = self.python_stats["total_objects"]
        prev_obj_count = previous.python_stats["total_objects"]
        obj_diff = curr_obj_count - prev_obj_count
        
        # Calculate type count changes
        type_changes = {}
        
        for obj_type, count in self.python_stats["type_counts"].items():
            prev_count = previous.python_stats["type_counts"].get(obj_type, 0)
            diff = count - prev_count
            if diff != 0:
                type_changes[obj_type] = diff
        
        # Sort type changes by absolute difference
        sorted_changes = sorted(
            type_changes.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:TRACK_TOP_OBJECTS]
        
        return {
            "rss_diff_mb": rss_diff_mb,
            "rss_percent": rss_percent,
            "time_diff_minutes": minutes,
            "growth_rate_mb_per_hour": growth_rate,
            "object_count_diff": obj_diff,
            "type_changes": dict(sorted_changes)
        }


class MemoryProfiler:
    """Memory profiling and analysis for Flask applications."""
    
    def __init__(
        self,
        app=None,
        snapshot_interval: int = SNAPSHOT_INTERVAL_SECONDS,
        max_snapshots: int = MAX_SNAPSHOTS,
        track_top_objects: int = TRACK_TOP_OBJECTS,
        leak_detection_threshold_mb: float = 50.0,
        high_memory_threshold_mb: float = 500.0
    ):
        """
        Initialize memory profiler.
        
        Args:
            app: Flask application instance
            snapshot_interval: Interval between automatic snapshots in seconds
            max_snapshots: Maximum number of snapshots to keep
            track_top_objects: Number of top objects to track
            leak_detection_threshold_mb: Memory growth threshold for leak detection
            high_memory_threshold_mb: Threshold for high memory warnings
        """
        global MAX_SNAPSHOTS, TRACK_TOP_OBJECTS
        
        self.snapshot_interval = snapshot_interval
        MAX_SNAPSHOTS = max_snapshots
        TRACK_TOP_OBJECTS = track_top_objects
        self.leak_detection_threshold_mb = leak_detection_threshold_mb
        self.high_memory_threshold_mb = high_memory_threshold_mb
        
        # Pympler tracker if available
        self.tracker = None
        if PYMPLER_AVAILABLE:
            self.tracker = pympler.tracker.SummaryTracker()
        
        # Initialize snapshot timer
        self.snapshot_timer = None
        self._start_snapshot_timer()
        
        # Take initial snapshot
        self.take_snapshot("startup")
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app) -> None:
        """
        Initialize with a Flask application.
        
        Args:
            app: Flask application instance
        """
        # Store in app extensions
        app.extensions["memory_profiler"] = self
        
        # Configure from app config
        if app.config.get("MEMORY_SNAPSHOT_INTERVAL"):
            self.snapshot_interval = app.config.get("MEMORY_SNAPSHOT_INTERVAL")
        
        if app.config.get("MEMORY_MAX_SNAPSHOTS"):
            global MAX_SNAPSHOTS
            MAX_SNAPSHOTS = app.config.get("MEMORY_MAX_SNAPSHOTS")
        
        if app.config.get("MEMORY_TRACK_TOP_OBJECTS"):
            global TRACK_TOP_OBJECTS
            TRACK_TOP_OBJECTS = app.config.get("MEMORY_TRACK_TOP_OBJECTS")
        
        if app.config.get("MEMORY_LEAK_THRESHOLD_MB"):
            self.leak_detection_threshold_mb = app.config.get("MEMORY_LEAK_THRESHOLD_MB")
        
        if app.config.get("MEMORY_HIGH_THRESHOLD_MB"):
            self.high_memory_threshold_mb = app.config.get("MEMORY_HIGH_THRESHOLD_MB")
        
        # Register request handlers
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        
        # Register memory endpoints
        self._register_endpoints(app)
        
        # Register teardown handler
        @app.teardown_appcontext
        def teardown_memory_profiling(exception=None):
            # Clean up thread local data
            if hasattr(_thread_local, "memory_start"):
                delattr(_thread_local, "memory_start")
    
    def take_snapshot(self, trigger: str = "manual") -> MemorySnapshot:
        """
        Take a snapshot of current memory usage.
        
        Args:
            trigger: What triggered this snapshot
            
        Returns:
            Memory snapshot object
        """
        snapshot = MemorySnapshot(trigger)
        
        # Check for memory growth if we have previous snapshots
        self._check_memory_growth(snapshot)
        
        # Add to snapshots list with lock
        with _snapshot_lock:
            _memory_snapshots.append(snapshot)
            
            # Trim if exceeding max snapshots
            if len(_memory_snapshots) > MAX_SNAPSHOTS:
                _memory_snapshots.pop(0)
        
        return snapshot
    
    def _check_memory_growth(self, snapshot: MemorySnapshot) -> None:
        """
        Check for significant memory growth since last snapshot.
        
        Args:
            snapshot: Current memory snapshot
        """
        with _snapshot_lock:
            if not _memory_snapshots:
                return
            
            # Get the previous snapshot
            prev_snapshot = _memory_snapshots[-1]
            
            # Calculate growth
            growth = snapshot.get_growth_since(prev_snapshot)
            
            # Check for high memory usage
            if snapshot.get_rss_mb() > self.high_memory_threshold_mb:
                logger.warning(
                    f"High memory usage detected: {snapshot.get_rss_mb():.2f}MB "
                    f"(threshold: {self.high_memory_threshold_mb}MB)"
                )
                
                # Log top memory types
                top_types = list(snapshot.python_stats["type_counts"].items())[:10]
                logger.info(f"Top object types: {top_types}")
            
            # Check for significant growth
            if (growth["rss_diff_mb"] > self.leak_detection_threshold_mb and 
                    growth["time_diff_minutes"] < 60):
                logger.warning(
                    f"Significant memory growth detected: {growth['rss_diff_mb']:.2f}MB "
                    f"in {growth['time_diff_minutes']:.2f} minutes "
                    f"({growth['growth_rate_mb_per_hour']:.2f}MB/hour)"
                )
                
                # Log significant type changes
                significant_changes = {
                    t: c for t, c in growth["type_changes"].items() if c > 100
                }
                if significant_changes:
                    logger.info(f"Significant type growth: {significant_changes}")
                
                # If objgraph is available, log growth data
                if OBJGRAPH_AVAILABLE and snapshot.python_stats.get("growth_stats"):
                    growth_data = snapshot.python_stats["growth_stats"].get("growth", [])
                    if growth_data:
                        logger.info(f"Object growth data: {growth_data[:10]}")
    
    def _start_snapshot_timer(self) -> None:
        """Start the automatic snapshot timer."""
        def snapshot_job():
            try:
                self.take_snapshot("automatic")
            except Exception as e:
                logger.error(f"Error taking automatic snapshot: {str(e)}")
            finally:
                # Schedule next snapshot
                self.snapshot_timer = threading.Timer(
                    self.snapshot_interval, snapshot_job
                )
                self.snapshot_timer.daemon = True
                self.snapshot_timer.start()
        
        # Schedule first snapshot
        self.snapshot_timer = threading.Timer(self.snapshot_interval, snapshot_job)
        self.snapshot_timer.daemon = True
        self.snapshot_timer.start()
    
    def get_snapshots(self) -> List[MemorySnapshot]:
        """
        Get all memory snapshots.
        
        Returns:
            List of memory snapshots
        """
        with _snapshot_lock:
            return list(_memory_snapshots)
    
    def get_latest_snapshot(self) -> Optional[MemorySnapshot]:
        """
        Get the latest memory snapshot.
        
        Returns:
            Latest memory snapshot or None if no snapshots
        """
        with _snapshot_lock:
            if not _memory_snapshots:
                return None
            return _memory_snapshots[-1]
    
    def clear_snapshots(self) -> None:
        """Clear all memory snapshots."""
        with _snapshot_lock:
            _memory_snapshots.clear()
    
    def get_memory_timeline(self) -> List[Dict[str, Any]]:
        """
        Get memory usage timeline data.
        
        Returns:
            List of memory data points
        """
        timeline = []
        
        with _snapshot_lock:
            for snapshot in _memory_snapshots:
                # Get basic data for the timeline
                point = {
                    "timestamp": snapshot.timestamp.isoformat(),
                    "rss_mb": snapshot.get_rss_mb(),
                    "virtual_mb": snapshot.process_info["memory_info"]["vms"] / (1024 * 1024),
                    "system_percent": snapshot.system_info["percent"],
                    "total_objects": snapshot.python_stats["total_objects"],
                    "trigger": snapshot.trigger
                }
                timeline.append(point)
        
        return timeline
    
    def get_growth_analysis(self) -> Dict[str, Any]:
        """
        Analyze memory growth between snapshots.
        
        Returns:
            Dictionary with growth analysis
        """
        with _snapshot_lock:
            if len(_memory_snapshots) < 2:
                return {"error": "Not enough snapshots for analysis"}
            
            # Get first and last snapshots for overall growth
            first_snapshot = _memory_snapshots[0]
            last_snapshot = _memory_snapshots[-1]
            
            # Calculate overall growth
            overall_growth = last_snapshot.get_growth_since(first_snapshot)
            
            # Calculate incremental growth between consecutive snapshots
            incremental_growth = []
            for i in range(1, len(_memory_snapshots)):
                curr = _memory_snapshots[i]
                prev = _memory_snapshots[i-1]
                growth = curr.get_growth_since(prev)
                
                incremental_growth.append({
                    "start_time": prev.timestamp.isoformat(),
                    "end_time": curr.timestamp.isoformat(),
                    "duration_minutes": growth["time_diff_minutes"],
                    "rss_diff_mb": growth["rss_diff_mb"],
                    "growth_rate_mb_per_hour": growth["growth_rate_mb_per_hour"],
                    "object_count_diff": growth["object_count_diff"]
                })
            
            # Find highest growth rate periods
            sorted_periods = sorted(
                incremental_growth,
                key=lambda x: abs(x["growth_rate_mb_per_hour"]),
                reverse=True
            )
            top_growth_periods = sorted_periods[:5]
            
            # Calculate type growth
            type_growth = {}
            
            for obj_type, count in last_snapshot.python_stats["type_counts"].items():
                first_count = first_snapshot.python_stats["type_counts"].get(obj_type, 0)
                diff = count - first_count
                if diff != 0:
                    type_growth[obj_type] = diff
            
            # Sort by absolute growth
            sorted_type_growth = sorted(
                type_growth.items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )[:TRACK_TOP_OBJECTS]
            
            return {
                "first_snapshot": first_snapshot.timestamp.isoformat(),
                "last_snapshot": last_snapshot.timestamp.isoformat(),
                "duration_hours": overall_growth["time_diff_minutes"] / 60,
                "overall_growth_mb": overall_growth["rss_diff_mb"],
                "growth_rate_mb_per_hour": overall_growth["growth_rate_mb_per_hour"],
                "total_object_growth": overall_growth["object_count_diff"],
                "type_growth": dict(sorted_type_growth),
                "top_growth_periods": top_growth_periods
            }
    
    def dump_heap(self, output_file: str) -> str:
        """
        Dump heap statistics to a file.
        
        Args:
            output_file: File path for heap dump
            
        Returns:
            Path to the generated file
        """
        if not OBJGRAPH_AVAILABLE:
            return "Error: objgraph module not available"
        
        try:
            # Get top objects by count
            objgraph.show_most_common_types(
                limit=50,
                file=open(f"{output_file}_types.txt", "w")
            )
            
            # Get object growth since last call
            objgraph.show_growth(
                limit=50,
                file=open(f"{output_file}_growth.txt", "w")
            )
            
            # Create a sample graph of references for top object types
            top_types = objgraph.most_common_types(5)
            for obj_type, _ in top_types:
                try:
                    # Find objects of this type
                    objs = objgraph.by_type(obj_type)
                    if objs:
                        # Get one sample object
                        sample = objs[0]
                        # Generate graph for this object
                        objgraph.show_backrefs(
                            [sample],
                            max_depth=5,
                            filename=f"{output_file}_{obj_type}_refs.png"
                        )
                except Exception as e:
                    logger.error(f"Error generating graph for {obj_type}: {str(e)}")
            
            return f"Heap dump generated to {output_file}_*.txt/png"
        except Exception as e:
            logger.error(f"Error dumping heap: {str(e)}")
            return f"Error: {str(e)}"
    
    def detect_leaks(self) -> Dict[str, Any]:
        """
        Run leak detection analysis.
        
        Returns:
            Dictionary with leak analysis results
        """
        # Take a snapshot before analysis
        before_snapshot = self.take_snapshot("leak_detection_start")
        
        # Force garbage collection
        gc.collect()
        
        # Take a snapshot after garbage collection
        after_snapshot = self.take_snapshot("leak_detection_end")
        
        # Calculate differences
        diff = after_snapshot.get_growth_since(before_snapshot)
        
        # Check for uncollectable objects
        uncollectable = len(gc.garbage)
        
        # Check for objects with finalizers
        objects_with_finalizers = 0
        for obj in gc.get_objects():
            if hasattr(obj, "__del__"):
                objects_with_finalizers += 1
        
        # Find potential circular references if objgraph is available
        circular_references = []
        if OBJGRAPH_AVAILABLE:
            try:
                # Find objects that are part of a cycle
                cycle_candidates = []
                for obj in gc.get_objects():
                    if isinstance(obj, (list, dict, set, tuple)):
                        try:
                            if gc.is_tracked(obj) and len(gc.get_referents(obj)) > 0:
                                cycle_candidates.append(obj)
                        except:
                            pass
                
                # Limit to a manageable number
                if len(cycle_candidates) > 100:
                    cycle_candidates = cycle_candidates[:100]
                
                # Find actual cycles
                for obj in cycle_candidates:
                    try:
                        # Create a simple string representation
                        obj_repr = repr(obj)[:100]
                        
                        # Check if object references itself
                        referents = gc.get_referents(obj)
                        if obj in referents:
                            circular_references.append({
                                "type": type(obj).__name__,
                                "repr": obj_repr,
                                "cycle_type": "self_reference"
                            })
                            continue
                        
                        # Check for cycles in reference chain
                        chain = objgraph.find_backref_chain(obj, lambda x: x is obj)
                        if chain and len(chain) > 1:
                            circular_references.append({
                                "type": type(obj).__name__,
                                "repr": obj_repr,
                                "cycle_type": "cycle",
                                "cycle_length": len(chain)
                            })
                    except:
                        pass
            except Exception as e:
                logger.error(f"Error detecting circular references: {str(e)}")
        
        return {
            "before_gc_memory_mb": before_snapshot.get_rss_mb(),
            "after_gc_memory_mb": after_snapshot.get_rss_mb(),
            "memory_diff_mb": diff["rss_diff_mb"],
            "object_count_before": before_snapshot.python_stats["total_objects"],
            "object_count_after": after_snapshot.python_stats["total_objects"],
            "object_count_diff": diff["object_count_diff"],
            "uncollectable_objects": uncollectable,
            "objects_with_finalizers": objects_with_finalizers,
            "circular_references": circular_references[:20] if circular_references else [],
            "type_changes": diff["type_changes"]
        }
    
    def _before_request(self) -> None:
        """Record memory usage before handling a request."""
        _thread_local.memory_start = psutil.Process(os.getpid()).memory_info().rss
    
    def _after_request(self, response) -> Response:
        """
        Record memory usage after handling a request.
        
        Args:
            response: Flask response object
            
        Returns:
            Unmodified response
        """
        if hasattr(_thread_local, "memory_start"):
            # Calculate memory difference
            end_memory = psutil.Process(os.getpid()).memory_info().rss
            memory_diff = end_memory - _thread_local.memory_start
            memory_diff_mb = memory_diff / (1024 * 1024)
            
            # Add memory usage header
            response.headers["X-Memory-Usage-MB"] = f"{memory_diff_mb:.2f}"
            
            # Check for high memory usage per request
            if memory_diff_mb > 10:  # 10MB threshold for a single request
                endpoint = request.endpoint or "unknown"
                logger.warning(
                    f"High memory usage for request: {request.method} {request.path} - "
                    f"{memory_diff_mb:.2f}MB - Endpoint: {endpoint}"
                )
                
                # Take a snapshot for high memory requests
                if memory_diff_mb > 50:  # Higher threshold for snapshot
                    self.take_snapshot(f"high_memory_request:{endpoint}")
        
        return response
    
    def _register_endpoints(self, app) -> None:
        """
        Register memory profiling endpoints.
        
        Args:
            app: Flask application instance
        """
        # Define endpoint for memory analysis
        @app.route("/api/memory/analysis")
        def memory_analysis():
            # Check if user has admin permission
            if not self._check_admin_permission():
                return {"error": "Unauthorized"}, 403
            
            # Take a fresh snapshot
            snapshot = self.take_snapshot("api_request")
            
            # Return memory analysis
            return {
                "current": {
                    "rss_mb": snapshot.get_rss_mb(),
                    "virtual_mb": snapshot.process_info["memory_info"]["vms"] / (1024 * 1024),
                    "memory_percent": snapshot.process_info["memory_percent"],
                    "total_objects": snapshot.python_stats["total_objects"],
                    "top_types": snapshot.python_stats["type_counts"],
                    "timestamp": snapshot.timestamp.isoformat()
                },
                "system": {
                    "total_mb": snapshot.system_info["total"] / (1024 * 1024),
                    "available_mb": snapshot.system_info["available"] / (1024 * 1024),
                    "percent": snapshot.system_info["percent"]
                },
                "timeline": self.get_memory_timeline(),
                "growth": self.get_growth_analysis() if len(_memory_snapshots) > 1 else None
            }
        
        @app.route("/api/memory/snapshot")
        def memory_snapshot():
            # Check if user has admin permission
            if not self._check_admin_permission():
                return {"error": "Unauthorized"}, 403
            
            # Take a new snapshot
            snapshot = self.take_snapshot("api_request")
            
            # Return snapshot data
            return snapshot.to_dict()
        
        @app.route("/api/memory/snapshots")
        def memory_snapshots():
            # Check if user has admin permission
            if not self._check_admin_permission():
                return {"error": "Unauthorized"}, 403
            
            # Get all snapshots
            with _snapshot_lock:
                snapshots = [s.to_dict() for s in _memory_snapshots]
            
            return {"snapshots": snapshots}
        
        @app.route("/api/memory/leaks")
        def memory_leaks():
            # Check if user has admin permission
            if not self._check_admin_permission():
                return {"error": "Unauthorized"}, 403
            
            # Run leak detection
            leak_analysis = self.detect_leaks()
            
            return {"leak_analysis": leak_analysis}
    
    def _check_admin_permission(self) -> bool:
        """
        Check if the current user has admin permission.
        
        Returns:
            True if user has permission, False otherwise
        """
        # Simple implementation for now
        from flask import current_app, g
        
        if current_app.config.get("TESTING", False):
            return True
        
        # Check if user is authenticated and has admin role
        if hasattr(g, "user") and hasattr(g.user, "is_admin"):
            return g.user.is_admin
        
        return False


def profile_memory(func):
    """
    Decorator to profile memory usage of a function.
    
    Args:
        func: Function to profile
        
    Returns:
        Decorated function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get process
        process = psutil.Process(os.getpid())
        
        # Force garbage collection before measuring
        gc.collect()
        
        # Get initial memory usage
        start_memory = process.memory_info().rss
        
        # Call the function
        result = func(*args, **kwargs)
        
        # Force garbage collection after function call
        gc.collect()
        
        # Get final memory usage
        end_memory = process.memory_info().rss
        
        # Calculate difference
        diff = end_memory - start_memory
        diff_mb = diff / (1024 * 1024)
        
        # Log memory usage
        logger.info(f"Memory usage for {func.__name__}: {diff_mb:.2f}MB")
        
        return result
    
    return wrapper


if __name__ == "__main__":
    # Example usage
    print("This module provides memory profiling for Flask applications.")
    print("Example usage:")
    print("")
    print("  from performance.memory_profiler import MemoryProfiler, profile_memory")
    print("")
    print("  # Initialize with Flask app")
    print("  memory_profiler = MemoryProfiler(app)")
    print("")
    print("  # Profile a function's memory usage")
    print("  @profile_memory")
    print("  def memory_intensive_operation():")
    print("      # Do something memory intensive")
    print("      return result")