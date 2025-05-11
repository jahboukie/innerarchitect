import os
import logging
import uuid
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, flash, redirect, url_for
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize database
from database import db
db.init_app(app)

# Import models
from models import User, ChatHistory, JournalEntry, TechniqueEffectiveness, TechniqueUsageStats

# Create database tables
with app.app_context():
    db.create_all()
    logging.info("Database tables created")

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Import NLP analyzer and exercises
from nlp_analyzer import recommend_technique, get_technique_description
from nlp_exercises import (
    initialize_default_exercises,
    get_exercises_by_technique,
    get_exercise_by_id,
    start_exercise,
    update_exercise_progress,
    get_exercise_progress
)

# Import progress tracker
from progress_tracker import (
    add_technique_rating,
    update_technique_stats,
    get_technique_usage,
    get_technique_ratings,
    get_chat_history_with_techniques,
    get_progress_summary
)

# Import technique details
from nlp_techniques import (
    get_technique_details,
    get_all_technique_names,
    get_example_for_technique,
    get_practice_tips
)

# Import communication analyzer
from communication_analyzer import (
    analyze_communication_style,
    get_improvement_suggestions,
    get_all_communication_styles
)

# Import personalized journeys
from personalized_journeys import (
    create_personalized_journey,
    get_journey_progress,
    get_next_milestone,
    update_milestone_status,
    get_all_journey_types,
    get_focus_areas,
    get_techniques_by_communication_style
)

# Initialize default NLP exercises
with app.app_context():
    initialize_default_exercises()

# Home route
@app.route('/')
def index():
    # Generate a session ID if one doesn't exist
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    return render_template('index.html')

# Route to get NLP technique recommendations
@app.route('/recommend_technique', methods=['POST'])
def get_technique_recommendation():
    """
    Endpoint for recommending the most appropriate NLP technique
    based on the user's message and mood.
    """
    # Get the user message and mood from the request
    data = request.json
    message = data.get('message', '')
    mood = data.get('mood', 'neutral')
    
    # Log the received request
    logging.debug(f"Technique recommendation request: Message={message}, Mood={mood}")
    
    # Get technique recommendation
    recommendation = recommend_technique(message, mood)
    
    # Return the recommendation as JSON
    return jsonify(recommendation)

@app.route('/chat', methods=['POST'])
def chat():
    """
    Endpoint for AI interaction.
    Receives user message, processes it through OpenAI,
    and returns the AI response.
    """
    # Get the user message, mood, and NLP technique from the request
    data = request.json
    message = data.get('message', '')
    mood = data.get('mood', 'neutral')
    technique = data.get('technique', 'reframing')
    
    # Get session ID for tracking the conversation
    session_id = session.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    
    # Log the received message for debugging
    logging.debug(f"Received message: {message} (Mood: {mood}, Technique: {technique}, Session: {session_id})")
    
    # Check if OpenAI API key is available
    if not OPENAI_API_KEY:
        logging.error("OpenAI API key is missing")
        return jsonify({
            'response': "I'm sorry, but I'm not fully configured yet. Please provide an OpenAI API key to enable AI responses."
        })
    
    try:
        # Prepare the prompt for OpenAI with NLP techniques
        system_prompt = """You are The Inner Architect, a supportive self-help guide with expertise in Neuro-Linguistic Programming (NLP).
        
        Your goal is to help users reframe negative thoughts and build more positive mental patterns using NLP techniques including:
        
        1. Reframing: Help users see situations from different perspectives.
        2. Pattern interruption: Suggest ways to break negative thought cycles.
        3. Anchoring: Associate positive emotions with specific triggers.
        4. Future pacing: Guide users to visualize positive future outcomes.
        5. Sensory-based language: Use visual, auditory, and kinesthetic language matching the user's communication style.
        6. Meta model questioning: Ask questions that challenge limiting beliefs and generalizations.
        
        Based on the user's mood and message:
        1. Acknowledge their current emotional state with empathy
        2. Identify any limiting beliefs or negative patterns
        3. Apply 1-2 appropriate NLP techniques to help reframe their thinking
        4. Provide a practical, actionable suggestion they can implement immediately
        
        Keep responses concise (2-3 short paragraphs maximum) and conversational. Use the user's name if available.
        """
        
        # Make the API call to OpenAI
        # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"User mood: {mood}\nUser message: {message}\nRequested NLP technique: {technique}"}
            ],
            max_tokens=300  # Limit response length
        )
        
        # Extract the AI response
        ai_response = response.choices[0].message.content.strip()
        logging.debug(f"AI response: {ai_response}")
        
        # Save the chat history to the database
        try:
            chat_entry = ChatHistory(
                session_id=session_id,
                user_message=message,
                ai_response=ai_response,
                mood=mood,
                nlp_technique=technique
            )
            db.session.add(chat_entry)
            db.session.commit()
            logging.info(f"Chat history saved with ID: {chat_entry.id}")
        except Exception as db_error:
            # Log the error but don't interrupt user experience
            logging.error(f"Error saving chat history: {str(db_error)}")
            db.session.rollback()
        
        # Return the AI response to the frontend
        return jsonify({
            'response': ai_response
        })
        
    except Exception as e:
        # Log any errors
        logging.error(f"Error calling OpenAI API: {str(e)}")
        return jsonify({
            'response': "I'm sorry, I encountered an error while processing your message. Please try again later."
        })

# NLP Exercise routes
@app.route('/exercises/<technique>', methods=['GET'])
def get_technique_exercises(technique):
    """
    Get exercises for a specific NLP technique.
    """
    exercises = get_exercises_by_technique(technique)
    return jsonify([{
        'id': ex.id,
        'title': ex.title,
        'description': ex.description,
        'difficulty': ex.difficulty,
        'estimated_time': ex.estimated_time
    } for ex in exercises])

@app.route('/exercise/<int:exercise_id>', methods=['GET'])
def get_exercise(exercise_id):
    """
    Get details for a specific exercise.
    """
    exercise = get_exercise_by_id(exercise_id)
    if not exercise:
        return jsonify({'error': 'Exercise not found'}), 404
    
    # Parse the steps JSON
    steps = json.loads(exercise.steps)
    
    return jsonify({
        'id': exercise.id,
        'technique': exercise.technique,
        'title': exercise.title,
        'description': exercise.description,
        'difficulty': exercise.difficulty,
        'estimated_time': exercise.estimated_time,
        'steps': steps
    })

@app.route('/exercise/<int:exercise_id>/start', methods=['POST'])
def start_exercise_route(exercise_id):
    """
    Start a new exercise session.
    """
    # Get session ID
    session_id = session.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    
    # Get user ID if logged in (for future auth)
    user_id = None
    
    # Start the exercise
    progress = start_exercise(exercise_id, session_id, user_id)
    if not progress:
        return jsonify({'error': 'Could not start exercise'}), 500
    
    return jsonify({
        'progress_id': progress.id,
        'exercise_id': progress.exercise_id,
        'current_step': progress.current_step,
        'completed': progress.completed
    })

@app.route('/exercise/progress/<int:progress_id>', methods=['PUT'])
def update_progress(progress_id):
    """
    Update the progress of an exercise.
    """
    data = request.json
    current_step = data.get('current_step', 0)
    notes = data.get('notes')
    completed = data.get('completed', False)
    
    success = update_exercise_progress(progress_id, current_step, notes, completed)
    if not success:
        return jsonify({'error': 'Could not update progress'}), 500
    
    return jsonify({'success': True})

@app.route('/exercise/progress', methods=['GET'])
def get_progress():
    """
    Get exercise progress for the current session.
    """
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'error': 'No active session'}), 400
    
    exercise_id = request.args.get('exercise_id')
    if exercise_id:
        try:
            exercise_id = int(exercise_id)
        except ValueError:
            return jsonify({'error': 'Invalid exercise ID'}), 400
    
    progress_records = get_exercise_progress(session_id, exercise_id)
    
    return jsonify([{
        'id': p.id,
        'exercise_id': p.exercise_id,
        'current_step': p.current_step,
        'completed': p.completed,
        'started_at': p.started_at.isoformat(),
        'completed_at': p.completed_at.isoformat() if p.completed_at else None
    } for p in progress_records])

# Progress Dashboard Routes
@app.route('/progress/dashboard', methods=['GET'])
def progress_dashboard():
    """
    Render the progress dashboard page.
    """
    # Get session ID
    session_id = session.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        
    # Render the dashboard template
    return render_template('dashboard.html')

@app.route('/progress/summary', methods=['GET'])
def get_progress_summary_route():
    """
    Get progress summary data.
    """
    # Get session ID
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'error': 'No active session'}), 400
        
    # Get the summary
    summary = get_progress_summary(session_id)
    
    return jsonify(summary)

@app.route('/progress/technique-usage', methods=['GET'])
def get_technique_usage_route():
    """
    Get technique usage statistics.
    """
    # Get session ID
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'error': 'No active session'}), 400
        
    # Get the usage stats
    usage = get_technique_usage(session_id)
    
    return jsonify(usage)

@app.route('/progress/technique-ratings', methods=['GET'])
def get_technique_ratings_route():
    """
    Get technique ratings history.
    """
    # Get session ID
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'error': 'No active session'}), 400
        
    # Get optional technique parameter
    technique = request.args.get('technique')
    
    # Get the ratings
    ratings = get_technique_ratings(session_id, technique)
    
    return jsonify(ratings)

@app.route('/progress/chat-history', methods=['GET'])
def get_chat_history_route():
    """
    Get chat history with techniques.
    """
    # Get session ID
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'error': 'No active session'}), 400
        
    # Get the chat history
    history = get_chat_history_with_techniques(session_id)
    
    return jsonify(history)

@app.route('/progress/rate-technique', methods=['POST'])
def rate_technique():
    """
    Add a rating for a technique.
    """
    # Get session ID
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'error': 'No active session'}), 400
        
    # Get the request data
    data = request.json
    technique = data.get('technique')
    rating = data.get('rating')
    notes = data.get('notes')
    situation = data.get('situation')
    
    # Validate the data
    if not technique or not rating:
        return jsonify({'error': 'Technique and rating are required'}), 400
        
    try:
        rating = int(rating)
    except ValueError:
        return jsonify({'error': 'Rating must be a number'}), 400
        
    # Add the rating
    success = add_technique_rating(
        session_id=session_id,
        technique=technique,
        rating=rating,
        notes=notes,
        situation=situation
    )
    
    if not success:
        return jsonify({'error': 'Failed to add rating'}), 500
        
    return jsonify({'success': True})

@app.route('/progress/update-chat', methods=['POST'])
def update_chat_effectiveness():
    """
    Update the effectiveness of a technique after a chat interaction.
    Called when user provides feedback on how helpful an AI response was.
    """
    # Get session ID
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'error': 'No active session'}), 400
        
    # Get the request data
    data = request.json
    technique = data.get('technique')
    rating = data.get('rating')
    
    # Validate the data
    if not technique or not rating:
        return jsonify({'error': 'Technique and rating are required'}), 400
        
    try:
        rating = int(rating)
    except ValueError:
        return jsonify({'error': 'Rating must be a number'}), 400
        
    # Update the statistics
    stats = update_technique_stats(
        session_id=session_id,
        technique=technique,
        rating=rating
    )
    
    if not stats:
        return jsonify({'error': 'Failed to update stats'}), 500
        
    return jsonify({
        'success': True,
        'usage_count': stats.usage_count,
        'avg_rating': round(stats.avg_rating, 1)
    })

# Technique Details Routes - API Endpoints
@app.route('/api/techniques', methods=['GET'])
def get_technique_list_api():
    """
    Get a list of all available NLP techniques (API).
    """
    techniques = get_all_technique_names()
    return jsonify(techniques)

@app.route('/api/techniques/<technique>', methods=['GET'])
def get_technique_info_api(technique):
    """
    Get detailed information about a specific NLP technique (API).
    """
    details = get_technique_details(technique)
    
    if not details:
        return jsonify({'error': 'Technique not found'}), 404
        
    return jsonify(details)

@app.route('/api/techniques/<technique>/example', methods=['GET'])
def get_technique_example_api(technique):
    """
    Get a practical example of a specific NLP technique (API).
    """
    example = get_example_for_technique(technique)
    
    if not example:
        return jsonify({'error': 'Example not found for this technique'}), 404
        
    return jsonify(example)

@app.route('/api/techniques/<technique>/tips', methods=['GET'])
def get_technique_tips_api(technique):
    """
    Get practice tips for a specific NLP technique (API).
    """
    tips = get_practice_tips(technique)
    
    if not tips:
        return jsonify({'error': 'No tips found for this technique'}), 404
        
    return jsonify({'tips': tips})

# Technique Details Routes - Web Pages
@app.route('/techniques', methods=['GET'])
def techniques_page():
    """
    Render the techniques list page.
    """
    techniques = {}
    for technique_id, name in get_all_technique_names().items():
        details = get_technique_details(technique_id)
        if details:
            techniques[technique_id] = details
    
    return render_template('techniques.html', techniques=techniques)

@app.route('/techniques/<technique_id>', methods=['GET'])
def technique_details_page(technique_id):
    """
    Render the technique details page.
    """
    technique = get_technique_details(technique_id)
    
    if not technique:
        flash('Technique not found', 'danger')
        return redirect(url_for('techniques_page'))
    
    return render_template('technique_details.html', technique=technique, technique_id=technique_id)

# ===== Communication Analysis Routes =====

@app.route('/api/communication/analyze', methods=['POST'])
def analyze_communication():
    """
    Analyze the user's communication style from provided text.
    """
    data = request.json
    message = data.get('message', '')
    
    if not message or len(message.strip()) < 20:
        return jsonify({
            'error': 'Message too short for analysis. Please provide at least 20 characters.'
        }), 400
    
    # Get session history for context
    session_id = session.get('session_id', str(uuid.uuid4()))
    # Limit to last 5 entries for context
    history = []  # We can extend this to use actual chat history
    
    # Use OpenAI if available, otherwise fallback to rule-based
    use_gpt = openai_client is not None
    
    # Perform analysis
    analysis = analyze_communication_style(message, history, use_gpt)
    
    return jsonify(analysis)

@app.route('/api/communication/styles')
def get_all_styles():
    """
    Get a list of all communication style definitions.
    """
    styles = get_all_communication_styles()
    return jsonify({'styles': styles})

@app.route('/api/communication/improvements/<style_id>')
def get_improvements_for_style(style_id):
    """
    Get improvement suggestions for a specific communication style.
    """
    suggestions = get_improvement_suggestions(style_id)
    return jsonify({
        'style_id': style_id,
        'improvement_suggestions': suggestions
    })

@app.route('/communication-analysis')
def communication_analysis_page():
    """
    Render the communication analysis page.
    """
    return render_template('communication_analysis.html')

# ===== Personalized Journey Routes =====

@app.route('/api/journeys/types')
def get_journey_types_api():
    """
    Get all available journey types.
    """
    journey_types = get_all_journey_types()
    return jsonify({'journey_types': journey_types})

@app.route('/api/journeys/focus-areas')
def get_focus_areas_api():
    """
    Get all available focus areas for personalized journeys.
    """
    focus_areas = get_focus_areas()
    return jsonify({'focus_areas': focus_areas})

@app.route('/api/journeys/create', methods=['POST'])
def create_journey_api():
    """
    Create a new personalized journey.
    """
    data = request.json
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    journey_type = data.get('journey_type', 'communication_improvement')
    comm_style = data.get('communication_style')
    focus_areas = data.get('focus_areas', [])
    intensity = data.get('intensity', 'moderate')
    
    # Get session ID
    session_id = session.get('session_id', str(uuid.uuid4()))
    if 'session_id' not in session:
        session['session_id'] = session_id
    
    # Create the journey
    journey = create_personalized_journey(
        session_id=session_id,
        journey_type=journey_type,
        comm_style=comm_style,
        focus_areas=focus_areas,
        intensity=intensity
    )
    
    if not journey:
        return jsonify({'error': 'Failed to create journey'}), 500
    
    # Store journey in session
    if 'journeys' not in session:
        session['journeys'] = {}
    
    session['journeys'][journey.journey_id] = journey.to_dict()
    session.modified = True
    
    return jsonify({
        'success': True,
        'journey': journey.to_dict()
    })

@app.route('/api/journeys/list')
def list_journeys_api():
    """
    Get all journeys for the current session.
    """
    session_id = session.get('session_id')
    
    if not session_id:
        return jsonify({'journeys': []})
    
    # Get journeys from session
    journeys = session.get('journeys', {})
    
    return jsonify({'journeys': list(journeys.values())})

@app.route('/api/journeys/<journey_id>')
def get_journey_api(journey_id):
    """
    Get a specific journey.
    """
    journeys = session.get('journeys', {})
    
    if journey_id not in journeys:
        return jsonify({'error': 'Journey not found'}), 404
    
    return jsonify({'journey': journeys[journey_id]})

@app.route('/api/journeys/<journey_id>/progress')
def get_journey_progress_api(journey_id):
    """
    Get progress statistics for a journey.
    """
    journeys = session.get('journeys', {})
    
    if journey_id not in journeys:
        return jsonify({'error': 'Journey not found'}), 404
    
    journey = journeys[journey_id]
    
    # Calculate progress
    total_milestones = len(journey['milestones'])
    completed_milestones = sum(1 for m in journey['milestones'] if m.get('completed', False))
    
    progress_percentage = 0
    if total_milestones > 0:
        progress_percentage = round((completed_milestones / total_milestones) * 100)
    
    progress = {
        'journey_id': journey_id,
        'total_milestones': total_milestones,
        'completed_milestones': completed_milestones,
        'progress_percentage': progress_percentage
    }
    
    return jsonify({'progress': progress})

@app.route('/api/journeys/<journey_id>/next-milestone')
def get_next_milestone_api(journey_id):
    """
    Get the next milestone for a journey.
    """
    journeys = session.get('journeys', {})
    
    if journey_id not in journeys:
        return jsonify({'error': 'Journey not found'}), 404
    
    journey = journeys[journey_id]
    
    # Find next incomplete milestone
    next_milestone = None
    today = datetime.now().strftime('%Y-%m-%d')
    
    # First try to find any incomplete milestone on or before today
    for milestone in journey['milestones']:
        if not milestone.get('completed', False) and milestone['date'] <= today:
            next_milestone = milestone
            break
    
    # If none found, find the next upcoming milestone
    if not next_milestone:
        upcoming_milestones = [
            m for m in journey['milestones'] 
            if not m.get('completed', False) and m['date'] > today
        ]
        upcoming_milestones.sort(key=lambda m: m['date'])
        
        if upcoming_milestones:
            next_milestone = upcoming_milestones[0]
    
    if not next_milestone:
        return jsonify({'message': 'All milestones completed', 'milestone': None})
    
    return jsonify({'milestone': next_milestone})

@app.route('/api/journeys/<journey_id>/milestones/<int:milestone_number>/complete', methods=['POST'])
def complete_milestone_api(journey_id, milestone_number):
    """
    Mark a milestone as completed.
    """
    journeys = session.get('journeys', {})
    
    if journey_id not in journeys:
        return jsonify({'error': 'Journey not found'}), 404
    
    journey = journeys[journey_id]
    
    # Find and update the milestone
    milestone_found = False
    for milestone in journey['milestones']:
        if milestone['number'] == milestone_number:
            milestone['completed'] = True
            milestone_found = True
            break
    
    if not milestone_found:
        return jsonify({'error': 'Milestone not found'}), 404
    
    # Update the journey in session
    journeys[journey_id] = journey
    session['journeys'] = journeys
    session.modified = True
    
    return jsonify({
        'success': True,
        'message': 'Milestone completed',
        'milestone_number': milestone_number
    })

@app.route('/personalized-journeys')
def personalized_journeys_page():
    """
    Render the personalized journeys page.
    """
    return render_template('personalized_journeys.html')

@app.route('/personalized-journeys/<journey_id>')
def journey_details_page(journey_id):
    """
    Render the journey details page.
    """
    journeys = session.get('journeys', {})
    
    if journey_id not in journeys:
        flash('Journey not found', 'danger')
        return redirect(url_for('personalized_journeys_page'))
    
    return render_template('journey_details.html', journey=journeys[journey_id])

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
