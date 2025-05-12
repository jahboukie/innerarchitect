"""
NLP Analyzer module for The Inner Architect

This module provides functions to analyze user messages and recommend
the most appropriate NLP technique based on content and mood.
"""
import json
import logging
from openai import OpenAI
import os

from logging_config import get_logger, info, error, debug, warning, critical, exception



# Initialize OpenAI client
# Get module-specific logger
logger = get_logger('nlp_analyzer')

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
        warning("OpenAI API key is missing, cannot recommend technique")
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
        
        # Extract the AI response with proper null checking
        # This is a defensive implementation to handle unexpected response formats
        if not response or not hasattr(response, 'choices') or not response.choices:
            error("Invalid or empty response from OpenAI API")
            raise ValueError("Empty or invalid API response")
            
        if not hasattr(response.choices[0], 'message') or not response.choices[0].message:
            error("Missing message in API response")
            raise ValueError("Message content missing in API response")
            
        recommendation = getattr(response.choices[0].message, 'content', None)
        if not recommendation:
            error("Empty content in API response message")
            raise ValueError("Empty content in API response message")
        
        debug(f"Technique recommendation: {recommendation}")
        
        # Convert string to dictionary with error handling
        try:
            # json is already imported at the module level
            if isinstance(recommendation, str):
                recommendation = json.loads(recommendation)
                
            # Validate required fields
            if not isinstance(recommendation, dict):
                raise ValueError("API response is not a valid JSON object")
                
            if 'technique' not in recommendation:
                raise ValueError("API response missing 'technique' field")
                
            # Ensure technique is one of the valid options
            if recommendation['technique'] not in NLP_TECHNIQUES:
                warning(f"API returned invalid technique: {recommendation.get('technique')}")
                recommendation['technique'] = 'reframing'  # Default to a safe option
                
            return recommendation
        except json.JSONDecodeError as json_err:
            error(f"Failed to parse API response as JSON: {json_err}")
            raise
            
    except json.JSONDecodeError as json_err:
        error(f"JSON parsing error in technique recommendation: {json_err}")
        return {
            "technique": "reframing",  # Default technique
            "confidence": 0.5,
            "explanation": "Could not parse the recommendation data. Using default technique."
        }
    except ValueError as value_err:
        error(f"Value error in technique recommendation: {value_err}")
        return {
            "technique": "reframing",
            "confidence": 0.5,
            "explanation": "There was an issue with the recommendation format. Using default technique."
        }
    except Exception as e:
        error_type = type(e).__name__
        error(f"Error ({error_type}) recommending technique: {str(e)}")
        # Add more detailed logging for network-related errors
        if "APIConnectionError" in error_type or "Timeout" in error_type:
            error("Network connection issue with OpenAI API")
        elif "RateLimitError" in error_type:
            error("OpenAI API rate limit exceeded")
        
        return {
            "technique": "reframing",  # Default technique
            "confidence": 0.5,
            "explanation": "Could not analyze message due to a technical issue."
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