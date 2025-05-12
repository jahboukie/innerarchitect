"""
Voice-Based Interactions module for The Inner Architect

This module provides functionality for voice-based practice of NLP techniques,
allowing users to speak their responses and receive feedback on their vocal delivery.
"""

import logging
import base64
import os
import json
from datetime import datetime

# External OpenAI API for speech processing
from openai import OpenAI

from logging_config import get_logger, info, error, debug, warning, critical, exception



# Initialize OpenAI client
# Get module-specific logger
logger = get_logger('voice_interactions')

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Performance metrics for voice analysis
VOCAL_METRICS = [
    'clarity',
    'pacing',
    'tone_variation',
    'confidence',
    'engagement',
    'naturalness'
]

# Descriptions of the vocal metrics
METRIC_DESCRIPTIONS = {
    'clarity': 'How clearly words are articulated and understood',
    'pacing': 'The speed and rhythm of speech, including appropriate pauses',
    'tone_variation': 'The range of pitch, emphasis, and emotional expression',
    'confidence': 'How assured and authoritative the delivery sounds',
    'engagement': 'How captivating and interesting the speech is to listen to',
    'naturalness': 'How organic and conversational the speech sounds'
}

# Speech exercise types
EXERCISE_TYPES = {
    'mirroring': {
        'name': 'Mirroring Exercise',
        'description': 'Listen to an example and mirror the delivery style',
        'instructions': 'Listen carefully to the example audio, then record yourself saying the same phrase with similar tone, pacing, and emphasis.'
    },
    'reframing': {
        'name': 'Reframing Exercise',
        'description': 'Convert a negative statement into a positive one',
        'instructions': 'Listen to the negative statement, then record yourself reframing it into a positive, constructive alternative.'
    },
    'sensory_language': {
        'name': 'Sensory Language Exercise',
        'description': 'Enhance a description using vivid sensory language',
        'instructions': 'Listen to the basic description, then record yourself enhancing it with rich sensory details (visual, auditory, kinesthetic, etc.).'
    },
    'meta_model': {
        'name': 'Meta Model Exercise',
        'description': 'Ask clarifying questions to recover deleted information',
        'instructions': 'Listen to the vague statement, then record yourself asking specific clarifying questions to recover missing information.'
    },
    'future_pacing': {
        'name': 'Future Pacing Exercise',
        'description': 'Describe a future scenario with compelling detail',
        'instructions': 'Listen to the goal statement, then record yourself describing what success looks and feels like in vivid, compelling detail.'
    }
}

class VoiceExercise:
    """Class representing a voice-based NLP exercise."""
    
    def __init__(self, exercise_id, exercise_type, prompt, example_text=None, 
                 example_audio_url=None, technique=None, difficulty='beginner'):
        self.exercise_id = exercise_id
        self.exercise_type = exercise_type
        self.prompt = prompt
        self.example_text = example_text
        self.example_audio_url = example_audio_url
        self.technique = technique
        self.difficulty = difficulty
        self.created_at = datetime.now()
        
    def to_dict(self):
        """Convert exercise to dictionary for JSON serialization."""
        return {
            'exercise_id': self.exercise_id,
            'exercise_type': self.exercise_type,
            'type_name': EXERCISE_TYPES[self.exercise_type]['name'],
            'type_description': EXERCISE_TYPES[self.exercise_type]['description'],
            'instructions': EXERCISE_TYPES[self.exercise_type]['instructions'],
            'prompt': self.prompt,
            'example_text': self.example_text,
            'example_audio_url': self.example_audio_url,
            'technique': self.technique,
            'difficulty': self.difficulty,
            'created_at': self.created_at.isoformat()
        }

class VoiceSubmission:
    """Class representing a user's voice submission for an exercise."""
    
    def __init__(self, submission_id, exercise_id, audio_data=None, 
                 transcript=None, session_id=None, user_id=None, feedback=None, metrics=None):
        self.submission_id = submission_id
        self.exercise_id = exercise_id
        self.audio_data = audio_data  # Base64 encoded audio data
        self.transcript = transcript
        self.session_id = session_id
        self.user_id = user_id
        self.feedback = feedback  # JSON string of feedback data
        self.metrics = metrics    # JSON string of metrics data
        self.created_at = datetime.now()
        
    def to_dict(self):
        """Convert submission to dictionary for JSON serialization."""
        return {
            'submission_id': self.submission_id,
            'exercise_id': self.exercise_id,
            'transcript': self.transcript,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'feedback': self.feedback,
            'metrics': self.metrics,
            'created_at': self.created_at.isoformat()
        }

def get_available_exercise_types():
    """
    Get information about all available voice exercise types.
    
    Returns:
        dict: All exercise types and their details
    """
    return EXERCISE_TYPES

def get_voice_exercise(exercise_id):
    """
    Get a specific voice exercise by ID.
    
    Args:
        exercise_id (str): The exercise ID
        
    Returns:
        VoiceExercise: The exercise object or None if not found
    """
    # In a real application, this would fetch from a database
    # Here we'll use a mock example for demonstration
    default_exercises = get_default_exercises()
    for exercise in default_exercises:
        if exercise.exercise_id == exercise_id:
            return exercise
    return None

def get_exercises_by_technique(technique, limit=None):
    """
    Get voice exercises for a specific NLP technique.
    
    Args:
        technique (str): The technique name
        limit (int, optional): Maximum number of exercises to return
        
    Returns:
        list: List of voice exercise objects
    """
    exercises = get_default_exercises()
    matching_exercises = [e for e in exercises if e.technique == technique]
    
    if limit:
        return matching_exercises[:limit]
    return matching_exercises

def get_exercises_by_type(exercise_type, limit=None):
    """
    Get voice exercises of a specific type.
    
    Args:
        exercise_type (str): The exercise type
        limit (int, optional): Maximum number of exercises to return
        
    Returns:
        list: List of voice exercise objects
    """
    exercises = get_default_exercises()
    matching_exercises = [e for e in exercises if e.exercise_type == exercise_type]
    
    if limit:
        return matching_exercises[:limit]
    return matching_exercises

def get_default_exercises():
    """
    Get a list of default voice exercises.
    
    Returns:
        list: List of VoiceExercise objects
    """
    exercises = [
        VoiceExercise(
            exercise_id='voice_ex_1',
            exercise_type='mirroring',
            prompt='Listen to how this positive affirmation is delivered, then mirror the delivery style',
            example_text='I am confident in my ability to communicate effectively in any situation.',
            technique='anchoring',
            difficulty='beginner'
        ),
        VoiceExercise(
            exercise_id='voice_ex_2',
            exercise_type='reframing',
            prompt='Reframe this negative statement into a positive, constructive alternative',
            example_text='I always mess up important presentations and forget what I want to say.',
            technique='reframing',
            difficulty='beginner'
        ),
        VoiceExercise(
            exercise_id='voice_ex_3',
            exercise_type='sensory_language',
            prompt='Enhance this basic description with vivid sensory details',
            example_text='The beach was nice and the water was warm.',
            technique='sensory_language',
            difficulty='intermediate'
        ),
        VoiceExercise(
            exercise_id='voice_ex_4',
            exercise_type='meta_model',
            prompt='Ask clarifying questions to recover the deleted information',
            example_text='The meeting didn\'t go well, and now everything is ruined.',
            technique='meta_model',
            difficulty='intermediate'
        ),
        VoiceExercise(
            exercise_id='voice_ex_5',
            exercise_type='future_pacing',
            prompt='Describe what success looks and feels like for this goal',
            example_text='Goal: To become a more confident public speaker',
            technique='future_pacing',
            difficulty='advanced'
        ),
        VoiceExercise(
            exercise_id='voice_ex_6',
            exercise_type='mirroring',
            prompt='Listen to this empathetic response and mirror the tone and pacing',
            example_text='I understand how challenging this situation is for you, and I want you to know that your feelings are completely valid.',
            technique='sensory_language',
            difficulty='intermediate'
        ),
        VoiceExercise(
            exercise_id='voice_ex_7',
            exercise_type='reframing',
            prompt='Reframe this limiting belief into an empowering alternative',
            example_text='I\'m too old to learn new technologies or change careers at this point.',
            technique='reframing',
            difficulty='intermediate'
        ),
        VoiceExercise(
            exercise_id='voice_ex_8',
            exercise_type='sensory_language',
            prompt='Use sensory language to describe your ideal workspace',
            example_text='A desk in a quiet room.',
            technique='sensory_language',
            difficulty='beginner'
        ),
    ]
    
    return exercises

def transcribe_audio(audio_data):
    """
    Transcribe audio data using OpenAI Whisper.
    
    Args:
        audio_data (str): Base64 encoded audio data
        
    Returns:
        str: Transcribed text or None if transcription failed
    """
    if not openai_client:
        warning("OpenAI client not initialized, cannot transcribe audio")
        return None
    
    try:
        # Decode base64 audio data
        decoded_audio = base64.b64decode(audio_data)
        
        # Save to a temporary file
        temp_filename = f"temp_audio_{datetime.now().strftime('%Y%m%d%H%M%S')}.wav"
        with open(temp_filename, 'wb') as f:
            f.write(decoded_audio)
        
        # Use OpenAI to transcribe
        with open(temp_filename, 'rb') as audio_file:
            response = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        
        # Clean up temp file
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        
        return response.text
    
    except Exception as e:
        error(f"Error transcribing audio: {e}")
        # Clean up temp file if it exists
        if 'temp_filename' in locals() and os.path.exists(temp_filename):
            os.remove(temp_filename)
        return None

def analyze_vocal_delivery(audio_data, transcript, exercise=None):
    """
    Analyze the vocal delivery aspects of a speech recording.
    
    Args:
        audio_data (str): Base64 encoded audio data
        transcript (str): Transcribed text
        exercise (VoiceExercise, optional): The exercise being attempted
        
    Returns:
        dict: Analysis results including metrics and feedback
    """
    if not openai_client:
        warning("OpenAI client not initialized, cannot analyze vocal delivery")
        return generate_fallback_analysis(transcript, exercise)
    
    try:
        # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # Do not change this unless explicitly requested by the user
        
        # Create a prompt for analyzing vocal delivery
        prompt = f"""Analyze the vocal delivery of the following transcript:

Transcript: "{transcript}"

{f'This was in response to the exercise prompt: "{exercise.prompt}"' if exercise else ''}
{f'The exercise type was: {EXERCISE_TYPES[exercise.exercise_type]["name"]}' if exercise else ''}
{f'The exercise relates to the NLP technique: {exercise.technique}' if exercise and exercise.technique else ''}

Rate the following aspects on a scale of 1-10:
- Clarity: How clearly words are articulated and understood
- Pacing: The speed and rhythm of speech, including appropriate pauses
- Tone Variation: The range of pitch, emphasis, and emotional expression
- Confidence: How assured and authoritative the delivery sounds (based on the transcript)
- Engagement: How captivating and interesting the speech is to listen to
- Naturalness: How organic and conversational the speech sounds

Also provide:
1. Specific strengths of the vocal delivery
2. Areas for improvement
3. Practical tips for enhancing vocal delivery next time

Respond with JSON in this format:
{
  "metrics": {
    "clarity": 7,
    "pacing": 6,
    "tone_variation": 8,
    "confidence": 7,
    "engagement": 7,
    "naturalness": 8
  },
  "feedback": {
    "strengths": ["Strength 1", "Strength 2", "Strength 3"],
    "areas_for_improvement": ["Area 1", "Area 2"],
    "practical_tips": ["Tip 1", "Tip 2", "Tip 3"]
  }
}
"""
        
        # Send to OpenAI for analysis
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a vocal coach and NLP expert analyzing speech patterns."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=800
        )
        
        # Parse the response
        analysis = json.loads(response.choices[0].message.content)
        return analysis
        
    except Exception as e:
        error(f"Error analyzing vocal delivery: {e}")
        return generate_fallback_analysis(transcript, exercise)

def generate_fallback_analysis(transcript, exercise=None):
    """
    Generate a basic analysis when OpenAI is unavailable.
    
    Args:
        transcript (str): Transcribed text
        exercise (VoiceExercise, optional): The exercise being attempted
        
    Returns:
        dict: Basic analysis results
    """
    # Very simple analysis based on text length and complexity
    word_count = len(transcript.split())
    sentence_count = len([s for s in transcript.split('.') if s.strip()])
    avg_words_per_sentence = word_count / max(1, sentence_count)
    unique_words = len(set(w.lower() for w in transcript.split()))
    vocabulary_richness = unique_words / max(1, word_count)
    
    # Generate baseline metrics
    clarity = min(8, 5 + int(vocabulary_richness * 10))
    pacing = 7 if 10 <= avg_words_per_sentence <= 20 else 5
    confidence = min(8, 4 + int(word_count / 20))
    
    return {
        "metrics": {
            "clarity": clarity,
            "pacing": pacing,
            "tone_variation": 6,  # Default without audio analysis
            "confidence": confidence,
            "engagement": 6,  # Default without audio analysis
            "naturalness": 7   # Default without audio analysis
        },
        "feedback": {
            "strengths": [
                "You completed the exercise successfully",
                "Your response addressed the prompt"
            ],
            "areas_for_improvement": [
                "Consider varying your tone more for emphasis",
                "Practice with different pacing to enhance engagement"
            ],
            "practical_tips": [
                "Record yourself and listen back to identify patterns",
                "Practice emphasizing key words in sentences",
                "Try incorporating deliberate pauses for effect"
            ]
        }
    }

def evaluate_technique_application(transcript, technique, exercise_type):
    """
    Evaluate how well the user applied a specific NLP technique.
    
    Args:
        transcript (str): Transcribed text
        technique (str): The NLP technique
        exercise_type (str): The type of exercise
        
    Returns:
        dict: Evaluation results
    """
    if not openai_client:
        warning("OpenAI client not initialized, cannot evaluate technique application")
        return {
            "application_score": 7,
            "feedback": "Your application of the technique shows understanding, but additional practice would enhance effectiveness."
        }
    
    try:
        # Create a prompt for evaluating technique application
        prompt = f"""Evaluate how well the following transcript applies the NLP technique of "{technique}" in a {exercise_type} exercise:

Transcript: "{transcript}"

Provide:
1. A score from 1-10 on how effectively the technique was applied
2. Specific feedback on the application of the technique
3. Examples of how the technique could be better applied

Respond with JSON in this format:
{{
  "application_score": 7,
  "strengths": ["Strength 1", "Strength 2"],
  "improvement_areas": ["Area 1", "Area 2"],
  "enhanced_examples": ["Example 1", "Example 2"]
}}
"""
        
        # Send to OpenAI for evaluation
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an NLP expert evaluating technique application."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=600
        )
        
        # Parse the response
        evaluation = json.loads(response.choices[0].message.content)
        return evaluation
        
    except Exception as e:
        error(f"Error evaluating technique application: {e}")
        return {
            "application_score": 7,
            "strengths": ["You made an attempt to apply the technique"],
            "improvement_areas": ["Consider studying the technique more deeply"],
            "enhanced_examples": ["Try practicing with varied scenarios"]
        }

def save_submission(submission):
    """
    Save a voice submission to storage.
    
    Args:
        submission (VoiceSubmission): The submission object
        
    Returns:
        bool: Success or failure
    """
    # In a real application, this would save to a database
    # Here we'll just pretend it worked
    submission.submission_id = f"sub_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return True

def get_submission(submission_id):
    """
    Get a specific submission by ID.
    
    Args:
        submission_id (str): The submission ID
        
    Returns:
        VoiceSubmission: The submission object or None
    """
    # In a real application, this would fetch from a database
    # Here we'll return None as if it wasn't found
    return None

def get_user_submissions(session_id, limit=10):
    """
    Get recent submissions for a session.
    
    Args:
        session_id (str): The session ID
        limit (int): Maximum number of submissions to return
        
    Returns:
        list: List of submission objects
    """
    # In a real application, this would fetch from a database
    # Here we'll return an empty list as if there were no submissions
    return []

def get_metric_descriptions():
    """
    Get descriptions of the vocal metrics.
    
    Returns:
        dict: Metric descriptions
    """
    return METRIC_DESCRIPTIONS