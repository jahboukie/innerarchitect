"""
Integration tests for admin routes.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from inner_architect.app.utils.monitoring import MetricsCollector


@pytest.fixture
def admin_user(app, client):
    """Create an admin user."""
    from inner_architect.app.models.user import User
    from inner_architect.app import db
    
    with app.app_context():
        # Create admin user
        admin = User(
            id='admin-user-id',
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            auth_provider='email',
            is_admin=True
        )
        admin.set_password('adminpassword')
        admin.email_verified = True
        db.session.add(admin)
        db.session.commit()
    
    return admin


@pytest.fixture
def logged_in_admin(client, admin_user):
    """Log in the admin user."""
    client.post(
        '/auth/login',
        data={'email': 'admin@example.com', 'password': 'adminpassword'}
    )
    return client


class TestAdminRoutes:
    """Integration tests for admin routes."""
    
    def test_error_dashboard_access(self, client, logged_in_admin):
        """Test access to the error dashboard."""
        # Anonymous user should be redirected
        response = client.get('/admin/error-dashboard')
        assert response.status_code == 302
        
        # Admin user should have access
        response = logged_in_admin.get('/admin/error-dashboard')
        assert response.status_code == 200
        assert b'Error Monitoring Dashboard' in response.data
    
    def test_error_logs_access(self, client, logged_in_admin):
        """Test access to the error logs."""
        # Anonymous user should be redirected
        response = client.get('/admin/error-logs')
        assert response.status_code == 302
        
        # Admin user should have access
        response = logged_in_admin.get('/admin/error-logs')
        assert response.status_code == 200
        assert b'Error Logs' in response.data
    
    def test_api_metrics_access(self, client, logged_in_admin):
        """Test access to the API metrics."""
        # Anonymous user should be redirected
        response = client.get('/admin/api-metrics')
        assert response.status_code == 302
        
        # Admin user should have access
        response = logged_in_admin.get('/admin/api-metrics')
        assert response.status_code == 200
        assert b'API Metrics' in response.data
    
    def test_health_check_endpoint(self, client, logged_in_admin):
        """Test the health check endpoint."""
        # Mock the metrics collector
        with patch.object(MetricsCollector, 'check_api_health') as mock_check_health:
            mock_check_health.return_value = {
                'status': 'healthy',
                'providers': {
                    'claude': {
                        'status': 'healthy',
                        'success_rate': 0.95,
                        'avg_response_time': 0.5
                    },
                    'openai': {
                        'status': 'healthy',
                        'success_rate': 0.98,
                        'avg_response_time': 0.3
                    }
                }
            }
            
            # Call the health check endpoint
            response = logged_in_admin.get('/admin/api/health')
            assert response.status_code == 200
            
            # Check the response
            data = json.loads(response.data)
            assert data['status'] == 'healthy'
            assert 'providers' in data
            assert 'claude' in data['providers']
            assert 'openai' in data['providers']
    
    def test_export_logs(self, client, logged_in_admin):
        """Test exporting logs."""
        # Mock the log file
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', MagicMock()), \
             patch('csv.writer', MagicMock()):
            
            # Test exporting logs in different formats
            for format in ['csv', 'json', 'txt']:
                response = logged_in_admin.get(f'/admin/export-logs?format={format}')
                assert response.status_code == 200
                
                # Check content type
                if format == 'csv':
                    assert response.content_type == 'text/csv'
                elif format == 'json':
                    assert response.content_type == 'application/json'
                elif format == 'txt':
                    assert response.content_type == 'text/plain'
    
    def test_system_metrics_endpoint(self, client, logged_in_admin):
        """Test the system metrics endpoint."""
        # Mock the metrics collector
        with patch.object(MetricsCollector, 'get_system_metrics') as mock_get_metrics:
            mock_get_metrics.return_value = {
                'cpu_percent': 30.0,
                'memory_percent': 50.0,
                'memory_available_mb': 1024,
                'memory_total_mb': 2048,
                'disk_percent': 40.0,
                'disk_free_gb': 10,
                'disk_total_gb': 20
            }
            
            # Call the system metrics endpoint
            response = logged_in_admin.get('/admin/api/system-metrics')
            assert response.status_code == 200
            
            # Check the response
            data = json.loads(response.data)
            assert 'cpu_percent' in data
            assert 'memory_percent' in data
            assert 'disk_percent' in data