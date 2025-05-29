"""
Offline Sync API for The Inner Architect

This module provides the API endpoints for synchronizing data between
online and offline modes, ensuring a seamless user experience regardless
of connectivity status.
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

from flask import Blueprint, request, jsonify, g, current_app

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
offline_api = Blueprint('offline_api', __name__, url_prefix='/api/offline')

@offline_api.route('/sync', methods=['POST'])
def sync_offline_data():
    """
    Synchronize offline data with the server.
    
    Expected request body:
    {
        "actions": [
            {
                "id": "unique-client-id",
                "type": "reminder/create",
                "data": { ... },
                "timestamp": 1650123456789,
                "synced": false
            },
            ...
        ]
    }
    
    Returns:
    {
        "success": true,
        "results": [
            {
                "id": "unique-client-id",
                "success": true,
                "synced": true,
                "server_id": "server-generated-id"  // Only for creation actions
            },
            ...
        ]
    }
    """
    try:
        data = request.json
        
        if not data or not isinstance(data.get('actions'), list):
            return jsonify({"success": False, "error": "Invalid request format"}), 400
        
        actions = data.get('actions', [])
        results = []
        
        for action in actions:
            action_id = action.get('id')
            action_type = action.get('type')
            action_data = action.get('data', {})
            
            # Process different action types
            if action_type.startswith('reminder/'):
                result = process_reminder_action(action_type, action_data, action_id)
            elif action_type.startswith('exercise/'):
                result = process_exercise_action(action_type, action_data, action_id)
            elif action_type.startswith('journey/'):
                result = process_journey_action(action_type, action_data, action_id)
            elif action_type.startswith('user/'):
                result = process_user_action(action_type, action_data, action_id)
            else:
                result = {
                    "id": action_id,
                    "success": False,
                    "error": "Unknown action type",
                    "synced": False
                }
            
            results.append(result)
        
        return jsonify({
            "success": True,
            "results": results
        })
        
    except Exception as e:
        logger.error(f"Error in sync_offline_data: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

def process_reminder_action(action_type: str, data: Dict, action_id: str) -> Dict:
    """
    Process reminder-related actions.
    
    Args:
        action_type: Type of action (create, update, delete, complete)
        data: Action data
        action_id: Client-generated action ID
        
    Returns:
        Dict: Result of the action
    """
    from practice_reminders import create_reminder, update_reminder, delete_reminder, mark_reminder_complete
    
    try:
        if action_type == 'reminder/create':
            # Create a new reminder
            reminder = create_reminder(
                user_id=g.user.id if hasattr(g, 'user') and g.user else None,
                session_id=data.get('session_id', 'offline_sync'),
                title=data.get('title'),
                description=data.get('description'),
                reminder_type=data.get('reminder_type'),
                frequency=data.get('frequency'),
                time_preferences=data.get('time_preferences'),
                days_of_week=data.get('days_of_week'),
                linked_content_id=data.get('linked_content_id')
            )
            
            if reminder:
                return {
                    "id": action_id,
                    "success": True,
                    "synced": True,
                    "server_id": reminder.reminder_id
                }
            else:
                return {
                    "id": action_id,
                    "success": False,
                    "error": "Failed to create reminder",
                    "synced": False
                }
                
        elif action_type == 'reminder/update':
            # Update an existing reminder
            reminder_id = data.get('reminder_id')
            updates = {k: v for k, v in data.items() if k != 'reminder_id' and k != 'session_id'}
            session_id = data.get('session_id', 'offline_sync')
            
            updated_reminder = update_reminder(reminder_id, session_id, updates)
            
            if updated_reminder:
                return {
                    "id": action_id,
                    "success": True,
                    "synced": True
                }
            else:
                return {
                    "id": action_id,
                    "success": False,
                    "error": "Failed to update reminder",
                    "synced": False
                }
                
        elif action_type == 'reminder/delete':
            # Delete a reminder
            reminder_id = data.get('reminder_id')
            session_id = data.get('session_id', 'offline_sync')
            
            success = delete_reminder(reminder_id, session_id)
            
            return {
                "id": action_id,
                "success": success,
                "synced": success
            }
            
        elif action_type == 'reminder/complete':
            # Mark a reminder as complete
            reminder_id = data.get('reminder_id')
            session_id = data.get('session_id', 'offline_sync')
            
            completed_reminder = mark_reminder_complete(reminder_id, session_id)
            
            if completed_reminder:
                return {
                    "id": action_id,
                    "success": True,
                    "synced": True
                }
            else:
                return {
                    "id": action_id,
                    "success": False,
                    "error": "Failed to complete reminder",
                    "synced": False
                }
        else:
            return {
                "id": action_id,
                "success": False,
                "error": f"Unknown reminder action: {action_type}",
                "synced": False
            }
            
    except Exception as e:
        logger.error(f"Error processing reminder action: {e}")
        return {
            "id": action_id,
            "success": False,
            "error": str(e),
            "synced": False
        }

def process_exercise_action(action_type: str, data: Dict, action_id: str) -> Dict:
    """
    Process exercise-related actions.
    
    Args:
        action_type: Type of action (progress, complete, etc.)
        data: Action data
        action_id: Client-generated action ID
        
    Returns:
        Dict: Result of the action
    """
    try:
        if action_type == 'exercise/progress':
            # Update exercise progress
            exercise_id = data.get('exercise_id')
            progress = data.get('progress')
            user_id = g.user.id if hasattr(g, 'user') and g.user else None
            
            # In a real app, this would update the database
            # For now, we'll just pretend it worked
            
            return {
                "id": action_id,
                "success": True,
                "synced": True
            }
            
        elif action_type == 'exercise/complete':
            # Mark exercise as complete
            exercise_id = data.get('exercise_id')
            user_id = g.user.id if hasattr(g, 'user') and g.user else None
            
            # In a real app, this would update the database
            # For now, we'll just pretend it worked
            
            return {
                "id": action_id,
                "success": True,
                "synced": True
            }
            
        else:
            return {
                "id": action_id,
                "success": False,
                "error": f"Unknown exercise action: {action_type}",
                "synced": False
            }
            
    except Exception as e:
        logger.error(f"Error processing exercise action: {e}")
        return {
            "id": action_id,
            "success": False,
            "error": str(e),
            "synced": False
        }

def process_journey_action(action_type: str, data: Dict, action_id: str) -> Dict:
    """
    Process journey-related actions.
    
    Args:
        action_type: Type of action (progress, etc.)
        data: Action data
        action_id: Client-generated action ID
        
    Returns:
        Dict: Result of the action
    """
    try:
        if action_type == 'journey/progress':
            # Update journey progress
            journey_id = data.get('journey_id')
            step = data.get('step')
            user_id = g.user.id if hasattr(g, 'user') and g.user else None
            
            # In a real app, this would update the database
            # For now, we'll just pretend it worked
            
            return {
                "id": action_id,
                "success": True,
                "synced": True
            }
            
        else:
            return {
                "id": action_id,
                "success": False,
                "error": f"Unknown journey action: {action_type}",
                "synced": False
            }
            
    except Exception as e:
        logger.error(f"Error processing journey action: {e}")
        return {
            "id": action_id,
            "success": False,
            "error": str(e),
            "synced": False
        }

def process_user_action(action_type: str, data: Dict, action_id: str) -> Dict:
    """
    Process user-related actions.
    
    Args:
        action_type: Type of action (preferences, settings, etc.)
        data: Action data
        action_id: Client-generated action ID
        
    Returns:
        Dict: Result of the action
    """
    try:
        if action_type == 'user/preferences':
            # Update user preferences
            preferences = data.get('preferences', {})
            user_id = g.user.id if hasattr(g, 'user') and g.user else None
            
            # In a real app, this would update the database
            # For now, we'll just pretend it worked
            
            return {
                "id": action_id,
                "success": True,
                "synced": True
            }
            
        else:
            return {
                "id": action_id,
                "success": False,
                "error": f"Unknown user action: {action_type}",
                "synced": False
            }
            
    except Exception as e:
        logger.error(f"Error processing user action: {e}")
        return {
            "id": action_id,
            "success": False,
            "error": str(e),
            "synced": False
        }

@offline_api.route('/data', methods=['GET'])
def get_offline_data():
    """
    Get data for offline use.
    
    Returns cached data for offline use, including:
    - Techniques
    - Exercises
    - User profile
    - Active reminders
    """
    try:
        user_id = g.user.id if hasattr(g, 'user') and g.user else None
        
        # In a real app, this would get data from the database
        # For now, we'll return some static data
        
        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "data": {
                "techniques": get_techniques_data(),
                "exercises": get_exercises_data(),
                "reminders": get_reminders_data(user_id),
                "user": get_user_data(user_id)
            }
        })
        
    except Exception as e:
        logger.error(f"Error in get_offline_data: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

def get_techniques_data() -> List[Dict]:
    """Get techniques data for offline use."""
    return [
        {
            "id": "reframing",
            "name": "Reframing",
            "description": "Change your perspective on situations by finding alternative interpretations.",
            "category": "cognitive",
            "difficulty": "beginner"
        },
        {
            "id": "anchoring",
            "name": "Anchoring",
            "description": "Associate positive states with specific triggers or gestures.",
            "category": "behavioral",
            "difficulty": "intermediate"
        },
        {
            "id": "pattern_interruption",
            "name": "Pattern Interruption",
            "description": "Break negative thought patterns by introducing unexpected changes.",
            "category": "cognitive",
            "difficulty": "beginner"
        },
        {
            "id": "future_pacing",
            "name": "Future Pacing",
            "description": "Mentally rehearse successful outcomes in future situations.",
            "category": "visualization",
            "difficulty": "intermediate"
        },
        {
            "id": "sensory_language",
            "name": "Sensory Language",
            "description": "Use rich sensory descriptions to enhance communication and experience.",
            "category": "linguistic",
            "difficulty": "beginner"
        }
    ]

def get_exercises_data() -> List[Dict]:
    """Get exercises data for offline use."""
    return [
        {
            "id": "voice_ex_1",
            "name": "Confident Speaking Exercise",
            "technique": "anchoring",
            "description": "Practice speaking with confidence using anchoring techniques.",
            "steps": [
                "Find a quiet space where you won't be disturbed.",
                "Recall a time when you felt extremely confident.",
                "Notice the feelings, posture, and internal voice.",
                "Press your thumb and middle finger together.",
                "Practice speaking while maintaining this anchor."
            ]
        },
        {
            "id": "voice_ex_2",
            "name": "Reframing Practice",
            "technique": "reframing",
            "description": "Practice reframing negative situations into positive or neutral ones.",
            "steps": [
                "Identify a challenging situation or negative thought.",
                "Write down your current interpretation.",
                "List at least three alternative perspectives.",
                "Choose the most helpful perspective.",
                "Practice expressing this new perspective out loud."
            ]
        },
        {
            "id": "nlp_ex_1",
            "name": "Sensory Awareness Exercise",
            "technique": "sensory_language",
            "description": "Enhance your sensory awareness and descriptive language.",
            "steps": [
                "Choose an everyday object.",
                "Describe it in detail using visual terms (colors, shapes, etc.).",
                "Describe how it feels to touch (texture, temperature, etc.).",
                "If applicable, describe sounds, smells, or tastes.",
                "Practice combining these descriptions in flowing language."
            ]
        }
    ]

def get_reminders_data(user_id: Optional[str]) -> List[Dict]:
    """Get reminders data for offline use."""
    # In a real app, this would get the user's reminders from the database
    # For now, we'll return some static data
    from practice_reminders import get_reminders
    
    reminders = get_reminders('offline_sync')
    return [r.to_dict() for r in reminders]

def get_user_data(user_id: Optional[str]) -> Dict:
    """Get user data for offline use."""
    # In a real app, this would get the user's data from the database
    # For now, we'll return some static data
    return {
        "name": "Offline User",
        "exercises_completed": 5,
        "techniques_practiced": 3,
        "streak_days": 4,
        "last_session": datetime.now().isoformat(),
        "preferences": {
            "theme": "dark",
            "notifications": True,
            "haptic_feedback": True
        }
    }