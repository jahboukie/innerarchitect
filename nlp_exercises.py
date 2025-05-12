"""
NLP Exercises module for The Inner Architect

This module provides structured exercises for different NLP techniques
and functions to create, retrieve, and track progress on exercises.
"""
import json
import logging
from datetime import datetime

from models import NLPExercise, NLPExerciseProgress
from database import db

from logging_config import get_logger, info, error, debug, warning, critical, exception



# Default exercises for each NLP technique
# Get module-specific logger
logger = get_logger('nlp_exercises')

DEFAULT_EXERCISES = [
    # Reframing exercises
    {
        "technique": "reframing",
        "title": "Positive Reframing Challenge",
        "description": "This exercise helps you practice seeing challenging situations from new perspectives, focusing on finding the positive aspects or learning opportunities in difficult experiences.",
        "difficulty": "beginner",
        "estimated_time": 5,
        "steps": json.dumps([
            {
                "type": "instruction",
                "content": "Think of a recent challenging situation or problem that bothered you. Write it down briefly below."
            },
            {
                "type": "text_input",
                "prompt": "Describe the challenging situation:",
                "placeholder": "E.g., I failed to meet a deadline at work..."
            },
            {
                "type": "instruction",
                "content": "Now, identify the negative thoughts or interpretations you had about this situation."
            },
            {
                "type": "text_input",
                "prompt": "What negative thoughts did you have?",
                "placeholder": "E.g., I'm terrible at managing my time..."
            },
            {
                "type": "instruction",
                "content": "Let's reframe this situation. For each negative thought, try to find an alternative, more empowering perspective."
            },
            {
                "type": "text_input",
                "prompt": "Reframe #1:",
                "placeholder": "E.g., This is an opportunity for me to improve my planning skills..."
            },
            {
                "type": "text_input",
                "prompt": "Reframe #2:",
                "placeholder": "E.g., Everyone misses deadlines occasionally; it doesn't define my abilities..."
            },
            {
                "type": "text_input",
                "prompt": "Reframe #3:",
                "placeholder": "E.g., I can use this experience to create a better system for the future..."
            },
            {
                "type": "reflection",
                "prompt": "How does seeing the situation from these new perspectives change how you feel about it? What did you learn from this exercise?",
                "placeholder": "Reflect on how your feelings have changed..."
            }
        ])
    },
    
    # Pattern Interruption exercise
    {
        "technique": "pattern_interruption",
        "title": "Breaking Negative Thought Cycles",
        "description": "This exercise helps you identify recurring negative thought patterns and practice techniques to interrupt them before they escalate.",
        "difficulty": "beginner",
        "estimated_time": 7,
        "steps": json.dumps([
            {
                "type": "instruction",
                "content": "Pattern interruption is about breaking habitual negative thought cycles. In this exercise, you'll identify a recurring negative thought pattern and practice techniques to disrupt it."
            },
            {
                "type": "text_input",
                "prompt": "Describe a negative thought pattern you notice yourself repeating:",
                "placeholder": "E.g., Whenever I make a small mistake, I spiral into thinking I'm incompetent..."
            },
            {
                "type": "instruction",
                "content": "Identify the typical triggers that start this thought pattern."
            },
            {
                "type": "text_input",
                "prompt": "What situations typically trigger this pattern?",
                "placeholder": "E.g., Making errors in my work, receiving criticism..."
            },
            {
                "type": "instruction",
                "content": "Now, choose a physical or mental 'pattern interrupt' from the options below or create your own."
            },
            {
                "type": "multiple_choice",
                "prompt": "Select a pattern interrupt technique to try:",
                "options": [
                    "Snap a rubber band on your wrist (physical)",
                    "Clap your hands once loudly (physical)",
                    "Mentally shout 'STOP!' (mental)",
                    "Visualize a red stop sign (mental)",
                    "Create your own technique"
                ]
            },
            {
                "type": "text_input",
                "prompt": "If you selected 'Create your own technique', describe it here:",
                "placeholder": "E.g., I'll splash cold water on my face..."
            },
            {
                "type": "instruction",
                "content": "Practice your chosen technique now. The next time you notice the negative thought pattern beginning, immediately use your pattern interrupt, then redirect to a more constructive thought."
            },
            {
                "type": "text_input",
                "prompt": "What positive or constructive thought will you redirect to after the interrupt?",
                "placeholder": "E.g., 'Mistakes are how I learn and grow...'"
            },
            {
                "type": "reflection",
                "prompt": "How do you think this technique will help break your negative thought cycle? When will you practice it in real life?",
                "placeholder": "Reflect on how and when you'll use this technique..."
            }
        ])
    },
    
    # Anchoring exercise
    {
        "technique": "anchoring",
        "title": "Creating Positive Emotional Anchors",
        "description": "Learn to create and use emotional anchors that can help you access positive emotional states when needed.",
        "difficulty": "intermediate",
        "estimated_time": 10,
        "steps": json.dumps([
            {
                "type": "instruction",
                "content": "Anchoring in NLP is about associating a specific trigger (like a physical touch) with a positive emotional state. This exercise will help you create your own positive anchor."
            },
            {
                "type": "instruction",
                "content": "First, choose a physical anchor - something you can do easily anywhere. Common examples include pressing your thumb and forefinger together, touching a specific knuckle, or pressing a spot on your wrist."
            },
            {
                "type": "text_input",
                "prompt": "Describe your chosen physical anchor:",
                "placeholder": "E.g., Pressing my thumb and middle finger together firmly..."
            },
            {
                "type": "instruction",
                "content": "Now, think of a time when you felt extremely confident, capable, or calm - whatever positive state you'd like to be able to access more often."
            },
            {
                "type": "text_input",
                "prompt": "Describe this positive memory in detail:",
                "placeholder": "E.g., The time I gave a presentation and everyone was engaged..."
            },
            {
                "type": "instruction",
                "content": "Close your eyes and vividly recall this memory. Remember the sights, sounds, and especially how it felt in your body. As the positive feeling reaches its peak, apply your physical anchor for about 5-10 seconds, then release. Repeat this 3 times."
            },
            {
                "type": "checkbox",
                "prompt": "I've practiced my anchor with the positive memory 3 times"
            },
            {
                "type": "instruction",
                "content": "To test your anchor, clear your mind for a moment, then apply your physical anchor. Notice if you feel a hint of the positive emotion returning."
            },
            {
                "type": "text_input",
                "prompt": "Describe what you felt when testing your anchor:",
                "placeholder": "E.g., I noticed a slight increase in confidence..."
            },
            {
                "type": "instruction",
                "content": "To strengthen your anchor, practice this exercise daily for a week. You can use the same memory or different positive memories."
            },
            {
                "type": "reflection",
                "prompt": "When would accessing this positive state be most helpful in your daily life? How will you remember to use your anchor?",
                "placeholder": "Reflect on when and how you'll use this technique..."
            }
        ])
    },
    
    # Future Pacing exercise
    {
        "technique": "future_pacing",
        "title": "Visualizing Success with Future Pacing",
        "description": "Use the power of detailed mental rehearsal to prepare for future situations and increase your chances of success.",
        "difficulty": "beginner",
        "estimated_time": 8,
        "steps": json.dumps([
            {
                "type": "instruction",
                "content": "Future pacing is a powerful NLP technique where you mentally rehearse a future event in detail, experiencing success before it happens. This creates neural pathways that make success more likely when the actual event occurs."
            },
            {
                "type": "text_input",
                "prompt": "Identify an upcoming challenging situation or important event:",
                "placeholder": "E.g., Job interview next week, difficult conversation with a colleague..."
            },
            {
                "type": "instruction",
                "content": "Now, close your eyes and imagine yourself in this future situation. We'll build the visualization step by step."
            },
            {
                "type": "text_input",
                "prompt": "What will you see in this situation? Describe the environment and visual details:",
                "placeholder": "E.g., The interviewer's office, their desk, the view from the window..."
            },
            {
                "type": "text_input",
                "prompt": "What sounds will be present? Describe what you'll hear:",
                "placeholder": "E.g., The interviewer's questions, background office noises..."
            },
            {
                "type": "text_input",
                "prompt": "How will you want to feel in this situation? Describe your ideal emotional state:",
                "placeholder": "E.g., Calm, confident, articulate, engaged..."
            },
            {
                "type": "text_input",
                "prompt": "What specific actions will you take to succeed? Describe your behaviors:",
                "placeholder": "E.g., Making eye contact, speaking clearly, asking thoughtful questions..."
            },
            {
                "type": "instruction",
                "content": "Now, take a few minutes to run through a complete mental rehearsal of the situation. See yourself handling it perfectly, feeling confident, and achieving your desired outcome. Experience it as vividly as possible."
            },
            {
                "type": "checkbox",
                "prompt": "I've completed a detailed mental rehearsal of success in this situation"
            },
            {
                "type": "reflection",
                "prompt": "How did the future pacing exercise make you feel about the upcoming situation? What details were most helpful to visualize?",
                "placeholder": "Reflect on your experience with this visualization..."
            }
        ])
    },
    
    # Sensory Language exercise
    {
        "technique": "sensory_language",
        "title": "Discovering Your Representational Systems",
        "description": "Learn to identify your preferred representational system (visual, auditory, kinesthetic) and practice using sensory-rich language.",
        "difficulty": "intermediate",
        "estimated_time": 12,
        "steps": json.dumps([
            {
                "type": "instruction",
                "content": "In NLP, we process information through different sensory systems: visual (seeing), auditory (hearing), and kinesthetic (feeling). Most people have a preference. This exercise helps you identify and expand your sensory language."
            },
            {
                "type": "multiple_choice",
                "prompt": "When recalling a vacation, what do you typically remember first?",
                "options": [
                    "The sights and scenes - how things looked (Visual)",
                    "The sounds - conversations, music, or environmental sounds (Auditory)",
                    "The feelings - both emotions and physical sensations (Kinesthetic)"
                ]
            },
            {
                "type": "multiple_choice",
                "prompt": "When learning something new, you prefer to:",
                "options": [
                    "See demonstrations or read instructions with diagrams (Visual)",
                    "Listen to verbal instructions or discuss the process (Auditory)",
                    "Try it hands-on through direct experience (Kinesthetic)"
                ]
            },
            {
                "type": "multiple_choice",
                "prompt": "When explaining directions, you're likely to:",
                "options": [
                    "Draw a map or use visual references (Visual)",
                    "Explain verbally with detailed instructions (Auditory)",
                    "Take them there or describe based on landmarks and feelings (Kinesthetic)"
                ]
            },
            {
                "type": "instruction",
                "content": "Based on your answers, you may have a preferred representational system. Now, practice expanding your sensory language by describing a recent positive experience using all three systems."
            },
            {
                "type": "text_input",
                "prompt": "Describe the experience using visual language (what you saw):",
                "placeholder": "E.g., The bright blue sky stretched endlessly, with vibrant green trees framing the scene..."
            },
            {
                "type": "text_input",
                "prompt": "Describe the same experience using auditory language (what you heard):",
                "placeholder": "E.g., The soft melody of birds chirping harmonized with the gentle rustling of leaves in the breeze..."
            },
            {
                "type": "text_input",
                "prompt": "Describe the same experience using kinesthetic language (what you felt):",
                "placeholder": "E.g., The warm sunshine caressed my skin as a sense of deep contentment spread through my body..."
            },
            {
                "type": "instruction",
                "content": "In your daily communications, practice using language that matches the other person's preferred system. Listen for their sensory predicates (see, look, hear, feel) and respond in kind."
            },
            {
                "type": "reflection",
                "prompt": "What did you learn about your preferred representational system? How might using multi-sensory language enhance your communication?",
                "placeholder": "Reflect on your sensory preferences and communication style..."
            }
        ])
    },
    
    # Meta Model exercise
    {
        "technique": "meta_model",
        "title": "Challenging Limiting Beliefs with Meta Model Questions",
        "description": "Learn to identify and challenge limiting beliefs using the NLP Meta Model questioning techniques.",
        "difficulty": "advanced",
        "estimated_time": 15,
        "steps": json.dumps([
            {
                "type": "instruction",
                "content": "The NLP Meta Model helps identify and challenge limiting language patterns that may restrict your thinking and possibilities. This exercise focuses on recognizing and questioning these patterns."
            },
            {
                "type": "instruction",
                "content": "First, identify a limiting belief you hold about yourself or a situation. These often contain absolutes like 'never,' 'always,' 'everyone,' or unspecified references."
            },
            {
                "type": "text_input",
                "prompt": "Write down a limiting belief you hold:",
                "placeholder": "E.g., I'll never be good at public speaking; Everyone thinks my ideas are bad..."
            },
            {
                "type": "instruction",
                "content": "Now, identify what type of limiting pattern this represents:"
            },
            {
                "type": "multiple_choice",
                "prompt": "Which pattern best describes your limiting belief?",
                "options": [
                    "Universal Quantifier (words like 'all,' 'every,' 'never,' 'always')",
                    "Mind Reading (claiming to know what others think)",
                    "Cause-Effect (assuming one thing automatically causes another)",
                    "Complex Equivalence (equating two unrelated things)",
                    "Deletion (important information is missing)",
                    "Unspecified Referent (not clear who/what is being referenced)"
                ]
            },
            {
                "type": "instruction",
                "content": "Each pattern type can be challenged with specific Meta Model questions. Based on your pattern, here are questions to ask yourself:"
            },
            {
                "type": "text_input",
                "prompt": "Universal Quantifier: Ask 'Never? Has there ever been a time when this wasn't true?' or 'Always? Every single time without exception?'",
                "placeholder": "Your answer..."
            },
            {
                "type": "text_input",
                "prompt": "Mind Reading: Ask 'How specifically do you know what they think?' or 'Has everyone told you this directly?'",
                "placeholder": "Your answer..."
            },
            {
                "type": "text_input",
                "prompt": "Cause-Effect: Ask 'How exactly does this cause that?' or 'Is there ever a time when this happens but that doesn't?'",
                "placeholder": "Your answer..."
            },
            {
                "type": "text_input",
                "prompt": "Based on your answers to these challenging questions, rewrite your original belief in a more accurate, empowering way:",
                "placeholder": "E.g., 'I'm still developing my public speaking skills, and I improve with each opportunity...'"
            },
            {
                "type": "reflection",
                "prompt": "How does the reframed belief change how you feel and what actions seem possible now? What other limiting beliefs could you challenge?",
                "placeholder": "Reflect on the impact of this reframing process..."
            }
        ])
    }
]

def initialize_default_exercises():
    """
    Populate the database with default NLP exercises if they don't exist.
    """
    try:
        # Check if we already have exercises
        existing_count = NLPExercise.query.count()
        if existing_count > 0:
            info(f"Database already contains {existing_count} exercises, skipping initialization")
            return
        
        # Add default exercises
        for exercise_data in DEFAULT_EXERCISES:
            exercise = NLPExercise(**exercise_data)
            db.session.add(exercise)
        
        db.session.commit()
        info(f"Successfully added {len(DEFAULT_EXERCISES)} default NLP exercises")
    except Exception as e:
        db.session.rollback()
        error(f"Error initializing default exercises: {str(e)}")

def get_exercises_by_technique(technique):
    """
    Get all exercises for a specific NLP technique.
    
    Args:
        technique (str): The technique name
        
    Returns:
        list: A list of exercise objects
    """
    try:
        exercises = NLPExercise.query.filter_by(technique=technique).all()
        return exercises
    except Exception as e:
        error(f"Error retrieving exercises for {technique}: {str(e)}")
        return []

def get_exercise_by_id(exercise_id):
    """
    Get a specific exercise by ID.
    
    Args:
        exercise_id (int): The exercise ID
        
    Returns:
        NLPExercise: The exercise object or None
    """
    try:
        return NLPExercise.query.get(exercise_id)
    except Exception as e:
        error(f"Error retrieving exercise {exercise_id}: {str(e)}")
        return None

def start_exercise(exercise_id, session_id, user_id=None):
    """
    Start a new exercise and track progress.
    
    Args:
        exercise_id (int): The exercise ID
        session_id (str): The current session ID
        user_id (int, optional): The user ID if logged in
        
    Returns:
        NLPExerciseProgress: The progress tracking object or None
    """
    try:
        # Check if the exercise exists
        exercise = NLPExercise.query.get(exercise_id)
        if not exercise:
            error(f"Exercise {exercise_id} not found")
            return None
        
        # Create a progress record
        progress = NLPExerciseProgress(
            exercise_id=exercise_id,
            session_id=session_id,
            user_id=user_id,
            current_step=0,
            completed=False,
            started_at=datetime.utcnow()
        )
        
        db.session.add(progress)
        db.session.commit()
        info(f"Started exercise {exercise_id} for session {session_id}")
        
        return progress
    except Exception as e:
        db.session.rollback()
        error(f"Error starting exercise {exercise_id}: {str(e)}")
        return None

def update_exercise_progress(progress_id, current_step, notes=None, completed=False):
    """
    Update the progress of an exercise.
    
    Args:
        progress_id (int): The progress record ID
        current_step (int): The current step number
        notes (str, optional): User notes on the exercise
        completed (bool): Whether the exercise is completed
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        progress = NLPExerciseProgress.query.get(progress_id)
        if not progress:
            error(f"Progress record {progress_id} not found")
            return False
        
        progress.current_step = current_step
        if notes:
            progress.notes = notes
        
        if completed and not progress.completed:
            progress.completed = True
            progress.completed_at = datetime.utcnow()
        
        db.session.commit()
        info(f"Updated progress {progress_id} to step {current_step}, completed: {completed}")
        return True
    except Exception as e:
        db.session.rollback()
        error(f"Error updating exercise progress {progress_id}: {str(e)}")
        return False

def get_exercise_progress(session_id, exercise_id=None):
    """
    Get progress records for a session.
    
    Args:
        session_id (str): The session ID
        exercise_id (int, optional): Specific exercise ID
        
    Returns:
        list: Progress records
    """
    try:
        query = NLPExerciseProgress.query.filter_by(session_id=session_id)
        if exercise_id:
            query = query.filter_by(exercise_id=exercise_id)
        
        return query.all()
    except Exception as e:
        error(f"Error retrieving exercise progress for session {session_id}: {str(e)}")
        return []