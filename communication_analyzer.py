"""
Communication Style Analyzer module for The Inner Architect

This module analyzes text to identify communication styles, patterns,
and provides suggestions for improvement.
"""

import re
import logging
from openai import OpenAI
import os
import json

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Communication style categories
STYLE_CATEGORIES = {
    'assertive': {
        'name': 'Assertive',
        'description': 'Direct, confident, and respectful communication that expresses needs and ideas clearly',
        'signs': [
            'Uses clear, direct statements',
            'Expresses thoughts and feelings honestly',
            'Shows confidence through tone and word choice',
            'Balances speaking and listening',
            'Uses "I" statements to take ownership'
        ],
        'strengths': [
            'Effective at addressing problems',
            'Builds authentic relationships',
            'Reduces misunderstandings',
            'Facilitates problem-solving',
            'Demonstrates self-respect and respect for others'
        ],
        'improvement_tips': [
            'Continue practicing self-awareness',
            'Keep balancing confidence with empathy',
            'Maintain open body language',
            'Use "I" statements when expressing concerns',
            'Remember to validate others\' perspectives'
        ]
    },
    'passive': {
        'name': 'Passive',
        'description': 'Indirect communication that avoids expressing true thoughts, feelings, or needs',
        'signs': [
            'Avoids expressing opinions or needs directly',
            'Uses apologetic or qualifying language',
            'Speaks softly or hesitantly',
            'Tends to agree with others to avoid conflict',
            'Uses vague or indirect statements'
        ],
        'strengths': [
            'Often appears cooperative and agreeable',
            'Rarely offends others',
            'Can create a non-threatening presence',
            'May be good at observing group dynamics',
            'Often seen as patient and easy-going'
        ],
        'improvement_tips': [
            'Practice expressing opinions in low-risk situations',
            'Start using "I" statements to express needs',
            'Work on saying "no" when necessary',
            'Reduce qualifying phrases like "just" and "sorry"',
            'Set small goals for speaking up in conversations'
        ]
    },
    'aggressive': {
        'name': 'Aggressive',
        'description': 'Forceful communication that prioritizes personal expression without regard for others',
        'signs': [
            'Uses accusatory language ("you always" or "you never")',
            'Interrupts or talks over others',
            'Speaks loudly or intensely',
            'Uses controlling or demanding language',
            'Dismisses others\' perspectives'
        ],
        'strengths': [
            'Clearly expresses thoughts and feelings',
            'Gets immediate attention',
            'Shows conviction and passion',
            'Usually not misunderstood',
            'Can take decisive action'
        ],
        'improvement_tips': [
            'Practice pausing before responding',
            'Convert "you" statements to "I" statements',
            'Work on active listening skills',
            'Monitor tone and volume when speaking',
            'Ask questions instead of making assumptions'
        ]
    },
    'passive_aggressive': {
        'name': 'Passive-Aggressive',
        'description': 'Indirect expression of negative feelings instead of openly addressing them',
        'signs': [
            'Uses sarcasm or subtle jabs',
            'Shows contradiction between words and actions',
            'Gives backhanded compliments',
            'Appears cooperative but sabotages or delays',
            'Uses indirect resistance or procrastination'
        ],
        'strengths': [
            'Avoids direct confrontation',
            'May preserve surface-level harmony',
            'Often uses humor (though misdirected)',
            'Can recognize underlying issues',
            'Shows awareness of social dynamics'
        ],
        'improvement_tips': [
            'Practice identifying and naming true feelings',
            'Choose direct communication for expressing concerns',
            'Examine fears around direct confrontation',
            'Separate issues from personal relationships',
            'Work on constructive expression of negative emotions'
        ]
    },
    'manipulative': {
        'name': 'Manipulative',
        'description': 'Calculating communication designed to influence others through indirect tactics',
        'signs': [
            'Uses guilt, flattery, or shame to influence',
            'Changes facts or information when convenient',
            'Creates confusion or doubt to maintain control',
            'Exploits emotional reactions',
            'Employs subtle threats or ultimatums'
        ],
        'strengths': [
            'Demonstrates strategic thinking',
            'Shows awareness of social dynamics',
            'Often appears charismatic or persuasive',
            'Can be effective at short-term influence',
            'Understands emotional motivators'
        ],
        'improvement_tips': [
            'Practice direct requests instead of manipulation',
            'Examine fears of rejection or powerlessness',
            'Work on genuine connection rather than control',
            'Develop authentic persuasion skills',
            'Build self-esteem separate from controlling outcomes'
        ]
    },
    'analytical': {
        'name': 'Analytical',
        'description': 'Logical, detail-oriented communication focused on facts and processes',
        'signs': [
            'Prioritizes facts, data, and logic',
            'Examines issues methodically',
            'Uses precise language',
            'Avoids emotional expressions',
            'Focuses on details and accuracy'
        ],
        'strengths': [
            'Brings clarity to complex problems',
            'Maintains objectivity',
            'Thinks systematically',
            'Notices inconsistencies and gaps',
            'Provides well-reasoned perspectives'
        ],
        'improvement_tips': [
            'Remember to acknowledge emotional aspects',
            'Practice expressing personal perspectives',
            'Work on summarizing details for others',
            'Consider how delivery affects reception',
            'Balance analysis with relationship-building'
        ]
    },
    'intuitive': {
        'name': 'Intuitive',
        'description': 'Big-picture communication focused on concepts, possibilities, and future implications',
        'signs': [
            'Focuses on concepts and big-picture ideas',
            'Talks about possibilities and future implications',
            'Makes conceptual leaps and connections',
            'Uses metaphors and analogies',
            'May gloss over specific details'
        ],
        'strengths': [
            'Generates innovative ideas',
            'Sees connections others might miss',
            'Envisions future possibilities',
            'Thinks outside conventional boundaries',
            'Inspires creative thinking in others'
        ],
        'improvement_tips': [
            'Include more concrete examples',
            'Check that others are following your conceptual leaps',
            'Be patient with those who need more details',
            'Ground abstract ideas in practical applications',
            'Practice clarifying your vision step by step'
        ]
    },
    'empathetic': {
        'name': 'Empathetic',
        'description': 'Relationship-oriented communication that prioritizes understanding others\' feelings and needs',
        'signs': [
            'Focuses on understanding others\' feelings',
            'Uses supportive and validating language',
            'Asks questions about emotions and experiences',
            'Shows active listening',
            'Demonstrates compassion and care'
        ],
        'strengths': [
            'Builds strong relationships',
            'Creates psychological safety',
            'Helps others feel understood',
            'Defuses tension effectively',
            'Fosters open communication'
        ],
        'improvement_tips': [
            'Remember to express your own needs too',
            'Set appropriate boundaries',
            'Balance empathy with problem-solving when needed',
            'Avoid taking on others\' emotional burdens',
            'Practice self-care to prevent empathy fatigue'
        ]
    }
}

# Language markers for different communication styles
STYLE_MARKERS = {
    'assertive': [
        r'\bI (think|feel|need|want|would like)\b',
        r'\bspecifically\b',
        r'\bclearly\b',
        r'\bdirectly\b',
        r'\bmy (perspective|opinion|view|take|thought)\b'
    ],
    'passive': [
        r'\bjust\b',
        r'\bsort of\b',
        r'\bkind of\b',
        r'\bmaybe\b',
        r'\bif (it\'s not too much|you don\'t mind|that\'s okay)\b',
        r'\bI\'m sorry\b',
        r'\bwhatever you think\b'
    ],
    'aggressive': [
        r'\byou (always|never)\b',
        r'\bobviously\b',
        r'\bclearly\b',
        r'\babsolutely\b',
        r'\bmust\b',
        r'\bhave to\b',
        r'\bno excuse\b'
    ],
    'passive_aggressive': [
        r'\bfine\b',
        r'\bwhatever\b',
        r'\bno problem\b',
        r'\bI guess\b',
        r'\bnot that it matters\b',
        r'\bdon\'t worry about it\b'
    ],
    'analytical': [
        r'\bspecifically\b',
        r'\bdata\b',
        r'\bevidence\b',
        r'\bfacts\b',
        r'\blogically\b',
        r'\bprocess\b',
        r'\banalysis\b'
    ],
    'intuitive': [
        r'\bbig picture\b',
        r'\bpossibilities\b',
        r'\bfuture\b',
        r'\bpotential\b',
        r'\bvision\b',
        r'\bimagine\b',
        r'\bcreative\b'
    ],
    'empathetic': [
        r'\bunderstand\b',
        r'\bfeel\b',
        r'\bexperience\b',
        r'\bperspective\b',
        r'\bsupport\b',
        r'\bcare\b',
        r'\blisten\b'
    ]
}

def analyze_communication_style(text, session_history=None, use_gpt=True):
    """
    Analyze text to determine communication style and patterns.
    
    Args:
        text (str): The text to analyze
        session_history (list, optional): Previous messages for context
        use_gpt (bool): Whether to use GPT for enhanced analysis
        
    Returns:
        dict: Analysis results including style, patterns, and suggestions
    """
    # If GPT is available and enabled, use it for enhanced analysis
    if openai_client and use_gpt:
        try:
            return analyze_with_gpt(text, session_history)
        except Exception as e:
            logging.error(f"Error using GPT for communication analysis: {e}")
            # Fall back to rule-based analysis
    
    # Perform rule-based analysis as a fallback
    return analyze_with_rules(text)

def analyze_with_rules(text):
    """
    Analyze communication style using rule-based approach.
    
    Args:
        text (str): The text to analyze
        
    Returns:
        dict: Analysis results
    """
    # Convert to lowercase for better matching
    text_lower = text.lower()
    
    # Initialize style scores
    style_scores = {style: 0 for style in STYLE_MARKERS.keys()}
    
    # Count markers for each style
    for style, patterns in STYLE_MARKERS.items():
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            style_scores[style] += len(matches)
    
    # Determine primary and secondary styles
    sorted_styles = sorted(style_scores.items(), key=lambda x: x[1], reverse=True)
    primary_style = sorted_styles[0][0]
    secondary_style = sorted_styles[1][0] if len(sorted_styles) > 1 else None
    
    # Calculate confidence (normalize by text length)
    total_markers = sum(style_scores.values())
    word_count = len(text.split())
    confidence = min(0.9, total_markers / max(1, word_count) * 3) if word_count > 0 else 0.3
    
    # Prepare result
    result = {
        'primary_style': {
            'id': primary_style,
            'name': STYLE_CATEGORIES[primary_style]['name'],
            'description': STYLE_CATEGORIES[primary_style]['description'],
            'signs': STYLE_CATEGORIES[primary_style]['signs'],
            'strengths': STYLE_CATEGORIES[primary_style]['strengths'],
            'improvement_tips': STYLE_CATEGORIES[primary_style]['improvement_tips']
        },
        'confidence': confidence,
        'pattern_details': {
            'sentence_length': analyze_sentence_length(text),
            'word_choice': analyze_word_choice(text),
            'listening_indicators': analyze_listening_indicators(text)
        }
    }
    
    # Add secondary style if relevant (score at least 50% of primary)
    if secondary_style and sorted_styles[1][1] >= sorted_styles[0][1] * 0.5:
        result['secondary_style'] = {
            'id': secondary_style,
            'name': STYLE_CATEGORIES[secondary_style]['name'],
            'description': STYLE_CATEGORIES[secondary_style]['description']
        }
    
    return result

def analyze_with_gpt(text, session_history=None):
    """
    Use GPT to analyze communication style.
    
    Args:
        text (str): The text to analyze
        session_history (list, optional): Previous messages for context
        
    Returns:
        dict: Analysis results
    """
    # Prepare context from session history
    context = ""
    if session_history and len(session_history) > 0:
        context = "Previous messages in the conversation:\n"
        for i, msg in enumerate(session_history[-5:]):  # Use last 5 messages for context
            context += f"Message {i+1}: {msg}\n"
    
    # Construct the prompt
    prompt = f"""Analyze the following text to determine the communication style, patterns, and provide suggestions for improvement:

{context}

Text to analyze: "{text}"

Determine the primary and (if applicable) secondary communication style from these categories:
- Assertive: Direct, confident, and respectful communication
- Passive: Indirect communication that avoids expressing true thoughts or needs
- Aggressive: Forceful communication without regard for others
- Passive-Aggressive: Indirect expression of negative feelings
- Analytical: Logical, detail-oriented communication
- Intuitive: Big-picture communication focused on concepts and possibilities
- Empathetic: Relationship-oriented communication prioritizing understanding others

Also analyze:
1. Sentence structure and length
2. Word choice patterns
3. Listening indicators
4. Strengths in the communication
5. Areas for improvement

Respond with JSON in this format:
{
  "primary_style": {
    "id": "style_id",
    "name": "Style Name",
    "description": "Brief description",
    "signs": ["Sign 1", "Sign 2", "Sign 3"],
    "strengths": ["Strength 1", "Strength 2", "Strength 3"],
    "improvement_tips": ["Tip 1", "Tip 2", "Tip 3"]
  },
  "secondary_style": {
    "id": "style_id",
    "name": "Style Name",
    "description": "Brief description"
  },
  "confidence": 0.85,
  "pattern_details": {
    "sentence_length": "Analysis of sentence length and structure",
    "word_choice": "Analysis of word choice patterns",
    "listening_indicators": "Analysis of listening behaviors"
  }
}

If there's no clear secondary style, omit that field. Confidence should be between 0 and 1.
"""
    
    try:
        # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # Do not change this unless explicitly requested by the user.
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a communication style analyst specializing in NLP."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=1000
        )
        
        # Parse and return the response
        result = json.loads(response.choices[0].message.content)
        return result
    
    except Exception as e:
        logging.error(f"Error in GPT communication analysis: {e}")
        # Fall back to rule-based analysis
        return analyze_with_rules(text)

def analyze_sentence_length(text):
    """
    Analyze sentence length patterns in the text.
    
    Args:
        text (str): The text to analyze
        
    Returns:
        str: Analysis of sentence length
    """
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return "Text too short to analyze sentence structure."
    
    # Calculate average sentence length
    avg_length = sum(len(s.split()) for s in sentences) / len(sentences)
    
    if avg_length < 5:
        return "Very short sentences, potentially indicating direct or fragmented communication."
    elif avg_length < 10:
        return "Concise sentences, suggesting clear and direct communication."
    elif avg_length < 15:
        return "Moderate sentence length, balanced and accessible."
    elif avg_length < 20:
        return "Longer sentences, potentially indicating complex or nuanced thinking."
    else:
        return "Very long sentences, may suggest analytical thinking or difficulty being concise."

def analyze_word_choice(text):
    """
    Analyze patterns in word choice.
    
    Args:
        text (str): The text to analyze
        
    Returns:
        str: Analysis of word choice patterns
    """
    text_lower = text.lower()
    
    # Check for emotional words
    emotional_words = ['feel', 'happy', 'sad', 'angry', 'excited', 'frustrated', 'worried', 'anxious']
    emotional_count = sum(1 for word in emotional_words if word in text_lower.split())
    
    # Check for qualifying words
    qualifying_words = ['just', 'maybe', 'perhaps', 'possibly', 'somewhat', 'sort of', 'kind of']
    qualifying_count = sum(1 for word in qualifying_words if word in text_lower)
    
    # Check for absolute words
    absolute_words = ['always', 'never', 'everyone', 'nobody', 'absolutely', 'definitely', 'certainly']
    absolute_count = sum(1 for word in absolute_words if word in text_lower.split())
    
    # Analyze patterns
    patterns = []
    
    if emotional_count > 2:
        patterns.append("Uses emotional language frequently")
    elif emotional_count > 0:
        patterns.append("Includes some emotional language")
    else:
        patterns.append("Limited emotional language")
        
    if qualifying_count > 3:
        patterns.append("Uses many qualifying or hedging words")
    elif qualifying_count > 1:
        patterns.append("Some use of qualifying language")
        
    if absolute_count > 2:
        patterns.append("Uses absolute or black-and-white language")
        
    # Overall analysis
    if not patterns:
        return "Word choice analysis inconclusive due to limited text."
        
    return " and ".join(patterns) + "."

def analyze_listening_indicators(text):
    """
    Analyze indicators of active listening.
    
    Args:
        text (str): The text to analyze
        
    Returns:
        str: Analysis of listening indicators
    """
    text_lower = text.lower()
    
    # Listening indicators
    asks_questions = bool(re.search(r'\?', text))
    references_others = bool(re.search(r'\byou (said|mentioned|noted|expressed|shared)\b', text_lower))
    shows_understanding = bool(re.search(r'\b(understand|see what you mean|makes sense|appreciate)\b', text_lower))
    
    if asks_questions and (references_others or shows_understanding):
        return "Shows strong active listening behaviors through questions and acknowledgment."
    elif asks_questions or references_others or shows_understanding:
        return "Demonstrates some listening behaviors."
    else:
        return "Limited indicators of active listening in this text."

def get_improvement_suggestions(style_id):
    """
    Get improvement suggestions for a specific communication style.
    
    Args:
        style_id (str): The style identifier
        
    Returns:
        list: List of improvement suggestions
    """
    if style_id in STYLE_CATEGORIES:
        return STYLE_CATEGORIES[style_id]['improvement_tips']
    return []

def get_all_communication_styles():
    """
    Get information about all communication styles.
    
    Returns:
        dict: Information about all styles
    """
    return {style_id: {
        'name': info['name'], 
        'description': info['description']
    } for style_id, info in STYLE_CATEGORIES.items()}