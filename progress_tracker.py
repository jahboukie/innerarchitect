"""
Progress Tracker module for The Inner Architect

This module provides functions to track and analyze user progress with NLP techniques.
"""
import logging
from datetime import datetime, timedelta

from models import (
    TechniqueEffectiveness,
    TechniqueUsageStats,
    ChatHistory,
    NLPExerciseProgress
)
from database import db

from logging_config import get_logger, info, error, debug, warning, critical, exception



# Maximum number of data points to return for charts
# Get module-specific logger
logger = get_logger('progress_tracker')

MAX_DATA_POINTS = 50

def add_technique_rating(session_id, technique, rating, notes=None, situation=None, user_id=None):
    """
    Add a rating for an NLP technique's effectiveness.
    
    Args:
        session_id (str): Session identifier
        technique (str): The NLP technique being rated
        rating (int): Rating from 1-5
        notes (str, optional): User notes about the technique
        situation (str, optional): Brief description of the situation
        user_id (int, optional): The user ID if logged in
        
    Returns:
        bool: Success or failure
    """
    try:
        # Normalize the rating to 1-5 scale
        normalized_rating = max(1, min(5, rating))
        
        # Create a new rating entry
        rating_entry = TechniqueEffectiveness(
            session_id=session_id,
            technique=technique,
            rating=normalized_rating,
            notes=notes,
            situation=situation,
            user_id=user_id
        )
        
        db.session.add(rating_entry)
        
        # Update the usage stats
        update_technique_stats(session_id, technique, normalized_rating)
        
        db.session.commit()
        info(f"Added rating {normalized_rating} for {technique}")
        return True
    except Exception as e:
        db.session.rollback()
        error(f"Error adding technique rating: {str(e)}")
        return False

def update_technique_stats(session_id, technique, rating=None):
    """
    Update the usage statistics for a technique.
    
    Args:
        session_id (str): Session identifier
        technique (str): The NLP technique
        rating (int, optional): New rating to incorporate into average
        
    Returns:
        TechniqueUsageStats: The updated stats object or None
    """
    try:
        # Find or create stats record
        stats = TechniqueUsageStats.query.filter_by(
            session_id=session_id, 
            technique=technique
        ).first()
        
        if not stats:
            stats = TechniqueUsageStats(
                session_id=session_id,
                technique=technique,
                usage_count=0,
                avg_rating=0.0
            )
            db.session.add(stats)
        
        # Update usage count
        stats.usage_count += 1
        stats.last_used = datetime.utcnow()
        
        # Update average rating if provided
        if rating:
            if stats.avg_rating == 0:
                stats.avg_rating = float(rating)
            else:
                # Weighted average favoring recent ratings
                stats.avg_rating = (stats.avg_rating * 0.7) + (float(rating) * 0.3)
        
        db.session.commit()
        return stats
    except Exception as e:
        db.session.rollback()
        error(f"Error updating technique stats: {str(e)}")
        return None

def get_technique_usage(session_id):
    """
    Get usage statistics for all techniques in a session.
    
    Args:
        session_id (str): The session identifier
        
    Returns:
        dict: Technique usage statistics
    """
    try:
        stats = TechniqueUsageStats.query.filter_by(session_id=session_id).all()
        
        # Count completed exercises by technique
        exercises = NLPExerciseProgress.query.filter_by(
            session_id=session_id,
            completed=True
        ).all()
        
        exercise_counts = {}
        for ex in exercises:
            # Get the technique from the exercise
            from nlp_exercises import get_exercise_by_id
            exercise = get_exercise_by_id(ex.exercise_id)
            if exercise:
                technique = exercise.technique
                exercise_counts[technique] = exercise_counts.get(technique, 0) + 1
        
        # Format the response
        result = []
        for stat in stats:
            result.append({
                'technique': stat.technique,
                'usage_count': stat.usage_count,
                'avg_rating': round(stat.avg_rating, 1),
                'exercises_completed': exercise_counts.get(stat.technique, 0),
                'last_used': stat.last_used.isoformat()
            })
        
        # Sort by usage count
        result.sort(key=lambda x: x['usage_count'], reverse=True)
        
        return result
    except Exception as e:
        error(f"Error getting technique usage: {str(e)}")
        return []

def get_technique_ratings(session_id, technique=None, limit=MAX_DATA_POINTS):
    """
    Get historical ratings for techniques.
    
    Args:
        session_id (str): The session identifier
        technique (str, optional): Specific technique to filter by
        limit (int): Maximum number of entries to return
        
    Returns:
        list: Rating history
    """
    try:
        query = TechniqueEffectiveness.query.filter_by(session_id=session_id)
        
        if technique:
            query = query.filter_by(technique=technique)
        
        ratings = query.order_by(TechniqueEffectiveness.entry_date.desc()).limit(limit).all()
        
        # Format the response
        result = []
        for rating in ratings:
            result.append({
                'id': rating.id,
                'technique': rating.technique,
                'rating': rating.rating,
                'notes': rating.notes,
                'situation': rating.situation,
                'date': rating.entry_date.isoformat()
            })
        
        return result
    except Exception as e:
        error(f"Error getting technique ratings: {str(e)}")
        return []

def get_chat_history_with_techniques(session_id, limit=MAX_DATA_POINTS):
    """
    Get chat history with the associated NLP techniques.
    
    Args:
        session_id (str): The session identifier
        limit (int): Maximum number of entries to return
        
    Returns:
        list: Chat history with techniques
    """
    try:
        chats = ChatHistory.query.filter_by(
            session_id=session_id
        ).order_by(
            ChatHistory.created_at.desc()
        ).limit(limit).all()
        
        # Format the response
        result = []
        for chat in chats:
            result.append({
                'message': chat.user_message[:100] + '...' if len(chat.user_message) > 100 else chat.user_message,
                'technique': chat.nlp_technique,
                'mood': chat.mood,
                'date': chat.created_at.isoformat()
            })
        
        return result
    except Exception as e:
        error(f"Error getting chat history: {str(e)}")
        return []

def get_progress_summary(session_id):
    """
    Get a summary of user progress across all techniques.
    
    Args:
        session_id (str): The session identifier
        
    Returns:
        dict: Progress summary
    """
    try:
        # Get total chat interactions
        chat_count = ChatHistory.query.filter_by(session_id=session_id).count()
        
        # Get exercises started and completed
        exercises_started = NLPExerciseProgress.query.filter_by(session_id=session_id).count()
        exercises_completed = NLPExerciseProgress.query.filter_by(
            session_id=session_id,
            completed=True
        ).count()
        
        # Get technique usage stats
        technique_stats = TechniqueUsageStats.query.filter_by(session_id=session_id).all()
        
        # Get most used and highest rated techniques
        most_used = None
        highest_rated = None
        most_used_count = 0
        highest_rating = 0
        
        for stat in technique_stats:
            if stat.usage_count > most_used_count:
                most_used_count = stat.usage_count
                most_used = stat.technique
                
            if stat.avg_rating > highest_rating:
                highest_rating = stat.avg_rating
                highest_rated = stat.technique
        
        # Calculate active streak
        today = datetime.utcnow().date()
        streak = 0
        
        # Get all chat dates, sorted in descending order
        chat_dates = db.session.query(db.func.date(ChatHistory.created_at)).filter_by(
            session_id=session_id
        ).order_by(
            db.func.date(ChatHistory.created_at).desc()
        ).distinct().all()
        
        if chat_dates:
            # Extract date objects from the result tuples
            chat_dates = [date[0] for date in chat_dates]
            
            # Calculate streak
            check_date = today
            for date in chat_dates:
                if date == check_date:
                    streak += 1
                    check_date = check_date - timedelta(days=1)
                elif date < check_date:
                    # Skip ahead to this date
                    check_date = date
                    streak += 1
                    check_date = check_date - timedelta(days=1)
                else:
                    # Future date, should not happen but just in case
                    continue
        
        # Format the response
        return {
            'chat_count': chat_count,
            'exercises_started': exercises_started,
            'exercises_completed': exercises_completed,
            'completion_rate': round(exercises_completed / exercises_started * 100, 1) if exercises_started > 0 else 0,
            'most_used_technique': most_used,
            'highest_rated_technique': highest_rated,
            'active_days_streak': streak,
            'techniques_tried': len(technique_stats)
        }
    except Exception as e:
        error(f"Error getting progress summary: {str(e)}")
        return {
            'chat_count': 0,
            'exercises_started': 0,
            'exercises_completed': 0,
            'completion_rate': 0,
            'most_used_technique': None,
            'highest_rated_technique': None,
            'active_days_streak': 0,
            'techniques_tried': 0
        }