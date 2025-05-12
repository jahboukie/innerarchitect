"""
Logging configuration for The Inner Architect application.

This module provides standardized logging setup for all parts of the application,
ensuring consistent log formatting, levels, and handling across modules.
"""

import os
import logging
import logging.handlers
from datetime import datetime

# Create a logger object
logger = logging.getLogger('inner_architect')

# Set the default logging level from environment or default to INFO
DEFAULT_LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
LOG_LEVEL = getattr(logging, DEFAULT_LOG_LEVEL, logging.INFO)
logger.setLevel(LOG_LEVEL)

# Create formatters
default_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
)
simple_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(simple_formatter)
console_handler.setLevel(LOG_LEVEL)

# Add handlers to the logger
logger.addHandler(console_handler)

# Function to get a module-specific logger
def get_logger(module_name):
    """
    Get a module-specific logger that inherits from the main application logger.
    
    Args:
        module_name (str): The name of the module requesting the logger
        
    Returns:
        logging.Logger: A configured logger for the module
    """
    module_logger = logger.getChild(module_name)
    return module_logger

# Convenience functions for common log levels
def debug(message, *args, **kwargs):
    """Log a debug message."""
    logger.debug(message, *args, **kwargs)

def info(message, *args, **kwargs):
    """Log an info message."""
    logger.info(message, *args, **kwargs)

def warning(message, *args, **kwargs):
    """Log a warning message."""
    logger.warning(message, *args, **kwargs)

def error(message, *args, **kwargs):
    """Log an error message."""
    logger.error(message, *args, **kwargs)

def critical(message, *args, **kwargs):
    """Log a critical message."""
    logger.critical(message, *args, **kwargs)

def exception(message, *args, exc_info=True, **kwargs):
    """Log an exception with traceback."""
    logger.exception(message, *args, exc_info=exc_info, **kwargs)