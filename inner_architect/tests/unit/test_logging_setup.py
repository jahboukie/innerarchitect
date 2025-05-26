"""
Unit tests for the logging setup module.
"""
import json
import logging
import os
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask, request

from inner_architect.app.utils.logging_setup import (JSONFormatter,
                                                  RequestFormatter,
                                                  configure_logging,
                                                  track_api_call)


class TestLoggingSetup:
    """Tests for the logging setup module."""

    def test_request_formatter(self):
        """Test that RequestFormatter adds request information."""
        formatter = RequestFormatter('%(message)s')
        
        # Mock request context
        with patch('flask.request', MagicMock(
            remote_addr='127.0.0.1',
            method='GET',
            path='/test',
            user_agent=MagicMock(string='Test User Agent')
        )):
            record = logging.LogRecord(
                name='test',
                level=logging.INFO,
                pathname='test.py',
                lineno=1,
                msg='Test message',
                args=(),
                exc_info=None
            )
            
            formatted = formatter.format(record)
            assert 'Test message' in formatted
            assert hasattr(record, 'remote_addr')
            assert record.remote_addr == '127.0.0.1'
            assert hasattr(record, 'request_method')
            assert record.request_method == 'GET'
            assert hasattr(record, 'request_path')
            assert record.request_path == '/test'
    
    def test_json_formatter(self):
        """Test that JSONFormatter formats logs as JSON."""
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        
        assert parsed['message'] == 'Test message'
        assert parsed['level'] == 'INFO'
        assert parsed['name'] == 'test'
        assert 'timestamp' in parsed
    
    def test_configure_logging(self):
        """Test that configure_logging sets up logging correctly."""
        app = Flask(__name__)
        
        # Create a temporary log directory
        log_dir = 'test_logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Test with default config
        with patch('inner_architect.app.utils.logging_setup.LOG_DIR', log_dir):
            configure_logging(app)
            
            # Check that handlers were added to the root logger
            root_logger = logging.getLogger()
            handler_types = [type(h) for h in root_logger.handlers]
            
            # Should have at least one handler
            assert len(root_logger.handlers) > 0
        
        # Cleanup
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Test with custom config
        custom_config = {
            'level': 'debug',
            'format': 'json',
            'file_logging': True,
            'console_logging': True
        }
        
        with patch('inner_architect.app.utils.logging_setup.LOG_DIR', log_dir):
            configure_logging(app, custom_config)
            
            # Check that handlers were added to the root logger
            root_logger = logging.getLogger()
            assert len(root_logger.handlers) > 0
            
            # Check log level
            assert root_logger.level == logging.DEBUG
        
        # Cleanup
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        if os.path.exists(log_dir):
            for file in os.listdir(log_dir):
                os.remove(os.path.join(log_dir, file))
            os.rmdir(log_dir)
    
    def test_track_api_call_decorator(self):
        """Test that track_api_call decorator logs API calls."""
        # Create a test function
        @track_api_call
        def test_function(self, arg1, arg2=None):
            return {'result': 'success'}
        
        # Create a mock logger
        mock_logger = MagicMock()
        
        # Test the decorator
        with patch('inner_architect.app.utils.logging_setup.logger', mock_logger):
            # Call the function
            result = test_function(None, 'test_arg', arg2='test_kwarg')
            
            # Check that the function was called and returned correctly
            assert result == {'result': 'success'}
            
            # Check that logger.info was called
            mock_logger.info.assert_called_once()
            
            # Check the log message
            call_args = mock_logger.info.call_args[0][0]
            assert 'API call to test_function' in call_args