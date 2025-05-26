import json
import logging
from typing import Dict, List, Optional, Tuple, Any

from app.nlp.claude_client import get_claude_client

logger = logging.getLogger(__name__)

# Define available NLP techniques
NLP_TECHNIQUES = {
    "reframing": {
        "name": "Cognitive Reframing",
        "description": "Helps identify and challenge negative thought patterns and replace them with positive ones.",
        "prompts": [
            "What's another way to look at this situation?",
            "How might someone else view this differently?",
            "What evidence supports or contradicts your perspective?",
            "What's a more balanced way to think about this?"
        ]
    },
    "pattern_interruption": {
        "name": "Pattern Interruption",
        "description": "Breaks habitual thought patterns to create space for new perspectives.",
        "prompts": [
            "What assumptions are you making that could be questioned?",
            "If this belief wasn't true, what would be possible?",
            "What's a completely different approach you haven't considered?",
            "If you had to argue against your current view, what points would you make?"
        ]
    },
    "anchoring": {
        "name": "Emotional Anchoring",
        "description": "Creates associations between specific triggers and positive emotional states.",
        "prompts": [
            "When have you felt particularly confident or capable?",
            "What physical sensations accompany your positive emotions?",
            "How can you recreate this positive feeling in challenging situations?",
            "What simple trigger (word, gesture, image) could help recall this feeling?"
        ]
    },
    "future_pacing": {
        "name": "Future Pacing",
        "description": "Visualizes successful future outcomes to enhance motivation and confidence.",
        "prompts": [
            "What would success in this situation look like?",
            "How will you feel when you've overcome this challenge?",
            "What steps will have led to your success?",
            "How can you bring that future feeling into the present moment?"
        ]
    },
    "sensory_language": {
        "name": "Sensory Language",
        "description": "Uses precise sensory words to communicate more effectively and create powerful imagery.",
        "prompts": [
            "What do you see, hear, and feel in this situation?",
            "How can you describe this experience in rich sensory detail?",
            "Which sense (visual, auditory, kinesthetic) feels most important here?",
            "What metaphor or analogy captures the essence of this experience?"
        ]
    },
    "meta_model": {
        "name": "Meta Model Questioning",
        "description": "Identifies and challenges linguistic patterns that reflect limiting beliefs.",
        "prompts": [
            "What do you mean specifically by that term?",
            "How do you know that's true?",
            "Are there any exceptions or counterexamples?",
            "What would happen if you did have a choice?"
        ]
    }
}

def get_technique_details(technique_id: str) -> Dict[str, Any]:
    """
    Get details about a specific NLP technique.
    
    Args:
        technique_id: The technique identifier
        
    Returns:
        Dictionary with technique details or empty dict if not found
    """
    return NLP_TECHNIQUES.get(technique_id, {})

def get_all_techniques() -> Dict[str, Dict[str, Any]]:
    """
    Get details about all available NLP techniques.
    
    Returns:
        Dictionary of all techniques
    """
    return NLP_TECHNIQUES

def apply_technique(
    technique_id: str,
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    user_preferences: Optional[Dict[str, Any]] = None
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Apply a specific NLP technique to generate a response.
    
    Args:
        technique_id: The technique to apply
        user_message: The user's message
        conversation_history: Previous messages in the conversation
        user_preferences: User preferences to customize the response
        
    Returns:
        Tuple of (response text, metadata)
    """
    # Get the Claude client
    claude = get_claude_client()
    
    # Get technique details
    technique = get_technique_details(technique_id)
    if not technique:
        logger.warning(f"Unknown technique requested: {technique_id}")
        return "I'm not familiar with that technique. Let's try a different approach.", None
    
    # Create system prompt based on the technique
    system_prompt = _create_technique_prompt(technique_id, technique, user_preferences)
    
    # Apply the technique using Claude
    try:
        response = claude.chat_completion(
            user_message=user_message,
            conversation_history=conversation_history,
            system_prompt=system_prompt,
            temperature=0.7
        )
        
        # Extract any metadata (in a real implementation, parse structured data)
        metadata = {"technique": technique_id, "technique_name": technique.get("name")}
        
        return response, metadata
        
    except Exception as e:
        logger.error(f"Error applying {technique_id} technique: {str(e)}")
        return "I encountered an issue while processing your request. Let's try a different approach.", None

def _create_technique_prompt(
    technique_id: str, 
    technique_details: Dict[str, Any],
    user_preferences: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a system prompt for a specific NLP technique.
    
    Args:
        technique_id: The technique identifier
        technique_details: Details about the technique
        user_preferences: User preferences for customization
        
    Returns:
        System prompt for Claude
    """
    # Base prompt for all techniques
    base_prompt = """
    You are an expert AI assistant specializing in NLP (Neuro-Linguistic Programming) techniques 
    for improving mental well-being, emotional intelligence, and communication skills.
    Your responses should be supportive, insightful, and focused on helping the user.
    """
    
    # Customize based on user preferences if available
    experience_level = "beginner"
    show_explanations = True
    communication_style = "supportive"
    
    if user_preferences:
        experience_level = user_preferences.get("experience_level", experience_level)
        show_explanations = user_preferences.get("show_explanations", show_explanations)
        communication_style = user_preferences.get("communication_style", communication_style)
    
    # Technique-specific instructions
    technique_prompts = {
        "reframing": f"""
            Apply cognitive reframing techniques to help the user see their situation from new perspectives.
            Focus on identifying negative thought patterns, challenging distorted thinking, and suggesting 
            alternative interpretations that are more balanced and positive.
            
            When appropriate, gently highlight thought distortions like black-and-white thinking, 
            catastrophizing, or overgeneralization.
            
            Experience level: {experience_level}
            Show technique explanations: {show_explanations}
            Communication style: {communication_style}
            
            Remember to validate the user's feelings first before suggesting reframes.
        """,
        
        "pattern_interruption": f"""
            Use pattern interruption techniques to help the user break free from limiting patterns of thought.
            Your goal is to create a mental "pattern break" that opens space for new ways of thinking.
            
            Techniques include:
            - Unexpected questions that challenge assumptions
            - Presenting surprising perspectives or counterexamples
            - Using metaphors that recontextualize the situation
            - Socratic questioning to reveal flaws in reasoning
            
            Experience level: {experience_level}
            Show technique explanations: {show_explanations}
            Communication style: {communication_style}
            
            Be bold but respectful in challenging the user's thinking patterns.
        """,
        
        "anchoring": f"""
            Apply emotional anchoring techniques to help the user create positive emotional associations.
            Guide them to identify and access resourceful emotional states that they can "anchor" to specific
            triggers (words, gestures, images) for future use.
            
            The process includes:
            1. Helping the user identify and intensify positive emotional states
            2. Establishing clear sensory-rich descriptions of these states
            3. Creating reliable triggers to recall these states
            4. Practicing the anchor in different contexts
            
            Experience level: {experience_level}
            Show technique explanations: {show_explanations}
            Communication style: {communication_style}
            
            Use vivid sensory language to help the user fully experience positive emotional states.
        """,
        
        "future_pacing": f"""
            Use future pacing techniques to help the user visualize successful outcomes and rehearse future scenarios.
            Guide them to create detailed mental simulations of successfully navigating challenges.
            
            Effective future pacing includes:
            1. Establishing a specific future scenario
            2. Creating a vivid multi-sensory experience of success
            3. Identifying resources and strategies needed
            4. Mental rehearsal of the successful outcome
            
            Experience level: {experience_level}
            Show technique explanations: {show_explanations}
            Communication style: {communication_style}
            
            Help the user experience their future success as if it were happening now.
        """,
        
        "sensory_language": f"""
            Apply sensory language techniques to help the user communicate more effectively and process
            experiences in rich detail. Guide them to use precise visual, auditory, and kinesthetic language.
            
            Key aspects include:
            1. Identifying the user's primary representational system (visual, auditory, kinesthetic)
            2. Matching and expanding their sensory language
            3. Using metaphors and analogies that resonate with their experience
            4. Helping them translate between different sensory modalities
            
            Experience level: {experience_level}
            Show technique explanations: {show_explanations}
            Communication style: {communication_style}
            
            Model rich sensory language in your own responses.
        """,
        
        "meta_model": f"""
            Apply Meta Model questioning techniques to help the user identify and challenge linguistic
            patterns that reflect limiting beliefs and distortions.
            
            Focus on:
            1. Identifying deletions (missing information)
            2. Clarifying generalizations (always, never, everyone)
            3. Challenging distortions (mind reading, cause-effect assumptions)
            
            Key question patterns include:
            - "What specifically do you mean by X?"
            - "How do you know that's true?"
            - "According to whom? Compared to what?"
            - "What would happen if you did/didn't?"
            
            Experience level: {experience_level}
            Show technique explanations: {show_explanations}
            Communication style: {communication_style}
            
            Be curious and gentle, not confrontational, when challenging linguistic patterns.
        """
    }
    
    # Get the appropriate prompt for the technique
    technique_prompt = technique_prompts.get(technique_id, "")
    
    # Combine base prompt with technique-specific instructions
    full_prompt = f"{base_prompt}\n\n{technique_prompt}"
    
    return full_prompt

def detect_user_mood(message: str) -> str:
    """
    Detect the user's emotional state from their message.
    
    Args:
        message: The user's message
        
    Returns:
        Detected mood (e.g., "anxious", "hopeful", "frustrated")
    """
    # Get the Claude client
    claude = get_claude_client()
    
    system_prompt = """
    You are an expert in emotional intelligence and psychological analysis.
    Based on the message, identify the primary emotional state of the user.
    Choose one of the following mood categories: happy, sad, anxious, frustrated, 
    confused, hopeful, neutral, excited, angry, thankful, curious, overwhelmed.
    Respond with ONLY the single most applicable mood word from the list above, 
    nothing else.
    """
    
    try:
        mood = claude.analyze_text(
            text=message,
            task_description=system_prompt,
            temperature=0.3
        ).strip().lower()
        
        # Validate the response (ensure it's one of our expected moods)
        valid_moods = [
            "happy", "sad", "anxious", "frustrated", "confused", 
            "hopeful", "neutral", "excited", "angry", "thankful", 
            "curious", "overwhelmed"
        ]
        
        if mood in valid_moods:
            return mood
        else:
            logger.warning(f"Unexpected mood detected: {mood}. Defaulting to 'neutral'.")
            return "neutral"
            
    except Exception as e:
        logger.error(f"Error detecting user mood: {str(e)}")
        return "neutral"

def suggest_technique(message: str, user_history: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Suggest an appropriate NLP technique based on the user's message and history.
    
    Args:
        message: The user's current message
        user_history: Previous interactions with technique effectiveness
        
    Returns:
        Technique ID that's most appropriate
    """
    # Get the Claude client
    claude = get_claude_client()
    
    # If we have user history, include information about technique effectiveness
    technique_preference = ""
    if user_history:
        # Format history information for the prompt
        technique_ratings = {}
        for interaction in user_history:
            technique = interaction.get("technique")
            rating = interaction.get("rating", 0)
            if technique and rating:
                if technique not in technique_ratings:
                    technique_ratings[technique] = {"count": 0, "total": 0}
                technique_ratings[technique]["count"] += 1
                technique_ratings[technique]["total"] += rating
        
        # Calculate average ratings
        avg_ratings = {}
        for technique, data in technique_ratings.items():
            if data["count"] > 0:
                avg_ratings[technique] = data["total"] / data["count"]
        
        # Include this information in the prompt
        if avg_ratings:
            technique_preference = "Based on previous interactions, the user has responded well to: "
            for technique, rating in avg_ratings.items():
                if rating >= 3.5:  # Only include positively rated techniques
                    technique_name = NLP_TECHNIQUES.get(technique, {}).get("name", technique)
                    technique_preference += f"{technique_name} (avg rating: {rating:.1f}/5), "
            technique_preference = technique_preference.rstrip(", ") + "."
    
    # Create system prompt for technique suggestion
    techniques_info = "\n".join([
        f"{technique_id}: {details['name']} - {details['description']}" 
        for technique_id, details in NLP_TECHNIQUES.items()
    ])
    
    system_prompt = f"""
    You are an expert in NLP (Neuro-Linguistic Programming) techniques.
    Based on the user's message, determine the most appropriate NLP technique to apply.
    
    Available techniques:
    {techniques_info}
    
    {technique_preference}
    
    Analyze the message and respond with ONLY the technique ID (e.g., "reframing") 
    that would be most helpful for this user's situation. Don't include any other text.
    """
    
    try:
        suggested_technique = claude.analyze_text(
            text=message,
            task_description=system_prompt,
            temperature=0.3
        ).strip().lower()
        
        # Validate the response
        if suggested_technique in NLP_TECHNIQUES:
            return suggested_technique
        else:
            logger.warning(f"Invalid technique suggested: {suggested_technique}. Defaulting to 'reframing'.")
            return "reframing"
            
    except Exception as e:
        logger.error(f"Error suggesting technique: {str(e)}")
        return "reframing"  # Default to reframing