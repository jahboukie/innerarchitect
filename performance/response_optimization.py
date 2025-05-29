"""
Response Optimization Module

This module provides tools for optimizing HTTP responses through compression,
ETags, conditional responses, and other HTTP optimizations.
"""

import os
import time
import gzip
import hashlib
import logging
import re
from typing import Dict, List, Optional, Union, Callable, Set, Any
from functools import wraps

from flask import Flask, request, Response, make_response, current_app

# Initialize logging
from logging_config import get_logger
logger = get_logger('performance.response')


class CompressionManager:
    """
    Manages response compression.
    """
    
    def __init__(self, min_size: int = 1024, compression_level: int = 6):
        """
        Initialize compression manager.
        
        Args:
            min_size: Minimum response size in bytes for compression
            compression_level: Gzip compression level (1-9)
        """
        self.min_size = min_size
        self.compression_level = compression_level
        
        # MIME types that should be compressed
        self.compressible_types = {
            'text/html', 'text/css', 'text/javascript', 'application/javascript',
            'application/json', 'text/plain', 'text/xml', 'application/xml',
            'application/xhtml+xml', 'image/svg+xml'
        }
    
    def should_compress(self, response: Response) -> bool:
        """
        Check if a response should be compressed.
        
        Args:
            response: Flask response object
            
        Returns:
            True if the response should be compressed
        """
        # Check if already compressed
        if 'Content-Encoding' in response.headers:
            return False
        
        # Check request headers
        accept_encoding = request.headers.get('Accept-Encoding', '')
        if 'gzip' not in accept_encoding:
            return False
        
        # Check response size
        if response.content_length is not None and response.content_length < self.min_size:
            return False
        
        # Check content type
        content_type = response.headers.get('Content-Type', '')
        if not any(ct in content_type for ct in self.compressible_types):
            return False
        
        return True
    
    def compress_response(self, response: Response) -> Response:
        """
        Compress a response using gzip.
        
        Args:
            response: Flask response object
            
        Returns:
            Compressed response
        """
        if not self.should_compress(response):
            return response
        
        # Get response data
        data = response.get_data()
        
        # Compress data
        compressed = gzip.compress(data, self.compression_level)
        
        # Update response
        response.set_data(compressed)
        response.headers['Content-Encoding'] = 'gzip'
        response.headers['Content-Length'] = str(len(compressed))
        response.headers['Vary'] = 'Accept-Encoding'
        
        return response


class ETagManager:
    """
    Manages HTTP ETags for conditional requests.
    """
    
    def __init__(self, weak: bool = False):
        """
        Initialize ETag manager.
        
        Args:
            weak: Whether to use weak ETags
        """
        self.weak = weak
    
    def generate_etag(self, data: bytes) -> str:
        """
        Generate an ETag for response data.
        
        Args:
            data: Response data
            
        Returns:
            ETag string
        """
        # Generate MD5 hash of data
        etag = hashlib.md5(data).hexdigest()
        
        # Format as weak or strong ETag
        if self.weak:
            return f'W/"{etag}"'
        else:
            return f'"{etag}"'
    
    def set_etag(self, response: Response) -> Response:
        """
        Set ETag header on a response.
        
        Args:
            response: Flask response object
            
        Returns:
            Response with ETag header
        """
        # Skip if ETag already set
        if 'ETag' in response.headers:
            return response
        
        # Skip for streaming responses
        if response.direct_passthrough:
            return response
        
        # Get response data and generate ETag
        data = response.get_data()
        etag = self.generate_etag(data)
        
        # Set ETag header
        response.headers['ETag'] = etag
        
        return response
    
    def check_conditional_request(self, response: Response) -> Response:
        """
        Check for conditional request headers and return appropriate response.
        
        Args:
            response: Flask response object
            
        Returns:
            Original response or 304 Not Modified
        """
        # Ensure response has an ETag
        response = self.set_etag(response)
        etag = response.headers.get('ETag')
        
        # Check If-None-Match header
        if_none_match = request.headers.get('If-None-Match')
        if if_none_match and etag:
            # Parse ETag list from header
            etags = [tag.strip() for tag in if_none_match.split(',')]
            
            # Check if ETag matches
            if etag in etags or '*' in etags:
                # Return 304 Not Modified
                return make_response('', 304)
        
        # Check If-Modified-Since header
        if_modified_since = request.headers.get('If-Modified-Since')
        last_modified = response.headers.get('Last-Modified')
        
        if if_modified_since and last_modified:
            # Parse dates (simplified - in production use proper date parsing)
            # This is just an example, datetime parsing would be more robust
            if if_modified_since >= last_modified:
                # Return 304 Not Modified
                return make_response('', 304)
        
        return response


class CacheControlManager:
    """
    Manages Cache-Control headers for responses.
    """
    
    def __init__(self):
        """Initialize Cache-Control manager."""
        # Default cache times (in seconds)
        self.default_cache_time = 0  # No caching by default
        self.static_cache_time = 86400  # 1 day for static assets
        self.long_cache_time = 31536000  # 1 year for static assets with cache busting
        
        # File extensions for long caching
        self.long_cache_extensions = {
            '.js', '.css', '.jpg', '.jpeg', '.png', '.gif', '.svg',
            '.woff', '.woff2', '.ttf', '.eot', '.otf', '.ico', '.webp'
        }
    
    def get_cache_control_headers(self, path: str, is_static: bool = False) -> Dict[str, str]:
        """
        Get appropriate Cache-Control headers for a path.
        
        Args:
            path: Request path
            is_static: Whether the path is for a static asset
            
        Returns:
            Dictionary of cache control headers
        """
        headers = {}
        
        if not is_static:
            # Non-static resources - default to no caching
            headers['Cache-Control'] = f'no-cache, private'
            headers['Pragma'] = 'no-cache'
            return headers
        
        # Static assets - determine appropriate caching
        # Check if the path has a cache-busting hash
        has_cache_busting = bool(re.search(r'\.[a-f0-9]{8,}\.', path))
        
        # Check file extension
        _, ext = os.path.splitext(path)
        is_long_cache = ext.lower() in self.long_cache_extensions
        
        if has_cache_busting and is_long_cache:
            # Long cache for static assets with cache busting
            headers['Cache-Control'] = f'public, max-age={self.long_cache_time}, immutable'
        elif is_long_cache:
            # Medium cache for static assets without cache busting
            headers['Cache-Control'] = f'public, max-age={self.static_cache_time}, must-revalidate'
        else:
            # Short cache for other static files
            headers['Cache-Control'] = f'public, max-age={self.default_cache_time}, must-revalidate'
        
        return headers
    
    def set_cache_headers(self, response: Response, path: Optional[str] = None, is_static: Optional[bool] = None) -> Response:
        """
        Set appropriate cache headers on a response.
        
        Args:
            response: Flask response object
            path: Request path (if None, uses request.path)
            is_static: Whether the path is for a static asset (if None, determined from path)
            
        Returns:
            Response with cache headers
        """
        # Skip for error responses
        if response.status_code >= 400:
            response.headers['Cache-Control'] = 'no-store'
            return response
        
        # Use current request path if not provided
        if path is None:
            path = request.path
        
        # Determine if static if not provided
        if is_static is None:
            is_static = path.startswith('/static/') or path.startswith('/dist/')
        
        # Get appropriate cache headers
        cache_headers = self.get_cache_control_headers(path, is_static)
        
        # Set headers on response
        for header, value in cache_headers.items():
            if header not in response.headers:
                response.headers[header] = value
        
        # Add Vary header if not present
        if 'Vary' not in response.headers:
            response.headers['Vary'] = 'Accept-Encoding'
        
        return response


class ResponseOptimizer:
    """
    Optimizes HTTP responses for better performance.
    """
    
    def __init__(self, app=None):
        """
        Initialize response optimizer.
        
        Args:
            app: Flask application (optional)
        """
        self.app = app
        self.compression_manager = CompressionManager()
        self.etag_manager = ETagManager()
        self.cache_control_manager = CacheControlManager()
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """
        Initialize the optimizer with a Flask application.
        
        Args:
            app: Flask application
        """
        self.app = app
        
        # Register after_request handler
        app.after_request(self.optimize_response)
        
        # Configure from app config
        self._configure_from_app()
    
    def _configure_from_app(self):
        """Configure optimizer from app config."""
        app = self.app
        
        # Configure compression
        min_size = app.config.get('COMPRESSION_MIN_SIZE', 1024)
        compression_level = app.config.get('COMPRESSION_LEVEL', 6)
        self.compression_manager = CompressionManager(min_size, compression_level)
        
        # Configure ETags
        weak_etags = app.config.get('WEAK_ETAGS', False)
        self.etag_manager = ETagManager(weak_etags)
        
        # Configure cache control
        cache_control = self.cache_control_manager
        cache_control.default_cache_time = app.config.get('DEFAULT_CACHE_TIME', 0)
        cache_control.static_cache_time = app.config.get('STATIC_CACHE_TIME', 86400)
        cache_control.long_cache_time = app.config.get('LONG_CACHE_TIME', 31536000)
    
    def optimize_response(self, response: Response) -> Response:
        """
        Apply all optimizations to a response.
        
        Args:
            response: Flask response object
            
        Returns:
            Optimized response
        """
        # Skip for streaming responses
        if response.direct_passthrough:
            return response
        
        # Set cache control headers
        response = self.cache_control_manager.set_cache_headers(response)
        
        # Set ETag and check conditional request
        response = self.etag_manager.set_etag(response)
        response = self.etag_manager.check_conditional_request(response)
        
        # Compress response if appropriate
        response = self.compression_manager.compress_response(response)
        
        return response
    
    def add_security_headers(self, response: Response) -> Response:
        """
        Add security headers to a response.
        
        Args:
            response: Flask response object
            
        Returns:
            Response with security headers
        """
        # Set security headers if not already present
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        
        for header, value in security_headers.items():
            if header not in response.headers:
                response.headers[header] = value
        
        return response
    
    def no_cache(self, view_func: Callable) -> Callable:
        """
        Decorator to disable caching for a view.
        
        Args:
            view_func: Flask view function
            
        Returns:
            Decorated view function
        """
        @wraps(view_func)
        def decorated_view(*args, **kwargs):
            response = view_func(*args, **kwargs)
            
            # Set no-cache headers
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            
            return response
        
        return decorated_view
    
    def cache_for(self, seconds: int) -> Callable:
        """
        Decorator to set cache duration for a view.
        
        Args:
            seconds: Cache duration in seconds
            
        Returns:
            Decorator function
        """
        def decorator(view_func: Callable) -> Callable:
            @wraps(view_func)
            def decorated_view(*args, **kwargs):
                response = view_func(*args, **kwargs)
                
                # Set cache headers
                response.headers['Cache-Control'] = f'public, max-age={seconds}'
                
                return response
            
            return decorated_view
        
        return decorator


# Initialize for Flask app
def init_app(app: Flask) -> ResponseOptimizer:
    """
    Initialize response optimization for a Flask app.
    
    Args:
        app: Flask application
        
    Returns:
        ResponseOptimizer instance
    """
    optimizer = ResponseOptimizer(app)
    
    # Add security headers if enabled
    if app.config.get('ADD_SECURITY_HEADERS', True):
        app.after_request(optimizer.add_security_headers)
    
    # Make decorators available in the app context
    app.no_cache = optimizer.no_cache
    app.cache_for = optimizer.cache_for
    
    return optimizer