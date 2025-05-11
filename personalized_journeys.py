"""
Personalized NLP Journeys module for The Inner Architect

This module provides customized learning paths based on user's communication style,
technique preferences, and specific goals. It recommends techniques, exercises,
and practice sequences tailored to individual needs.
"""

import logging
import random
from datetime import datetime, timedelta

from models import User, TechniqueEffectiveness, NLPExerciseProgress, ChatHistory, db
from nlp_techniques import get_technique_details, get_all_technique_names
from nlp_exercises import get_exercises_by_technique
from communication_analyzer import get_all_communication_styles

# Journey types with specific focus areas
JOURNEY_TYPES = {
    'communication_improvement': {
        'name': 'Communication Improvement',
        'description': 'Enhance your general communication effectiveness',
        'focus': ['clarity', 'persuasion', 'listening', 'empathy'],
        'duration_days': 14,
        'intensity_levels': ['light', 'moderate', 'intensive']
    },
    'confidence_building': {
        'name': 'Confidence Building',
        'description': 'Develop greater self-assurance in your interactions',
        'focus': ['self_expression', 'assertiveness', 'resilience'],
        'duration_days': 21,
        'intensity_levels': ['light', 'moderate', 'intensive']
    },
    'relationship_enhancement': {
        'name': 'Relationship Enhancement',
        'description': 'Improve personal and professional relationships',
        'focus': ['empathy', 'understanding', 'conflict_resolution'],
        'duration_days': 21,
        'intensity_levels': ['light', 'moderate', 'intensive']
    },
    'professional_growth': {
        'name': 'Professional Growth',
        'description': 'Develop communication skills for workplace success',
        'focus': ['leadership', 'negotiation', 'clarity', 'persuasion'],
        'duration_days': 30,
        'intensity_levels': ['light', 'moderate', 'intensive']
    },
    'emotional_regulation': {
        'name': 'Emotional Regulation',
        'description': 'Manage emotions effectively in your communications',
        'focus': ['self_awareness', 'resilience', 'mindfulness'],
        'duration_days': 21,
        'intensity_levels': ['light', 'moderate', 'intensive']
    }
}

# Technique recommendation weights by communication style
STYLE_TO_TECHNIQUE_WEIGHTS = {
    'assertive': {
        'reframing': 0.7,
        'pattern_interruption': 0.5,
        'anchoring': 0.7,
        'future_pacing': 0.8,
        'sensory_language': 0.6,
        'meta_model': 0.9
    },
    'passive': {
        'reframing': 0.9,
        'pattern_interruption': 0.8,
        'anchoring': 0.7,
        'future_pacing': 0.6, 
        'sensory_language': 0.5,
        'meta_model': 0.7
    },
    'aggressive': {
        'reframing': 0.8,
        'pattern_interruption': 0.9,
        'anchoring': 0.6,
        'future_pacing': 0.5,
        'sensory_language': 0.6,
        'meta_model': 0.7
    },
    'passive_aggressive': {
        'reframing': 0.9,
        'pattern_interruption': 0.8,
        'anchoring': 0.7,
        'future_pacing': 0.6,
        'sensory_language': 0.5,
        'meta_model': 0.9
    },
    'analytical': {
        'reframing': 0.6,
        'pattern_interruption': 0.5,
        'anchoring': 0.7,
        'future_pacing': 0.8,
        'sensory_language': 0.9,
        'meta_model': 0.7
    },
    'intuitive': {
        'reframing': 0.7,
        'pattern_interruption': 0.6,
        'anchoring': 0.8,
        'future_pacing': 0.9,
        'sensory_language': 0.7,
        'meta_model': 0.5
    },
    'empathetic': {
        'reframing': 0.8,
        'pattern_interruption': 0.5,
        'anchoring': 0.7,
        'future_pacing': 0.6,
        'sensory_language': 0.9,
        'meta_model': 0.7
    }
}

# Journey focus areas to technique mapping
FOCUS_TO_TECHNIQUES = {
    'clarity': ['meta_model', 'sensory_language', 'reframing'],
    'persuasion': ['anchoring', 'future_pacing', 'sensory_language'],
    'listening': ['meta_model', 'reframing', 'pattern_interruption'],
    'empathy': ['sensory_language', 'reframing', 'meta_model'],
    'self_expression': ['sensory_language', 'meta_model', 'reframing'],
    'assertiveness': ['meta_model', 'reframing', 'pattern_interruption'],
    'resilience': ['reframing', 'anchoring', 'pattern_interruption'],
    'understanding': ['meta_model', 'sensory_language', 'reframing'],
    'conflict_resolution': ['reframing', 'pattern_interruption', 'meta_model'],
    'leadership': ['future_pacing', 'anchoring', 'meta_model'],
    'negotiation': ['reframing', 'meta_model', 'future_pacing'],
    'self_awareness': ['reframing', 'pattern_interruption', 'sensory_language'],
    'mindfulness': ['pattern_interruption', 'anchoring', 'sensory_language']
}

# Intensity to daily practice time mapping (in minutes)
INTENSITY_TO_PRACTICE_TIME = {
    'light': 10,
    'moderate': 20,
    'intensive': 30
}

class Journey:
    """Class representing a personalized NLP journey."""
    
    def __init__(self, journey_id, journey_type, focus_areas, techniques, 
                 exercises, start_date, end_date, intensity, milestones=None):
        self.journey_id = journey_id
        self.journey_type = journey_type
        self.focus_areas = focus_areas
        self.techniques = techniques
        self.exercises = exercises
        self.start_date = start_date
        self.end_date = end_date
        self.intensity = intensity
        self.milestones = milestones or []
        
    def to_dict(self):
        """Convert journey to dictionary for JSON serialization."""
        return {
            'journey_id': self.journey_id,
            'journey_type': self.journey_type,
            'name': JOURNEY_TYPES[self.journey_type]['name'],
            'description': JOURNEY_TYPES[self.journey_type]['description'],
            'focus_areas': self.focus_areas,
            'techniques': self.techniques,
            'exercises': self.exercises,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'intensity': self.intensity,
            'daily_practice_minutes': INTENSITY_TO_PRACTICE_TIME[self.intensity],
            'duration_days': (self.end_date - self.start_date).days,
            'milestones': self.milestones
        }

def create_personalized_journey(
    session_id, 
    journey_type, 
    comm_style=None, 
    focus_areas=None, 
    intensity='moderate', 
    user_id=None
):
    """
    Create a personalized NLP journey based on user profile and preferences.
    
    Args:
        session_id (str): The session identifier
        journey_type (str): Type of journey to create
        comm_style (str, optional): User's communication style
        focus_areas (list, optional): Specific focus areas
        intensity (str): Intensity level ('light', 'moderate', 'intensive')
        user_id (int, optional): Database user ID if available
        
    Returns:
        Journey: A personalized journey object
    """
    # Validate inputs
    if journey_type not in JOURNEY_TYPES:
        logging.error(f"Invalid journey type: {journey_type}")
        return None
        
    if intensity not in ['light', 'moderate', 'intensive']:
        intensity = 'moderate'
    
    journey_config = JOURNEY_TYPES[journey_type]
    
    # If focus areas not specified, use journey defaults
    if not focus_areas:
        focus_areas = journey_config['focus']
    else:
        # Filter to valid focus areas
        focus_areas = [f for f in focus_areas if f in FOCUS_TO_TECHNIQUES]
        if not focus_areas:
            focus_areas = journey_config['focus'][:2]  # Use first two defaults
    
    # Determine techniques based on focus areas and communication style
    techniques = []
    
    for focus in focus_areas:
        if focus in FOCUS_TO_TECHNIQUES:
            focus_techniques = FOCUS_TO_TECHNIQUES[focus]
            
            # Apply communication style weighting if available
            if comm_style and comm_style in STYLE_TO_TECHNIQUE_WEIGHTS:
                # Sort techniques by weight for this communication style
                weighted_techniques = [
                    (t, STYLE_TO_TECHNIQUE_WEIGHTS[comm_style].get(t, 0.5))
                    for t in focus_techniques
                ]
                weighted_techniques.sort(key=lambda x: x[1], reverse=True)
                techniques.extend([t[0] for t in weighted_techniques])
            else:
                techniques.extend(focus_techniques)
    
    # Remove duplicates while preserving order
    unique_techniques = []
    for t in techniques:
        if t not in unique_techniques:
            unique_techniques.append(t)
    
    # Limit to 4-6 techniques based on intensity
    max_techniques = 4 if intensity == 'light' else (5 if intensity == 'moderate' else 6)
    techniques = unique_techniques[:max_techniques]
    
    # Select exercises for each technique
    exercises = {}
    for technique in techniques:
        available_exercises = get_exercises_by_technique(technique)
        if available_exercises:
            # Choose exercises appropriate for the intensity level
            if intensity == 'light':
                # Select 1-2 beginner exercises
                beginner_exercises = [e for e in available_exercises if e.difficulty == 'beginner']
                if beginner_exercises:
                    exercises[technique] = random.sample(beginner_exercises, min(2, len(beginner_exercises)))
                else:
                    exercises[technique] = random.sample(available_exercises, min(1, len(available_exercises)))
            elif intensity == 'moderate':
                # Select 2-3 beginner to intermediate exercises
                mixed_exercises = [e for e in available_exercises if e.difficulty in ['beginner', 'intermediate']]
                if mixed_exercises:
                    exercises[technique] = random.sample(mixed_exercises, min(3, len(mixed_exercises)))
                else:
                    exercises[technique] = random.sample(available_exercises, min(2, len(available_exercises)))
            else:  # intensive
                # Select 3-4 exercises of all levels
                exercises[technique] = random.sample(available_exercises, min(4, len(available_exercises)))
    
    # Determine journey dates
    start_date = datetime.now()
    duration = journey_config['duration_days']
    if intensity == 'light':
        duration = int(duration * 1.5)  # Extend for light intensity
    elif intensity == 'intensive':
        duration = int(duration * 0.8)  # Shorten for intensive
    
    end_date = start_date + timedelta(days=duration)
    
    # Create milestones
    milestones = create_journey_milestones(
        start_date, end_date, techniques, exercises, intensity
    )
    
    # Generate a unique journey ID
    journey_id = f"{session_id}_{journey_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Create journey object
    journey = Journey(
        journey_id=journey_id,
        journey_type=journey_type,
        focus_areas=focus_areas,
        techniques=techniques,
        exercises={t: [e.id for e in exs] for t, exs in exercises.items()},
        start_date=start_date,
        end_date=end_date,
        intensity=intensity,
        milestones=milestones
    )
    
    return journey

def create_journey_milestones(start_date, end_date, techniques, exercises, intensity):
    """
    Create milestones for a journey.
    
    Args:
        start_date (datetime): Journey start date
        end_date (datetime): Journey end date
        techniques (list): List of technique IDs
        exercises (dict): Dict of technique ID to list of exercise objects
        intensity (str): Intensity level
        
    Returns:
        list: List of milestone dictionaries
    """
    milestones = []
    
    # Determine frequency based on intensity
    if intensity == 'light':
        frequency_days = 3  # Every 3 days
    elif intensity == 'moderate':
        frequency_days = 2  # Every 2 days
    else:  # intensive
        frequency_days = 1  # Daily
    
    # Create a timeline of dates
    duration = (end_date - start_date).days
    milestone_dates = []
    
    # Start from day 1, not day 0
    current_date = start_date + timedelta(days=1)
    
    while current_date < end_date:
        milestone_dates.append(current_date)
        current_date += timedelta(days=frequency_days)
    
    # Ensure we have a balanced distribution of techniques and exercises
    technique_cycle = techniques.copy()
    
    # Create milestones for each date
    milestone_number = 1
    for date in milestone_dates:
        # Cycle through techniques
        if not technique_cycle:
            technique_cycle = techniques.copy()
            random.shuffle(technique_cycle)
        
        technique = technique_cycle.pop(0)
        
        # Select an exercise for this technique
        milestone_exercise = None
        if technique in exercises and exercises[technique]:
            milestone_exercise = random.choice(exercises[technique])
        
        # Create the milestone
        milestone = {
            'number': milestone_number,
            'date': date.strftime('%Y-%m-%d'),
            'technique': technique,
            'exercise_id': milestone_exercise.id if milestone_exercise else None,
            'completed': False
        }
        
        milestones.append(milestone)
        milestone_number += 1
    
    return milestones

def get_next_milestone(journey, date=None):
    """
    Get the next incomplete milestone in a journey.
    
    Args:
        journey (Journey): The journey object
        date (datetime, optional): Reference date (defaults to today)
        
    Returns:
        dict: The next milestone or None if all are completed
    """
    if not date:
        date = datetime.now()
    
    date_str = date.strftime('%Y-%m-%d')
    
    # First try to find any incomplete milestone on or before today
    for milestone in journey.milestones:
        if not milestone['completed'] and milestone['date'] <= date_str:
            return milestone
    
    # If none found, find the next upcoming milestone
    for milestone in sorted(journey.milestones, key=lambda m: m['date']):
        if not milestone['completed'] and milestone['date'] > date_str:
            return milestone
    
    return None

def update_milestone_status(journey_id, milestone_number, completed=True):
    """
    Update the status of a milestone.
    
    Args:
        journey_id (str): The journey identifier
        milestone_number (int): The milestone number
        completed (bool): Whether milestone is completed
        
    Returns:
        bool: Success or failure
    """
    # This would normally update the milestone in a database
    # For now, we're working with in-memory data
    return True

def get_techniques_by_communication_style(comm_style, limit=3):
    """
    Get recommended techniques for a communication style.
    
    Args:
        comm_style (str): Communication style identifier
        limit (int): Maximum number of techniques to return
        
    Returns:
        list: List of recommended technique IDs
    """
    if comm_style not in STYLE_TO_TECHNIQUE_WEIGHTS:
        return list(get_all_technique_names().keys())[:limit]
    
    # Sort techniques by weight for this style
    weighted_techniques = [
        (t, w) for t, w in STYLE_TO_TECHNIQUE_WEIGHTS[comm_style].items()
    ]
    weighted_techniques.sort(key=lambda x: x[1], reverse=True)
    
    # Return top N techniques
    return [t[0] for t in weighted_techniques[:limit]]

def get_journey_progress(journey_id):
    """
    Calculate progress statistics for a journey.
    
    Args:
        journey_id (str): The journey identifier
        
    Returns:
        dict: Progress statistics
    """
    # This would normally retrieve journey data from database
    # For now, we'll return a placeholder
    return {
        'journey_id': journey_id,
        'total_milestones': 0,
        'completed_milestones': 0,
        'progress_percentage': 0,
        'techniques_practiced': [],
        'exercises_completed': []
    }

def get_all_journey_types():
    """
    Get all available journey types.
    
    Returns:
        dict: All journey types and their details
    """
    return JOURNEY_TYPES

def get_focus_areas():
    """
    Get all available focus areas for journeys.
    
    Returns:
        dict: Focus areas with descriptions
    """
    focus_areas = {
        'clarity': 'Communicate ideas more clearly and effectively',
        'persuasion': 'Influence others more effectively with your communication',
        'listening': 'Improve your active listening skills',
        'empathy': 'Better understand and relate to others\' experiences',
        'self_expression': 'Express yourself more authentically and confidently',
        'assertiveness': 'Communicate your needs directly while respecting others',
        'resilience': 'Handle challenging communications with greater ease',
        'understanding': 'Improve your comprehension of complex messages',
        'conflict_resolution': 'Navigate disagreements more productively',
        'leadership': 'Communicate more effectively as a leader',
        'negotiation': 'Improve your ability to reach mutually beneficial agreements',
        'self_awareness': 'Understand your own communication patterns better',
        'mindfulness': 'Be more present and deliberate in your communications'
    }
    
    return focus_areas