"""
Module for handling API timeouts and failures with graceful fallback responses.
"""
import time
import json
import functools
import logging
from typing import Any, Dict, Optional, Union, Callable
from flask import flash, g

# Create logger for this module
logger = logging.getLogger(__name__)

# Default timeout for API calls (in seconds)
DEFAULT_TIMEOUT = 15

# Default retry attempts
DEFAULT_RETRIES = 2

# Default backoff factor (seconds)
DEFAULT_BACKOFF = 1.5

class APIError(Exception):
    """Base exception for API errors."""
    pass

class APITimeoutError(APIError):
    """Exception raised when an API call times out."""
    pass

class APIConnectionError(APIError):
    """Exception raised when there's a connection issue with the API."""
    pass

class APIResponseError(APIError):
    """Exception raised when the API returns an error response."""
    pass

def with_retry_and_timeout(
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF
) -> Callable:
    """
    Decorator to add timeout, retry logic, and error handling to API functions.
    
    Args:
        timeout: Maximum time to wait for API response in seconds
        retries: Number of retry attempts
        backoff_factor: Multiplier for exponential backoff between retries
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retry_count = 0
            last_error = None
            
            while retry_count <= retries:
                # Set timeout for this API call
                kwargs['timeout'] = timeout
                
                # Attempt the API call
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    elapsed_time = time.time() - start_time
                    
                    # Log successful call with timing
                    logger.info(f"API call to {func.__name__} succeeded in {elapsed_time:.2f}s")
                    
                    return result
                    
                except Exception as e:
                    elapsed_time = time.time() - start_time
                    retry_count += 1
                    last_error = e
                    
                    # Categorize error
                    if "timeout" in str(e).lower() or elapsed_time >= timeout:
                        error_type = "timeout"
                        logger.warning(f"API timeout in {func.__name__}: {elapsed_time:.2f}s > {timeout}s")
                    elif "connection" in str(e).lower():
                        error_type = "connection"
                        logger.warning(f"API connection error in {func.__name__}: {str(e)}")
                    else:
                        error_type = "response"
                        logger.warning(f"API response error in {func.__name__}: {str(e)}")
                    
                    # Log retry attempt
                    if retry_count <= retries:
                        wait_time = backoff_factor * (2 ** (retry_count - 1))
                        logger.info(f"Retrying {func.__name__} after {wait_time:.2f}s (attempt {retry_count}/{retries})")
                        time.sleep(wait_time)
                    else:
                        # Log final failure
                        logger.error(f"API call to {func.__name__} failed after {retries} retries: {str(last_error)}")
            
            # All retries exhausted, raise appropriate exception
            if "timeout" in str(last_error).lower():
                raise APITimeoutError(f"API call timed out after {retries} retries: {str(last_error)}")
            elif "connection" in str(last_error).lower():
                raise APIConnectionError(f"API connection failed after {retries} retries: {str(last_error)}")
            else:
                raise APIResponseError(f"API returned error after {retries} retries: {str(last_error)}")
                
        return wrapper
    return decorator

def get_fallback_response(error_type: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Provides a appropriate fallback response when an API fails.
    
    Args:
        error_type: Type of error (timeout, connection, response)
        context: Optional context about the failed request
    
    Returns:
        Dictionary with fallback response content
    """
    context = context or {}
    user_message = context.get('user_message', '')
    endpoint = context.get('endpoint', 'unknown')
    
    # Default fallback message
    fallback = {
        "message": "I'm having trouble processing your request right now. Please try again in a moment.",
        "is_fallback": True,
        "error_type": error_type
    }
    
    # Customize fallback based on error and context
    if error_type == "timeout":
        fallback["message"] = "I'm taking longer than expected to process your request. This might be due to high demand. Please try again in a moment."
    elif error_type == "connection":
        fallback["message"] = "I'm having trouble connecting to my services. This could be due to network issues. Please try again in a moment."
    elif error_type == "response":
        fallback["message"] = "I encountered an issue while processing your request. My team has been notified and is working on it."
        
    # Add contextual help based on endpoint if available
    if endpoint == "chat":
        fallback["message"] += " Your message has been saved, and you can continue our conversation when the service recovers."
    elif endpoint == "technique":
        fallback["message"] += " In the meantime, you can explore other NLP techniques available in the library section."
    elif endpoint == "exercise":
        fallback["message"] += " You can try a different exercise or come back to this one later."
        
    # Add a translation if available
    if hasattr(g, 'translate'):
        try:
            fallback["message"] = g.translate('fallback_' + error_type, fallback["message"])
        except:
            # If translation fails, keep original message
            pass
            
    return fallback

def show_user_friendly_error(error_type: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Prepares and shows a user-friendly error message for API failures.
    
    Args:
        error_type: Type of error (timeout, connection, response)
        context: Optional context about the failed request
        
    Returns:
        Dict containing error details for rendering
    """
    context = context or {}
    category = "warning"
    
    # Define error templates for different error types
    error_details = {
        'timeout': {
            'title': 'Taking Longer Than Expected',
            'message': 'Our AI service is busy. We\'re using a simplified response for now.',
            'retry_action': {
                'text': 'Try Again',
                'url': '#'  # Will be filled by the caller
            },
            'category': 'warning'
        },
        'connection': {
            'title': 'Connection Issue',
            'message': 'We\'re having trouble connecting to our AI service. Please check your internet connection.',
            'retry_action': {
                'text': 'Reconnect',
                'url': '#'  # Will be filled by the caller
            },
            'category': 'warning'
        },
        'response': {
            'title': 'Unexpected Response',
            'message': 'We received an unusual response from our AI. Our team has been notified.',
            'retry_action': {
                'text': 'Try Again',
                'url': '#'  # Will be filled by the caller
            },
            'category': 'danger'
        },
        'auth': {
            'title': 'Authentication Required',
            'message': 'This feature requires authentication or subscription.',
            'alternative_action': {
                'text': 'Learn More',
                'url': '#'  # Will be filled by the caller
            },
            'category': 'info'
        }
    }
    
    # Get current endpoint from context
    endpoint = context.get('endpoint', '') if context else ''
    current_url = f"/{endpoint}" if endpoint else '/'
    
    # Get error details based on type, or use default if type not found
    error_info = error_details.get(error_type, {
        'title': 'Something Went Wrong',
        'message': 'We encountered an unexpected error. Please try again later.',
        'retry_action': {
            'text': 'Try Again',
            'url': current_url
        },
        'category': 'danger'
    })
    
    # Fill in dynamic URLs
    if 'retry_action' in error_info and error_info['retry_action']['url'] == '#':
        error_info['retry_action']['url'] = current_url
    
    # Apply translations if available
    if hasattr(g, 'translate'):
        try:
            error_info['message'] = g.translate('error_' + error_type + '_message', error_info['message'])
            error_info['title'] = g.translate('error_' + error_type + '_title', error_info['title'])
        except:
            # If translation fails, keep original message
            pass
    
    # Flash the message for immediate feedback
    flash(error_info['message'], error_info['category'])
    
    # Return structured error details for template rendering
    return {
        'error_type': error_type,
        'error_title': error_info['title'],
        'error_message': error_info['message'],
        'retry_action': error_info.get('retry_action'),
        'alternative_action': error_info.get('alternative_action')
    }