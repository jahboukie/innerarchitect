"""
Integration tests for the chat functionality.

These tests verify the complete flow from user input to AI response
through the chat routes and NLP techniques application.
"""

import pytest
from flask import url_for

class TestChatIntegration:
    """Integration tests for chat functionality."""
    
    def test_chat_page_loads(self, client):
        """Test that the chat page loads successfully."""
        response = client.get(url_for('chat.index'))
        assert response.status_code == 200
        assert b'chat-container' in response.data
        assert b'message-input' in response.data
    
    def test_create_new_conversation(self, logged_in_client):
        """Test creating a new conversation."""
        response = logged_in_client.post('/chat/new-conversation')
        data = response.get_json()
        
        assert response.status_code == 200
        assert data['success'] is True
        assert 'context_id' in data
        assert 'title' in data
        assert data['title'] == 'New Conversation'  # Default title
    
    def test_send_message(self, logged_in_client, mock_claude_client):
        """Test sending a message and getting a response."""
        # First create a new conversation
        create_response = logged_in_client.post('/chat/new-conversation')
        create_data = create_response.get_json()
        context_id = create_data['context_id']
        
        # Send a message
        message_response = logged_in_client.post(
            '/chat/message',
            json={
                'message': 'I feel anxious about my presentation tomorrow',
                'context_id': context_id,
                'technique': 'reframing'
            }
        )
        message_data = message_response.get_json()
        
        assert message_response.status_code == 200
        assert message_data['success'] is True
        assert 'message' in message_data
        assert 'technique' in message_data
        assert message_data['technique']['id'] == 'reframing'
        assert 'mood' in message_data
    
    def test_auto_technique_selection(self, logged_in_client, mock_claude_client):
        """Test that a technique is automatically selected if none specified."""
        # Create a new conversation
        create_response = logged_in_client.post('/chat/new-conversation')
        create_data = create_response.get_json()
        context_id = create_data['context_id']
        
        # Send a message without specifying a technique
        message_response = logged_in_client.post(
            '/chat/message',
            json={
                'message': 'I feel stuck in a pattern of negative thinking',
                'context_id': context_id,
                'technique': ''  # No technique specified
            }
        )
        message_data = message_response.get_json()
        
        assert message_response.status_code == 200
        assert message_data['success'] is True
        assert 'technique' in message_data
        assert message_data['technique']['id'] in [
            'reframing', 'pattern_interruption', 'anchoring', 
            'future_pacing', 'sensory_language', 'meta_model'
        ]
    
    def test_get_chat_history(self, logged_in_client, mock_claude_client):
        """Test retrieving chat history for a conversation."""
        # Create a new conversation
        create_response = logged_in_client.post('/chat/new-conversation')
        create_data = create_response.get_json()
        context_id = create_data['context_id']
        
        # Send a message
        logged_in_client.post(
            '/chat/message',
            json={
                'message': 'Hello, I need help with stress',
                'context_id': context_id,
                'technique': 'reframing'
            }
        )
        
        # Get history
        history_response = logged_in_client.get(f'/chat/history?context_id={context_id}')
        history_data = history_response.get_json()
        
        assert history_response.status_code == 200
        assert history_data['success'] is True
        assert 'history' in history_data
        assert len(history_data['history']) == 1
        assert history_data['history'][0]['user_message'] == 'Hello, I need help with stress'
    
    def test_premium_technique_restriction(self, logged_in_client, mock_claude_client, monkeypatch):
        """Test that premium techniques are restricted for non-premium users."""
        # Mock the check_feature_access function to return False (non-premium)
        from app.utils.subscription import check_feature_access
        monkeypatch.setattr('app.routes.chat.check_feature_access', lambda user_id, feature: False)
        
        # Create a new conversation
        create_response = logged_in_client.post('/chat/new-conversation')
        create_data = create_response.get_json()
        context_id = create_data['context_id']
        
        # Try to use a premium technique
        message_response = logged_in_client.post(
            '/chat/message',
            json={
                'message': 'Help me with anxiety using anchoring',
                'context_id': context_id,
                'technique': 'anchoring'  # Premium technique
            }
        )
        message_data = message_response.get_json()
        
        # Should fall back to reframing
        assert message_response.status_code == 200
        assert message_data['success'] is True
        assert message_data['technique']['id'] == 'reframing'
    
    def test_rename_conversation(self, logged_in_client):
        """Test renaming a conversation."""
        # Create a new conversation
        create_response = logged_in_client.post('/chat/new-conversation')
        create_data = create_response.get_json()
        context_id = create_data['context_id']
        
        # Rename the conversation
        rename_response = logged_in_client.post(
            f'/chat/rename-context/{context_id}',
            json={'title': 'My Custom Title'}
        )
        rename_data = rename_response.get_json()
        
        assert rename_response.status_code == 200
        assert rename_data['success'] is True
        assert rename_data['title'] == 'My Custom Title'
        
        # Verify the title was updated by getting contexts
        contexts_response = logged_in_client.get('/chat/contexts')
        contexts_data = contexts_response.get_json()
        
        found_context = False
        for context in contexts_data['contexts']:
            if context['id'] == context_id:
                found_context = True
                assert context['title'] == 'My Custom Title'
        
        assert found_context is True
    
    def test_delete_conversation(self, logged_in_client):
        """Test deleting a conversation."""
        # Create a new conversation
        create_response = logged_in_client.post('/chat/new-conversation')
        create_data = create_response.get_json()
        context_id = create_data['context_id']
        
        # Delete the conversation
        delete_response = logged_in_client.post(f'/chat/delete-context/{context_id}')
        delete_data = delete_response.get_json()
        
        assert delete_response.status_code == 200
        assert delete_data['success'] is True
        
        # Verify the context was deleted by getting contexts
        contexts_response = logged_in_client.get('/chat/contexts')
        contexts_data = contexts_response.get_json()
        
        for context in contexts_data['contexts']:
            assert context['id'] != context_id