import os
import logging
import uuid
import json
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, flash, redirect, url_for, g
from flask_login import current_user, login_required
from openai import OpenAI
import stripe
from werkzeug.middleware.proxy_fix import ProxyFix

# Set up Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Subscription plan configuration
SUBSCRIPTION_PLANS = {
    'premium': {
        'name': 'The Inner Architect Premium',
        'price_id': None,  # Will be set dynamically or from Stripe Dashboard
        'amount': 999,  # $9.99 in cents
        'currency': 'usd',
        'interval': 'month',
        'features': [
            'All NLP techniques', 
            'Unlimited AI chat interactions', 
            'Full progress tracking', 
            'Communication analysis', 
            'Priority support'
        ]
    },
    'professional': {
        'name': 'The Inner Architect Professional',
        'price_id': None,  # Will be set dynamically or from Stripe Dashboard
        'amount': 1999,  # $19.99 in cents
        'currency': 'usd',
        'interval': 'month',
        'features': [
            'Everything in Premium',
            'Voice practice features',
            'Personalized journeys',
            'Belief change protocol',
            'Practice reminders',
            'Priority support'
        ]
    }
}

# Import language utilities
import language_util

# Import models
from models import User, OAuth, Subscription

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize database
from database import db
db.init_app(app)

# Initialize login manager and replit auth after db init
from replit_auth import make_replit_blueprint, require_login

# Subscription access decorators
def require_premium(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            session["next_url"] = request.url
            return redirect(url_for('login_check'))
            
        # Check if user has premium or better subscription
        subscription = Subscription.query.filter_by(user_id=current_user.id).first()
        if not (subscription and subscription.has_premium_access):
            flash("This feature requires a Premium subscription. Please upgrade your plan.", "warning")
            return redirect(url_for('landing'))
            
        return f(*args, **kwargs)
    return decorated_function


def require_professional(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            session["next_url"] = request.url
            return redirect(url_for('login_check'))
            
        # Check if user has professional subscription
        subscription = Subscription.query.filter_by(user_id=current_user.id).first()
        if not (subscription and subscription.has_professional_access):
            flash("This feature requires a Professional subscription. Please upgrade your plan.", "warning")
            return redirect(url_for('landing'))
            
        return f(*args, **kwargs)
    return decorated_function
app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")

# Import models
from models import User, ChatHistory, JournalEntry, NLPExercise, NLPExerciseProgress, TechniqueEffectiveness, TechniqueUsageStats

# Create database tables
with app.app_context():
    db.create_all()
    logging.info("Database tables created")

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Language middleware
@app.before_request
def before_request():
    # Make session permanent
    session.permanent = True
    
    # Set default language if not in session
    if 'language' not in session:
        # Try to detect from Accept-Language header
        if request.accept_languages:
            for lang_code, _ in request.accept_languages:
                if lang_code in language_util.SUPPORTED_LANGUAGES:
                    session['language'] = lang_code
                    break
                # Check if it's a locale with a region (e.g., en-US)
                main_lang = lang_code.split('-')[0]
                if main_lang in language_util.SUPPORTED_LANGUAGES:
                    session['language'] = main_lang
                    break
            else:
                session['language'] = language_util.DEFAULT_LANGUAGE
        else:
            session['language'] = language_util.DEFAULT_LANGUAGE
    
    # Store language in g for templates
    g.language = session.get('language', language_util.DEFAULT_LANGUAGE)
    g.languages = language_util.get_supported_languages()
    g.is_rtl = language_util.is_rtl(g.language)
    
    # Helper function for templates
    def translate(text_key, default=None):
        return language_util.translate_ui_text(text_key, g.language, default)
    
    g.translate = translate


# Decorator to translate API responses
def translate_response(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = f(*args, **kwargs)
        
        # Only translate if we have a JSON response and a non-default language
        if (isinstance(response, tuple) and len(response) > 0 and isinstance(response[0], dict)) or \
           isinstance(response, dict):
            target_lang = session.get('language', language_util.DEFAULT_LANGUAGE)
            
            if target_lang != language_util.DEFAULT_LANGUAGE:
                if isinstance(response, tuple):
                    translated_response = language_util.translate_content(response[0], target_lang)
                    return (translated_response,) + response[1:]
                else:
                    return language_util.translate_content(response, target_lang)
        
        return response
    return decorated_function

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

# Import voice interactions
from voice_interactions import (
    get_available_exercise_types,
    get_voice_exercise,
    get_exercises_by_technique,
    get_exercises_by_type,
    get_default_exercises,
    transcribe_audio,
    analyze_vocal_delivery,
    evaluate_technique_application,
    save_submission,
    get_submission,
    get_user_submissions,
    get_metric_descriptions,
    VoiceSubmission
)

# Import practice reminders
from practice_reminders import (
    create_reminder,
    update_reminder,
    delete_reminder,
    get_reminder,
    get_reminders,
    mark_reminder_complete,
    get_due_reminders,
    get_reminder_streak,
    get_reminder_statistics,
    get_reminder_frequencies,
    get_reminder_types,
    PracticeReminder
)

# Import belief change protocol
from belief_change import (
    create_belief_session,
    get_belief_session,
    save_belief_session,
    update_step_response,
    get_belief_sessions,
    categorize_belief,
    analyze_belief,
    generate_reframe_suggestions,
    generate_meta_model_questions,
    suggest_action_steps,
    get_belief_categories,
    get_protocol_steps,
    get_techniques_for_belief_change,
    BeliefChangeSession
)

# Initialize default NLP exercises
with app.app_context():
    initialize_default_exercises()

# Home route
@app.route('/language/<lang_code>')
def set_language(lang_code):
    """
    Set the user's preferred language.
    """
    # Validate language
    if lang_code in language_util.SUPPORTED_LANGUAGES:
        session['language'] = lang_code
        session.modified = True
    
    # Redirect back to referrer or home
    referrer = request.referrer
    if referrer and referrer.startswith(request.host_url):
        return redirect(referrer)
    
    return redirect(url_for('index'))


# Login check route
@app.route('/auth/login-check')
def login_check():
    """
    Check if user is already logged in and redirect accordingly.
    """
    if current_user.is_authenticated:
        flash("You are already logged in.", "info") 
        return redirect(url_for('profile'))
    
    # Not logged in, proceed to Replit auth
    return redirect(url_for('replit_auth.login'))


# User Profile route
@app.route('/profile')
@require_login
def profile():
    """
    User profile page.
    """
    # Get user stats
    exercise_count = NLPExerciseProgress.query.filter_by(
        user_id=current_user.id, 
        completed=True
    ).count()
    
    # Get unique techniques used
    techniques = TechniqueEffectiveness.query.filter_by(
        user_id=current_user.id
    ).with_entities(TechniqueEffectiveness.technique).distinct().count()
    
    # Get subscription info using the subscription manager
    from subscription_manager import get_subscription_details
    
    # Get detailed subscription information
    subscription_details = get_subscription_details(current_user.id)
    
    # Format for template display
    subscription_info = {
        'plan_name': subscription_details['plan_name'].capitalize(),
        'status': subscription_details['status'],
        'current_period_end': subscription_details.get('current_period_end'),
        'features': []
    }
    
    # Format features for display
    for feature in subscription_details['features']:
        # Convert snake_case to readable text
        readable_feature = feature.replace('_', ' ').title()
        subscription_info['features'].append(readable_feature)
    
    # Get recent activity (last 5 items)
    recent_chats = ChatHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(ChatHistory.created_at.desc()).limit(3).all()
    
    recent_exercises = NLPExerciseProgress.query.filter_by(
        user_id=current_user.id
    ).order_by(NLPExerciseProgress.started_at.desc()).limit(2).all()
    
    # Format for display
    activity = []
    
    for chat in recent_chats:
        activity.append({
            'title': 'Chat Interaction',
            'description': f"Used technique: {chat.nlp_technique or 'None'}",
            'date': chat.created_at.strftime('%b %d, %Y')
        })
    
    for ex in recent_exercises:
        status = "Completed" if ex.completed else f"In Progress (Step {ex.current_step})"
        exercise = NLPExercise.query.get(ex.exercise_id)
        if exercise:
            activity.append({
                'title': f"Exercise: {exercise.title}",
                'description': f"Status: {status}",
                'date': ex.started_at.strftime('%b %d, %Y')
            })
    
    # Sort by date (newest first)
    activity.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template(
        'profile.html',
        exercise_count=exercise_count,
        technique_count=techniques,
        recent_activity=activity,
        subscription=subscription_info
    )

# Landing page route
@app.route('/landing')
def landing():
    """
    Render the landing page with pricing information.
    """
    # Generate a session ID if one doesn't exist
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        
    return render_template('landing.html')


# Checkout route for subscription plans
@app.route('/checkout/<plan>')
@require_login
def create_checkout(plan):
    """
    Create a Stripe checkout session for subscription plans.
    
    Args:
        plan (str): The subscription plan ('premium' or 'professional')
    """
    if plan not in SUBSCRIPTION_PLANS:
        flash(f"Invalid plan: {plan}", "danger")
        return redirect(url_for('landing'))
        
    plan_data = SUBSCRIPTION_PLANS[plan]
    
    # Get the domain for the success/cancel URLs
    domain_url = request.host_url.rstrip('/')
    
    try:
        # Check if user already has a customer ID
        subscription = Subscription.query.filter_by(user_id=current_user.id).first()
        
        if subscription and subscription.stripe_customer_id:
            # Existing customer
            customer_id = subscription.stripe_customer_id
        else:
            # Create a new customer in Stripe
            customer = stripe.Customer.create(
                email=current_user.email,
                name=f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or None,
                metadata={
                    'user_id': current_user.id
                }
            )
            customer_id = customer.id
            
            # Create or update subscription record
            if not subscription:
                subscription = Subscription(
                    user_id=current_user.id,
                    stripe_customer_id=customer_id,
                    plan_name='free',
                    status='active'
                )
                db.session.add(subscription)
            else:
                subscription.stripe_customer_id = customer_id
            
            db.session.commit()
        
        # Create a checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': plan_data['currency'],
                        'product_data': {
                            'name': plan_data['name'],
                            'description': f"The Inner Architect {plan.capitalize()} Plan",
                            'metadata': {
                                'plan': plan
                            }
                        },
                        'unit_amount': plan_data['amount'],
                        'recurring': {
                            'interval': plan_data['interval'],
                        },
                    },
                    'quantity': 1,
                }
            ],
            metadata={
                'user_id': current_user.id,
                'plan': plan
            },
            mode='subscription',
            success_url=f"{domain_url}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{domain_url}/subscription/cancel",
        )
        
        # Redirect to Stripe checkout
        return redirect(checkout_session.url)
    except Exception as e:
        logging.error(f"Error creating checkout session: {str(e)}")
        flash("An error occurred while processing your request. Please try again later.", "danger")
        return redirect(url_for('landing'))


# Subscription success route
@app.route('/subscription/success')
@require_login
def subscription_success():
    """
    Handle successful subscription checkout.
    """
    session_id = request.args.get('session_id')
    if not session_id:
        flash("Invalid checkout session.", "danger")
        return redirect(url_for('profile'))
        
    try:
        # Retrieve checkout session from Stripe
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        # Ensure this session belongs to the current user
        if checkout_session.metadata.get('user_id') != current_user.id:
            flash("Invalid checkout session.", "danger")
            return redirect(url_for('profile'))
            
        # Get the subscription ID
        subscription_id = checkout_session.subscription
        
        # Retrieve the subscription details
        stripe_subscription = stripe.Subscription.retrieve(subscription_id)
        
        # Update the user's subscription in the database
        subscription = Subscription.query.filter_by(user_id=current_user.id).first()
        
        if not subscription:
            # Create a new subscription record
            subscription = Subscription(
                user_id=current_user.id,
                stripe_customer_id=checkout_session.customer,
                stripe_subscription_id=subscription_id,
                plan_name=checkout_session.metadata.get('plan', 'premium'),
                status='active',
                current_period_start=datetime.fromtimestamp(stripe_subscription.current_period_start),
                current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end)
            )
            db.session.add(subscription)
        else:
            # Update existing subscription
            subscription.stripe_subscription_id = subscription_id
            subscription.plan_name = checkout_session.metadata.get('plan', 'premium')
            subscription.status = 'active'
            subscription.current_period_start = datetime.fromtimestamp(stripe_subscription.current_period_start)
            subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end)
            
        db.session.commit()
        
        # Show success message
        plan_name = subscription.plan_name.capitalize()
        flash(f"Thank you! Your {plan_name} subscription has been activated.", "success")
        
        return redirect(url_for('profile'))
        
    except Exception as e:
        logging.error(f"Error processing subscription: {str(e)}")
        flash("An error occurred while processing your subscription. Please contact support.", "danger")
        return redirect(url_for('profile'))


# Subscription cancel route
@app.route('/subscription/cancel')
@require_login
def subscription_cancel():
    """
    Handle canceled subscription checkout.
    """
    flash("Your subscription checkout was canceled. You can try again anytime.", "info")
    return redirect(url_for('landing'))


# Stripe webhook handler
@app.route('/webhooks/stripe', methods=['POST'])
def stripe_webhook():
    """
    Handle Stripe webhook events.
    """
    from subscription_manager import process_webhook_event
    
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    # Verify webhook signature
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        else:
            # For development, we can parse the payload directly
            data = json.loads(payload)
            event = data
        
        # Process the event
        if process_webhook_event(event):
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Event processing failed'}), 500
            
    except ValueError as e:
        # Invalid payload
        return jsonify({'status': 'error', 'message': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return jsonify({'status': 'error', 'message': 'Invalid signature'}), 400
    except Exception as e:
        logging.error(f"Error processing webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# User subscription management
@app.route('/subscription/manage')
@require_login
def manage_subscription():
    """
    Render the subscription management page.
    """
    from subscription_manager import get_subscription_details
    
    # Get subscription details
    subscription_details = get_subscription_details(current_user.id)
    
    return render_template('subscription_manage.html', subscription=subscription_details)


# Cancel subscription
@app.route('/subscription/cancel-subscription', methods=['POST'])
@require_login
def cancel_user_subscription():
    """
    Cancel the user's subscription.
    """
    from subscription_manager import cancel_subscription
    
    try:
        if cancel_subscription(current_user.id):
            flash("Your subscription has been canceled. You will still have access until the end of your billing period.", "success")
        else:
            flash("Unable to cancel subscription. Please try again later.", "danger")
    except Exception as e:
        logging.error(f"Error canceling subscription: {str(e)}")
        flash("An error occurred while processing your request. Please try again later.", "danger")
    
    return redirect(url_for('manage_subscription'))

@app.route('/')
def index():
    """
    Render the index page for authenticated users, or redirect to landing for visitors.
    """
    # Generate a session ID if one doesn't exist
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    # For non-authenticated users, redirect to landing page
    if not current_user.is_authenticated:
        return redirect(url_for('landing'))
    
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
    
    # Check usage quotas based on subscription tier
    user_id = None
    if current_user.is_authenticated:
        user_id = current_user.id
    
    # Import subscription manager functions
    from subscription_manager import check_usage_quota, increment_usage_quota
    
    # Check if user has reached their daily message limit
    has_quota = check_usage_quota(user_id, 'messages_per_day')
    if not has_quota:
        return jsonify({
            'response': "You've reached your daily message limit. Please upgrade your subscription for unlimited conversations or wait until tomorrow.",
            'quota_exceeded': True
        })
    
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
            # Associate with user if authenticated
            user_id_for_chat = None
            if current_user.is_authenticated:
                user_id_for_chat = current_user.id
                
            chat_entry = ChatHistory(
                user_id=user_id_for_chat,
                session_id=session_id,
                user_message=message,
                ai_response=ai_response,
                mood=mood,
                nlp_technique=technique
            )
            db.session.add(chat_entry)
            db.session.commit()
            logging.info(f"Chat history saved with ID: {chat_entry.id}")
            
            # Increment usage quota counter for user
            increment_usage_quota(user_id, 'messages_per_day')
            
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
    
    # Get user ID if logged in
    user_id = None
    if current_user.is_authenticated:
        user_id = current_user.id
        
        # Import subscription manager functions
        from subscription_manager import check_usage_quota, increment_usage_quota
        
        # Check if user has reached their weekly exercise limit
        has_quota = check_usage_quota(user_id, 'exercises_per_week')
        if not has_quota:
            return jsonify({
                'error': 'You have reached your weekly exercise limit. Please upgrade your subscription for unlimited exercises.',
                'quota_exceeded': True
            }), 403
    
    # Start the exercise
    progress = start_exercise(exercise_id, session_id, user_id)
    if not progress:
        return jsonify({'error': 'Could not start exercise'}), 500
    
    # Increment usage quota counter for exercises if user is authenticated
    if current_user.is_authenticated:
        try:
            increment_usage_quota(user_id, 'exercises_per_week')
        except Exception as e:
            # Log but don't interrupt experience
            logging.error(f"Error incrementing exercise quota: {str(e)}")
    
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
@require_premium
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
@require_premium
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
@require_premium
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
@require_professional
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

# ===== Voice Interaction Routes =====

@app.route('/api/voice/exercise-types')
def get_voice_exercise_types_api():
    """
    Get all available voice exercise types.
    """
    exercise_types = get_available_exercise_types()
    return jsonify({'exercise_types': exercise_types})

@app.route('/api/voice/exercises')
def get_voice_exercises_api():
    """
    Get voice exercises with optional filters.
    """
    technique = request.args.get('technique')
    exercise_type = request.args.get('type')
    limit = request.args.get('limit')
    
    if limit:
        try:
            limit = int(limit)
        except ValueError:
            limit = None
    
    if technique:
        exercises = get_exercises_by_technique(technique, limit)
    elif exercise_type:
        exercises = get_exercises_by_type(exercise_type, limit)
    else:
        exercises = get_default_exercises()
        if limit:
            exercises = exercises[:limit]
    
    return jsonify({
        'exercises': [e.to_dict() for e in exercises]
    })

@app.route('/api/voice/exercises/<exercise_id>')
def get_voice_exercise_api(exercise_id):
    """
    Get a specific voice exercise.
    """
    exercise = get_voice_exercise(exercise_id)
    
    if not exercise:
        return jsonify({'error': 'Exercise not found'}), 404
    
    return jsonify({'exercise': exercise.to_dict()})

@app.route('/api/voice/transcribe', methods=['POST'])
def transcribe_audio_api():
    """
    Transcribe audio data.
    """
    data = request.json
    
    if not data or 'audio_data' not in data:
        return jsonify({'error': 'No audio data provided'}), 400
    
    audio_data = data.get('audio_data', '')
    
    # Remove the data URL prefix if present
    if audio_data.startswith('data:audio/'):
        audio_data = audio_data.split('base64,')[1]
    
    if not audio_data:
        return jsonify({'error': 'Invalid audio data format'}), 400
    
    # Transcribe the audio
    transcript = transcribe_audio(audio_data)
    
    if not transcript:
        return jsonify({
            'error': 'Transcription failed',
            'message': 'Could not transcribe the audio. Please try again with a clearer recording.'
        }), 500
    
    return jsonify({
        'success': True,
        'transcript': transcript
    })

@app.route('/api/voice/analyze', methods=['POST'])
def analyze_voice_api():
    """
    Analyze a voice submission.
    """
    data = request.json
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    audio_data = data.get('audio_data', '')
    transcript = data.get('transcript')
    exercise_id = data.get('exercise_id')
    
    # Remove the data URL prefix if present
    if audio_data.startswith('data:audio/'):
        audio_data = audio_data.split('base64,')[1]
    
    # Get the exercise if provided
    exercise = None
    if exercise_id:
        exercise = get_voice_exercise(exercise_id)
    
    # If no transcript provided, transcribe the audio
    if not transcript and audio_data:
        transcript = transcribe_audio(audio_data)
    
    if not transcript:
        return jsonify({
            'error': 'No transcript available',
            'message': 'Could not analyze the submission without a transcript.'
        }), 400
    
    # Analyze the vocal delivery
    analysis = analyze_vocal_delivery(audio_data, transcript, exercise)
    
    # If exercise has a specific technique, evaluate the application
    technique_evaluation = None
    if exercise and exercise.technique:
        technique_evaluation = evaluate_technique_application(
            transcript, exercise.technique, exercise.exercise_type
        )
    
    # Get session ID
    session_id = session.get('session_id', str(uuid.uuid4()))
    if 'session_id' not in session:
        session['session_id'] = session_id
    
    # Create and save the submission
    submission = VoiceSubmission(
        submission_id=None,  # Will be generated by save_submission
        exercise_id=exercise_id if exercise else None,
        audio_data=audio_data,
        transcript=transcript,
        session_id=session_id
    )
    
    # Set feedback and metrics
    submission.feedback = {
        'vocal_delivery': analysis.get('feedback', {}),
        'technique_application': technique_evaluation if technique_evaluation else None
    }
    
    submission.metrics = {
        'vocal_delivery': analysis.get('metrics', {}),
        'technique_application': {
            'score': technique_evaluation.get('application_score') if technique_evaluation else None
        }
    }
    
    # Save the submission
    success = save_submission(submission)
    
    if not success:
        return jsonify({'error': 'Failed to save submission'}), 500
    
    # Return the analysis results
    return jsonify({
        'success': True,
        'submission_id': submission.submission_id,
        'transcript': transcript,
        'analysis': {
            'vocal_delivery': analysis,
            'technique_application': technique_evaluation
        }
    })

@app.route('/api/voice/metrics')
def get_voice_metrics_api():
    """
    Get descriptions of vocal metrics.
    """
    return jsonify({
        'metrics': get_metric_descriptions()
    })

@app.route('/api/voice/submissions')
def get_voice_submissions_api():
    """
    Get voice submissions for the current session.
    """
    session_id = session.get('session_id')
    
    if not session_id:
        return jsonify({'submissions': []})
    
    submissions = get_user_submissions(session_id)
    
    return jsonify({
        'submissions': [s.to_dict() for s in submissions]
    })

@app.route('/voice-practice')
@require_professional
def voice_practice_page():
    """
    Render the voice practice page.
    """
    return render_template('voice_practice.html')

@app.route('/voice-practice/<exercise_id>')
def voice_exercise_page(exercise_id):
    """
    Render the specific voice exercise page.
    """
    exercise = get_voice_exercise(exercise_id)
    
    if not exercise:
        flash('Exercise not found', 'danger')
        return redirect(url_for('voice_practice_page'))
    
    return render_template('voice_exercise.html', exercise=exercise.to_dict())

# ===== Practice Reminders Routes =====

@app.route('/api/reminders/frequencies')
def get_reminder_frequencies_api():
    """
    Get available reminder frequencies.
    """
    return jsonify({'frequencies': get_reminder_frequencies()})

@app.route('/api/reminders/types')
def get_reminder_types_api():
    """
    Get available reminder types.
    """
    return jsonify({'types': get_reminder_types()})

@app.route('/api/reminders', methods=['GET'])
def get_reminders_api():
    """
    Get reminders for the current session.
    """
    session_id = session.get('session_id')
    
    if not session_id:
        return jsonify({'reminders': []})
    
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    reminder_type = request.args.get('type')
    
    reminders = get_reminders(session_id, active_only, reminder_type)
    
    return jsonify({
        'reminders': [r.to_dict() for r in reminders]
    })

@app.route('/api/reminders/<reminder_id>', methods=['GET'])
def get_reminder_api(reminder_id):
    """
    Get a specific reminder.
    """
    session_id = session.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'No active session'}), 400
    
    reminder = get_reminder(reminder_id, session_id)
    
    if not reminder:
        return jsonify({'error': 'Reminder not found'}), 404
    
    return jsonify({'reminder': reminder.to_dict()})

@app.route('/api/reminders', methods=['POST'])
def create_reminder_api():
    """
    Create a new reminder.
    """
    data = request.json
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Get session ID
    session_id = session.get('session_id', str(uuid.uuid4()))
    if 'session_id' not in session:
        session['session_id'] = session_id
    
    # Extract fields from request
    title = data.get('title')
    description = data.get('description', '')
    reminder_type = data.get('reminder_type')
    frequency = data.get('frequency')
    time_preferences = data.get('time_preferences')
    days_of_week = data.get('days_of_week')
    linked_content_id = data.get('linked_content_id')
    
    # Validate required fields
    if not title or not reminder_type or not frequency:
        return jsonify({
            'error': 'Missing required fields',
            'required': ['title', 'reminder_type', 'frequency']
        }), 400
    
    # Create the reminder
    reminder = create_reminder(
        user_id=None,  # No user ID for now
        session_id=session_id,
        title=title,
        description=description,
        reminder_type=reminder_type,
        frequency=frequency,
        time_preferences=time_preferences,
        days_of_week=days_of_week,
        linked_content_id=linked_content_id
    )
    
    if not reminder:
        return jsonify({'error': 'Failed to create reminder'}), 500
    
    return jsonify({
        'success': True,
        'reminder': reminder.to_dict()
    })

@app.route('/api/reminders/<reminder_id>', methods=['PUT'])
def update_reminder_api(reminder_id):
    """
    Update an existing reminder.
    """
    data = request.json
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    session_id = session.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'No active session'}), 400
    
    # Update the reminder
    reminder = update_reminder(reminder_id, session_id, data)
    
    if not reminder:
        return jsonify({'error': 'Reminder not found or update failed'}), 404
    
    return jsonify({
        'success': True,
        'reminder': reminder.to_dict()
    })

@app.route('/api/reminders/<reminder_id>', methods=['DELETE'])
def delete_reminder_api(reminder_id):
    """
    Delete a reminder.
    """
    session_id = session.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'No active session'}), 400
    
    # Delete the reminder
    success = delete_reminder(reminder_id, session_id)
    
    if not success:
        return jsonify({'error': 'Reminder not found or deletion failed'}), 404
    
    return jsonify({
        'success': True,
        'message': 'Reminder deleted successfully'
    })

@app.route('/api/reminders/<reminder_id>/complete', methods=['POST'])
def complete_reminder_api(reminder_id):
    """
    Mark a reminder as completed for today.
    """
    session_id = session.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'No active session'}), 400
    
    # Mark the reminder as completed
    reminder = mark_reminder_complete(reminder_id, session_id)
    
    if not reminder:
        return jsonify({'error': 'Reminder not found or completion failed'}), 404
    
    return jsonify({
        'success': True,
        'reminder': reminder.to_dict()
    })

@app.route('/api/reminders/due')
def get_due_reminders_api():
    """
    Get reminders that are due for notification.
    """
    session_id = session.get('session_id')
    
    if not session_id:
        return jsonify({'reminders': []})
    
    reminders = get_due_reminders(session_id)
    
    return jsonify({
        'reminders': [r.to_dict() for r in reminders]
    })

@app.route('/api/reminders/statistics')
def get_reminder_statistics_api():
    """
    Get statistics about reminder completion.
    """
    session_id = session.get('session_id')
    
    if not session_id:
        return jsonify({
            'total_reminders': 0,
            'active_reminders': 0,
            'completion_rate': 0,
            'longest_streak': 0
        })
    
    stats = get_reminder_statistics(session_id)
    
    return jsonify(stats)

@app.route('/practice-reminders')
@require_professional
def reminders_page():
    """
    Render the practice reminders page.
    """
    return render_template('practice_reminders.html')

# ===== Belief Change Protocol Routes =====

@app.route('/api/belief-change/categories')
def get_belief_categories_api():
    """
    Get all belief categories.
    """
    categories = get_belief_categories()
    return jsonify({'categories': categories})

@app.route('/api/belief-change/steps')
def get_protocol_steps_api():
    """
    Get all steps in the belief change protocol.
    """
    steps = get_protocol_steps()
    return jsonify({'steps': steps})

@app.route('/api/belief-change/techniques')
def get_belief_techniques_api():
    """
    Get NLP techniques used in belief change.
    """
    techniques = get_techniques_for_belief_change()
    return jsonify({'techniques': techniques})

@app.route('/api/belief-change/analyze', methods=['POST'])
def analyze_belief_api():
    """
    Analyze a belief statement to identify patterns and suggest approaches.
    """
    data = request.json
    
    if not data or 'belief' not in data:
        return jsonify({'error': 'No belief provided'}), 400
    
    belief_text = data.get('belief')
    
    if not belief_text or len(belief_text.strip()) < 5:
        return jsonify({
            'error': 'Belief too short for analysis. Please provide at least 5 characters.'
        }), 400
    
    # Analyze the belief
    analysis = analyze_belief(belief_text)
    
    return jsonify({
        'belief': belief_text,
        'analysis': analysis
    })

@app.route('/api/belief-change/reframe', methods=['POST'])
def reframe_belief_api():
    """
    Generate suggestions for reframing a limiting belief.
    """
    data = request.json
    
    if not data or 'belief' not in data:
        return jsonify({'error': 'No belief provided'}), 400
    
    belief_text = data.get('belief')
    
    if not belief_text or len(belief_text.strip()) < 5:
        return jsonify({
            'error': 'Belief too short for reframing. Please provide at least 5 characters.'
        }), 400
    
    # Generate reframing suggestions
    suggestions = generate_reframe_suggestions(belief_text)
    
    return jsonify({
        'belief': belief_text,
        'suggestions': suggestions
    })

@app.route('/api/belief-change/meta-model', methods=['POST'])
def meta_model_questions_api():
    """
    Generate Meta Model questions to challenge a limiting belief.
    """
    data = request.json
    
    if not data or 'belief' not in data:
        return jsonify({'error': 'No belief provided'}), 400
    
    belief_text = data.get('belief')
    
    if not belief_text or len(belief_text.strip()) < 5:
        return jsonify({
            'error': 'Belief too short for questioning. Please provide at least 5 characters.'
        }), 400
    
    # Generate Meta Model questions
    questions = generate_meta_model_questions(belief_text)
    
    return jsonify({
        'belief': belief_text,
        'questions': questions
    })

@app.route('/api/belief-change/actions', methods=['POST'])
def suggest_actions_api():
    """
    Suggest concrete actions to reinforce a new empowering belief.
    """
    data = request.json
    
    if not data or 'belief' not in data:
        return jsonify({'error': 'No belief provided'}), 400
    
    belief_text = data.get('belief')
    
    if not belief_text or len(belief_text.strip()) < 5:
        return jsonify({
            'error': 'Belief too short for action planning. Please provide at least 5 characters.'
        }), 400
    
    # Generate action suggestions
    actions = suggest_action_steps(belief_text)
    
    return jsonify({
        'belief': belief_text,
        'actions': actions
    })

@app.route('/api/belief-change/sessions', methods=['GET'])
def get_belief_sessions_api():
    """
    Get belief change sessions for the current user or browser session.
    """
    session_id = session.get('session_id')
    
    if not session_id:
        return jsonify({'sessions': []})
    
    include_completed = request.args.get('include_completed', 'true').lower() == 'true'
    limit = request.args.get('limit')
    
    if limit:
        try:
            limit = int(limit)
        except ValueError:
            limit = None
    
    sessions = get_belief_sessions(browser_session_id=session_id, limit=limit, include_completed=include_completed)
    
    return jsonify({
        'sessions': [s.to_dict() for s in sessions]
    })

@app.route('/api/belief-change/sessions', methods=['POST'])
def create_belief_session_api():
    """
    Create a new belief change session.
    """
    data = request.json
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Get session ID
    session_id = session.get('session_id', str(uuid.uuid4()))
    if 'session_id' not in session:
        session['session_id'] = session_id
    
    # Extract fields from request
    initial_belief = data.get('initial_belief')
    category = data.get('category')
    
    # Validate if initial belief provided
    if initial_belief and len(initial_belief.strip()) < 5:
        return jsonify({
            'error': 'Belief too short. Please provide at least 5 characters.'
        }), 400
    
    # If category not provided but belief is, auto-categorize
    if initial_belief and not category:
        category = categorize_belief(initial_belief)
    
    # Create the session
    belief_session = create_belief_session(
        user_id=None,  # No user ID for now
        initial_belief=initial_belief,
        category=category
    )
    
    if not belief_session:
        return jsonify({'error': 'Failed to create belief change session'}), 500
    
    # Save the session
    save_success = save_belief_session(belief_session)
    
    if not save_success:
        return jsonify({'error': 'Failed to save belief change session'}), 500
    
    # Store session in browser session storage
    if 'belief_sessions' not in session:
        session['belief_sessions'] = {}
    
    session['belief_sessions'][belief_session.belief_session_id] = belief_session.to_dict()
    session.modified = True
    
    return jsonify({
        'success': True,
        'session': belief_session.to_dict()
    })

@app.route('/api/belief-change/sessions/<session_id>', methods=['GET'])
def get_belief_session_api(session_id):
    """
    Get a specific belief change session.
    """
    # Try to get from browser session first
    browser_sessions = session.get('belief_sessions', {})
    
    if session_id in browser_sessions:
        return jsonify({'session': browser_sessions[session_id]})
    
    # If not in browser session, try to get from database
    belief_session = get_belief_session(session_id)
    
    if not belief_session:
        return jsonify({'error': 'Session not found'}), 404
    
    return jsonify({'session': belief_session.to_dict()})

@app.route('/api/belief-change/sessions/<session_id>/advance', methods=['POST'])
def advance_session_step_api(session_id):
    """
    Advance a belief change session to the next step.
    """
    data = request.json or {}
    response = data.get('response')
    
    # Try to get from browser session first
    browser_sessions = session.get('belief_sessions', {})
    
    if session_id not in browser_sessions:
        # If not in browser session, try to get from database
        belief_session = get_belief_session(session_id)
        
        if not belief_session:
            return jsonify({'error': 'Session not found'}), 404
    else:
        # Recreate the session object from stored data
        session_data = browser_sessions[session_id]
        belief_session = BeliefChangeSession(
            session_id=session_data['belief_session_id'],
            user_id=session_data['user_id'],
            initial_belief=session_data['initial_belief'],
            category=session_data['category'],
            current_step=session_data['current_step'],
            completed=session_data['completed']
        )
        belief_session.responses = session_data['responses']
        
        if 'created_at' in session_data:
            belief_session.created_at = datetime.fromisoformat(session_data['created_at'])
        if 'updated_at' in session_data:
            belief_session.updated_at = datetime.fromisoformat(session_data['updated_at'])
        if 'completed_at' in session_data and session_data['completed_at']:
            belief_session.completed_at = datetime.fromisoformat(session_data['completed_at'])
    
    # Save current response if provided
    if response:
        belief_session.responses[belief_session.current_step] = response
    
    # Advance to the next step
    advanced = belief_session.advance_step()
    
    # Save the updated session
    save_success = save_belief_session(belief_session)
    
    if not save_success:
        return jsonify({'error': 'Failed to save session update'}), 500
    
    # Update browser session storage
    browser_sessions[belief_session.belief_session_id] = belief_session.to_dict()
    session['belief_sessions'] = browser_sessions
    session.modified = True
    
    return jsonify({
        'success': True,
        'advanced': advanced,
        'session': belief_session.to_dict()
    })

@app.route('/api/belief-change/sessions/<session_id>/back', methods=['POST'])
def go_back_session_step_api(session_id):
    """
    Go back to the previous step in a belief change session.
    """
    # Try to get from browser session first
    browser_sessions = session.get('belief_sessions', {})
    
    if session_id not in browser_sessions:
        # If not in browser session, try to get from database
        belief_session = get_belief_session(session_id)
        
        if not belief_session:
            return jsonify({'error': 'Session not found'}), 404
    else:
        # Recreate the session object from stored data
        session_data = browser_sessions[session_id]
        belief_session = BeliefChangeSession(
            session_id=session_data['belief_session_id'],
            user_id=session_data['user_id'],
            initial_belief=session_data['initial_belief'],
            category=session_data['category'],
            current_step=session_data['current_step'],
            completed=session_data['completed']
        )
        belief_session.responses = session_data['responses']
        
        if 'created_at' in session_data:
            belief_session.created_at = datetime.fromisoformat(session_data['created_at'])
        if 'updated_at' in session_data:
            belief_session.updated_at = datetime.fromisoformat(session_data['updated_at'])
        if 'completed_at' in session_data and session_data['completed_at']:
            belief_session.completed_at = datetime.fromisoformat(session_data['completed_at'])
    
    # Go back to the previous step
    went_back = belief_session.go_back()
    
    # Save the updated session
    save_success = save_belief_session(belief_session)
    
    if not save_success:
        return jsonify({'error': 'Failed to save session update'}), 500
    
    # Update browser session storage
    browser_sessions[belief_session.belief_session_id] = belief_session.to_dict()
    session['belief_sessions'] = browser_sessions
    session.modified = True
    
    return jsonify({
        'success': True,
        'went_back': went_back,
        'session': belief_session.to_dict()
    })

@app.route('/belief-change')
@require_professional
def belief_change_page():
    """
    Render the belief change protocol page.
    """
    return render_template('belief_change.html')

@app.route('/belief-change/session/<session_id>')
def belief_session_page(session_id):
    """
    Render the specific belief change session page.
    """
    # Try to get from browser session first
    browser_sessions = session.get('belief_sessions', {})
    
    if session_id in browser_sessions:
        session_data = browser_sessions[session_id]
        return render_template('belief_session.html', session=session_data)
    
    # If not in browser session, try to get from database
    belief_session = get_belief_session(session_id)
    
    if not belief_session:
        flash('Belief change session not found', 'danger')
        return redirect(url_for('belief_change_page'))
    
    return render_template('belief_session.html', session=belief_session.to_dict())


# Administrative route for development testing
@app.route('/admin/enable-professional')
@require_login
def admin_enable_professional():
    """
    Developer route to set the current user to have a Professional subscription.
    This is for testing purposes only.
    """
    from datetime import datetime, timedelta
    
    # Debug information
    app.logger.debug(f"Admin route accessed by user ID: {current_user.id}")
    
    # Check if user already has a subscription
    subscription = Subscription.query.filter_by(user_id=current_user.id).first()
    
    current_time = datetime.utcnow()
    one_year_later = current_time + timedelta(days=365)
    
    try:
        if not subscription:
            # Create a new subscription
            subscription = Subscription(
                user_id=current_user.id,
                stripe_customer_id=f"dev_customer_{current_user.id}",
                stripe_subscription_id=f"dev_subscription_{current_user.id}",
                plan_name='professional',
                status='active',
                current_period_start=current_time,
                current_period_end=one_year_later
            )
            db.session.add(subscription)
            app.logger.debug("Created new subscription")
        else:
            # Update existing subscription
            subscription.plan_name = 'professional'
            subscription.status = 'active'
            subscription.current_period_start = current_time
            subscription.current_period_end = one_year_later
            app.logger.debug("Updated existing subscription")
        
        db.session.commit()
        app.logger.debug("Committed subscription changes to database")
        
        flash("Professional subscription enabled for your account.", "success")
        return redirect(url_for('profile'))
    except Exception as e:
        app.logger.error(f"Error setting professional subscription: {str(e)}")
        db.session.rollback()
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('profile'))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
