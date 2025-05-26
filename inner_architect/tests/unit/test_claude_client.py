"""
Unit tests for the Claude client.

These tests verify the functionality of the Claude client without making actual API calls.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.nlp.claude_client import ClaudeClient, get_claude_client

class TestClaudeClient:
    """Tests for the ClaudeClient class."""
    
    def test_initialization(self):
        """Test that the client initializes correctly."""
        client = ClaudeClient(api_key='test_key', model='test_model')
        assert client.api_key == 'test_key'
        assert client.model == 'test_model'
    
    def test_initialization_with_defaults(self, monkeypatch):
        """Test initialization with default values from environment."""
        monkeypatch.setenv('ANTHROPIC_API_KEY', 'env_test_key')
        client = ClaudeClient()
        assert client.api_key == 'env_test_key'
        assert client.model == 'claude-3-opus-20240229'  # Default model
    
    def test_initialization_missing_api_key(self, monkeypatch):
        """Test that initialization fails without an API key."""
        monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
        
        with pytest.raises(ValueError) as excinfo:
            ClaudeClient()
        
        assert "API key not found" in str(excinfo.value)
    
    @patch('anthropic.Anthropic')
    def test_generate_response(self, mock_anthropic):
        """Test the generate_response method."""
        # Set up the mock
        mock_content = MagicMock()
        mock_content.text = "Mock response text"
        mock_messages_response = MagicMock()
        mock_messages_response.content = [mock_content]
        
        mock_messages = MagicMock()
        mock_messages.create.return_value = mock_messages_response
        
        mock_anthropic_instance = MagicMock()
        mock_anthropic_instance.messages = mock_messages
        mock_anthropic.return_value = mock_anthropic_instance
        
        # Create client and call method
        client = ClaudeClient(api_key='test_key')
        response = client.generate_response(
            messages=[{"role": "user", "content": "Test message"}],
            system_prompt="Test system prompt",
            temperature=0.5,
            max_tokens=1000
        )
        
        # Verify the response
        assert response == "Mock response text"
        
        # Verify the API call
        mock_messages.create.assert_called_once_with(
            model=client.model,
            messages=[{"role": "user", "content": "Test message"}],
            system="Test system prompt",
            temperature=0.5,
            max_tokens=1000
        )
    
    @patch('anthropic.Anthropic')
    def test_generate_response_error_handling(self, mock_anthropic):
        """Test that errors are handled properly in generate_response."""
        # Set up the mock to raise an exception
        mock_messages = MagicMock()
        mock_messages.create.side_effect = Exception("API error")
        
        mock_anthropic_instance = MagicMock()
        mock_anthropic_instance.messages = mock_messages
        mock_anthropic.return_value = mock_anthropic_instance
        
        # Create client and call method
        client = ClaudeClient(api_key='test_key')
        response = client.generate_response(
            messages=[{"role": "user", "content": "Test message"}]
        )
        
        # Verify the fallback response
        assert "I'm having trouble" in response
    
    def test_chat_completion(self):
        """Test the chat_completion method."""
        with patch.object(ClaudeClient, 'generate_response', return_value="Mock response") as mock_generate:
            client = ClaudeClient(api_key='test_key')
            response = client.chat_completion(
                user_message="Hello",
                conversation_history=[
                    {"role": "user", "content": "Previous message"},
                    {"role": "assistant", "content": "Previous response"}
                ],
                system_prompt="Be helpful",
                temperature=0.7
            )
            
            # Verify the response
            assert response == "Mock response"
            
            # Verify generate_response was called correctly
            mock_generate.assert_called_once_with(
                messages=[
                    {"role": "user", "content": "Previous message"},
                    {"role": "assistant", "content": "Previous response"},
                    {"role": "user", "content": "Hello"}
                ],
                system_prompt="Be helpful",
                temperature=0.7
            )
    
    def test_analyze_text(self):
        """Test the analyze_text method."""
        with patch.object(ClaudeClient, 'generate_response', return_value="Analysis result") as mock_generate:
            client = ClaudeClient(api_key='test_key')
            response = client.analyze_text(
                text="Text to analyze",
                task_description="Analyze sentiment",
                temperature=0.3
            )
            
            # Verify the response
            assert response == "Analysis result"
            
            # Verify generate_response was called correctly
            mock_generate.assert_called_once_with(
                messages=[{"role": "user", "content": "Text to analyze"}],
                system_prompt="You are an expert in natural language processing and psychological analysis. Analyze sentiment",
                temperature=0.3
            )
    
    def test_extract_insights(self):
        """Test the extract_insights method."""
        with patch.object(ClaudeClient, 'generate_response', return_value="Extracted insights") as mock_generate:
            client = ClaudeClient(api_key='test_key')
            response = client.extract_insights(
                conversation=[
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there"}
                ],
                extraction_type="themes"
            )
            
            # Verify the response
            assert response == {"result": "Extracted insights"}
            
            # Verify generate_response was called correctly
            expected_system_prompt = (
                "You are an AI assistant specializing in conversation analysis and psychological insights.\n"
                "Identify the main themes, topics, and emotional patterns in this conversation.\n"
                "Format your response as a JSON object with appropriate keys and values.\n"
                "Be concise but thorough in your analysis.\n"
            )
            
            mock_generate.assert_called_once()
            args, kwargs = mock_generate.call_args
            assert kwargs['messages'] == [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"}
            ]
            assert kwargs['system_prompt'].strip() == expected_system_prompt.strip()
            assert kwargs['temperature'] == 0.3
    
    def test_get_claude_client_singleton(self):
        """Test that get_claude_client returns a singleton instance."""
        # Reset the singleton for testing
        import app.nlp.claude_client
        app.nlp.claude_client.claude_client = None
        
        with patch.object(app.nlp.claude_client, 'ClaudeClient') as mock_client_class:
            # First call should create a new client
            client1 = get_claude_client()
            mock_client_class.assert_called_once()
            
            # Reset the mock to verify second call
            mock_client_class.reset_mock()
            
            # Second call should return the same instance without creating a new one
            client2 = get_claude_client()
            mock_client_class.assert_not_called()
            
            # Both variables should reference the same object
            assert client1 is client2