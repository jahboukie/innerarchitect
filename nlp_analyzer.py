"""
NLP Analyzer module for The Inner Architect

This module provides functions to analyze user messages and recommend
the most appropriate NLP technique based on content and mood.
"""
import logging
from openai import OpenAI
import os

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Dictionary mapping technique names to their descriptions
NLP_TECHNIQUES = {
    'reframing': 'Reframing helps users see situations from different perspectives and find positive aspects in challenges.',
    'pattern_interruption': 'Pattern interruption breaks negative thought cycles and establishes new, healthier patterns.',
    'anchoring': 'Anchoring associates positive emotions with specific physical or mental triggers.',
    'future_pacing': 'Future pacing guides users to visualize positive outcomes and mentally rehearse success.',
    'sensory_language': 'Sensory language uses visual, auditory, and kinesthetic language to enhance communication.',
    'meta_model': 'Meta model questioning challenges limiting beliefs and generalizations through targeted questions.'
}

def recommend_technique(message, mood):
    """
    Analyzes the message content and mood to recommend the most appropriate NLP technique.
    
    Args:
        message (str): The user's message
        mood (str): The user's current mood
        
    Returns:
        dict: Contains recommended technique, confidence score, and explanation
    """
    if not OPENAI_API_KEY or not openai_client:
        logging.warning("OpenAI API key is missing, cannot recommend technique")
        return {
            "technique": "reframing",  # Default technique
            "confidence": 0.5,
            "explanation": "Technique recommendation requires API connection."
        }
    
    try:
        # Construct the prompt for the recommendation
        system_prompt = """You are an expert in Neuro-Linguistic Programming (NLP) techniques.
        Analyze the user's message and mood, then recommend the most appropriate NLP technique from the following options:
        
        1. reframing - Help users see situations from different perspectives
        2. pattern_interruption - Break negative thought cycles
        3. anchoring - Associate positive emotions with specific triggers
        4. future_pacing - Guide users to visualize positive future outcomes
        5. sensory_language - Use visual, auditory, and kinesthetic language matching their style
        6. meta_model - Ask questions that challenge limiting beliefs and generalizations
        
        Return your response as JSON with three fields:
        - technique: The recommended technique (use the exact name from the list above)
        - confidence: A confidence score between 0 and 1
        - explanation: A brief explanation of why this technique is recommended
        """
        
        # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"User mood: {mood}\nUser message: {message}"}
            ],
            response_format={"type": "json_object"},
            max_tokens=150
        )
        
        # Parse the recommendation
        recommendation = response.choices[0].message.content
        logging.debug(f"Technique recommendation: {recommendation}")
        
        # Convert string to dictionary if needed
        if isinstance(recommendation, str):
            import json
            recommendation = json.loads(recommendation)
            
        return recommendation
        
    except Exception as e:
        logging.error(f"Error recommending technique: {str(e)}")
        return {
            "technique": "reframing",  # Default technique
            "confidence": 0.5,
            "explanation": "Could not analyze message due to an error."
        }

def get_technique_description(technique):
    """
    Gets the description for a specific NLP technique.
    
    Args:
        technique (str): The technique name
        
    Returns:
        str: The description of the technique
    """
    return NLP_TECHNIQUES.get(technique, "No description available.")