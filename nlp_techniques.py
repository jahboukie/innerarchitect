"""
NLP Techniques module for The Inner Architect

This module provides detailed explanations and examples for various NLP techniques.
"""

# Comprehensive information about each NLP technique
TECHNIQUE_DETAILS = {
    'reframing': {
        'name': 'Reframing',
        'short_description': 'See situations from new perspectives and find positive aspects in challenges.',
        'description': """
Reframing is the process of changing the way you look at something and, in turn, changing your experience of it. 
It involves consciously shifting your perspective to view a situation, person, or relationship from a different angle, 
often finding more positive or constructive interpretations.

Reframing doesn't deny or ignore the facts of a situation, but rather changes the meaning you attach to those facts. 
By changing the meaning, you can change your emotional response and discover new possibilities for action.
        """,
        'key_concepts': [
            'Cognitive reframing focuses on changing thought patterns',
            'Context reframing places the situation in a different context',
            'Content reframing gives a different meaning to the same content',
            'The meaning you give to events shapes your emotional response'
        ],
        'benefits': [
            'Reduces anxiety and stress',
            'Transforms negative thoughts into constructive thinking',
            'Develops resilience and adaptability',
            'Creates new opportunities for problem-solving',
            'Improves relationships by changing perspectives'
        ],
        'examples': [
            {
                'situation': 'Being laid off from a job',
                'negative_frame': 'This is terrible! My career is ruined, and I will never find another job.',
                'positive_reframe': 'This is an opportunity to find a position that better matches my skills and interests. I now have time to explore paths I could not before.'
            },
            {
                'situation': 'Making a mistake on an important project',
                'negative_frame': 'I am incompetent and cannot do anything right. Everyone will think less of me.',
                'positive_reframe': 'Everyone makes mistakes, and this is how I learn and grow. The mistake has shown me areas where I can improve.'
            },
            {
                'situation': 'Having to wait in a long line',
                'negative_frame': 'This is a complete waste of my time. I am getting nothing accomplished.',
                'positive_reframe': 'This unexpected break gives me time to plan my day, catch up on reading, or simply practice mindfulness.'
            }
        ],
        'practice_tips': [
            'Question your automatic interpretations of events',
            'Ask yourself, "What else could this mean?" or "How else could I look at this?"',
            'Consider what advice you would give a friend in the same situation',
            'Look for the learning opportunity or growth potential',
            'Focus on what you can control rather than what you cannot control'
        ],
        'common_pitfalls': [
            'Trying to force positive thinking without acknowledging real challenges',
            'Using reframing to avoid addressing problems that need action',
            'Creating unrealistic or delusional interpretations',
            'Expecting immediate emotional changes without practice'
        ],
        'scientific_basis': """
Cognitive reframing is a core concept in Cognitive Behavioral Therapy (CBT), which has extensive research supporting its effectiveness. 
Studies show that how we interpret events (our cognitive appraisals) directly affects our emotional responses and behaviors. 
Neuroimaging research indicates that reframing can reduce activity in the amygdala (the brain's fear center) and increase activity 
in prefrontal regions associated with cognitive control.
        """
    },
    
    'pattern_interruption': {
        'name': 'Pattern Interruption',
        'short_description': 'Break negative thought cycles and establish new, healthier patterns.',
        'description': """
Pattern interruption is a technique that involves disrupting an established pattern of thought or behavior. 
By interrupting habitual negative patterns, you create a moment of confusion or novelty that allows you to 
insert a new, more beneficial pattern.

Our brains naturally form neural pathways through repetition. When we repeatedly think or behave in certain ways, 
these pathways become stronger and automatic. Pattern interruption creates an opportunity to break these automatic 
responses and establish new neural connections.
        """,
        'key_concepts': [
            'Patterns become automatic through repetition',
            'Interruption creates a brief window for change',
            'The interruption must be followed by a new pattern',
            'Both mental and physical interruptions can be effective',
            'Pattern interruption works at both conscious and unconscious levels'
        ],
        'benefits': [
            'Stops rumination and negative thought spirals',
            'Creates space for more conscious choices',
            'Reduces automatic emotional reactions',
            'Increases mental flexibility',
            'Helps establish new, healthier habits'
        ],
        'examples': [
            {
                'situation': 'Spiraling into anxiety about future events',
                'pattern': 'One worry leads to another in a chain reaction of anxious thoughts',
                'interruption': 'Clap your hands loudly once and say "STOP!" Then take three deep breaths.',
                'new_pattern': 'Focus on the present moment and what you can control right now'
            },
            {
                'situation': 'Critical self-talk after a mistake',
                'pattern': 'Automatically berating yourself with thoughts like "I always mess up"',
                'interruption': 'Visualize a large red STOP sign, then smile (even if forced at first)',
                'new_pattern': 'Ask yourself, "What would I say to a friend who made this mistake?"'
            },
            {
                'situation': 'Conflict pattern with a partner',
                'pattern': 'Same arguments escalate in predictable ways',
                'interruption': 'Change your physical position or suggest a 10-minute break',
                'new_pattern': 'Return to the conversation with a focus on understanding rather than winning'
            }
        ],
        'practice_tips': [
            'Create a distinctive physical interruption (snap a rubber band, tap a specific spot)',
            'Make the interruption strong enough to break your mental state',
            'Practice your chosen interruption consistently',
            'Plan your replacement pattern in advance',
            'Start with smaller patterns before tackling deeply ingrained ones'
        ],
        'common_pitfalls': [
            'Not having a replacement pattern ready',
            'Interrupting without redirecting to something positive',
            'Using subtle interruptions that do not actually break the pattern',
            'Expecting instant results without consistent practice',
            'Not recognizing when you are in a pattern in the first place'
        ],
        'scientific_basis': """
Pattern interruption has roots in both behavioral psychology and neuroscience. Research in habit formation shows that 
habitual behaviors are triggered automatically by environmental cues. The technique creates what neuroscientists call 
a "pattern separation" in neural activity, allowing new neural pathways to form. The effectiveness of pattern interruption 
is supported by studies on habit reversal training and mindfulness-based interventions.
        """
    },
    
    'anchoring': {
        'name': 'Anchoring',
        'short_description': 'Associate positive emotions with specific physical or mental triggers.',
        'description': """
Anchoring is a technique that creates a connection between a specific stimulus (anchor) and a particular 
emotional state or response. This allows you to intentionally access desired emotional states by activating 
the anchor. Anchors can be visual, auditory, kinesthetic (touch-based), or even olfactory (smell-based).

The concept is based on Pavlovian conditioning, where a neutral stimulus becomes associated with a specific 
response through repeated pairing. In NLP, anchoring is used deliberately to create resources that help you 
access confidence, calmness, motivation, or other beneficial states when needed.
        """,
        'key_concepts': [
            'Anchors create neural associations between stimuli and responses',
            'Effective anchors are unique, specific, and replicable',
            'The emotional state must be strong when setting the anchor',
            'Anchors can be stacked and chained for more powerful effects',
            'Both conscious and unconscious anchors influence our behavior'
        ],
        'benefits': [
            'Provides quick access to resourceful emotional states',
            'Creates emotional stability during challenging situations',
            'Helps override negative emotional reactions',
            'Increases confidence and performance in specific contexts',
            'Assists in breaking unwanted emotional associations'
        ],
        'examples': [
            {
                'situation': 'Preparing for a presentation or interview',
                'desired_state': 'Confidence and clarity',
                'anchor_creation': 'Recall a time when you felt extremely confident and capable. As you intensify this feeling, press your thumb and middle finger together firmly for 5-10 seconds.',
                'anchor_use': 'Before and during the presentation, press your thumb and middle finger together in the same way to recall the feeling of confidence'
            },
            {
                'situation': 'Managing stress or anxiety',
                'desired_state': 'Calmness and centered focus',
                'anchor_creation': 'While in a deeply relaxed state (perhaps after meditation), touch a specific point on your wrist while focusing on the feeling of tranquility',
                'anchor_use': 'When feeling stressed, touch the same point on your wrist in the identical way'
            },
            {
                'situation': 'Motivating yourself for exercise',
                'desired_state': 'Energy and enthusiasm',
                'anchor_creation': 'Remember times when you felt energized and motivated to exercise. While experiencing these feelings strongly, listen to a specific song',
                'anchor_use': 'Play the same song when you need motivation to exercise'
            }
        ],
        'practice_tips': [
            'Choose anchors that are distinctive and not used in everyday life',
            'Ensure you are in a peak emotional state when setting the anchor',
            'Apply the anchor for a consistent duration (5-10 seconds works well)',
            'Practice firing the anchor frequently to strengthen the association',
            'Create different anchors for different emotional states you want to access'
        ],
        'common_pitfalls': [
            'Setting anchors when the emotional state is not strong enough',
            'Using inconsistent or imprecise anchor application',
            'Creating too many anchors without properly reinforcing them',
            'Setting anchors in distracting environments',
            'Expecting anchors to work immediately without reinforcement'
        ],
        'scientific_basis': """
Anchoring is based on classical conditioning, a well-established psychological principle discovered by Ivan Pavlov. 
Neurologically, anchoring works by creating neural pathways that associate specific stimuli with emotional states. 
Research in neuroscience confirms that repeated pairing strengthens these neural connections through a process 
called Hebbian learning ("neurons that fire together, wire together"). Studies in sports psychology have shown 
the effectiveness of anchoring techniques for enhancing athletic performance.
        """
    },
    
    'future_pacing': {
        'name': 'Future Pacing',
        'short_description': 'Guide users to visualize positive outcomes and mentally rehearse success.',
        'description': """
Future pacing is a technique that involves mentally rehearsing a future event or situation in vivid detail. 
It creates a multi-sensory internal representation of successfully handling a situation before you actually 
experience it. This mental rehearsal primes your nervous system and mind to respond effectively when the 
real situation occurs.

The technique leverages the fact that your nervous system doesn't fully distinguish between a vividly 
imagined experience and an actual experience. By repeatedly imagining success in specific situations, 
you create neural pathways that support that successful outcome.
        """,
        'key_concepts': [
            'Mental rehearsal creates neural pathways similar to actual experience',
            'Multi-sensory visualization enhances effectiveness',
            'Future pacing connects current decisions to future outcomes',
            'The technique builds both competence and confidence',
            'Future pacing can be used to test the ecological impact of changes'
        ],
        'benefits': [
            'Reduces anxiety about future events',
            'Improves performance through mental practice',
            'Increases motivation by connecting to desired outcomes',
            'Helps identify potential obstacles before they occur',
            'Creates a sense of familiarity in new situations'
        ],
        'examples': [
            {
                'situation': 'Job interview preparation',
                'process': 'Visualize the entire interview process: walking into the room confidently, answering questions articulately, and connecting well with the interviewers',
                'sensory_elements': 'See the interview room, hear the questions and your composed responses, feel the comfortable chair, sense your steady breathing',
                'outcome': 'Experience the satisfaction of a successful interview and receiving the job offer'
            },
            {
                'situation': 'Athletic performance',
                'process': 'Mentally rehearse your perfect performance: the starting position, the execution of movements, maintaining focus throughout',
                'sensory_elements': 'Feel the movements in your body, hear the sounds of the environment, see the course or field from your perspective',
                'outcome': 'Visualize completing the performance successfully and feeling the positive emotions of achievement'
            },
            {
                'situation': 'Public speaking',
                'process': 'Imagine giving your presentation from start to finish: walking on stage, delivering key points clearly, engaging with the audience',
                'sensory_elements': 'See the audience responding positively, hear your confident voice, feel your relaxed posture and steady breathing',
                'outcome': 'Experience receiving positive feedback and applause after your presentation'
            }
        ],
        'practice_tips': [
            'Make your visualization as detailed and multi-sensory as possible',
            'Include potential challenges and visualize overcoming them',
            'Practice future pacing regularly for important upcoming events',
            'Maintain a positive emotional state during the visualization',
            'Incorporate actual physical movements when appropriate (e.g., practice gestures)'
        ],
        'common_pitfalls': [
            'Creating vague or abstract visualizations',
            'Focusing only on visual elements while ignoring other senses',
            'Allowing doubts or negative outcomes to enter the visualization',
            'Future pacing without addressing underlying skills or preparation',
            'Rushing through the visualization rather than experiencing it fully'
        ],
        'scientific_basis': """
Future pacing builds on extensive research in sports psychology and performance enhancement. Studies show that 
mental practice activates many of the same neural pathways as physical practice. Functional MRI studies demonstrate 
that visualization activates motor cortex regions similarly to actual movement. Research in behavioral psychology 
confirms that mental rehearsal improves performance across various domains, from sports to surgery to public speaking.
        """
    },
    
    'sensory_language': {
        'name': 'Sensory Language',
        'short_description': 'Use visual, auditory, and kinesthetic language to enhance communication.',
        'description': """
Sensory language involves using words and phrases that appeal to specific sensory modalities (visual, auditory, 
kinesthetic, olfactory, and gustatory) to enhance communication and understanding. This technique recognizes 
that people tend to process information differently based on their preferred representational systems.

In NLP, it's understood that people have preferences for different sensory modalities when thinking and communicating. 
By identifying someone's preferred modality and matching your language to it, you can establish deeper rapport and 
ensure your message resonates more effectively. Additionally, using rich sensory language creates more vivid and 
memorable communication regardless of modality preference.
        """,
        'key_concepts': [
            'People have preferred representational systems (visual, auditory, kinesthetic)',
            'Matching language to the preferred system of another person builds rapport',
            'Predicates (verbs, adverbs, adjectives) indicate sensory preference',
            'Multi-sensory descriptions create richer experiences',
            'Eye movements often correlate with sensory thinking'
        ],
        'benefits': [
            'Creates deeper connection and understanding in communication',
            'Makes abstract concepts more concrete and relatable',
            'Enhances memory and retention of information',
            'Helps overcome communication barriers',
            'Creates more persuasive and engaging messages'
        ],
        'examples': [
            {
                'modality': 'Visual language',
                'predicates': 'see, look, appear, view, show, clear, foggy, bright, perspective, focus',
                'phrases': 'I see what you mean. Let me paint a picture for you. That looks right to me. The future appears bright.',
                'effective_for': 'Creating clear mental images and helping people "see" your point'
            },
            {
                'modality': 'Auditory language',
                'predicates': 'hear, listen, sound, tune, tell, resonate, harmonize, loud, quiet, discuss',
                'phrases': 'That sounds good to me. Let us talk it through. I hear what you are saying. Something tells me this will work out.',
                'effective_for': 'Establishing dialogue and helping information "sound right" to others'
            },
            {
                'modality': 'Kinesthetic language',
                'predicates': 'feel, touch, grasp, handle, pressure, stress, rough, smooth, heavy, light',
                'phrases': 'I can grasp that concept. Let us get in touch soon. That feels right to me. I am carrying a heavy load right now.',
                'effective_for': 'Creating emotional connection and making concepts tangible'
            }
        ],
        'identifying_preferences': [
            'Listen for sensory predicates in speech patterns',
            'Notice common phrases they use repeatedly',
            'Observe eye movements (up for visual, side for auditory, down for kinesthetic)',
            'Pay attention to breathing patterns and speaking pace',
            'Ask how they remember information best'
        ],
        'practice_tips': [
            'Expand your vocabulary in all sensory modalities',
            'Practice translating concepts into different sensory languages',
            'Use all modalities for important communications',
            'Listen actively for preferred representational systems of others',
            'Match your speaking pace to the sensory system you are using'
        ],
        'scientific_basis': """
Research in cognitive psychology supports the existence of preferred learning and processing styles, though the 
field has moved away from strict categorization of "visual/auditory/kinesthetic learners." Neurolinguistic studies 
confirm that sensory-rich language activates corresponding sensory processing regions in the brain. Studies in 
communication effectiveness show that matching communication style to audience preferences significantly improves 
comprehension and persuasiveness.
        """
    },
    
    'meta_model': {
        'name': 'Meta Model Questions',
        'short_description': 'Challenge limiting beliefs and generalizations through targeted questions.',
        'description': """
The Meta Model is a set of language patterns and questioning techniques designed to challenge and clarify vague, 
distorted, or limited thinking. It works by identifying common language patterns that often represent deletions, 
distortions, or generalizations in a person's mental map of the world.

When we communicate, we inevitably leave out information, make generalizations, and distort our experience through 
language. The Meta Model provides specific questions to recover the deleted information, challenge unhelpful 
generalizations, and clarify distortions, helping to reconnect language with the underlying experience and expand 
the range of choices available.
        """,
        'key_concepts': [
            'The map is not the territory (language represents but is not reality)',
            'Communication involves deletions, distortions, and generalizations',
            'Specific questioning patterns can reveal these linguistic limitations',
            'Challenging language patterns expands choice and possibility',
            'The goal is to reconnect language with experience'
        ],
        'benefits': [
            'Identifies and challenges limiting beliefs',
            'Improves clarity in thinking and communication',
            'Reveals hidden assumptions and presuppositions',
            'Expands awareness of choices and possibilities',
            'Helps move from vague complaints to specific solutions'
        ],
        'pattern_categories': [
            {
                'category': 'Deletions',
                'description': 'Information that has been left out of the communication',
                'examples': 'I am uncomfortable. (About what?) I cannot do it. (What specifically? What stops you?)',
                'challenge_questions': 'What specifically? About what or whom? Compared to what?'
            },
            {
                'category': 'Generalizations',
                'description': 'Universal quantifiers and rules that limit possibilities',
                'examples': 'Nobody listens to me. Everyone ignores my contributions. I always mess things up.',
                'challenge_questions': 'Never? Always? Everyone? No one? What would happen if someone did?'
            },
            {
                'category': 'Distortions',
                'description': 'Mind reading, cause-effect assumptions, and complex equivalences',
                'examples': 'She does not like my idea. (How do you know?) If I speak up, people will reject me.',
                'challenge_questions': 'How do you know? How does X cause Y? In what way does X mean Y?'
            }
        ],
        'specific_patterns': [
            {
                'pattern': 'Universal Quantifiers (all, every, never, always)',
                'example': 'I always make mistakes in presentations.',
                'challenging_question': 'Always? Has there ever been a time when you did not make a mistake?',
                'purpose': 'Reveals exceptions that challenge the limitation'
            },
            {
                'pattern': 'Modal Operators (should, must, have to, cannot)',
                'example': 'I cannot speak in public.',
                'challenging_question': 'What would happen if you did? What stops you?',
                'purpose': 'Explores the perceived limitations and potential consequences'
            },
            {
                'pattern': 'Cause-Effect (X causes Y)',
                'example': 'His criticism makes me feel worthless.',
                'challenging_question': 'How specifically does his criticism cause you to feel worthless?',
                'purpose': 'Reveals the process and challenges the automatic connection'
            }
        ],
        'practice_tips': [
            'Start by identifying patterns in your own language and thoughts',
            'Ask Meta Model questions with curiosity rather than confrontation',
            'Listen for vague language and gentle probe for specificity',
            'Pay attention to verbal and non-verbal responses to your questions',
            'Use the Meta Model to achieve clarity, not to prove someone wrong'
        ],
        'scientific_basis': """
The Meta Model aligns with cognitive linguistics and cognitive-behavioral psychology. Research on cognitive distortions 
in CBT validates many of the patterns identified in the Meta Model. Linguists studying transformational grammar have 
confirmed how surface structure language often omits or distorts deep structure meaning. Studies in communication 
show that specific, precise language leads to clearer understanding and more effective problem-solving than vague, 
overgeneralized language.
        """
    }
}

def get_technique_details(technique):
    """
    Get detailed information about a specific NLP technique.
    
    Args:
        technique (str): The technique name (e.g., 'reframing', 'anchoring')
        
    Returns:
        dict: Detailed information about the technique or None if not found
    """
    return TECHNIQUE_DETAILS.get(technique)

def get_all_technique_names():
    """
    Get names of all available techniques.
    
    Returns:
        dict: Mapping of technique IDs to their display names
    """
    return {tech_id: details['name'] for tech_id, details in TECHNIQUE_DETAILS.items()}

def get_example_for_technique(technique):
    """
    Get a random example for a specific technique.
    
    Args:
        technique (str): The technique name
        
    Returns:
        dict: An example of the technique in use or None if not found
    """
    import random
    
    details = TECHNIQUE_DETAILS.get(technique)
    if not details or 'examples' not in details:
        return None
    
    return random.choice(details['examples'])

def get_practice_tips(technique):
    """
    Get practice tips for a specific technique.
    
    Args:
        technique (str): The technique name
        
    Returns:
        list: List of practice tips or empty list if not found
    """
    details = TECHNIQUE_DETAILS.get(technique)
    if not details or 'practice_tips' not in details:
        return []
    
    return details['practice_tips']