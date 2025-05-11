"""
Belief Change Protocol module for The Inner Architect

This module provides a structured process for identifying and transforming
limiting beliefs using NLP techniques.
"""

import logging
import re
import uuid
import json
from datetime import datetime
import os

# External OpenAI API for cognitive analysis
from openai import OpenAI

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Belief categories
BELIEF_CATEGORIES = {
    'self': 'Self-Image & Identity',
    'capability': 'Abilities & Skills',
    'possibility': 'Possibilities & Opportunities',
    'worth': 'Worthiness & Deservingness',
    'relationships': 'Relationships & Connection',
    'world': 'World & Environment'
}

# Belief change steps
PROTOCOL_STEPS = [
    {
        'id': 'identify',
        'name': 'Identify Limiting Belief',
        'description': 'Recognize and articulate a belief that is holding you back.',
        'prompt': 'What belief do you currently hold that might be limiting your potential?',
        'examples': [
            'I am not good enough to apply for that position.',
            'I always mess up important presentations.',
            'I do not deserve success or recognition.'
        ]
    },
    {
        'id': 'evidence',
        'name': 'Examine Supporting Evidence',
        'description': 'Explore what experiences or messages have reinforced this belief.',
        'prompt': 'What evidence or experiences seem to support this belief?',
        'examples': [
            'I was not selected for the last project I applied for.',
            'I stumbled over my words during my last presentation.',
            'My ideas have been overlooked in meetings before.'
        ]
    },
    {
        'id': 'challenge',
        'name': 'Challenge the Belief',
        'description': 'Question the validity and usefulness of the belief.',
        'prompt': 'How might this belief be inaccurate, incomplete, or unhelpful?',
        'examples': [
            'I have succeeded in many similar situations in the past.',
            'Everyone makes mistakes, and one poor presentation does not define my abilities.',
            'I am judging myself more harshly than I would judge others.'
        ]
    },
    {
        'id': 'alternative',
        'name': 'Create Empowering Alternative',
        'description': 'Develop a new belief that better serves your goals.',
        'prompt': 'What more empowering belief could replace the limiting one?',
        'examples': [
            'I have valuable skills and perspective to offer.',
            'I learn and improve with each presentation I give.',
            'I deserve success as much as anyone else.'
        ]
    },
    {
        'id': 'evidence_new',
        'name': 'Find Supporting Evidence',
        'description': 'Identify experiences that support your new empowering belief.',
        'prompt': 'What evidence exists that supports this new belief?',
        'examples': [
            'I have received positive feedback on my work in the past.',
            'I have successfully given many good presentations before.',
            'Others with similar backgrounds have succeeded in this field.'
        ]
    },
    {
        'id': 'embodiment',
        'name': 'Embody New Belief',
        'description': 'Experience how this new belief feels in your body and mind.',
        'prompt': 'How would you think, feel, and act differently if you fully believed this new perspective?',
        'examples': [
            'I would approach challenges with confidence rather than hesitation.',
            'I would prepare thoroughly but not obsess over perfection.',
            'I would recognize and celebrate my contributions and achievements.'
        ]
    },
    {
        'id': 'action',
        'name': 'Take Aligned Action',
        'description': 'Plan specific actions that align with your new belief.',
        'prompt': 'What specific actions would reinforce this new belief?',
        'examples': [
            'Volunteer for a project that stretches my abilities.',
            'Practice presentations regularly with constructive feedback.',
            'Keep a record of positive outcomes and acknowledgments.'
        ]
    }
]

# NLP techniques used in belief change
BELIEF_CHANGE_TECHNIQUES = {
    'reframing': {
        'name': 'Cognitive Reframing',
        'description': 'Changing the perspective or context to give a situation a different meaning.',
        'application': 'Used in the "Challenge the Belief" and "Create Empowering Alternative" steps.'
    },
    'pattern_interruption': {
        'name': 'Pattern Interruption',
        'description': 'Breaking habitual thought patterns to create space for new perspectives.',
        'application': 'Used throughout the process to disrupt automatic limiting thoughts.'
    },
    'future_pacing': {
        'name': 'Future Pacing',
        'description': 'Mentally rehearsing future scenarios with the new belief in place.',
        'application': 'Used in the "Embody New Belief" step to reinforce the new mental model.'
    },
    'anchoring': {
        'name': 'Anchoring',
        'description': 'Associating the new belief with a physical trigger to reinforce it.',
        'application': 'Used in the "Embody New Belief" step to create a physical reminder.'
    },
    'meta_model': {
        'name': 'Meta Model Questioning',
        'description': 'Using precise questioning to challenge generalizations, deletions, and distortions.',
        'application': 'Used in the "Examine Supporting Evidence" and "Challenge the Belief" steps.'
    }
}


class BeliefChangeSession:
    """Class representing a belief change protocol session."""
    
    def __init__(self, session_id=None, user_id=None, initial_belief=None,
                 category=None, current_step=None, completed=False):
        self.belief_session_id = session_id or str(uuid.uuid4())
        self.user_id = user_id
        self.initial_belief = initial_belief
        self.category = category
        self.current_step = current_step or 'identify'
        self.completed = completed
        self.responses = {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.completed_at = None
        
    def to_dict(self):
        """Convert session to dictionary for JSON serialization."""
        return {
            'belief_session_id': self.belief_session_id,
            'user_id': self.user_id,
            'initial_belief': self.initial_belief,
            'category': self.category,
            'category_name': BELIEF_CATEGORIES.get(self.category, 'Uncategorized'),
            'current_step': self.current_step,
            'current_step_index': self.get_current_step_index(),
            'current_step_data': self.get_current_step_data(),
            'total_steps': len(PROTOCOL_STEPS),
            'progress_percentage': self.get_progress_percentage(),
            'completed': self.completed,
            'responses': self.responses,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
        
    def get_current_step_index(self):
        """Get the index of the current step."""
        for i, step in enumerate(PROTOCOL_STEPS):
            if step['id'] == self.current_step:
                return i
        return 0
        
    def get_current_step_data(self):
        """Get data for the current step."""
        for step in PROTOCOL_STEPS:
            if step['id'] == self.current_step:
                return step
        return PROTOCOL_STEPS[0]
        
    def get_progress_percentage(self):
        """Calculate percentage of completion."""
        if self.completed:
            return 100
            
        total_steps = len(PROTOCOL_STEPS)
        current_index = self.get_current_step_index()
        
        return round((current_index / total_steps) * 100)
        
    def advance_step(self, response=None):
        """
        Advance to the next step in the protocol.
        
        Args:
            response (str, optional): User's response to the current step
            
        Returns:
            bool: True if advanced successfully, False if already at last step
        """
        if response:
            self.responses[self.current_step] = response
            
        current_index = self.get_current_step_index()
        
        if current_index >= len(PROTOCOL_STEPS) - 1:
            self.completed = True
            self.completed_at = datetime.now()
            return False
            
        self.current_step = PROTOCOL_STEPS[current_index + 1]['id']
        self.updated_at = datetime.now()
        
        return True
        
    def go_back(self):
        """
        Go back to the previous step in the protocol.
        
        Returns:
            bool: True if moved back successfully, False if already at first step
        """
        current_index = self.get_current_step_index()
        
        if current_index <= 0:
            return False
            
        self.current_step = PROTOCOL_STEPS[current_index - 1]['id']
        self.updated_at = datetime.now()
        
        # If was completed, mark as incomplete now
        if self.completed:
            self.completed = False
            self.completed_at = None
            
        return True
        
    def get_step_response(self, step_id):
        """
        Get the user's response for a specific step.
        
        Args:
            step_id (str): The step identifier
            
        Returns:
            str: The user's response or None if not found
        """
        return self.responses.get(step_id)


def create_belief_session(user_id=None, initial_belief=None, category=None):
    """
    Create a new belief change session.
    
    Args:
        user_id (int, optional): The user ID if logged in
        initial_belief (str, optional): The initial limiting belief
        category (str, optional): Belief category
        
    Returns:
        BeliefChangeSession: The created session
    """
    session = BeliefChangeSession(
        user_id=user_id,
        initial_belief=initial_belief,
        category=category
    )
    
    if initial_belief:
        session.responses['identify'] = initial_belief
        session.advance_step()
    
    return session


def get_belief_session(session_id):
    """
    Get a specific belief change session.
    
    Args:
        session_id (str): The session ID
        
    Returns:
        BeliefChangeSession: The session or None if not found
    """
    # In a real application, this would fetch from a database
    # For now, we'll just return None as if it wasn't found
    return None


def save_belief_session(session):
    """
    Save a belief change session.
    
    Args:
        session (BeliefChangeSession): The session to save
        
    Returns:
        bool: Success or failure
    """
    # In a real application, this would save to a database
    # For now, we'll just pretend it worked
    return True


def update_step_response(session_id, step_id, response):
    """
    Update the response for a specific step.
    
    Args:
        session_id (str): The session ID
        step_id (str): The step identifier
        response (str): The user's response
        
    Returns:
        BeliefChangeSession: The updated session or None if not found
    """
    # In a real application, this would fetch from and update a database
    # For now, we'll just return None as if it wasn't found
    return None


def get_belief_sessions(user_id=None, browser_session_id=None, limit=None, include_completed=True):
    """
    Get belief change sessions for a user or browser session.
    
    Args:
        user_id (int, optional): The user ID
        browser_session_id (str, optional): The browser session ID
        limit (int, optional): Maximum number of sessions to return
        include_completed (bool): Whether to include completed sessions
        
    Returns:
        list: List of session objects
    """
    # In a real application, this would fetch from a database
    # For now, we'll just return an empty list
    return []


def categorize_belief(belief_text):
    """
    Categorize a belief statement.
    
    Args:
        belief_text (str): The belief statement
        
    Returns:
        str: The category identifier
    """
    if not openai_client:
        # Simple rule-based fallback
        if re.search(r'\b(i am|my identity|who i am)\b', belief_text.lower()):
            return 'self'
        elif re.search(r'\b(cannot|can not|able|inability|skill|talent)\b', belief_text.lower()):
            return 'capability'
        elif re.search(r'\b(possible|impossible|opportunity|chance|luck)\b', belief_text.lower()):
            return 'possibility'
        elif re.search(r'\b(deserve|worthy|value|worth)\b', belief_text.lower()):
            return 'worth'
        elif re.search(r'\b(relationship|people|friend|partner|family)\b', belief_text.lower()):
            return 'relationships'
        else:
            return 'world'
    
    try:
        # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # Do not change this unless explicitly requested by the user
        prompt = f"""Categorize the following belief statement into one of these categories:
- self: Self-Image & Identity (beliefs about who you are)
- capability: Abilities & Skills (beliefs about what you can or cannot do)
- possibility: Possibilities & Opportunities (beliefs about what is possible or impossible)
- worth: Worthiness & Deservingness (beliefs about your value or what you deserve)
- relationships: Relationships & Connection (beliefs about relationships with others)
- world: World & Environment (beliefs about how the world works)

Belief statement: "{belief_text}"

Respond with only the category identifier (e.g., "self" or "capability").
"""
        
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a belief categorization specialist."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50
        )
        
        category = response.choices[0].message.content.strip().lower()
        
        # Make sure it's one of our categories
        if category in BELIEF_CATEGORIES:
            return category
        else:
            # Try to extract from response in case it gave more than just the category
            for cat in BELIEF_CATEGORIES.keys():
                if cat in category:
                    return cat
            
            # Default if we couldn't extract anything valid
            return 'self'
            
    except Exception as e:
        logging.error(f"Error categorizing belief: {e}")
        return 'self'  # Default to self if there's an error


def analyze_belief(belief_text):
    """
    Analyze a belief statement to identify patterns and suggest approaches.
    
    Args:
        belief_text (str): The belief statement
        
    Returns:
        dict: Analysis results
    """
    if not openai_client:
        # Simple analysis fallback
        return {
            'category': categorize_belief(belief_text),
            'patterns': [
                'All-or-nothing thinking',
                'Overgeneralization'
            ],
            'suggested_techniques': [
                'reframing',
                'meta_model'
            ],
            'potential_origin': 'This belief may have developed from past experiences or messages received from others.',
            'impact_areas': [
                'May affect confidence in professional settings',
                'Could limit willingness to take on challenges'
            ]
        }
    
    try:
        # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # Do not change this unless explicitly requested by the user
        prompt = f"""Analyze the following limiting belief statement through an NLP (Neuro-Linguistic Programming) lens:

Belief statement: "{belief_text}"

Provide:
1. The category it falls into (self, capability, possibility, worth, relationships, or world)
2. Thinking patterns exhibited (e.g., all-or-nothing thinking, overgeneralization, mental filtering, etc.)
3. NLP techniques that would be most effective for transforming this belief (from: reframing, pattern_interruption, future_pacing, anchoring, meta_model)
4. Potential origin of this belief
5. Areas of life this belief might be impacting

Respond with JSON in this format:
{{
  "category": "self",
  "patterns": ["All-or-nothing thinking", "Overgeneralization"],
  "suggested_techniques": ["reframing", "meta_model"],
  "potential_origin": "This belief may have developed from...",
  "impact_areas": ["May affect confidence in...", "Could limit..."]
}}
"""
        
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an NLP expert specializing in belief analysis."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=800
        )
        
        analysis = json.loads(response.choices[0].message.content)
        
        # Ensure category is valid
        if 'category' in analysis and analysis['category'] not in BELIEF_CATEGORIES:
            analysis['category'] = categorize_belief(belief_text)
            
        return analysis
        
    except Exception as e:
        logging.error(f"Error analyzing belief: {e}")
        return {
            'category': categorize_belief(belief_text),
            'patterns': [
                'All-or-nothing thinking',
                'Overgeneralization'
            ],
            'suggested_techniques': [
                'reframing',
                'meta_model'
            ],
            'potential_origin': 'This belief may have developed from past experiences or messages received from others.',
            'impact_areas': [
                'May affect confidence in professional settings',
                'Could limit willingness to take on challenges'
            ]
        }


def generate_reframe_suggestions(belief_text):
    """
    Generate suggestions for reframing a limiting belief.
    
    Args:
        belief_text (str): The limiting belief
        
    Returns:
        list: Suggestions for reframing
    """
    if not openai_client:
        # Simple fallback suggestions
        return [
            f"Instead of '{belief_text}', consider 'I am learning and growing in this area.'",
            f"What if you viewed this as an opportunity to develop rather than a fixed limitation?",
            f"How might someone who believed the opposite of '{belief_text}' approach this situation?"
        ]
    
    try:
        # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # Do not change this unless explicitly requested by the user
        prompt = f"""Generate 3-5 powerful reframes for the following limiting belief:

Limiting belief: "{belief_text}"

For each reframe:
1. Offer a specific alternative perspective that challenges the original belief
2. Ensure the reframe is empowering but still believable
3. Use language that opens possibilities rather than creating a new limitation

Format each suggestion as a complete thought that can stand alone. Make the reframes diverse in their approach.
"""
        
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an NLP coach specializing in cognitive reframing."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        
        suggestions_text = response.choices[0].message.content
        
        # Extract numbered or bulleted items
        suggestions = re.findall(r'(?:^|\n)[•\-\d]+\.?\s*(.*?)(?:\n|$)', suggestions_text)
        
        # If regex didn't find anything, just split by newlines and clean up
        if not suggestions:
            suggestions = [s.strip() for s in suggestions_text.split('\n') if s.strip()]
            
        # Ensure we have at least some suggestions
        if not suggestions:
            # Split by double newlines and take the resulting paragraphs
            suggestions = [s.strip() for s in suggestions_text.split('\n\n') if s.strip()]
            
        # Limit to 5 suggestions and ensure they're not too long
        suggestions = [s[:200] for s in suggestions[:5]]
        
        return suggestions
        
    except Exception as e:
        logging.error(f"Error generating reframe suggestions: {e}")
        return [
            f"Instead of '{belief_text}', consider 'I am learning and growing in this area.'",
            f"What if you viewed this as an opportunity to develop rather than a fixed limitation?",
            f"How might someone who believed the opposite of '{belief_text}' approach this situation?"
        ]


def generate_meta_model_questions(belief_text):
    """
    Generate Meta Model questions to challenge a limiting belief.
    
    Args:
        belief_text (str): The limiting belief
        
    Returns:
        list: Meta Model questions
    """
    if not openai_client:
        # Simple fallback questions
        return [
            f"What specifically makes you believe that {belief_text}?",
            f"How do you know this belief is true?",
            f"According to whom is this true?",
            f"What would happen if this wasn't true?",
            f"Is this always true, or are there exceptions?"
        ]
    
    try:
        # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # Do not change this unless explicitly requested by the user
        prompt = f"""Generate 5-7 Meta Model questions to challenge the following limiting belief:

Limiting belief: "{belief_text}"

Meta Model questions should address:
1. Deletions (missing information): What's been left out?
2. Distortions (misrepresentations): How has meaning been twisted?
3. Generalizations (universal claims): Where are the absolutes?

Focus on questions that:
- Challenge universal quantifiers (always, never, everyone, no one)
- Recover deleted information (specifically what/who/how)
- Challenge cause-effect assumptions
- Challenge mind reading (knowing others' thoughts)
- Challenge value judgments (good/bad, should/must)

Format as a list of questions, each challenging a different aspect of the belief.
"""
        
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an NLP practitioner specializing in the Meta Model."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        
        questions_text = response.choices[0].message.content
        
        # Extract numbered or bulleted items
        questions = re.findall(r'(?:^|\n)[•\-\d]+\.?\s*(.*?)(?:\n|$)', questions_text)
        
        # If regex didn't find anything, just split by newlines and clean up
        if not questions:
            questions = [q.strip() for q in questions_text.split('\n') if q.strip() and '?' in q]
            
        # If still no questions, look for question marks and take those sentences
        if not questions:
            questions = [s.strip() for s in re.findall(r'[^.!?]*\?', questions_text)]
            
        # Limit to 7 questions
        questions = [q[:150] for q in questions[:7]]
        
        return questions
        
    except Exception as e:
        logging.error(f"Error generating Meta Model questions: {e}")
        return [
            f"What specifically makes you believe that {belief_text}?",
            f"How do you know this belief is true?",
            f"According to whom is this true?",
            f"What would happen if this wasn't true?",
            f"Is this always true, or are there exceptions?"
        ]


def suggest_action_steps(new_belief):
    """
    Suggest concrete actions to reinforce a new empowering belief.
    
    Args:
        new_belief (str): The new empowering belief
        
    Returns:
        list: Suggested actions
    """
    if not openai_client:
        # Simple fallback suggestions
        return [
            "Practice daily affirmations reinforcing this new belief",
            "Create a vision board with images representing this belief in action",
            "Share your new perspective with a supportive friend",
            "Set a small, achievable goal aligned with this new belief",
            "Journal daily about evidence supporting this new belief"
        ]
    
    try:
        # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # Do not change this unless explicitly requested by the user
        prompt = f"""Suggest 5-7 specific, actionable steps to reinforce the following new empowering belief:

New belief: "{new_belief}"

For each suggestion:
1. Make it concrete and specific (not generic)
2. Ensure it's actionable within 1-2 weeks
3. Include a mix of internal practices and external actions
4. Make it measurable where possible

Focus on actions that:
- Create evidence supporting the new belief
- Build momentum through small wins
- Engage multiple senses and modalities
- Can be incorporated into existing routines
- Challenge the person slightly outside their comfort zone

Format as a list of clear action steps.
"""
        
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an NLP coach specializing in belief integration and behavior change."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600
        )
        
        actions_text = response.choices[0].message.content
        
        # Extract numbered or bulleted items
        actions = re.findall(r'(?:^|\n)[•\-\d]+\.?\s*(.*?)(?:\n|$)', actions_text)
        
        # If regex didn't find anything, just split by newlines and clean up
        if not actions:
            actions = [a.strip() for a in actions_text.split('\n') if a.strip()]
            
        # Ensure we have at least some actions
        if not actions:
            # Split by double newlines and take the resulting paragraphs
            actions = [a.strip() for a in actions_text.split('\n\n') if a.strip()]
            
        # Limit to 7 actions and ensure they're not too long
        actions = [a[:200] for a in actions[:7]]
        
        return actions
        
    except Exception as e:
        logging.error(f"Error generating action steps: {e}")
        return [
            "Practice daily affirmations reinforcing this new belief",
            "Create a vision board with images representing this belief in action",
            "Share your new perspective with a supportive friend",
            "Set a small, achievable goal aligned with this new belief",
            "Journal daily about evidence supporting this new belief"
        ]


def get_belief_categories():
    """
    Get all belief categories.
    
    Returns:
        dict: All categories and their descriptions
    """
    return BELIEF_CATEGORIES


def get_protocol_steps():
    """
    Get all steps in the belief change protocol.
    
    Returns:
        list: All protocol steps
    """
    return PROTOCOL_STEPS


def get_techniques_for_belief_change():
    """
    Get NLP techniques used in belief change.
    
    Returns:
        dict: Techniques and their descriptions
    """
    return BELIEF_CHANGE_TECHNIQUES