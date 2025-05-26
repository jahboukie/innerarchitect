"""
Unit tests for NLP techniques.

These tests verify the functionality of the NLP techniques module without making actual API calls.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.nlp.techniques import (
    get_technique_details,
    get_all_techniques,
    apply_technique,
    detect_user_mood,
    suggest_technique,
    NLP_TECHNIQUES
)

class TestTechniques:
    """Tests for the NLP techniques module."""
    
    def test_get_technique_details_existing(self):
        """Test retrieving details for an existing technique."""
        details = get_technique_details('reframing')
        
        assert details is not None
        assert details['name'] == 'Cognitive Reframing'
        assert 'description' in details
        assert 'prompts' in details
    
    def test_get_technique_details_nonexistent(self):
        """Test retrieving details for a nonexistent technique."""
        details = get_technique_details('nonexistent_technique')
        
        assert details == {}
    
    def test_get_all_techniques(self):
        """Test retrieving all techniques."""
        techniques = get_all_techniques()
        
        assert techniques is not None
        assert len(techniques) >= 6  # At least the 6 core techniques
        
        # Check for core techniques
        assert 'reframing' in techniques
        assert 'pattern_interruption' in techniques
        assert 'anchoring' in techniques
        assert 'future_pacing' in techniques
        assert 'sensory_language' in techniques
        assert 'meta_model' in techniques
        
        # Check structure of technique entries
        for technique_id, technique in techniques.items():
            assert 'name' in technique
            assert 'description' in technique
            assert 'prompts' in technique
    
    def test_apply_technique_reframing(self, mock_claude_client):
        """Test applying the reframing technique."""
        response, metadata = apply_technique(
            technique_id='reframing',
            user_message='I always fail at everything I try.',
            conversation_history=[],
            user_preferences=None
        )
        
        assert "reframed perspective" in response.lower()
        assert metadata is not None
        assert metadata['technique'] == 'reframing'
        assert metadata['technique_name'] == 'Cognitive Reframing'
    
    def test_apply_technique_pattern_interruption(self, mock_claude_client):
        """Test applying the pattern interruption technique."""
        response, metadata = apply_technique(
            technique_id='pattern_interruption',
            user_message='I keep thinking about my mistakes over and over.',
            conversation_history=[],
            user_preferences=None
        )
        
        assert "break that pattern" in response.lower()
        assert metadata is not None
        assert metadata['technique'] == 'pattern_interruption'
        assert metadata['technique_name'] == 'Pattern Interruption'
    
    def test_apply_technique_with_user_preferences(self, mock_claude_client):
        """Test applying a technique with user preferences."""
        with patch('app.nlp.techniques._create_technique_prompt') as mock_create_prompt:
            mock_create_prompt.return_value = "Customized system prompt"
            
            user_preferences = {
                'experience_level': 'advanced',
                'show_explanations': False,
                'communication_style': 'direct'
            }
            
            apply_technique(
                technique_id='anchoring',
                user_message='I need to feel more confident in meetings.',
                conversation_history=[],
                user_preferences=user_preferences
            )
            
            # Verify that user preferences were passed to the prompt creation
            mock_create_prompt.assert_called_once_with(
                'anchoring',
                NLP_TECHNIQUES['anchoring'],
                user_preferences
            )
    
    def test_apply_technique_unknown(self, mock_claude_client):
        """Test applying an unknown technique."""
        response, metadata = apply_technique(
            technique_id='unknown_technique',
            user_message='Test message',
            conversation_history=[],
            user_preferences=None
        )
        
        assert "not familiar with that technique" in response.lower()
        assert metadata is None
    
    def test_apply_technique_error_handling(self, mock_claude_client):
        """Test error handling when applying a technique."""
        with patch('app.nlp.techniques.get_claude_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_completion.side_effect = Exception("API error")
            mock_get_client.return_value = mock_client
            
            response, metadata = apply_technique(
                technique_id='reframing',
                user_message='Test message',
                conversation_history=[],
                user_preferences=None
            )
            
            assert "issue" in response.lower()
            assert metadata is None
    
    def test_detect_user_mood(self, mock_claude_client):
        """Test mood detection from user message."""
        mood = detect_user_mood("I'm feeling great today!")
        
        assert mood == "happy"
    
    def test_detect_user_mood_error_handling(self, mock_claude_client):
        """Test error handling in mood detection."""
        with patch('app.nlp.techniques.get_claude_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.analyze_text.side_effect = Exception("API error")
            mock_get_client.return_value = mock_client
            
            mood = detect_user_mood("Test message")
            
            assert mood == "neutral"  # Default mood on error
    
    def test_suggest_technique(self, mock_claude_client):
        """Test technique suggestion based on user message."""
        technique = suggest_technique("I can't stop thinking negative thoughts.")
        
        assert technique == "reframing"
    
    def test_suggest_technique_with_history(self, mock_claude_client):
        """Test technique suggestion with user history."""
        with patch('app.nlp.techniques.get_claude_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.analyze_text.return_value = "anchoring"
            mock_get_client.return_value = mock_client
            
            user_history = [
                {"technique": "reframing", "rating": 5},
                {"technique": "reframing", "rating": 4},
                {"technique": "pattern_interruption", "rating": 2}
            ]
            
            technique = suggest_technique("I need to feel more confident.", user_history)
            
            # Verify the technique and that history was considered in the prompt
            assert technique == "anchoring"
            
            # Extract the task_description to check if it includes history info
            call_args = mock_client.analyze_text.call_args
            task_description = call_args[1]['task_description']
            
            assert "Based on previous interactions" in task_description
            assert "reframing" in task_description
    
    def test_suggest_technique_error_handling(self, mock_claude_client):
        """Test error handling in technique suggestion."""
        with patch('app.nlp.techniques.get_claude_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.analyze_text.side_effect = Exception("API error")
            mock_get_client.return_value = mock_client
            
            technique = suggest_technique("Test message")
            
            assert technique == "reframing"  # Default technique on error
    
    def test_create_technique_prompt(self):
        """Test creation of system prompts for techniques."""
        from app.nlp.techniques import _create_technique_prompt
        
        # Test with default preferences
        prompt = _create_technique_prompt('reframing', NLP_TECHNIQUES['reframing'])
        
        assert "Apply cognitive reframing techniques" in prompt
        assert "Experience level: beginner" in prompt
        assert "Show technique explanations: True" in prompt
        assert "Communication style: supportive" in prompt
        
        # Test with custom preferences
        user_preferences = {
            'experience_level': 'advanced',
            'show_explanations': False,
            'communication_style': 'direct'
        }
        
        prompt = _create_technique_prompt('reframing', NLP_TECHNIQUES['reframing'], user_preferences)
        
        assert "Experience level: advanced" in prompt
        assert "Show technique explanations: False" in prompt
        assert "Communication style: direct" in prompt