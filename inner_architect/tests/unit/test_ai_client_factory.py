"""
Unit tests for the AI client factory module.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from inner_architect.app.services.ai_client_factory import (AIClientFactory,
                                                         AIProviderNotAvailableError,
                                                         AIProviderType)


class TestAIClientFactory:
    """Tests for the AIClientFactory class."""
    
    def test_singleton_pattern(self):
        """Test that AIClientFactory follows the singleton pattern."""
        factory1 = AIClientFactory()
        factory2 = AIClientFactory()
        
        # Both instances should be the same object
        assert factory1 is factory2
    
    def test_get_provider(self):
        """Test getting a provider."""
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
        
        # Get a specific provider
        provider = factory.get_provider(AIProviderType.CLAUDE)
        assert provider is mock_claude_client
        
        # Get the default provider
        factory._default_provider = AIProviderType.OPENAI
        provider = factory.get_provider()
        assert provider is mock_openai_client
    
    def test_get_provider_not_available(self):
        """Test getting a provider that is not available."""
        factory = AIClientFactory()
        
        # Set up the factory with a provider that is not available
        factory._provider_status = {
            AIProviderType.CLAUDE: False,
            AIProviderType.OPENAI: True
        }
        
        # Trying to get an unavailable provider should raise an error
        with pytest.raises(AIProviderNotAvailableError):
            factory.get_provider(AIProviderType.CLAUDE)
    
    def test_fallback_logic(self):
        """Test fallback logic when a provider fails."""
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
        
        # Mock the chat_completion method to fail for Claude
        mock_claude_client.chat_completion.side_effect = Exception("API error")
        
        # Mock the chat_completion method to succeed for OpenAI
        mock_openai_client.chat_completion.return_value = {"choices": [{"message": {"content": "OpenAI response"}}]}
        
        # Make a chat completion request
        result = factory.chat_completion([{"role": "user", "content": "Hello"}])
        
        # Should have fallen back to OpenAI
        mock_claude_client.chat_completion.assert_called_once()
        mock_openai_client.chat_completion.assert_called_once()
        assert result == {"choices": [{"message": {"content": "OpenAI response"}}]}
        
        # Claude should be marked as unavailable
        assert factory._provider_status[AIProviderType.CLAUDE] is False
    
    def test_all_providers_fail(self):
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
        
        # Make a chat completion request
        with pytest.raises(AIProviderNotAvailableError):
            factory.chat_completion([{"role": "user", "content": "Hello"}])
        
        # Both providers should be marked as unavailable
        assert factory._provider_status[AIProviderType.CLAUDE] is False
        assert factory._provider_status[AIProviderType.OPENAI] is False
    
    def test_health_check_restore_provider(self):
        """Test that health check can restore a provider."""
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
            AIProviderType.CLAUDE: False,  # Claude is initially marked as unavailable
            AIProviderType.OPENAI: True
        }
        
        # Mock the health check method to succeed for Claude
        mock_claude_client.health_check.return_value = True
        
        # Run health check
        factory.run_health_checks()
        
        # Claude should be marked as available again
        assert factory._provider_status[AIProviderType.CLAUDE] is True
        mock_claude_client.health_check.assert_called_once()
    
    def test_reset_provider_status(self):
        """Test resetting provider status."""
        factory = AIClientFactory()
        
        # Set all providers as unavailable
        factory._provider_status = {
            AIProviderType.CLAUDE: False,
            AIProviderType.OPENAI: False
        }
        
        # Reset provider status
        factory.reset_provider_status()
        
        # All providers should be marked as available
        assert factory._provider_status[AIProviderType.CLAUDE] is True
        assert factory._provider_status[AIProviderType.OPENAI] is True