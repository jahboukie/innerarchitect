import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from app import db
from app.models.nlp import NLPExercise, NLPExerciseProgress
from app.nlp.claude_client import get_claude_client

logger = logging.getLogger(__name__)

# Predefined exercises for each NLP technique
DEFAULT_EXERCISES = {
    "reframing": [
        {
            "title": "Thought Record Exercise",
            "description": "Practice identifying negative thoughts and creating balanced alternatives.",
            "steps": [
                "Identify a recent situation that triggered negative emotions",
                "Write down your automatic thoughts about the situation",
                "Identify any cognitive distortions in your thinking",
                "Create alternative, more balanced thoughts",
                "Rate how you feel after reframing the situation"
            ],
            "difficulty": "beginner",
            "estimated_time": 10
        },
        {
            "title": "Perspective Shift Challenge",
            "description": "Examine a situation from multiple perspectives to expand your thinking.",
            "steps": [
                "Choose a challenging situation you're facing",
                "Describe how you currently see the situation",
                "Imagine how three different people would view it",
                "Identify potential benefits or opportunities",
                "Integrate these perspectives into a new view"
            ],
            "difficulty": "intermediate",
            "estimated_time": 15
        }
    ],
    "pattern_interruption": [
        {
            "title": "Pattern Breaker",
            "description": "Learn to interrupt negative thought patterns with pattern disruption techniques.",
            "steps": [
                "Identify a recurring negative thought pattern",
                "Create a specific mental or physical interrupt",
                "Practice applying the interrupt when the pattern emerges",
                "Replace the interrupted pattern with a new response",
                "Test your pattern breaker in different situations"
            ],
            "difficulty": "beginner",
            "estimated_time": 10
        },
        {
            "title": "Assumption Challenger",
            "description": "Identify and challenge hidden assumptions that limit your thinking.",
            "steps": [
                "List assumptions you're making about a situation",
                "Rate your confidence in each assumption (1-10)",
                "Find evidence that contradicts each assumption",
                "Create alternative explanations or possibilities",
                "Develop a new perspective based on challenged assumptions"
            ],
            "difficulty": "intermediate",
            "estimated_time": 15
        }
    ],
    "anchoring": [
        {
            "title": "Resource State Anchoring",
            "description": "Create a physical anchor for accessing positive emotional states.",
            "steps": [
                "Identify a resourceful emotional state you want to access",
                "Recall a time when you fully experienced this state",
                "Intensify the memory using all your senses",
                "Create a physical anchor (gesture, touch) at peak intensity",
                "Test the anchor by clearing your mind and applying it"
            ],
            "difficulty": "beginner",
            "estimated_time": 10
        },
        {
            "title": "Stacked Anchors",
            "description": "Combine multiple resource states into a single powerful anchor.",
            "steps": [
                "Identify 3-4 different positive states you want to access",
                "Create and test a separate anchor for each state",
                "Design a unique anchor for the combined states",
                "Access each state in sequence, applying the new anchor at each peak",
                "Test the stacked anchor after a short break"
            ],
            "difficulty": "advanced",
            "estimated_time": 20
        }
    ],
    "future_pacing": [
        {
            "title": "Success Visualization",
            "description": "Mentally rehearse future success to increase confidence and motivation.",
            "steps": [
                "Identify an upcoming challenging situation",
                "Clarify your desired outcome in specific terms",
                "Visualize successfully navigating the situation",
                "Enhance the visualization with sensory details",
                "Practice stepping into the future success daily"
            ],
            "difficulty": "beginner",
            "estimated_time": 10
        },
        {
            "title": "Obstacle Navigation",
            "description": "Anticipate and mentally overcome potential obstacles to success.",
            "steps": [
                "Identify a goal and your path to achieving it",
                "List potential obstacles or challenges",
                "Develop specific strategies for each obstacle",
                "Visualize successfully implementing each strategy",
                "Create a mental movie of achieving your goal despite obstacles"
            ],
            "difficulty": "intermediate",
            "estimated_time": 15
        }
    ],
    "sensory_language": [
        {
            "title": "Sensory Acuity",
            "description": "Enhance your ability to observe and describe experiences in sensory terms.",
            "steps": [
                "Choose an everyday object or experience",
                "Describe it using visual terms (colors, shapes, etc.)",
                "Describe it using auditory terms (sounds, tones, etc.)",
                "Describe it using kinesthetic terms (textures, feelings, etc.)",
                "Practice translating between different sensory systems"
            ],
            "difficulty": "beginner",
            "estimated_time": 10
        },
        {
            "title": "Representational System Preference",
            "description": "Identify and leverage your preferred sensory processing style.",
            "steps": [
                "Take the representational system assessment",
                "Identify your primary and secondary systems",
                "Notice how you naturally process information",
                "Practice using your non-preferred systems",
                "Create messages that incorporate all sensory systems"
            ],
            "difficulty": "intermediate",
            "estimated_time": 15
        }
    ],
    "meta_model": [
        {
            "title": "Linguistic Detective",
            "description": "Identify and question language patterns that reveal hidden assumptions.",
            "steps": [
                "Write down a limiting belief or statement",
                "Identify deletions (missing information)",
                "Spot generalizations (always, never, everyone)",
                "Find distortions (mind reading, cause-effect assumptions)",
                "Create powerful questions to challenge each pattern"
            ],
            "difficulty": "beginner",
            "estimated_time": 10
        },
        {
            "title": "Precision Language Practice",
            "description": "Develop more precise language to communicate clearly and effectively.",
            "steps": [
                "Record yourself talking about a challenging situation",
                "Identify vague or imprecise language",
                "Replace generalizations with specific examples",
                "Clarify unclear cause-effect relationships",
                "Restate your description with precision language"
            ],
            "difficulty": "intermediate",
            "estimated_time": 15
        }
    ]
}

def initialize_default_exercises() -> None:
    """Initialize the database with default NLP exercises if they don't exist."""
    try:
        # Check if exercises exist
        exercise_count = NLPExercise.query.count()
        if exercise_count > 0:
            logger.info(f"Exercises already exist in database ({exercise_count} found)")
            return
            
        logger.info("Initializing default NLP exercises")
        
        # Add default exercises for each technique
        for technique, exercises in DEFAULT_EXERCISES.items():
            for exercise_data in exercises:
                # Convert steps list to JSON string
                steps_json = json.dumps(exercise_data["steps"])
                
                exercise = NLPExercise(
                    technique=technique,
                    title=exercise_data["title"],
                    description=exercise_data["description"],
                    steps=steps_json,
                    difficulty=exercise_data["difficulty"],
                    estimated_time=exercise_data["estimated_time"]
                )
                db.session.add(exercise)
        
        db.session.commit()
        logger.info("Default NLP exercises initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing default exercises: {str(e)}")
        db.session.rollback()

def get_exercises_for_technique(technique_id: str) -> List[Dict[str, Any]]:
    """
    Get all exercises for a specific NLP technique.
    
    Args:
        technique_id: The technique identifier
        
    Returns:
        List of exercise dictionaries
    """
    try:
        exercises = NLPExercise.query.filter_by(technique=technique_id).all()
        
        result = []
        for exercise in exercises:
            # Parse steps from JSON
            try:
                steps = json.loads(exercise.steps)
            except json.JSONDecodeError:
                steps = []
                
            result.append({
                "id": exercise.id,
                "technique": exercise.technique,
                "title": exercise.title,
                "description": exercise.description,
                "steps": steps,
                "difficulty": exercise.difficulty,
                "estimated_time": exercise.estimated_time,
                "created_at": exercise.created_at.isoformat()
            })
            
        return result
        
    except Exception as e:
        logger.error(f"Error getting exercises for technique {technique_id}: {str(e)}")
        return []

def get_exercise_by_id(exercise_id: int) -> Optional[Dict[str, Any]]:
    """
    Get details for a specific exercise.
    
    Args:
        exercise_id: The exercise ID
        
    Returns:
        Exercise dictionary or None if not found
    """
    try:
        exercise = NLPExercise.query.get(exercise_id)
        if not exercise:
            return None
            
        # Parse steps from JSON
        try:
            steps = json.loads(exercise.steps)
        except json.JSONDecodeError:
            steps = []
            
        return {
            "id": exercise.id,
            "technique": exercise.technique,
            "title": exercise.title,
            "description": exercise.description,
            "steps": steps,
            "difficulty": exercise.difficulty,
            "estimated_time": exercise.estimated_time,
            "created_at": exercise.created_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting exercise {exercise_id}: {str(e)}")
        return None

def start_exercise(
    exercise_id: int, 
    user_id: Optional[str] = None, 
    session_id: Optional[str] = None
) -> Optional[int]:
    """
    Start an NLP exercise and create a progress record.
    
    Args:
        exercise_id: The exercise ID
        user_id: The user ID (None for anonymous users)
        session_id: The session ID (required for anonymous users)
        
    Returns:
        Progress record ID or None if failed
    """
    if not session_id:
        session_id = "anonymous"
        
    try:
        # Check if exercise exists
        exercise = NLPExercise.query.get(exercise_id)
        if not exercise:
            logger.warning(f"Exercise not found: {exercise_id}")
            return None
            
        # Check if there's an existing progress record
        progress = None
        if user_id:
            progress = NLPExerciseProgress.query.filter_by(
                user_id=user_id,
                exercise_id=exercise_id,
                session_id=session_id,
                completed=False
            ).first()
        else:
            progress = NLPExerciseProgress.query.filter_by(
                user_id=None,
                exercise_id=exercise_id,
                session_id=session_id,
                completed=False
            ).first()
            
        # If progress exists, return it
        if progress:
            logger.info(f"Found existing progress for exercise {exercise_id}: {progress.id}")
            return progress.id
            
        # Create new progress record
        progress = NLPExerciseProgress(
            user_id=user_id,
            exercise_id=exercise_id,
            session_id=session_id,
            current_step=0,
            completed=False,
            notes=None
        )
        
        db.session.add(progress)
        db.session.commit()
        
        logger.info(f"Started exercise {exercise_id} with progress ID: {progress.id}")
        return progress.id
        
    except Exception as e:
        logger.error(f"Error starting exercise {exercise_id}: {str(e)}")
        db.session.rollback()
        return None

def update_exercise_progress(
    progress_id: int, 
    current_step: Optional[int] = None,
    completed: Optional[bool] = None,
    notes: Optional[str] = None
) -> bool:
    """
    Update the progress of an NLP exercise.
    
    Args:
        progress_id: The progress record ID
        current_step: The current step number (optional)
        completed: Whether the exercise is completed (optional)
        notes: User notes about the exercise (optional)
        
    Returns:
        Success flag
    """
    try:
        # Get the progress record
        progress = NLPExerciseProgress.query.get(progress_id)
        if not progress:
            logger.warning(f"Progress record not found: {progress_id}")
            return False
            
        # Update fields if provided
        if current_step is not None:
            progress.current_step = current_step
            
        if completed is not None:
            progress.completed = completed
            if completed:
                progress.completed_at = datetime.utcnow()
                
        if notes is not None:
            progress.notes = notes
            
        db.session.commit()
        
        logger.info(f"Updated progress {progress_id}: step={progress.current_step}, completed={progress.completed}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating exercise progress {progress_id}: {str(e)}")
        db.session.rollback()
        return False

def get_exercise_guidance(
    exercise_id: int,
    step_number: int,
    user_input: Optional[str] = None
) -> str:
    """
    Get AI guidance for a specific exercise step.
    
    Args:
        exercise_id: The exercise ID
        step_number: The step number (0-based)
        user_input: The user's input for this step (optional)
        
    Returns:
        Guidance text from Claude
    """
    try:
        # Get exercise details
        exercise = NLPExercise.query.get(exercise_id)
        if not exercise:
            logger.warning(f"Exercise not found: {exercise_id}")
            return "Sorry, I couldn't find that exercise."
            
        # Parse steps from JSON
        try:
            steps = json.loads(exercise.steps)
        except json.JSONDecodeError:
            steps = []
            
        # Check if step number is valid
        if step_number < 0 or step_number >= len(steps):
            logger.warning(f"Invalid step number {step_number} for exercise {exercise_id}")
            return "Sorry, that step doesn't exist for this exercise."
            
        # Get current step description
        current_step = steps[step_number]
        
        # Create prompt for Claude
        system_prompt = f"""
        You are an expert NLP (Neuro-Linguistic Programming) coach guiding a user through an exercise.
        
        Exercise: {exercise.title}
        Description: {exercise.description}
        Current step ({step_number+1}/{len(steps)}): {current_step}
        
        Provide supportive, insightful guidance for this specific step of the exercise.
        Your response should be:
        1. Encouraging and empathetic
        2. Specifically tailored to this step (not general advice)
        3. Include practical examples or prompts if appropriate
        4. Brief but comprehensive (200-300 words maximum)
        
        If the user has provided input for this step, respond directly to what they've shared.
        """
        
        # Get the Claude client
        claude = get_claude_client()
        
        # Generate guidance
        message_content = user_input if user_input else f"I'm working on step {step_number+1}: {current_step}. Can you guide me?"
        
        guidance = claude.analyze_text(
            text=message_content,
            task_description=system_prompt
        )
        
        return guidance
        
    except Exception as e:
        logger.error(f"Error getting exercise guidance: {str(e)}")
        return "I'm having trouble generating guidance for this exercise step. Please try again later."

def get_user_exercise_progress(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get progress information for all exercises a user has started.
    
    Args:
        user_id: The user ID (None for anonymous users)
        session_id: The session ID (required for anonymous users)
        
    Returns:
        List of progress dictionaries
    """
    if not user_id and not session_id:
        return []
        
    try:
        # Query progress records
        if user_id:
            progress_records = NLPExerciseProgress.query.filter_by(user_id=user_id).all()
        else:
            progress_records = NLPExerciseProgress.query.filter_by(session_id=session_id).all()
            
        result = []
        for progress in progress_records:
            # Get exercise details
            exercise = NLPExercise.query.get(progress.exercise_id)
            if not exercise:
                continue
                
            # Parse steps from JSON
            try:
                steps = json.loads(exercise.steps)
                total_steps = len(steps)
            except json.JSONDecodeError:
                total_steps = 0
                
            result.append({
                "progress_id": progress.id,
                "exercise_id": progress.exercise_id,
                "exercise_title": exercise.title,
                "technique": exercise.technique,
                "current_step": progress.current_step,
                "total_steps": total_steps,
                "completed": progress.completed,
                "started_at": progress.started_at.isoformat(),
                "completed_at": progress.completed_at.isoformat() if progress.completed_at else None
            })
            
        return result
        
    except Exception as e:
        logger.error(f"Error getting user exercise progress: {str(e)}")
        return []