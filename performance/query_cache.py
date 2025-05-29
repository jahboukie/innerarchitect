#!/usr/bin/env python
"""
Database Query Cache for Inner Architect

This module provides a caching system for database queries to improve performance
by reducing database load and speeding up repeated queries.

It supports:
- In-memory LRU cache for frequent queries
- Redis-based distributed caching
- Automatic cache invalidation based on model changes
- Query parameter-aware caching
- Time-based cache expiration
"""

import hashlib
import inspect
import json
import logging
import pickle
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union

from flask import current_app
from sqlalchemy import event
from sqlalchemy.orm import Query, Session

# Set up logging
logger = logging.getLogger("query_cache")

# Cache storage backends
class CacheBackend:
    """Base class for cache storage backends."""
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        raise NotImplementedError
    
    def set(self, key: str, value: Any, expire: Optional[int] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            expire: Expiration time in seconds (optional)
        """
        raise NotImplementedError
    
    def delete(self, key: str) -> None:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
        """
        raise NotImplementedError
    
    def clear(self) -> None:
        """Clear all values from the cache."""
        raise NotImplementedError


class MemoryCache(CacheBackend):
    """In-memory LRU cache implementation."""
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize in-memory cache.
        
        Args:
            max_size: Maximum number of items to store
        """
        self.max_size = max_size
        self.cache: Dict[str, Tuple[Any, Optional[float]]] = {}
        self.access_times: Dict[str, float] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if key not in self.cache:
            return None
        
        value, expire_time = self.cache[key]
        current_time = time.time()
        
        # Check if expired
        if expire_time is not None and current_time > expire_time:
            self.delete(key)
            return None
        
        # Update access time
        self.access_times[key] = current_time
        
        return value
    
    def set(self, key: str, value: Any, expire: Optional[int] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            expire: Expiration time in seconds (optional)
        """
        current_time = time.time()
        expire_time = current_time + expire if expire is not None else None
        
        # Check if we need to evict
        if len(self.cache) >= self.max_size and key not in self.cache:
            # Evict least recently used
            lru_key = min(self.access_times.items(), key=lambda x: x[1])[0]
            self.delete(lru_key)
        
        # Store value and update access time
        self.cache[key] = (value, expire_time)
        self.access_times[key] = current_time
    
    def delete(self, key: str) -> None:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
        """
        if key in self.cache:
            del self.cache[key]
        
        if key in self.access_times:
            del self.access_times[key]
    
    def clear(self) -> None:
        """Clear all values from the cache."""
        self.cache.clear()
        self.access_times.clear()


class RedisCache(CacheBackend):
    """Redis-based distributed cache implementation."""
    
    def __init__(self, redis_client=None, prefix: str = 'ia_query_cache:'):
        """
        Initialize Redis cache.
        
        Args:
            redis_client: Redis client instance
            prefix: Key prefix for cache entries
        """
        self.prefix = prefix
        self.redis = redis_client
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if self.redis is None:
            return None
        
        prefixed_key = f"{self.prefix}{key}"
        cached_data = self.redis.get(prefixed_key)
        
        if cached_data is None:
            return None
        
        try:
            return pickle.loads(cached_data)
        except (pickle.PickleError, TypeError):
            logger.warning(f"Failed to unpickle cached data for key: {key}")
            return None
    
    def set(self, key: str, value: Any, expire: Optional[int] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            expire: Expiration time in seconds (optional)
        """
        if self.redis is None:
            return
        
        prefixed_key = f"{self.prefix}{key}"
        
        try:
            pickled_value = pickle.dumps(value)
            if expire is not None:
                self.redis.setex(prefixed_key, expire, pickled_value)
            else:
                self.redis.set(prefixed_key, pickled_value)
        except (pickle.PickleError, TypeError):
            logger.warning(f"Failed to pickle data for key: {key}")
    
    def delete(self, key: str) -> None:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
        """
        if self.redis is None:
            return
        
        prefixed_key = f"{self.prefix}{key}"
        self.redis.delete(prefixed_key)
    
    def clear(self) -> None:
        """Clear all values from the cache."""
        if self.redis is None:
            return
        
        # Find all keys with our prefix and delete them
        pattern = f"{self.prefix}*"
        keys = self.redis.keys(pattern)
        
        if keys:
            self.redis.delete(*keys)


class TwoLevelCache(CacheBackend):
    """Two-level cache with memory and Redis backends."""
    
    def __init__(
        self, 
        memory_cache: MemoryCache,
        redis_cache: Optional[RedisCache] = None
    ):
        """
        Initialize two-level cache.
        
        Args:
            memory_cache: Memory cache instance
            redis_cache: Redis cache instance (optional)
        """
        self.memory_cache = memory_cache
        self.redis_cache = redis_cache
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        # Try memory cache first
        value = self.memory_cache.get(key)
        if value is not None:
            return value
        
        # Try Redis cache if memory cache miss
        if self.redis_cache is not None:
            value = self.redis_cache.get(key)
            if value is not None:
                # Update memory cache
                self.memory_cache.set(key, value)
                return value
        
        return None
    
    def set(self, key: str, value: Any, expire: Optional[int] = None) -> None:
        """
        Set a value in both caches.
        
        Args:
            key: Cache key
            value: Value to cache
            expire: Expiration time in seconds (optional)
        """
        # Set in memory cache
        self.memory_cache.set(key, value, expire)
        
        # Set in Redis cache if available
        if self.redis_cache is not None:
            self.redis_cache.set(key, value, expire)
    
    def delete(self, key: str) -> None:
        """
        Delete a value from both caches.
        
        Args:
            key: Cache key
        """
        self.memory_cache.delete(key)
        
        if self.redis_cache is not None:
            self.redis_cache.delete(key)
    
    def clear(self) -> None:
        """Clear all values from both caches."""
        self.memory_cache.clear()
        
        if self.redis_cache is not None:
            self.redis_cache.clear()


class QueryCache:
    """Query cache manager for SQLAlchemy queries."""
    
    def __init__(
        self,
        backend: CacheBackend,
        default_expire: int = 300,
        enabled: bool = True
    ):
        """
        Initialize query cache.
        
        Args:
            backend: Cache backend
            default_expire: Default expiration time in seconds
            enabled: Whether caching is enabled
        """
        self.backend = backend
        self.default_expire = default_expire
        self.enabled = enabled
        self.model_dependencies: Dict[str, Set[str]] = {}
    
    def cache_query(
        self,
        query: Query,
        key_prefix: str = "",
        expire: Optional[int] = None,
        include_params: bool = True
    ) -> Any:
        """
        Cache a SQLAlchemy query result.
        
        Args:
            query: SQLAlchemy query
            key_prefix: Prefix for the cache key
            expire: Expiration time in seconds (overrides default)
            include_params: Whether to include query parameters in the cache key
            
        Returns:
            Query result from cache or database
        """
        if not self.enabled:
            return query.all()
        
        # Generate cache key
        cache_key = self._generate_query_key(query, key_prefix, include_params)
        
        # Try to get from cache
        cached_result = self.backend.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for key: {cache_key}")
            return cached_result
        
        # Execute query and cache result
        result = query.all()
        
        # Track model dependencies for invalidation
        self._track_query_models(query, cache_key)
        
        # Cache the result
        self.backend.set(
            cache_key, 
            result, 
            expire=expire if expire is not None else self.default_expire
        )
        
        logger.debug(f"Cache miss for key: {cache_key}, stored result")
        return result
    
    def invalidate_for_model(self, model_name: str) -> None:
        """
        Invalidate cache entries for a specific model.
        
        Args:
            model_name: Name of the model
        """
        if not self.enabled:
            return
        
        # Find cache keys dependent on this model
        keys_to_invalidate = self.model_dependencies.get(model_name, set())
        
        # Delete each key
        for key in keys_to_invalidate:
            self.backend.delete(key)
        
        # Clear tracked dependencies for this model
        if model_name in self.model_dependencies:
            self.model_dependencies[model_name] = set()
        
        logger.debug(f"Invalidated {len(keys_to_invalidate)} cache entries for model: {model_name}")
    
    def clear(self) -> None:
        """Clear the entire cache."""
        if not self.enabled:
            return
        
        self.backend.clear()
        self.model_dependencies.clear()
        logger.debug("Cleared entire query cache")
    
    def _generate_query_key(
        self, 
        query: Query,
        key_prefix: str,
        include_params: bool
    ) -> str:
        """
        Generate a unique cache key for a query.
        
        Args:
            query: SQLAlchemy query
            key_prefix: Prefix for the cache key
            include_params: Whether to include query parameters
            
        Returns:
            Cache key string
        """
        # Get SQL statement
        statement = str(query.statement.compile(
            compile_kwargs={"literal_binds": True}
        ))
        
        # Add query parameters if needed
        if include_params and query._params:
            params = str(sorted(query._params.items()))
        else:
            params = ""
        
        # Create key by hashing the query details
        key_data = f"{key_prefix}:{statement}:{params}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _track_query_models(self, query: Query, cache_key: str) -> None:
        """
        Track which models a query depends on for invalidation.
        
        Args:
            query: SQLAlchemy query
            cache_key: Cache key for the query result
        """
        # Extract model classes from the query
        model_classes = {entity.class_ for entity in query._entities
                         if hasattr(entity, 'class_')}
        
        # Add relationships if any
        if hasattr(query, '_join_entities'):
            model_classes.update(entity for entity in query._join_entities
                                 if inspect.isclass(entity))
        
        # Register dependencies
        for model_class in model_classes:
            model_name = model_class.__name__
            if model_name not in self.model_dependencies:
                self.model_dependencies[model_name] = set()
            
            self.model_dependencies[model_name].add(cache_key)


def cache_query(
    expire: Optional[int] = None,
    key_prefix: str = "",
    include_params: bool = True
):
    """
    Decorator for caching query results.
    
    Args:
        expire: Cache expiration time in seconds
        key_prefix: Prefix for cache keys
        include_params: Whether to include function parameters in cache key
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get query cache from app
            query_cache = current_app.extensions.get('query_cache')
            
            if query_cache is None or not query_cache.enabled:
                # Cache not available, execute function normally
                return func(*args, **kwargs)
            
            # Generate a cache key
            key_parts = [key_prefix or func.__name__]
            
            # Add function args/kwargs to key if requested
            if include_params:
                # Add positional args (skip self/cls)
                if args and hasattr(args[0], '__class__'):
                    arg_values = args[1:]
                else:
                    arg_values = args
                
                if arg_values:
                    key_parts.append(str(arg_values))
                
                # Add keyword args
                if kwargs:
                    kwargs_str = json.dumps(
                        {k: str(v) for k, v in sorted(kwargs.items())},
                        sort_keys=True
                    )
                    key_parts.append(kwargs_str)
            
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            cached_result = query_cache.backend.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            
            # Only cache if result is not None
            if result is not None:
                query_cache.backend.set(
                    cache_key,
                    result,
                    expire=expire if expire is not None else query_cache.default_expire
                )
            
            return result
        
        return wrapper
    
    return decorator


def setup_query_cache(app, db, redis_client=None):
    """
    Set up query cache for a Flask application.
    
    Args:
        app: Flask application
        db: SQLAlchemy database instance
        redis_client: Redis client (optional)
        
    Returns:
        QueryCache instance
    """
    # Create cache backend
    memory_cache = MemoryCache(
        max_size=app.config.get('QUERY_CACHE_MEMORY_SIZE', 1000)
    )
    
    if redis_client is not None:
        redis_cache = RedisCache(
            redis_client=redis_client,
            prefix=app.config.get('QUERY_CACHE_REDIS_PREFIX', 'ia_query_cache:')
        )
        backend = TwoLevelCache(memory_cache, redis_cache)
    else:
        backend = memory_cache
    
    # Create query cache
    query_cache = QueryCache(
        backend=backend,
        default_expire=app.config.get('QUERY_CACHE_DEFAULT_EXPIRE', 300),
        enabled=app.config.get('QUERY_CACHE_ENABLED', True)
    )
    
    # Store in app extensions
    app.extensions['query_cache'] = query_cache
    
    # Set up automatic cache invalidation
    _setup_cache_invalidation(app, db, query_cache)
    
    return query_cache


def _setup_cache_invalidation(app, db, query_cache):
    """
    Set up automatic cache invalidation when models change.
    
    Args:
        app: Flask application
        db: SQLAlchemy database instance
        query_cache: QueryCache instance
    """
    # Set up model change tracking
    @event.listens_for(db.session, 'after_flush')
    def invalidate_cache_on_model_change(session, flush_context):
        # Skip if no changes or cache disabled
        if not query_cache.enabled or not session.dirty and not session.new and not session.deleted:
            return
        
        # Process all changed objects
        changed_models = set()
        
        for obj in session.new:
            changed_models.add(obj.__class__.__name__)
        
        for obj in session.dirty:
            changed_models.add(obj.__class__.__name__)
        
        for obj in session.deleted:
            changed_models.add(obj.__class__.__name__)
        
        # Invalidate cache for each changed model
        for model_name in changed_models:
            query_cache.invalidate_for_model(model_name)


if __name__ == "__main__":
    # Example usage
    print("This module provides query caching for SQLAlchemy.")
    print("Example usage:")
    print("")
    print("  from performance.query_cache import cache_query, setup_query_cache")
    print("")
    print("  # Setup in your Flask app")
    print("  query_cache = setup_query_cache(app, db, redis_client)")
    print("")
    print("  # Option 1: Using the decorator")
    print("  @cache_query(expire=300)")
    print("  def get_user_posts(user_id):")
    print("      return Post.query.filter_by(user_id=user_id).all()")
    print("")
    print("  # Option 2: Caching SQLAlchemy queries directly")
    print("  def get_recent_users():")
    print("      query = User.query.order_by(User.created_at.desc()).limit(10)")
    print("      return query_cache.cache_query(query, key_prefix='recent_users')")