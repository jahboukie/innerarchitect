"""
Unit tests for the monitoring module.
"""
import time
from unittest.mock import MagicMock, patch

import pytest

from inner_architect.app.utils.monitoring import MetricsCollector


class TestMetricsCollector:
    """Tests for the MetricsCollector class."""
    
    def test_singleton_pattern(self):
        """Test that MetricsCollector follows the singleton pattern."""
        collector1 = MetricsCollector()
        collector2 = MetricsCollector()
        
        # Both instances should be the same object
        assert collector1 is collector2
    
    def test_track_api_call(self):
        """Test tracking API calls."""
        collector = MetricsCollector()
        collector._metrics = {'api_calls': {}}
        
        # Track an API call
        collector.track_api_call('test_provider', 'test_endpoint', 200, 0.5)
        
        # Check that the call was tracked
        assert 'test_provider' in collector._metrics['api_calls']
        assert 'test_endpoint' in collector._metrics['api_calls']['test_provider']
        assert collector._metrics['api_calls']['test_provider']['test_endpoint']['total_calls'] == 1
        assert collector._metrics['api_calls']['test_provider']['test_endpoint']['successful_calls'] == 1
        
        # Track another API call with an error
        collector.track_api_call('test_provider', 'test_endpoint', 500, 0.3)
        
        # Check that the call was tracked
        assert collector._metrics['api_calls']['test_provider']['test_endpoint']['total_calls'] == 2
        assert collector._metrics['api_calls']['test_provider']['test_endpoint']['successful_calls'] == 1
        assert collector._metrics['api_calls']['test_provider']['test_endpoint']['error_calls'] == 1
    
    def test_track_error(self):
        """Test tracking errors."""
        collector = MetricsCollector()
        collector._metrics = {'errors': {}}
        
        # Track an error
        collector.track_error('test_error', 'Test error message')
        
        # Check that the error was tracked
        assert 'test_error' in collector._metrics['errors']
        assert collector._metrics['errors']['test_error']['count'] == 1
        
        # Track another error of the same type
        collector.track_error('test_error', 'Another test error message')
        
        # Check that the error was tracked
        assert collector._metrics['errors']['test_error']['count'] == 2
    
    def test_get_api_metrics(self):
        """Test getting API metrics."""
        collector = MetricsCollector()
        collector._metrics = {'api_calls': {
            'test_provider': {
                'test_endpoint': {
                    'total_calls': 10,
                    'successful_calls': 8,
                    'error_calls': 2,
                    'avg_response_time': 0.5,
                    'last_call_time': time.time()
                }
            }
        }}
        
        # Get metrics for a specific provider and endpoint
        metrics = collector.get_api_metrics('test_provider', 'test_endpoint')
        
        # Check the metrics
        assert metrics['total_calls'] == 10
        assert metrics['successful_calls'] == 8
        assert metrics['error_calls'] == 2
        assert metrics['success_rate'] == 0.8
        assert metrics['avg_response_time'] == 0.5
        
        # Get metrics for a specific provider
        metrics = collector.get_api_metrics('test_provider')
        
        # Check the metrics
        assert 'test_endpoint' in metrics
        assert metrics['test_endpoint']['total_calls'] == 10
        
        # Get metrics for all providers
        metrics = collector.get_api_metrics()
        
        # Check the metrics
        assert 'test_provider' in metrics
        assert 'test_endpoint' in metrics['test_provider']
    
    def test_get_error_metrics(self):
        """Test getting error metrics."""
        collector = MetricsCollector()
        current_time = time.time()
        collector._metrics = {'errors': {
            'test_error': {
                'count': 5,
                'first_occurrence': current_time - 3600,
                'last_occurrence': current_time,
                'messages': ['Test error message']
            }
        }}
        
        # Get metrics for a specific error
        metrics = collector.get_error_metrics('test_error')
        
        # Check the metrics
        assert metrics['count'] == 5
        assert metrics['first_occurrence'] == current_time - 3600
        assert metrics['last_occurrence'] == current_time
        assert 'Test error message' in metrics['messages']
        
        # Get metrics for all errors
        metrics = collector.get_error_metrics()
        
        # Check the metrics
        assert 'test_error' in metrics
        assert metrics['test_error']['count'] == 5
    
    def test_get_system_metrics(self):
        """Test getting system metrics."""
        collector = MetricsCollector()
        
        # Mock the psutil methods
        with patch('psutil.virtual_memory', return_value=MagicMock(
                percent=50.0,
                available=1024*1024*1024,
                total=2*1024*1024*1024
            )), \
            patch('psutil.cpu_percent', return_value=30.0), \
            patch('psutil.disk_usage', return_value=MagicMock(
                percent=40.0,
                free=3*1024*1024*1024,
                total=5*1024*1024*1024
            )):
            
            # Get system metrics
            metrics = collector.get_system_metrics()
            
            # Check the metrics
            assert metrics['cpu_percent'] == 30.0
            assert metrics['memory_percent'] == 50.0
            assert metrics['memory_available_mb'] == 1024
            assert metrics['memory_total_mb'] == 2048
            assert metrics['disk_percent'] == 40.0
            assert metrics['disk_free_gb'] == 3
            assert metrics['disk_total_gb'] == 5
    
    def test_check_api_health(self):
        """Test checking API health."""
        collector = MetricsCollector()
        collector._metrics = {'api_calls': {
            'test_provider': {
                'test_endpoint': {
                    'total_calls': 10,
                    'successful_calls': 8,
                    'error_calls': 2,
                    'avg_response_time': 0.5,
                    'last_call_time': time.time()
                }
            }
        }}
        
        # Check health with default thresholds
        health = collector.check_api_health()
        
        # Default thresholds should consider this healthy
        assert health['status'] == 'healthy'
        assert 'providers' in health
        assert 'test_provider' in health['providers']
        assert health['providers']['test_provider']['status'] == 'healthy'
        
        # Check health with strict thresholds
        health = collector.check_api_health(
            error_rate_threshold=0.1,  # 10% errors is too high
            response_time_threshold=0.3  # 0.5s is too slow
        )
        
        # Strict thresholds should consider this unhealthy
        assert health['status'] == 'unhealthy'
        assert health['providers']['test_provider']['status'] == 'unhealthy'
        assert len(health['providers']['test_provider']['issues']) == 2