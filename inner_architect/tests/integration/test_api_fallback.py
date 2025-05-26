"""
Integration tests for API fallback functionality.
"""
from unittest.mock import MagicMock, patch

import pytest

from inner_architect.app.services.ai_client_factory import (AIClientFactory,
                                                         AIProviderNotAvailableError,
                                                         AIProviderType)


class TestAPIFallback:
    """Integration tests for API fallback functionality."""
    
    def test_fallback_mechanism(self, app, client, logged_in_client):
        """Test the fallback mechanism when a provider fails."""
        factory = AIClientFactory()
        
        # Mock the provider clients
        mock_claude_client = MagicMock()
        mock_openai_client = MagicMock()
        
        # Set up the factory with mocked providers
        factory._provider_clients = {
            AIProviderType.CLAUDE: mock_claude_client,
            AIProviderType.OPENAI: mock_openai_client
        }
        factory._provider_status = {
            AIProviderType.CLAUDE: True,
            AIProviderType.OPENAI: True
        }
        factory._default_provider = AIProviderType.CLAUDE
        factory._fallback_order = [AIProviderType.CLAUDE, AIProviderType.OPENAI]
        
        # Mock Claude to fail
        mock_claude_client.chat_completion.side_effect = Exception("Claude API error")
        
        # Mock OpenAI to succeed
        mock_openai_client.chat_completion.return_value = {
            "choices": [{"message": {"content": "OpenAI response"}}]
        }
        
        # Patch the factory instance
        with patch('inner_architect.app.routes.chat.ai_client_factory', factory):
            # Make a chat request
            response = logged_in_client.post('/chat', json={
                'message': 'Hello, AI!',
                'session_id': 'test-session-id'
            })
            
            # Check that the request was successful
            assert response.status_code == 200
            data = response.get_json()
            assert 'response' in data
            assert data['response'] == 'OpenAI response'
            
            # Check that both providers were tried
            mock_claude_client.chat_completion.assert_called_once()
            mock_openai_client.chat_completion.assert_called_once()
            
            # Claude should be marked as unavailable
            assert factory._provider_status[AIProviderType.CLAUDE] is False
    
    def test_all_providers_fail(self, app, client, logged_in_client):
        """Test behavior when all providers fail."""
        factory = AIClientFactory()
        
        # Mock the provider clients
        mock_claude_client = MagicMock()
        mock_openai_client = MagicMock()
        
        # Set up the factory with mocked providers
        factory._provider_clients = {
            AIProviderType.CLAUDE: mock_claude_client,
            AIProviderType.OPENAI: mock_openai_client
        }
        factory._provider_status = {
            AIProviderType.CLAUDE: True,
            AIProviderType.OPENAI: True
        }
        factory._default_provider = AIProviderType.CLAUDE
        factory._fallback_order = [AIProviderType.CLAUDE, AIProviderType.OPENAI]
        
        # Mock both providers to fail
        mock_claude_client.chat_completion.side_effect = Exception("Claude API error")
        mock_openai_client.chat_completion.side_effect = Exception("OpenAI API error")
        
        # Patch the factory instance and the fallback response function
        with patch('inner_architect.app.routes.chat.ai_client_factory', factory), \
             patch('inner_architect.app.routes.chat.get_fallback_response') as mock_fallback:
            mock_fallback.return_value = "Fallback response when all providers fail"
            
            # Make a chat request
            response = logged_in_client.post('/chat', json={
                'message': 'Hello, AI!',
                'session_id': 'test-session-id'
            })
            
            # Check that the request was successful
            assert response.status_code == 200
            data = response.get_json()
            assert 'response' in data
            assert data['response'] == "Fallback response when all providers fail"
            
            # Check that both providers were tried
            mock_claude_client.chat_completion.assert_called_once()
            mock_openai_client.chat_completion.assert_called_once()
            
            # Both providers should be marked as unavailable
            assert factory._provider_status[AIProviderType.CLAUDE] is False
            assert factory._provider_status[AIProviderType.OPENAI] is False
            
            # Fallback response should have been used
            mock_fallback.assert_called_once()
    
    def test_api_test_interface(self, app, client, logged_in_admin):
        """Test the API test interface."""
        # Access the API test interface
        response = logged_in_admin.get('/admin/api-test')
        assert response.status_code == 200
        assert b'API Test Interface' in response.data
        
        # Mock the factory for testing providers
        factory = AIClientFactory()
        mock_claude_client = MagicMock()
        mock_openai_client = MagicMock()
        
        factory._provider_clients = {
            AIProviderType.CLAUDE: mock_claude_client,
            AIProviderType.OPENAI: mock_openai_client
        }
        
        # Mock responses
        mock_claude_client.chat_completion.return_value = {
            "choices": [{"message": {"content": "Claude response"}}]
        }
        mock_openai_client.chat_completion.return_value = {
            "choices": [{"message": {"content": "OpenAI response"}}]
        }
        
        # Patch the factory instance
        with patch('inner_architect.app.routes.api_test.ai_client_factory', factory):
            # Test Claude
            response = logged_in_admin.post('/admin/api-test/run', json={
                'provider': 'claude',
                'message': 'Test message',
                'temperature': 0.7
            })
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['response'] == 'Claude response'
            mock_claude_client.chat_completion.assert_called_once()
            
            # Test OpenAI
            mock_claude_client.chat_completion.reset_mock()
            response = logged_in_admin.post('/admin/api-test/run', json={
                'provider': 'openai',
                'message': 'Test message',
                'temperature': 0.7
            })
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['response'] == 'OpenAI response'
            mock_openai_client.chat_completion.assert_called_once()
            mock_claude_client.chat_completion.assert_not_called()
    
    def test_health_check_api(self, app, client, logged_in_admin):
        """Test the health check API."""
        factory = AIClientFactory()
        
        # Mock the provider clients
        mock_claude_client = MagicMock()
        mock_openai_client = MagicMock()
        
        # Set up the factory with mocked providers
        factory._provider_clients = {
            AIProviderType.CLAUDE: mock_claude_client,
            AIProviderType.OPENAI: mock_openai_client
        }
        factory._provider_status = {
            AIProviderType.CLAUDE: True,
            AIProviderType.OPENAI: False  # OpenAI is marked as unavailable
        }
        
        # Mock health checks
        mock_claude_client.health_check.return_value = True
        mock_openai_client.health_check.return_value = True
        
        # Patch the factory instance
        with patch('inner_architect.app.routes.api_test.ai_client_factory', factory):
            # Run health check
            response = logged_in_admin.post('/admin/api-test/health-check')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['results']['claude']['status'] is True
            assert data['results']['openai']['status'] is True
            
            # Both providers should have been checked
            mock_claude_client.health_check.assert_called_once()
            mock_openai_client.health_check.assert_called_once()
            
            # OpenAI should be marked as available again
            assert factory._provider_status[AIProviderType.CLAUDE] is True
            assert factory._provider_status[AIProviderType.OPENAI] is True