"""
Database Optimization Module

This module provides tools for optimizing database performance through query optimization,
connection pooling, and efficient data access patterns.
"""

import time
import logging
import functools
import threading
from typing import Dict, List, Optional, Union, Callable, Any, Tuple, Set
from contextlib import contextmanager

# Import SQLAlchemy components
try:
    from sqlalchemy import event, create_engine, text
    from sqlalchemy.orm import scoped_session, sessionmaker, Query
    from sqlalchemy.engine import Engine
    from sqlalchemy.sql import select, insert, update, delete
    from flask_sqlalchemy import SQLAlchemy
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

# Initialize logging
from logging_config import get_logger
logger = get_logger('performance.database')

# Import cache manager if available
try:
    from performance.cache_manager import cached, get_cache_manager
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    def cached(*args, **kwargs):
        """Dummy cached decorator when cache is not available."""
        def decorator(func):
            return func
        return decorator


class QueryPerformanceTracker:
    """
    Tracks and analyzes query performance.
    """
    
    def __init__(self, slow_query_threshold: float = 0.5):
        """
        Initialize query performance tracker.
        
        Args:
            slow_query_threshold: Threshold in seconds for slow query logging
        """
        self.slow_query_threshold = slow_query_threshold
        self.query_stats: Dict[str, Dict[str, Union[int, float]]] = {}
        self.slow_queries: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
    
    def track_query(self, query: str, duration: float, params: Optional[Dict[str, Any]] = None,
                   source: Optional[str] = None):
        """
        Track a database query.
        
        Args:
            query: SQL query string
            duration: Query execution time in seconds
            params: Query parameters
            source: Source of the query (e.g., function name)
        """
        with self._lock:
            # Normalize the query (remove specific values, whitespace)
            normalized_query = self._normalize_query(query)
            
            # Update query stats
            if normalized_query not in self.query_stats:
                self.query_stats[normalized_query] = {
                    'count': 0,
                    'total_time': 0.0,
                    'min_time': float('inf'),
                    'max_time': 0.0,
                    'avg_time': 0.0
                }
            
            stats = self.query_stats[normalized_query]
            stats['count'] += 1
            stats['total_time'] += duration
            stats['min_time'] = min(stats['min_time'], duration)
            stats['max_time'] = max(stats['max_time'], duration)
            stats['avg_time'] = stats['total_time'] / stats['count']
            
            # Log slow queries
            if duration >= self.slow_query_threshold:
                self.slow_queries.append({
                    'query': query,
                    'params': params,
                    'duration': duration,
                    'timestamp': time.time(),
                    'source': source
                })
                
                logger.warning(f"Slow query detected ({duration:.3f}s): {query}")
                if source:
                    logger.warning(f"Query source: {source}")
    
    def _normalize_query(self, query: str) -> str:
        """
        Normalize a SQL query for grouping similar queries.
        
        Args:
            query: SQL query string
            
        Returns:
            Normalized query string
        """
        # This is a simple normalization that removes numbers and simplifies whitespace
        # For production, consider a more sophisticated SQL parser
        import re
        
        # Replace numeric literals
        query = re.sub(r'\b\d+\b', '?', query)
        
        # Replace string literals
        query = re.sub(r"'[^']*'", "'?'", query)
        
        # Normalize whitespace
        query = re.sub(r'\s+', ' ', query)
        
        return query.strip()
    
    def get_slow_queries(self) -> List[Dict[str, Any]]:
        """
        Get list of slow queries.
        
        Returns:
            List of slow query details
        """
        with self._lock:
            return list(self.slow_queries)
    
    def get_query_stats(self) -> Dict[str, Dict[str, Union[int, float]]]:
        """
        Get query statistics.
        
        Returns:
            Dictionary of query statistics
        """
        with self._lock:
            return dict(self.query_stats)
    
    def get_top_queries(self, limit: int = 10, sort_by: str = 'total_time') -> List[Tuple[str, Dict[str, Union[int, float]]]]:
        """
        Get top queries by count or time.
        
        Args:
            limit: Number of queries to return
            sort_by: Field to sort by ('count', 'total_time', 'avg_time', 'max_time')
            
        Returns:
            List of (query, stats) tuples
        """
        with self._lock:
            sorted_queries = sorted(
                self.query_stats.items(),
                key=lambda x: x[1][sort_by],
                reverse=True
            )
            return sorted_queries[:limit]
    
    def clear_stats(self):
        """Clear all collected statistics."""
        with self._lock:
            self.query_stats.clear()
            self.slow_queries.clear()


class QueryOptimizer:
    """
    Optimizes database queries for better performance.
    """
    
    def __init__(self, db=None):
        """
        Initialize query optimizer.
        
        Args:
            db: SQLAlchemy database instance
        """
        self.db = db
        self.performance_tracker = QueryPerformanceTracker()
        
        # Only set up query tracking if SQLAlchemy is available
        if SQLALCHEMY_AVAILABLE and db is not None:
            self._setup_query_tracking()
    
    def _setup_query_tracking(self):
        """Set up query execution tracking for SQLAlchemy."""
        if hasattr(self.db, 'engine'):
            # Set up event listener for query execution
            @event.listens_for(self.db.engine, 'before_cursor_execute')
            def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
                conn.info.setdefault('query_start_time', []).append(time.time())
            
            @event.listens_for(self.db.engine, 'after_cursor_execute')
            def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
                start_time = conn.info['query_start_time'].pop()
                duration = time.time() - start_time
                
                # Get source of query if available
                source = None
                if hasattr(context, 'compiled'):
                    if hasattr(context.compiled, '_annotations'):
                        source = context.compiled._annotations.get('source')
                
                # Track the query
                self.performance_tracker.track_query(statement, duration, parameters, source)
    
    def optimize_query(self, query: Any, **kwargs) -> Any:
        """
        Optimize a SQLAlchemy query.
        
        Args:
            query: SQLAlchemy query object
            **kwargs: Additional optimization parameters
            
        Returns:
            Optimized query
        """
        if not SQLALCHEMY_AVAILABLE:
            return query
        
        # Skip optimization if not a SQLAlchemy Query
        if not isinstance(query, Query):
            return query
        
        # Apply various optimizations based on query type
        query = self._optimize_eager_loading(query, **kwargs)
        query = self._optimize_pagination(query, **kwargs)
        query = self._add_query_annotations(query, **kwargs)
        
        return query
    
    def _optimize_eager_loading(self, query: Query, **kwargs) -> Query:
        """
        Optimize eager loading relationships.
        
        Args:
            query: SQLAlchemy query
            **kwargs: Additional parameters
            
        Returns:
            Optimized query
        """
        # Get eager load relationships from kwargs
        eager_load = kwargs.get('eager_load', [])
        
        if eager_load:
            # Convert string to list if needed
            if isinstance(eager_load, str):
                eager_load = [eager_load]
            
            # Apply joinedload for each relationship
            for relationship in eager_load:
                query = query.options(joinedload(relationship))
        
        return query
    
    def _optimize_pagination(self, query: Query, **kwargs) -> Query:
        """
        Optimize pagination queries.
        
        Args:
            query: SQLAlchemy query
            **kwargs: Additional parameters
            
        Returns:
            Optimized query
        """
        # Check if pagination is requested
        page = kwargs.get('page')
        per_page = kwargs.get('per_page')
        
        if page is not None and per_page is not None:
            # Use efficient pagination (window functions if supported)
            if self._supports_window_functions():
                # This is a placeholder - actual implementation would depend on database
                # For MySQL 8+, PostgreSQL, Oracle, SQL Server, window functions can be used
                # Example: 
                # query = query.add_columns(func.row_number().over(order_by=query._order_by).label('row_num'))
                pass
            else:
                # Fall back to standard LIMIT/OFFSET
                query = query.limit(per_page).offset((page - 1) * per_page)
        
        return query
    
    def _add_query_annotations(self, query: Query, **kwargs) -> Query:
        """
        Add annotations to the query for tracking.
        
        Args:
            query: SQLAlchemy query
            **kwargs: Additional parameters
            
        Returns:
            Annotated query
        """
        # Extract caller information if available
        source = kwargs.get('source')
        
        if source:
            # Add source annotation to the query
            query = query.execution_options(compile_kwargs={"annotations": {"source": source}})
        
        return query
    
    def _supports_window_functions(self) -> bool:
        """
        Check if the database supports window functions.
        
        Returns:
            True if window functions are supported
        """
        if not self.db:
            return False
        
        # Check the database dialect
        dialect = self.db.engine.dialect.name
        
        # Dialects that support window functions
        window_function_dialects = {'postgresql', 'oracle', 'mssql', 'mysql'}
        
        # For MySQL, check version (8.0+ supports window functions)
        if dialect == 'mysql':
            try:
                conn = self.db.engine.connect()
                result = conn.execute(text("SELECT VERSION()"))
                version = result.scalar()
                conn.close()
                
                if version and version.split('.')[0] >= '8':
                    return True
                return False
            except:
                return False
        
        return dialect in window_function_dialects

    @contextmanager
    def optimized_query_context(self, **optimization_options):
        """
        Context manager for optimized queries.
        
        Args:
            **optimization_options: Options for query optimization
            
        Yields:
            Query optimizer instance
        """
        # Store optimization options
        self._optimization_options = optimization_options
        
        try:
            yield self
        finally:
            # Clear optimization options
            self._optimization_options = {}
    
    def apply_default_optimizations(self, query):
        """
        Apply default optimizations to a query.
        
        Args:
            query: SQLAlchemy query
            
        Returns:
            Optimized query
        """
        return self.optimize_query(query, **getattr(self, '_optimization_options', {}))


class ConnectionPoolManager:
    """
    Manages database connection pooling for optimal performance.
    """
    
    def __init__(self, db=None, pool_size=10, max_overflow=20, pool_timeout=30, pool_recycle=3600):
        """
        Initialize connection pool manager.
        
        Args:
            db: SQLAlchemy database instance
            pool_size: Connection pool size
            max_overflow: Maximum number of connections to create beyond pool_size
            pool_timeout: Seconds to wait before giving up on getting a connection
            pool_recycle: Seconds after which a connection is automatically recycled
        """
        self.db = db
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        
        # Only set up pool monitoring if SQLAlchemy is available
        if SQLALCHEMY_AVAILABLE and db is not None:
            self._setup_pool_monitoring()
    
    def _setup_pool_monitoring(self):
        """Set up connection pool monitoring."""
        if hasattr(self.db, 'engine'):
            # Set up event listeners for pool events
            @event.listens_for(self.db.engine, 'checkout')
            def receive_checkout(dbapi_connection, connection_record, connection_proxy):
                connection_record.info.setdefault('checkout_time', time.time())
            
            @event.listens_for(self.db.engine, 'checkin')
            def receive_checkin(dbapi_connection, connection_record):
                checkout_time = connection_record.info.get('checkout_time')
                if checkout_time:
                    connection_time = time.time() - checkout_time
                    if connection_time > 5:  # Log long connections
                        logger.warning(f"Database connection held for {connection_time:.2f} seconds")
    
    def configure_pool(self, app=None):
        """
        Configure connection pooling for an application.
        
        Args:
            app: Flask application to configure
        """
        if not SQLALCHEMY_AVAILABLE:
            logger.warning("SQLAlchemy not available, cannot configure connection pooling")
            return
        
        if app:
            # Configure SQLAlchemy pool settings
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                'pool_size': self.pool_size,
                'max_overflow': self.max_overflow,
                'pool_timeout': self.pool_timeout,
                'pool_recycle': self.pool_recycle,
                'pool_pre_ping': True,  # Enable pre-ping for dead connection detection
            }
            
            logger.info(f"Configured database connection pool: size={self.pool_size}, max_overflow={self.max_overflow}")
    
    def get_pool_status(self) -> Dict[str, Any]:
        """
        Get current connection pool status.
        
        Returns:
            Dictionary with pool status information
        """
        if not SQLALCHEMY_AVAILABLE or not self.db or not hasattr(self.db, 'engine'):
            return {'error': 'SQLAlchemy engine not available'}
        
        pool = self.db.engine.pool
        
        return {
            'size': self.pool_size,
            'max_overflow': self.max_overflow,
            'timeout': self.pool_timeout,
            'recycle': self.pool_recycle,
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'checkedin': pool.checkedin()
        }
    
    def optimize_for_read_heavy(self):
        """Optimize connection pool for read-heavy workloads."""
        self.pool_size = max(20, self.pool_size)
        self.max_overflow = max(30, self.max_overflow)
        self.pool_timeout = min(10, self.pool_timeout)  # Shorter timeout for faster failures
        
        if self.db and hasattr(self.db, 'engine'):
            # Update engine pool settings
            self.db.engine.pool.pool_size = self.pool_size
            self.db.engine.pool.max_overflow = self.max_overflow
            self.db.engine.pool.timeout = self.pool_timeout
    
    def optimize_for_write_heavy(self):
        """Optimize connection pool for write-heavy workloads."""
        self.pool_size = max(15, self.pool_size)
        self.max_overflow = max(15, self.max_overflow)
        self.pool_recycle = min(1800, self.pool_recycle)  # Shorter recycle time for fresher connections
        
        if self.db and hasattr(self.db, 'engine'):
            # Update engine pool settings
            self.db.engine.pool.pool_size = self.pool_size
            self.db.engine.pool.max_overflow = self.max_overflow
            self.db.engine.pool.recycle = self.pool_recycle


class QueryCache:
    """
    Caches database query results for improved performance.
    """
    
    def __init__(self, default_ttl: int = 300):
        """
        Initialize query cache.
        
        Args:
            default_ttl: Default time-to-live for cached queries in seconds
        """
        self.default_ttl = default_ttl
        self.cache_enabled = CACHE_AVAILABLE
        
        if not self.cache_enabled:
            logger.warning("Cache manager not available, query caching is disabled")
    
    def cached_query(self, ttl: Optional[int] = None, cache_key_prefix: Optional[str] = None):
        """
        Decorator for caching query results.
        
        Args:
            ttl: Time-to-live in seconds (overrides default)
            cache_key_prefix: Custom cache key prefix
            
        Returns:
            Decorated function
        """
        if not self.cache_enabled:
            # Return a no-op decorator if caching is disabled
            def decorator(func):
                return func
            return decorator
        
        # Use the cache manager's cached decorator
        return cached(ttl=ttl or self.default_ttl, key_prefix=cache_key_prefix)
    
    def invalidate_query_cache(self, model_name: str) -> bool:
        """
        Invalidate cache for a specific model.
        
        Args:
            model_name: Name of the model to invalidate cache for
            
        Returns:
            True if successful
        """
        if not self.cache_enabled:
            return False
        
        try:
            # Get cache manager and clear with prefix
            cache_manager = get_cache_manager()
            return cache_manager.clear(prefix=model_name)
        except Exception as e:
            logger.error(f"Error invalidating query cache: {e}")
            return False
    
    def cached_model_query(self, model_class, query_method_name: str = 'query', ttl: Optional[int] = None):
        """
        Decorator for caching model queries.
        
        Args:
            model_class: SQLAlchemy model class
            query_method_name: Name of the query method on the model
            ttl: Time-to-live in seconds (overrides default)
            
        Returns:
            Decorated function
        """
        if not self.cache_enabled:
            # Return a no-op decorator if caching is disabled
            def decorator(func):
                return func
            return decorator
        
        # Get model name for cache key prefix
        model_name = model_class.__name__
        
        # Use the cache manager's cached decorator
        return cached(ttl=ttl or self.default_ttl, key_prefix=f"{model_name}.{query_method_name}")


# Function to optimize database for Flask-SQLAlchemy
def optimize_flask_sqlalchemy(app, db):
    """
    Optimize Flask-SQLAlchemy for production.
    
    Args:
        app: Flask application
        db: SQLAlchemy database instance
        
    Returns:
        Tuple of (query_optimizer, connection_pool_manager, query_cache)
    """
    if not SQLALCHEMY_AVAILABLE:
        logger.warning("SQLAlchemy not available, cannot optimize database")
        return None, None, None
    
    # Create optimization components
    query_optimizer = QueryOptimizer(db)
    connection_pool_manager = ConnectionPoolManager(db)
    query_cache = QueryCache()
    
    # Configure connection pooling
    connection_pool_manager.configure_pool(app)
    
    # Set up SQLAlchemy query events
    if hasattr(db, 'session'):
        # Add query tracking
        @event.listens_for(db.session, 'before_flush')
        def before_flush(session, flush_context, instances):
            # Annotate queries with source information if possible
            for obj in session.new | session.dirty:
                # Could add more detailed tracking here
                pass
    
    # Add helpers to db object
    db.optimize_query = query_optimizer.optimize_query
    db.invalidate_cache = query_cache.invalidate_query_cache
    db.cached_query = query_cache.cached_query
    
    return query_optimizer, connection_pool_manager, query_cache

# Initialize for Flask app
def init_app(app):
    """
    Initialize database optimization for a Flask app.
    
    Args:
        app: Flask application
        
    Returns:
        Tuple of (query_optimizer, connection_pool_manager, query_cache)
    """
    # Get database instance from app
    db = app.extensions.get('sqlalchemy')
    
    if db:
        # Optimize Flask-SQLAlchemy
        optimizers = optimize_flask_sqlalchemy(app, db.db)
        
        # Store optimizers on app for access
        app.db_query_optimizer = optimizers[0]
        app.db_connection_pool_manager = optimizers[1]
        app.db_query_cache = optimizers[2]
        
        return optimizers
    else:
        logger.warning("SQLAlchemy extension not found in Flask app")
        return None, None, None