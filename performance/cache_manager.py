"""
Cache Manager for Performance Optimization

This module provides a comprehensive caching system for the application,
supporting various cache backends and strategies for optimal performance.
"""

import time
import json
import hashlib
import logging
import functools
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from datetime import datetime, timedelta
import threading
import inspect

# Initialize logging
from logging_config import get_logger
logger = get_logger('performance.cache')

# Cache backend options
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import memcache
    MEMCACHE_AVAILABLE = True
except ImportError:
    MEMCACHE_AVAILABLE = False


class CacheKey:
    """Utility for generating and managing cache keys."""
    
    @staticmethod
    def generate(prefix: str, *args, **kwargs) -> str:
        """
        Generate a deterministic cache key from arguments.
        
        Args:
            prefix: Cache key prefix (e.g., function name)
            *args: Positional arguments to include in key
            **kwargs: Keyword arguments to include in key
            
        Returns:
            A unique, deterministic cache key
        """
        # Create a string representation of args and kwargs
        args_str = json.dumps(args, sort_keys=True) if args else ""
        kwargs_str = json.dumps(kwargs, sort_keys=True) if kwargs else ""
        
        # Combine and hash to create a fixed-length key
        combined = f"{prefix}:{args_str}:{kwargs_str}"
        hashed = hashlib.md5(combined.encode()).hexdigest()
        
        return f"{prefix}:{hashed}"
    
    @staticmethod
    def for_function(func: Callable, *args, **kwargs) -> str:
        """
        Generate a cache key for a function call.
        
        Args:
            func: The function being called
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Cache key for the function call
        """
        prefix = f"{func.__module__}.{func.__qualname__}"
        return CacheKey.generate(prefix, *args, **kwargs)


class CacheBackend:
    """Base class for cache backends."""
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        raise NotImplementedError
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL in seconds."""
        raise NotImplementedError
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        raise NotImplementedError
    
    def clear(self, prefix: Optional[str] = None) -> bool:
        """Clear all keys or keys with prefix."""
        raise NotImplementedError
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        raise NotImplementedError


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend."""
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize memory cache.
        
        Args:
            max_size: Maximum number of items to store
        """
        self._cache: Dict[str, Tuple[Any, Optional[float]]] = {}  # (value, expiry)
        self._max_size = max_size
        self._lock = threading.RLock()
        
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            value, expiry = self._cache[key]
            
            # Check if expired
            if expiry is not None and time.time() > expiry:
                del self._cache[key]
                return None
                
            return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful
        """
        with self._lock:
            # Check if cache is full and needs eviction
            if len(self._cache) >= self._max_size and key not in self._cache:
                # Simple LRU: just remove a random key (not ideal but simple)
                # In a real implementation, track access time and remove oldest
                if self._cache:
                    del self._cache[next(iter(self._cache))]
            
            # Calculate expiry time if TTL provided
            expiry = time.time() + ttl if ttl is not None else None
            
            # Store value and expiry
            self._cache[key] = (value, expiry)
            return True
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was found and deleted
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self, prefix: Optional[str] = None) -> bool:
        """
        Clear all keys or keys with prefix.
        
        Args:
            prefix: Optional prefix to clear only matching keys
            
        Returns:
            True if successful
        """
        with self._lock:
            if prefix is None:
                self._cache.clear()
            else:
                keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
                for key in keys_to_delete:
                    del self._cache[key]
            return True
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists and is not expired
        """
        with self._lock:
            if key not in self._cache:
                return False
            
            _, expiry = self._cache[key]
            
            # Check if expired
            if expiry is not None and time.time() > expiry:
                del self._cache[key]
                return False
                
            return True


class RedisCacheBackend(CacheBackend):
    """Redis cache backend."""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, 
                 password: Optional[str] = None, prefix: str = 'innerarchitect:'):
        """
        Initialize Redis cache.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password
            prefix: Key prefix for namespacing
        """
        if not REDIS_AVAILABLE:
            raise ImportError("Redis package is not installed. Install with: pip install redis")
        
        self._redis = redis.Redis(host=host, port=port, db=db, password=password)
        self._prefix = prefix
    
    def _prefixed_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self._prefix}{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        prefixed_key = self._prefixed_key(key)
        value = self._redis.get(prefixed_key)
        
        if value is None:
            return None
            
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            # If not JSON, return as is
            return value.decode('utf-8')
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful
        """
        prefixed_key = self._prefixed_key(key)
        
        # Serialize value to JSON
        if not isinstance(value, (str, bytes)):
            value = json.dumps(value)
        
        # Set in Redis with optional expiry
        if ttl is not None:
            return bool(self._redis.setex(prefixed_key, ttl, value))
        else:
            return bool(self._redis.set(prefixed_key, value))
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted
        """
        prefixed_key = self._prefixed_key(key)
        return bool(self._redis.delete(prefixed_key))
    
    def clear(self, prefix: Optional[str] = None) -> bool:
        """
        Clear all keys or keys with prefix.
        
        Args:
            prefix: Optional prefix to clear only matching keys
            
        Returns:
            True if successful
        """
        if prefix is None:
            # Clear all keys with the backend prefix
            pattern = f"{self._prefix}*"
        else:
            # Clear keys with the backend prefix + provided prefix
            pattern = f"{self._prefix}{prefix}*"
        
        # Get all matching keys
        keys = self._redis.keys(pattern)
        
        if keys:
            return bool(self._redis.delete(*keys))
        return True
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists
        """
        prefixed_key = self._prefixed_key(key)
        return bool(self._redis.exists(prefixed_key))


class MemcachedCacheBackend(CacheBackend):
    """Memcached cache backend."""
    
    def __init__(self, servers: List[str], prefix: str = 'innerarchitect:'):
        """
        Initialize Memcached cache.
        
        Args:
            servers: List of Memcached servers (host:port)
            prefix: Key prefix for namespacing
        """
        if not MEMCACHE_AVAILABLE:
            raise ImportError("Memcache package is not installed. Install with: pip install python-memcached")
        
        self._memcached = memcache.Client(servers)
        self._prefix = prefix
    
    def _prefixed_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self._prefix}{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        prefixed_key = self._prefixed_key(key)
        return self._memcached.get(prefixed_key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful
        """
        prefixed_key = self._prefixed_key(key)
        return bool(self._memcached.set(prefixed_key, value, time=ttl or 0))
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted
        """
        prefixed_key = self._prefixed_key(key)
        return bool(self._memcached.delete(prefixed_key))
    
    def clear(self, prefix: Optional[str] = None) -> bool:
        """
        Clear all keys or keys with prefix.
        
        Args:
            prefix: Optional prefix (not fully supported by Memcached)
            
        Returns:
            True if successful
        """
        # Memcached doesn't support pattern-based deletion
        # For production, you'd need a more sophisticated approach
        # For now, just flush all if no prefix specified
        if prefix is None:
            return bool(self._memcached.flush_all())
        
        # If prefix specified, we can't efficiently clear just those keys
        # Return False to indicate limitation
        logger.warning("Prefix-based clearing not fully supported by Memcached backend")
        return False
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists
        """
        prefixed_key = self._prefixed_key(key)
        return self.get(prefixed_key) is not None


class CacheManager:
    """
    Central cache manager that coordinates cache operations.
    
    This class provides a unified interface to different cache backends,
    cache strategies, and utility functions for caching.
    """
    
    def __init__(self, backend: Optional[CacheBackend] = None, default_ttl: int = 3600):
        """
        Initialize cache manager.
        
        Args:
            backend: Cache backend to use (defaults to in-memory)
            default_ttl: Default time-to-live for cached items in seconds
        """
        self._backend = backend or MemoryCacheBackend()
        self._default_ttl = default_ttl
    
    @property
    def backend(self) -> CacheBackend:
        """Get the current cache backend."""
        return self._backend
    
    @backend.setter
    def backend(self, backend: CacheBackend):
        """Set a new cache backend."""
        self._backend = backend
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        value = self._backend.get(key)
        return default if value is None else value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (overrides default)
            
        Returns:
            True if successful
        """
        effective_ttl = ttl if ttl is not None else self._default_ttl
        return self._backend.set(key, value, effective_ttl)
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted
        """
        return self._backend.delete(key)
    
    def clear(self, prefix: Optional[str] = None) -> bool:
        """
        Clear all keys or keys with prefix.
        
        Args:
            prefix: Optional prefix to clear only matching keys
            
        Returns:
            True if successful
        """
        return self._backend.clear(prefix)
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists
        """
        return self._backend.exists(key)
    
    def get_or_set(self, key: str, value_func: Callable[[], Any], 
                  ttl: Optional[int] = None) -> Any:
        """
        Get value from cache or compute and store it if not present.
        
        Args:
            key: Cache key
            value_func: Function to compute value if not in cache
            ttl: Time to live in seconds (overrides default)
            
        Returns:
            Cached or computed value
        """
        # Check if value is in cache
        value = self.get(key)
        
        # If not in cache, compute and store
        if value is None:
            value = value_func()
            if value is not None:
                self.set(key, value, ttl)
        
        return value


# Decorator for caching function results
def cached(ttl: Optional[int] = None, key_prefix: Optional[str] = None, 
          cache_none: bool = False, cache_manager: Optional[CacheManager] = None):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds (overrides default)
        key_prefix: Custom key prefix (defaults to function name)
        cache_none: Whether to cache None results
        cache_manager: Custom cache manager to use
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get cache manager
            manager = cache_manager or _default_cache_manager
            
            # Generate cache key
            prefix = key_prefix or f"{func.__module__}.{func.__qualname__}"
            cache_key = CacheKey.generate(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_value = manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value
            
            # Not in cache, call function
            logger.debug(f"Cache miss for {cache_key}")
            result = func(*args, **kwargs)
            
            # Cache result if it's not None or cache_none is True
            if result is not None or cache_none:
                manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


# Default cache manager instance
_default_cache_manager = CacheManager()

# Get the default cache manager
def get_cache_manager() -> CacheManager:
    """Get the default cache manager instance."""
    return _default_cache_manager

# Set a custom default cache manager
def set_cache_manager(manager: CacheManager):
    """Set a new default cache manager."""
    global _default_cache_manager
    _default_cache_manager = manager

# Helper to create Redis cache manager
def create_redis_cache_manager(host: str = 'localhost', port: int = 6379, 
                              db: int = 0, password: Optional[str] = None,
                              prefix: str = 'innerarchitect:', default_ttl: int = 3600) -> CacheManager:
    """
    Create a cache manager with Redis backend.
    
    Args:
        host: Redis host
        port: Redis port
        db: Redis database number
        password: Redis password
        prefix: Key prefix
        default_ttl: Default TTL in seconds
        
    Returns:
        Configured cache manager
    """
    backend = RedisCacheBackend(host, port, db, password, prefix)
    return CacheManager(backend, default_ttl)

# Helper to create Memcached cache manager
def create_memcached_cache_manager(servers: List[str], prefix: str = 'innerarchitect:',
                                  default_ttl: int = 3600) -> CacheManager:
    """
    Create a cache manager with Memcached backend.
    
    Args:
        servers: List of Memcached servers (host:port)
        prefix: Key prefix
        default_ttl: Default TTL in seconds
        
    Returns:
        Configured cache manager
    """
    backend = MemcachedCacheBackend(servers, prefix)
    return CacheManager(backend, default_ttl)

# Initialize cache for Flask app
def init_app(app):
    """
    Initialize cache for Flask application.
    
    Args:
        app: Flask application
        
    Returns:
        Configured cache manager
    """
    # Get cache config from app config
    cache_type = app.config.get('CACHE_TYPE', 'memory')
    default_ttl = app.config.get('CACHE_DEFAULT_TTL', 3600)
    
    if cache_type == 'redis':
        # Redis cache
        host = app.config.get('REDIS_HOST', 'localhost')
        port = app.config.get('REDIS_PORT', 6379)
        db = app.config.get('REDIS_DB', 0)
        password = app.config.get('REDIS_PASSWORD')
        prefix = app.config.get('CACHE_KEY_PREFIX', 'innerarchitect:')
        
        try:
            backend = RedisCacheBackend(host, port, db, password, prefix)
            logger.info(f"Initialized Redis cache backend at {host}:{port}")
        except ImportError:
            logger.warning("Redis package not installed. Falling back to memory cache.")
            backend = MemoryCacheBackend()
            
    elif cache_type == 'memcached':
        # Memcached cache
        servers = app.config.get('MEMCACHED_SERVERS', ['localhost:11211'])
        prefix = app.config.get('CACHE_KEY_PREFIX', 'innerarchitect:')
        
        try:
            backend = MemcachedCacheBackend(servers, prefix)
            logger.info(f"Initialized Memcached cache backend with servers: {servers}")
        except ImportError:
            logger.warning("Memcached package not installed. Falling back to memory cache.")
            backend = MemoryCacheBackend()
            
    else:
        # Memory cache (default)
        max_size = app.config.get('MEMORY_CACHE_MAX_SIZE', 10000)
        backend = MemoryCacheBackend(max_size)
        logger.info(f"Initialized memory cache backend with max size: {max_size}")
    
    # Create and set the cache manager
    manager = CacheManager(backend, default_ttl)
    set_cache_manager(manager)
    
    # Store on app for direct access
    app.cache_manager = manager
    
    # Add jinja2 extension for cache control headers
    if hasattr(app, 'jinja_env'):
        app.jinja_env.globals['cache_bust'] = lambda: int(time.time())
    
    return manager