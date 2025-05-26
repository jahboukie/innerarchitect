"""
Claude API client adapter for InnerArchitect.

This module provides an adapter for the Claude API that handles message formatting,
prompting, and response parsing specific to the InnerArchitect app's NLP techniques.
"""
import os
import logging
import json
from typing import Dict, Any, List, Optional, Tuple, Union

from .ai_client_factory import ai_client_factory
from api_fallback import with_retry_and_timeout, APIError

# Initialize logger
logger = logging.getLogger(__name__)

# Default Claude model
DEFAULT_MODEL = "claude-3-sonnet-20240229"

class ClaudeClient:
    """
    Claude API client for the InnerArchitect app.
    Provides methods for chat completions with NLP technique integration.
    """
    
    def __init__(self, model: Optional[str] = None):
        """
        Initialize the Claude client.
        
        Args:
            model: Claude model to use (defaults to claude-3-sonnet)
        """
        self.model = model or DEFAULT_MODEL
        self.client_factory = ai_client_factory
        
        # Define technique prompts for each NLP technique
        self.technique_prompts = {
            'reframing': """
                You are a cognitive reframing expert using NLP (Neuro-Linguistic Programming) techniques.
                Help the user reframe negative thoughts or situations into positive or neutral perspectives.
                Identify limiting beliefs and offer alternative viewpoints that are more empowering.
                Be supportive and empathetic while challenging unhelpful thinking patterns.
            """,
            'pattern_interruption': """
                You are a pattern interruption specialist using NLP techniques.
                Help the user break unhelpful thought patterns or behaviors by introducing unexpected perspectives.
                Use unusual questions, metaphors, or reframes to shift their thinking.
                After interrupting negative patterns, guide them toward more constructive alternatives.
            """,
            'anchoring': """
                You are an NLP anchoring specialist.
                Help the user create mental anchors - associations between specific stimuli and positive emotional states.
                Guide them to recall vivid positive experiences and suggest anchors (physical gestures, mental images, etc.)
                that they can use to access those resourceful states when needed.
                Provide clear instructions for setting and triggering anchors in their daily life.
            """,
            'future_pacing': """
                You are a future pacing expert using NLP techniques.
                Help the user mentally rehearse future situations with their desired outcomes.
                Guide them through detailed visualizations of successfully navigating challenging scenarios.
                Focus on engaging all senses - what they'll see, hear, feel, etc.
                Build confidence by emphasizing the mind's ability to prepare for success through detailed mental practice.
            """,
            'sensory_language': """
                You are a sensory language specialist in NLP.
                Pay close attention to the sensory words (visual, auditory, kinesthetic) that the user favors.
                Respond using similar sensory predicates to build rapport and understanding.
                If they use visual words like "see, look, view," respond with visual language.
                If they use auditory words like "hear, sound, resonate," respond with auditory language.
                If they use kinesthetic words like "feel, grasp, handle," respond with kinesthetic language.
                Help them become more aware of their preferred representational system and how to use all sensory modalities.
            """,
            'meta_model': """
                You are a Meta Model specialist in NLP.
                The Meta Model identifies language patterns that indicate deleted, distorted, or generalized information.
                When you notice these patterns in the user's language, ask clarifying questions to recover the missing information.
                Challenge generalizations like "always" or "never" by asking for specific examples.
                Question distortions like mind-reading or cause-effect assumptions.
                Recover deleted information by asking who/what/when/how specifically.
                Your goal is to help the user develop more precise, accurate, and empowering mental models.
            """
        }
    
    def get_technique_system_prompt(self, technique_id: Optional[str] = None) -> str:
        """
        Get the system prompt for a specific NLP technique.
        
        Args:
            technique_id: The ID of the NLP technique to use
            
        Returns:
            System prompt for the specified technique or a default prompt
        """
        # Base system prompt that applies to all techniques
        base_prompt = """
            You are The Inner Architect, an AI assistant specializing in NLP (Neuro-Linguistic Programming) techniques.
            Your purpose is to help users improve their mental well-being, communication skills, and personal effectiveness.
            Always be supportive, empathetic, and constructive in your responses.
            Keep your responses concise and practical - focus on actionable advice the user can apply immediately.
            When appropriate, offer a specific exercise or practice related to the NLP technique being used.
        """
        
        # If no technique specified or invalid technique, return base prompt
        if not technique_id or technique_id not in self.technique_prompts:
            return base_prompt.strip()
            
        # Return combined base prompt and technique-specific prompt
        combined_prompt = base_prompt + "\n\n" + self.technique_prompts[technique_id]
        return combined_prompt.strip()
    
    def detect_mood(self, message: str) -> str:
        """
        Detect the user's mood from their message.
        
        Args:
            message: The user's message
            
        Returns:
            Detected mood as a string (e.g., "happy", "sad", "anxious")
        """
        # Create a prompt for mood detection
        mood_prompt = """
            Analyze the following message and determine the user's likely emotional state.
            Respond with a single word that best describes their mood (e.g., happy, sad, anxious, 
            excited, frustrated, confused, neutral, hopeful, etc.)
            
            Message: {message}
            
            Mood:
        """.format(message=message)
        
        try:
            # Request mood detection
            response = self.client_factory.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a mood detection specialist. Respond with only a single word."},
                    {"role": "user", "content": mood_prompt}
                ],
                temperature=0.3,
                max_tokens=10,
                context={"endpoint": "mood_detection"}
            )
            
            # Extract and clean up the mood
            mood = response.get("message", "neutral").strip().lower()
            
            # Remove punctuation and return only the first word
            mood = mood.replace(".", "").replace(",", "").split()[0]
            
            return mood
        except Exception as e:
            logger.warning(f"Error detecting mood: {e}")
            return "neutral"
    
    def select_technique(self, message: str) -> Tuple[str, float]:
        """
        Automatically select the most appropriate NLP technique for the user's message.
        
        Args:
            message: The user's message
            
        Returns:
            Tuple of (technique_id, confidence_score)
        """
        # Create a prompt for technique selection
        technique_prompt = """
            Based on the following user message, determine which NLP technique would be most helpful.
            Consider the content, emotional tone, and implicit needs in the message.
            
            Available techniques:
            1. Reframing - Changing perspective on negative situations to find positive aspects
            2. Pattern Interruption - Breaking unhelpful thought patterns
            3. Anchoring - Creating associations between stimuli and positive emotional states
            4. Future Pacing - Mentally rehearsing future scenarios with desired outcomes
            5. Sensory Language - Using language that matches the user's preferred sensory system
            6. Meta Model - Questioning generalizations, deletions, and distortions in language
            
            User message: {message}
            
            Respond in JSON format with:
            {{"technique": "technique_id", "confidence": confidence_score, "reasoning": "brief explanation"}}
            
            Where technique_id is one of: reframing, pattern_interruption, anchoring, future_pacing, sensory_language, meta_model
            And confidence_score is between 0.0 and 1.0
        """.format(message=message)
        
        try:
            # Request technique selection
            response = self.client_factory.chat_completion(
                messages=[
                    {"role": "system", "content": "You are an NLP technique selection specialist. Respond in valid JSON format only."},
                    {"role": "user", "content": technique_prompt}
                ],
                temperature=0.3,
                max_tokens=200,
                context={"endpoint": "technique_selection"}
            )
            
            # Parse the response to extract the technique and confidence
            response_text = response.get("message", "")
            
            # Extract JSON from response if needed
            if "{" in response_text and "}" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_str = response_text[json_start:json_end]
                
                try:
                    result = json.loads(json_str)
                    technique = result.get("technique", "reframing")
                    confidence = float(result.get("confidence", 0.7))
                    
                    # Validate technique
                    if technique not in self.technique_prompts:
                        logger.warning(f"Invalid technique selected: {technique}, defaulting to reframing")
                        technique = "reframing"
                    
                    # Validate confidence
                    confidence = max(0.0, min(1.0, confidence))
                    
                    return technique, confidence
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse technique selection response: {response_text}")
            
            # Default to reframing if parsing fails
            return "reframing", 0.5
        except Exception as e:
            logger.warning(f"Error selecting technique: {e}")
            return "reframing", 0.5
    
    def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        technique_id: Optional[str] = None,
        auto_select_technique: bool = False,
        context_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a chat completion request with NLP technique integration.
        
        Args:
            messages: List of message dictionaries with role and content
            technique_id: The ID of the NLP technique to use
            auto_select_technique: Whether to automatically select the best technique
            context_id: ID of the conversation context
            **kwargs: Additional parameters to pass to the client
            
        Returns:
            Dictionary with the model's response, technique used, and metadata
        """
        # Ensure we have at least one user message
        if not messages or not any(msg['role'] == 'user' for msg in messages):
            raise ValueError("At least one user message is required")
        
        # Get the last user message for analysis
        last_user_msg = next((msg['content'] for msg in reversed(messages) 
                              if msg['role'] == 'user'), "")
        
        # Auto-select technique if needed
        selected_technique = technique_id
        confidence = 1.0
        
        if auto_select_technique or not technique_id:
            selected_technique, confidence = self.select_technique(last_user_msg)
            logger.info(f"Auto-selected technique: {selected_technique} (confidence: {confidence:.2f})")
        
        # Detect user's mood
        mood = self.detect_mood(last_user_msg)
        logger.info(f"Detected mood: {mood}")
        
        # Get the system prompt for the selected technique
        system_prompt = self.get_technique_system_prompt(selected_technique)
        
        # Add system message to the beginning of the messages list
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        
        # Add context information for better fallback responses
        context = {
            "endpoint": "chat",
            "user_message": last_user_msg,
            "technique": selected_technique,
            "context_id": context_id
        }
        
        # Send the request with fallback handling
        response = self.client_factory.chat_completion(
            messages=full_messages,
            model=self.model,
            context=context,
            **kwargs
        )
        
        # Add technique and mood information to the response
        response.update({
            "technique": {
                "id": selected_technique,
                "confidence": confidence
            },
            "mood": mood
        })
        
        return response

# Create singleton instance
claude_client = ClaudeClient()