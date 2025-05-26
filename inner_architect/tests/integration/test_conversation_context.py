"""
Integration tests for conversation context management.

These tests verify the functionality for managing conversation contexts,
including memory extraction and context enhancement.
"""

import pytest
from flask import url_for
from app.nlp.conversation_context import (
    get_or_create_context,
    create_new_context,
    add_message_to_context,
    enhance_prompt_with_context,
    update_context_summary,
    consolidate_memories
)

class TestConversationContext:
    """Integration tests for conversation context management."""
    
    def test_create_and_retrieve_context(self, app):
        """Test creating and retrieving a conversation context."""
        with app.app_context():
            # Create a context
            session_id = 'test-session-123'
            user_id = 'test-user-id'
            
            context = create_new_context(user_id, session_id)
            assert context is not None
            assert context.user_id == user_id
            assert context.session_id == session_id
            assert context.is_active is True
            
            # Retrieve the context
            retrieved_context = get_or_create_context(user_id, session_id)
            assert retrieved_context is not None
            assert retrieved_context.id == context.id
            assert retrieved_context.user_id == user_id
            assert retrieved_context.session_id == session_id
    
    def test_add_message_to_context(self, app, mock_claude_client):
        """Test adding a message to a conversation context."""
        with app.app_context():
            # Create a context
            session_id = 'test-session-456'
            user_id = 'test-user-id'
            context = create_new_context(user_id, session_id)
            
            # Add a message
            user_message = "I'm feeling anxious about an upcoming presentation"
            ai_response = "That's understandable. Let's reframe this situation..."
            mood = "anxious"
            technique = "reframing"
            
            message_entry = add_message_to_context(
                context.id,
                user_message,
                ai_response,
                user_id,
                session_id,
                mood,
                technique
            )
            
            assert message_entry is not None
            assert message_entry.user_id == user_id
            assert message_entry.session_id == session_id
            assert message_entry.context_id == context.id
            assert message_entry.user_message == user_message
            assert message_entry.ai_response == ai_response
            assert message_entry.mood == mood
            assert message_entry.nlp_technique == technique
    
    def test_enhance_prompt_with_context(self, app, mock_claude_client):
        """Test enhancing a prompt with conversation context."""
        with app.app_context():
            # Create a context
            session_id = 'test-session-789'
            user_id = 'test-user-id'
            context = create_new_context(user_id, session_id)
            
            # Add a few messages
            add_message_to_context(
                context.id,
                "I'm nervous about my job interview tomorrow",
                "It's natural to feel nervous. Let's work on some preparation strategies...",
                user_id,
                session_id,
                "nervous",
                "reframing"
            )
            
            add_message_to_context(
                context.id,
                "I'm worried I'll freeze up when they ask me questions",
                "Let's prepare some responses for common questions...",
                user_id,
                session_id,
                "worried",
                "future_pacing"
            )
            
            # Now enhance a new prompt
            new_message = "What if they ask about my gap in employment?"
            enhanced_message, conversation_history = enhance_prompt_with_context(
                context.id,
                new_message,
                max_history=3,
                include_memories=True
            )
            
            # The enhanced message should still contain the original message
            assert new_message in enhanced_message
            
            # The conversation history should have 2 entries (our previous messages)
            assert len(conversation_history) == 4  # 2 user messages + 2 AI responses
    
    def test_update_context_summary(self, app, mock_claude_client):
        """Test updating the summary of a conversation context."""
        with app.app_context():
            # Create a context
            session_id = 'test-session-abc'
            user_id = 'test-user-id'
            context = create_new_context(user_id, session_id)
            
            # Add some messages
            add_message_to_context(
                context.id,
                "I've been having trouble sleeping lately",
                "Sleep problems can be challenging. Let's explore some strategies...",
                user_id,
                session_id,
                "tired",
                "reframing"
            )
            
            add_message_to_context(
                context.id,
                "I think it might be related to stress at work",
                "Work stress can definitely affect sleep. Let's look at ways to manage stress...",
                user_id,
                session_id,
                "stressed",
                "pattern_interruption"
            )
            
            # Update the context summary
            updated_context = update_context_summary(context.id)
            
            # The summary should now exist and contain relevant information
            assert updated_context.summary is not None
            assert len(updated_context.summary) > 0
            assert "sleep" in updated_context.summary.lower() or "stress" in updated_context.summary.lower()
    
    def test_consolidate_memories(self, app, mock_claude_client):
        """Test consolidating memories from a conversation."""
        with app.app_context():
            # Create a context
            session_id = 'test-session-xyz'
            user_id = 'test-user-id'
            context = create_new_context(user_id, session_id)
            
            # Add some messages with personal information
            add_message_to_context(
                context.id,
                "I've been working as a software engineer for 5 years",
                "That's a good amount of experience. How has your journey been?",
                user_id,
                session_id,
                "neutral",
                "meta_model"
            )
            
            add_message_to_context(
                context.id,
                "I recently moved to Seattle for a new job opportunity",
                "Moving to a new city for work is a big change...",
                user_id,
                session_id,
                "excited",
                "future_pacing"
            )
            
            # Consolidate memories
            memories = consolidate_memories(context.id)
            
            # Should have extracted some memories
            assert len(memories) > 0
            
            # Check if any of the memories contain relevant information
            memory_text = ' '.join([m.content for m in memories])
            assert any(keyword in memory_text.lower() for keyword in 
                      ['software engineer', 'experience', 'seattle', 'job', 'moved'])