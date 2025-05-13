import os
import uuid
import json
import time
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, flash, redirect, url_for, g
from typing import Dict, Any, Optional, Union, List, Tuple
from flask_login import current_user, login_required, logout_user, login_user
from openai import OpenAI
import stripe
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy.exc import SQLAlchemyError

# Import email authentication modules
from forms import (
    LoginForm, RegistrationForm, RequestResetForm, ResetPasswordForm,
    DeleteAccountForm, ChangePasswordForm, ResendVerificationForm, PrivacySettingsForm
)
from email_auth import (
    register_user, verify_email, login_with_email, request_password_reset, reset_password,
    delete_account, regenerate_verification_token
)
from email_service import send_verification_email, send_password_reset_email

# Import conversation context management
from conversation_context import (
    get_or_create_context,
    create_new_context, 
    add_message_to_context, 
    enhance_prompt_with_context,
    update_context_summary,
    consolidate_memories,
    get_context_messages
)

# Import models
from models import ChatHistory, Subscription
from typing import TYPE_CHECKING, cast

# Type checking imports
if TYPE_CHECKING:
    from models import NLPExercise

# Import standardized logging
from logging_config import get_logger, info, error, debug, warning, critical, exception

# Get module-specific logger
logger = get_logger('app')

# Helper function to safely extract JSON from request
def get_request_json() -> Dict[str, Any]:
    """
    Safely extract JSON data from request.
    Returns an empty dict if request.json is None.
    This helps with LSP type checking issues.
    """
    return request.json or {}

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
# Logging is configured in logging_config.py

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

# Run database migrations
with app.app_context():
    # Create all tables defined in models
    db.create_all()
    logger.info("Created database tables")
    
    # Import and run the database schema update
    from db_init import update_database_schema
    update_database_schema()
    logger.info("Updated database schema")

# Initialize login manager and replit auth after db init
from replit_auth import make_replit_blueprint, require_login

# Subscription access decorators
def require_premium(f):
    """
    Decorator to require premium or professional subscription.
    
    This decorator checks if the current user has access to premium features
    before allowing access to the decorated route.
    
    If the user is not authenticated, they will be redirected to login.
    If the user is authenticated but doesn't have premium access, they
    will be redirected to the landing page with subscription options.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated
        if not current_user.is_authenticated:
            info(f"Unauthenticated user attempted to access premium feature: {request.path}")
            session["next_url"] = request.url
            flash("Please log in to access this feature.", "info")
            return redirect(url_for('replit_auth.login'))
            
        # Import subscription manager
        from subscription_manager import check_feature_access, get_subscription_details
        
        user_id = current_user.id
        feature_name = 'advanced_nlp'  # Key feature that determines premium access
        
        # Log the access attempt
        info(f"User {user_id} attempting to access premium feature: {request.path}")
        
        # Get subscription details for better error messages
        try:
            subscription = get_subscription_details(user_id)
            current_plan = subscription.get('plan_name', 'free')
            info(f"User {user_id} has '{current_plan}' subscription")
        except Exception as e:
            error(f"Error retrieving subscription details: {str(e)}")
            current_plan = 'unknown'
        
        # Check if user has premium or professional subscription
        has_access = False
        try:
            # Check if user has access to premium features
            has_access = check_feature_access(user_id, feature_name)
            info(f"Feature access check for {feature_name}: {has_access}")
        except Exception as e:
            error(f"Error checking premium access for user {user_id}: {str(e)}")
            
        if not has_access:
            warning(f"User {user_id} with {current_plan} plan denied access to premium feature: {request.path}")
            message = g.translate('premium_required', 
                "This feature requires a Premium subscription. Please upgrade your plan to access advanced features.")
            flash(message, "warning")
            return redirect(url_for('landing'))
        
        # User has access, proceed with the route    
        info(f"User {user_id} granted access to premium feature: {request.path}")
        return f(*args, **kwargs)
    
    return decorated_function


def require_professional(f):
    """
    Decorator to require professional subscription.
    
    This decorator checks if the current user has access to professional features
    before allowing access to the decorated route.
    
    If the user is not authenticated, they will be redirected to login.
    If the user is authenticated but doesn't have professional access, they
    will be redirected to the landing page with subscription options.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated
        if not current_user.is_authenticated:
            info(f"Unauthenticated user attempted to access professional feature: {request.path}")
            session["next_url"] = request.url
            flash("Please log in to access this feature.", "info")
            return redirect(url_for('replit_auth.login'))
            
        # Import subscription manager
        from subscription_manager import check_feature_access, get_subscription_details
        
        user_id = current_user.id
        feature_name = 'personalized_journeys'  # Key feature that determines professional access
        
        # Log the access attempt
        info(f"User {user_id} attempting to access professional feature: {request.path}")
        
        # Get subscription details for better error messages
        try:
            subscription = get_subscription_details(user_id)
            current_plan = subscription.get('plan_name', 'free')
            info(f"User {user_id} has '{current_plan}' subscription")
        except Exception as e:
            error(f"Error retrieving subscription details: {str(e)}")
            current_plan = 'unknown'
        
        # Check if user has professional subscription
        has_access = False
        try:
            # Check if user has access to professional features
            has_access = check_feature_access(user_id, feature_name)
            info(f"Feature access check for {feature_name}: {has_access}")
        except Exception as e:
            error(f"Error checking professional access for user {user_id}: {str(e)}")
            
        if not has_access:
            warning(f"User {user_id} with {current_plan} plan denied access to professional feature: {request.path}")
            message = g.translate('professional_required', 
                "This feature requires a Professional subscription. Please upgrade your plan to access our most advanced features.")
            flash(message, "warning")
            return redirect(url_for('landing'))
        
        # User has access, proceed with the route    
        info(f"User {user_id} granted access to professional feature: {request.path}")
        return f(*args, **kwargs)
    
    return decorated_function
app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")

# Import models
from models import User, ChatHistory, JournalEntry, NLPExercise, NLPExerciseProgress, TechniqueEffectiveness, TechniqueUsageStats, Subscription, UsageQuota

# Create database tables
with app.app_context():
    db.create_all()
    info("Database tables created")
    
    # Initialize subscription manager
    try:
        import subscription_manager
        # Initialize subscription manager with database and models
        subscription_manager.init_db(db)
        subscription_manager.init_models(User, Subscription, UsageQuota)
        info("Subscription manager initialized")
    except Exception as e:
        error(f"Error initializing subscription manager: {str(e)}")
        exception("Full traceback for subscription manager initialization error:")

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Request middleware
@app.before_request
def before_request():
    # Make session permanent
    session.permanent = True
    
    # Create session ID if one doesn't exist
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
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
    
    # Auth provider integration
    if current_user.is_authenticated:
        # Import User model only when needed (to avoid circular imports)
        from models import User
            
        # Store the auth provider used for this session
        if 'auth_provider' not in session:
            session['auth_provider'] = current_user.auth_provider
            
        # Add account linking suggestions for better user experience
        try:
            # Handle Replit auth users who might have an existing email account
            if current_user.auth_provider == 'replit_auth' and current_user.email:
                email_user = User.query.filter_by(
                    email=current_user.email, 
                    auth_provider='email'
                ).first()
                
                if email_user and 'shown_auth_link_message' not in session:
                    flash('We noticed you have logged in with Replit, but you also have an email account with us. ' +
                         'You can <a href="' + url_for('account_linking_route') + '">link these accounts</a> for a seamless experience.', 'info')
                    session['shown_auth_link_message'] = True
                    
            # Handle email auth users who might have an existing Replit account
            elif current_user.auth_provider == 'email':
                replit_user = User.query.filter_by(
                    email=current_user.email, 
                    auth_provider='replit_auth'
                ).first()
                
                if replit_user and 'shown_auth_link_message' not in session:
                    flash('We noticed you have logged in with email, but you also have a Replit account with us. ' +
                         'You can <a href="' + url_for('account_linking_route') + '">link these accounts</a> for a seamless experience.', 'info')
                    session['shown_auth_link_message'] = True
        except Exception as e:
            # Don't interrupt the user experience if this fails
            # Use app.logger instead of separate logger import
            app.logger.error(f"Error in auth provider integration: {str(e)}")
            
    # This helps with CSRF protection across auth methods
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(16)
        
    # Add csrf_token to all templates
    g.csrf_token = session.get('csrf_token', '')


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
    
    # Not logged in, proceed to email login by default
    return redirect(url_for('email_login'))


# User Profile route
@app.route('/profile')
@require_login
def profile():
    """
    User profile page.
    """
    try:
        # Get subscription info using the subscription manager
        from subscription_manager import get_subscription_details
        
        # Get detailed subscription information
        subscription_details = get_subscription_details(current_user.id)
        
        # Format for template display
        subscription_info = {
            'plan_name': subscription_details['plan_name'].capitalize(),
            'status': subscription_details['status'],
            'current_period_end': subscription_details.get('current_period_end'),
            'features': [],
            'available_plans': [
                {
                    'name': 'Premium',
                    'price': '$9.99/month',
                    'description': 'All NLP techniques, unlimited chats, and progress tracking',
                    'plan_id': 'premium'
                },
                {
                    'name': 'Professional',
                    'price': '$19.99/month',
                    'description': 'Everything in Premium plus voice features, personalized journeys, and more',
                    'plan_id': 'professional'
                }
            ]
        }
        
        # Format features for display
        for feature in subscription_details['features']:
            # Convert snake_case to readable text
            readable_feature = feature.replace('_', ' ').title()
            subscription_info['features'].append(readable_feature)
        
        # Safely handle stats with error catching for type mismatches
        try:
            # Get user stats
            exercise_count = NLPExerciseProgress.query.filter_by(
                user_id=current_user.id, 
                completed=True
            ).count()
        except (ValueError, TypeError, SQLAlchemyError) as e:
            error(f"Error getting exercise count: {str(e)}")
            exercise_count = 0
        
        try:
            # Get unique techniques used
            techniques = TechniqueEffectiveness.query.filter_by(
                user_id=current_user.id
            ).with_entities(TechniqueEffectiveness.technique).distinct().count()
        except (ValueError, TypeError, SQLAlchemyError) as e:
            error(f"Error getting technique count: {str(e)}")
            techniques = 0
            
        # Get recent activity with error handling
        activity = []
        
        try:
            # Get recent activity (last 5 items)
            recent_chats = ChatHistory.query.filter_by(
                user_id=current_user.id
            ).order_by(ChatHistory.created_at.desc()).limit(3).all()
            
            for chat in recent_chats:
                activity.append({
                    'title': 'Chat Interaction',
                    'description': f"Used technique: {chat.nlp_technique or 'None'}",
                    'date': chat.created_at.strftime('%b %d, %Y')
                })
        except (ValueError, TypeError, SQLAlchemyError) as e:
            error(f"Error getting recent chats: {str(e)}")
        
        try:
            recent_exercises = NLPExerciseProgress.query.filter_by(
                user_id=current_user.id
            ).order_by(NLPExerciseProgress.started_at.desc()).limit(2).all()
            
            for ex in recent_exercises:
                status = "Completed" if ex.completed else f"In Progress (Step {ex.current_step})"
                exercise = NLPExercise.query.get(ex.exercise_id)
                if exercise:
                    activity.append({
                        'title': f"Exercise: {exercise.title}",
                        'description': f"Status: {status}",
                        'date': ex.started_at.strftime('%b %d, %Y')
                    })
        except (ValueError, TypeError, SQLAlchemyError) as e:
            error(f"Error getting recent exercises: {str(e)}")
        
        # Sort by date (newest first)
        if activity:
            activity.sort(key=lambda x: x['date'], reverse=True)
        
        return render_template(
            'profile.html',
            exercise_count=exercise_count,
            technique_count=techniques,
            recent_activity=activity,
            subscription=subscription_info,
            show_upgrade=True
        )
    
    except Exception as e:
        error_type = type(e).__name__
        error(f"Profile page error ({error_type}): {str(e)}")
        return render_template(
            'profile.html',
            error=True,
            error_message=str(e),
            subscription={
                'plan_name': current_user.subscription_plan or 'Free',
                'status': 'active',
                'features': [],
                'available_plans': [
                    {
                        'name': 'Premium',
                        'price': '$9.99/month',
                        'description': 'All NLP techniques, unlimited chats, and progress tracking',
                        'plan_id': 'premium'
                    },
                    {
                        'name': 'Professional',
                        'price': '$19.99/month',
                        'description': 'Everything in Premium plus voice features, personalized journeys, and more',
                        'plan_id': 'professional'
                    }
                ]
            },
            show_upgrade=True
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

# Account Management Routes
@app.route('/delete-account', methods=['GET', 'POST'])
@require_login
def delete_account_route():
    """
    Handle account deletion.
    Permanently deletes the user's account and associated data in a GDPR-compliant way.
    """
    form = DeleteAccountForm()
    
    if form.validate_on_submit():
        success = False
        
        if current_user.auth_provider == 'email':
            # Verify password for email users
            success = delete_account(current_user.id, form.password.data)
        else:
            # No password verification needed for Replit auth users
            success = delete_account(current_user.id)
            
        if success:
            # Account deleted, show message on landing page
            flash('Your account has been permanently deleted. We\'re sorry to see you go!', 'info')
            return redirect(url_for('landing'))
        else:
            flash('Failed to delete account. Please try again or contact support.', 'danger')
    
    return render_template('delete_account.html', form=form)

@app.route('/change-password', methods=['GET', 'POST'])
@require_login
def change_password_route():
    """
    Handle password change for email-authenticated users.
    """
    # Only available for email-authenticated users
    if current_user.auth_provider != 'email':
        flash('Password change is only available for email accounts.', 'warning')
        return redirect(url_for('profile'))
    
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        # Verify current password
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return render_template('change_password.html', form=form)
        
        # Update password
        current_user.set_password(form.new_password.data)
        db.session.commit()
        
        flash('Your password has been updated successfully.', 'success')
        return redirect(url_for('profile'))
    
    return render_template('change_password.html', form=form)

@app.route('/resend-verification', methods=['GET', 'POST'])
@require_login
def resend_verification_route():
    """
    Resend email verification link.
    """
    # Only available for unverified email-authenticated users
    if current_user.auth_provider != 'email' or current_user.email_verified:
        flash('Email verification is not needed for your account.', 'info')
        return redirect(url_for('profile'))
    
    form = ResendVerificationForm()
    
    if form.validate_on_submit():
        # Generate new verification token
        user, token = regenerate_verification_token(current_user.id)
        
        if user and token:
            # Send verification email
            base_url = request.host_url.rstrip('/')
            email_sent = send_verification_email(user, token, base_url)
            
            if email_sent:
                flash('A new verification email has been sent. Please check your inbox.', 'success')
            else:
                flash('Failed to send verification email. Please try again later.', 'danger')
                
            return redirect(url_for('profile'))
    
    return render_template('resend_verification.html', form=form)


@app.route('/account-linking')
@require_login
def account_linking_route():
    """
    Show account linking options for users with multiple auth methods.
    """
    # Import User model here to avoid circular imports
    from models import User
    
    # Detect other accounts with the same email
    other_auth_found = False
    
    if current_user.email:
        if current_user.auth_provider == 'replit_auth':
            # Check if email account exists
            email_user = User.query.filter_by(
                email=current_user.email, 
                auth_provider='email'
            ).first()
            other_auth_found = email_user is not None
        elif current_user.auth_provider == 'email':
            # Check if replit account exists
            replit_user = User.query.filter_by(
                email=current_user.email, 
                auth_provider='replit_auth'
            ).first()
            other_auth_found = replit_user is not None
    
    # If no other auth method found, show message and redirect
    if not other_auth_found:
        flash('No other accounts found with this email address.', 'info')
        return redirect(url_for('profile'))
        
    return render_template('account_linking.html')


@app.route('/link-email-account', methods=['POST'])
@require_login
def link_email_account():
    """
    Link a Replit account to an existing email account.
    For users logged in with Replit auth who want to link an email account.
    """
    # This route is only for Replit auth users
    if current_user.auth_provider != 'replit_auth':
        flash('This feature is only available for Replit login users.', 'info')
        return redirect(url_for('profile'))
    
    # Check CSRF token
    if request.form.get('csrf_token') != session.get('csrf_token'):
        flash('Invalid request. Please try again.', 'danger')
        return redirect(url_for('account_linking_route'))
    
    # Get password from form
    password = request.form.get('password')
    
    if not password:
        flash('Password is required.', 'danger')
        return redirect(url_for('account_linking_route'))
        
    # Import here to avoid circular imports
    from models import User
    
    try:
        # Find the email account with the same email
        email_user = User.query.filter_by(
            email=current_user.email, 
            auth_provider='email'
        ).first()
        
        if not email_user:
            flash('No matching email account found.', 'danger')
            return redirect(url_for('account_linking_route'))
            
        # Verify password
        if not email_user.check_password(password):
            flash('Incorrect password.', 'danger')
            return redirect(url_for('account_linking_route'))
            
        # Link accounts by merging data
        # This is a simple approach - a more complex implementation would
        # need to merge all user data, subscriptions, etc.
        
        # For demo purposes, we'll transfer the Replit user's data to the email user
        # and then use the email user going forward
        
        # Log in as the email user instead
        login_user(email_user)
        flash('Accounts linked successfully! You are now logged in with your email account.', 'success')
        
        # Update session
        session['auth_provider'] = 'email'
        
        return redirect(url_for('profile'))
        
    except Exception as e:
        app.logger.error(f"Error linking accounts: {str(e)}")
        flash('An error occurred while linking accounts. Please try again later.', 'danger')
        return redirect(url_for('account_linking_route'))
        
        
@app.route('/link-replit-account')
@require_login
def link_replit_account():
    """
    Handle linking a Replit account to an email account.
    This is part 1 - redirect to Replit OAuth flow.
    """
    # Only for email auth users
    if current_user.auth_provider != 'email':
        flash('This feature is only available for email login users.', 'info')
        return redirect(url_for('profile'))
    
    # Store a flag in the session to indicate we're doing account linking
    session['linking_accounts'] = True
    session['original_user_id'] = current_user.id
    
    # Redirect to Replit OAuth login
    return redirect(url_for('replit_auth.login'))


@app.route('/complete-account-linking')
@require_login
def complete_account_linking():
    """
    Complete the account linking process after Replit OAuth.
    This is part 2 - run when user returns from Replit OAuth.
    """
    # Check if we're in the process of linking accounts
    if not session.get('linking_accounts') or not session.get('original_user_id'):
        flash('Account linking process was not initiated correctly.', 'warning')
        return redirect(url_for('profile'))
    
    try:
        from models import User
        
        # Get the original email user
        original_user_id = session.get('original_user_id')
        email_user = User.query.get(original_user_id)
        
        if not email_user or email_user.auth_provider != 'email':
            flash('Original email account not found.', 'danger')
            return redirect(url_for('profile'))
            
        # Check that the email matches
        if email_user.email != current_user.email:
            flash('The email addresses do not match. Account linking failed.', 'danger')
            # Log the user back in as the email user
            login_user(email_user)
            
            # Clean up session
            session.pop('linking_accounts', None)
            session.pop('original_user_id', None)
            return redirect(url_for('profile'))
            
        # Successful linking - log the user back in as their email account
        login_user(email_user)
        flash('Your Replit account has been successfully linked!', 'success')
        
        # Update session state
        session['auth_provider'] = 'email'
        session.pop('linking_accounts', None)
        session.pop('original_user_id', None)
        
        return redirect(url_for('profile'))
        
    except Exception as e:
        app.logger.error(f"Error completing account linking: {str(e)}")
        flash('An error occurred while linking accounts. Please try again later.', 'danger')
        
        # Clean up session
        session.pop('linking_accounts', None)
        session.pop('original_user_id', None)
        return redirect(url_for('profile'))

@app.route('/privacy-settings', methods=['GET', 'POST'])
@require_login
def privacy_settings_route():
    """
    View and update privacy settings.
    """
    # Import the models in the function to avoid circular imports
    from models import PrivacySettings, OAuth
    
    # Get or create privacy settings
    privacy_settings = current_user.privacy_settings
    
    if not privacy_settings:
        # Create default privacy settings with explicit field assignment
        privacy_settings = PrivacySettings()
        privacy_settings.user_id = current_user.id
        privacy_settings.data_collection = True
        privacy_settings.progress_tracking = True
        privacy_settings.personalization = True
        privacy_settings.email_notifications = True
        privacy_settings.marketing_emails = False
        db.session.add(privacy_settings)
        db.session.commit()
    
    # Get active login sessions for this user
    active_sessions = []
    if current_user.auth_provider == 'replit_auth':
        try:
            # For Replit auth users, get active OAuth sessions
            sessions = OAuth.query.filter_by(user_id=current_user.id).all()
            for session_obj in sessions:
                # Extract information if available
                last_used = session_obj.created_at if hasattr(session_obj, 'created_at') else datetime.now() 
                
                active_sessions.append({
                    'id': session_obj.browser_session_key,
                    'provider': session_obj.provider,
                    'last_used': last_used,
                    'is_current': session_obj.browser_session_key == g.get('browser_session_key', '')
                })
        except Exception as e:
            app.logger.error(f"Error retrieving active sessions: {str(e)}")
    
    form = PrivacySettingsForm()
    
    if form.validate_on_submit():
        # Update privacy settings
        privacy_settings.data_collection = form.data_collection.data
        privacy_settings.progress_tracking = form.progress_tracking.data
        privacy_settings.personalization = form.personalization.data
        privacy_settings.email_notifications = form.email_notifications.data
        privacy_settings.marketing_emails = form.marketing_emails.data
        
        db.session.commit()
        
        flash('Your privacy settings have been updated.', 'success')
        return redirect(url_for('privacy_settings_route'))
    elif request.method == 'GET':
        # Populate form with current settings
        form.data_collection.data = privacy_settings.data_collection
        form.progress_tracking.data = privacy_settings.progress_tracking
        form.personalization.data = privacy_settings.personalization
        form.email_notifications.data = privacy_settings.email_notifications
        form.marketing_emails.data = privacy_settings.marketing_emails
    
    return render_template('privacy_settings.html', form=form, privacy_settings=privacy_settings, 
                          active_sessions=active_sessions)


@app.route('/revoke-session/<session_id>', methods=['POST'])
@require_login
def revoke_session(session_id):
    """
    Revoke a specific login session.
    """
    if not current_user.auth_provider == 'replit_auth':
        flash('Session management is only available for Replit login users.', 'info')
        return redirect(url_for('privacy_settings_route'))
    
    if not session_id:
        flash('Invalid session ID.', 'danger')
        return redirect(url_for('privacy_settings_route'))
    
    # Make sure we don't revoke the current session
    if session_id == g.get('browser_session_key', ''):
        flash('You cannot revoke your current session.', 'warning')
        return redirect(url_for('privacy_settings_route'))
        
    try:
        # Import here to avoid circular imports
        from models import OAuth
        
        # Delete the session
        result = OAuth.query.filter_by(
            user_id=current_user.id,
            browser_session_key=session_id
        ).delete()
        
        db.session.commit()
        
        if result:
            flash('Session has been revoked successfully.', 'success')
        else:
            flash('No matching session found.', 'warning')
            
    except Exception as e:
        app.logger.error(f"Error revoking session: {str(e)}")
        db.session.rollback()
        flash('An error occurred while revoking the session.', 'danger')
        
    return redirect(url_for('privacy_settings_route'))

@app.route('/export-data')
@require_login
def export_data_route():
    """
    Export user data in a machine-readable format (JSON).
    
    This exports ALL data associated with the user account.
    For more selective chat history exports, use export_history_route.
    """
    # Collect user data
    user_data = {
        'user': {
            'id': current_user.id,
            'email': current_user.email,
            'first_name': current_user.first_name,
            'last_name': current_user.last_name,
            'auth_provider': current_user.auth_provider,
            'created_at': current_user.created_at.isoformat() if current_user.created_at else None
        },
        'chats': [],
        'exercises': [],
        'technique_ratings': []
    }
    
    # Add chat history with null handling
    for chat in current_user.chats.all():
        chat_entry = {
            'id': chat.id,
            'session_id': getattr(chat, 'session_id', None),
            'user_message': getattr(chat, 'user_message', None),
            'ai_response': getattr(chat, 'ai_response', None),
            'nlp_technique': getattr(chat, 'nlp_technique', None),
            'mood': getattr(chat, 'mood', None),
            'created_at': chat.created_at.isoformat() if getattr(chat, 'created_at', None) else None
        }
        user_data['chats'].append(chat_entry)
    
    # Add exercise progress with null handling
    for progress in current_user.exercise_progress.all():
        progress_entry = {
            'id': progress.id,
            'exercise_id': getattr(progress, 'exercise_id', None),
            'completed': getattr(progress, 'completed', False),
            'current_step': getattr(progress, 'current_step', 0),
            'notes': getattr(progress, 'notes', None),
            'started_at': progress.started_at.isoformat() if getattr(progress, 'started_at', None) else None,
            'completed_at': progress.completed_at.isoformat() if getattr(progress, 'completed_at', None) else None
        }
        user_data['exercises'].append(progress_entry)
    
    # Add technique ratings with null handling
    for rating in current_user.technique_ratings.all():
        rating_entry = {
            'id': rating.id,
            'technique': getattr(rating, 'technique', None),
            'rating': getattr(rating, 'rating', None),
            'notes': getattr(rating, 'notes', None),
            'situation': getattr(rating, 'situation', None),
            'entry_date': rating.entry_date.isoformat() if getattr(rating, 'entry_date', None) else None
        }
        user_data['technique_ratings'].append(rating_entry)
    
    # Create response with appropriate headers
    response = jsonify(user_data)
    response.headers['Content-Disposition'] = f'attachment; filename=inner_architect_data_{current_user.id}.json'
    return response


@app.route('/export-history')
@require_login
def export_history_route():
    """
    View and export chat history with formatting options.
    
    Supports filtering by date range and exporting in multiple formats:
    - TXT (plain text)
    - CSV (comma-separated values)
    - JSON (JavaScript Object Notation)
    - PDF (Portable Document Format)
    """
    from datetime import datetime
    from models import ChatHistory
    from flask import Response
    
    # Parse filter parameters
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    export_format = request.args.get('format', None)  # If set, triggers an export
    
    # Convert date strings to datetime objects
    start_date = None
    end_date = None
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid start date format. Please use YYYY-MM-DD.', 'warning')
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            # Set time to end of day for inclusive filtering
            end_date = end_date.replace(hour=23, minute=59, second=59)
        except ValueError:
            flash('Invalid end date format. Please use YYYY-MM-DD.', 'warning')
    
    # Build query with filters
    query = ChatHistory.query.filter_by(user_id=current_user.id)
    
    if start_date:
        query = query.filter(ChatHistory.created_at >= start_date)
    
    if end_date:
        query = query.filter(ChatHistory.created_at <= end_date)
    
    # Get total count for pagination info
    total_count = query.count()
    
    # Limit results for preview to avoid overwhelming the page
    chat_history = query.order_by(ChatHistory.created_at.desc()).limit(25).all()
    
    # If an export format is specified, generate the export file
    if export_format:
        return generate_export(query.all(), export_format, start_date, end_date)
    
    # Otherwise render the export page with preview
    return render_template(
        'export_history.html',
        chat_history=chat_history,
        total_count=total_count
    )


def generate_export(chats, format_type, start_date=None, end_date=None):
    """
    Generate an export file of chat history in the specified format.
    
    Args:
        chats: List of ChatHistory objects
        format_type: Export format (txt, csv, json, pdf)
        start_date: Optional start date for filename
        end_date: Optional end date for filename
        
    Returns:
        Flask response with the exported file
    """
    from flask import Response, jsonify
    
    # Generate filename with date range if provided
    date_suffix = ""
    if start_date and end_date:
        date_suffix = f"_{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}"
    elif start_date:
        date_suffix = f"_{start_date.strftime('%Y%m%d')}-present"
    elif end_date:
        date_suffix = f"_until-{end_date.strftime('%Y%m%d')}"
        
    filename = f"chat_history{date_suffix}"
    
    # Export based on requested format
    if format_type == 'txt':
        return export_as_txt(chats, filename)
    elif format_type == 'csv':
        return export_as_csv(chats, filename)
    elif format_type == 'json':
        return export_as_json(chats, filename)
    elif format_type == 'pdf':
        return export_as_pdf(chats, filename)
    else:
        flash(f'Unsupported export format: {format_type}', 'danger')
        return redirect(url_for('export_history_route'))


def export_as_txt(chats, filename):
    """Export chat history as a plain text file."""
    from flask import Response
    
    lines = []
    lines.append("THE INNER ARCHITECT - CHAT HISTORY EXPORT")
    lines.append("=" * 50)
    lines.append("")
    
    for chat in chats:
        lines.append(f"Date: {chat.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Technique: {chat.nlp_technique or 'None'}")
        lines.append(f"Mood: {chat.mood or 'Not specified'}")
        lines.append("-" * 50)
        lines.append("You:")
        lines.append(chat.user_message)
        lines.append("")
        lines.append("Inner Architect:")
        lines.append(chat.ai_response)
        lines.append("=" * 50)
        lines.append("")
    
    text_content = "\n".join(lines)
    
    response = Response(text_content, mimetype='text/plain')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}.txt'
    return response


def export_as_csv(chats, filename):
    """Export chat history as a CSV file."""
    import csv
    from io import StringIO
    from flask import Response
    
    output = StringIO()
    csv_writer = csv.writer(output)
    
    # Write header
    csv_writer.writerow(['Date', 'Technique', 'Mood', 'Your Message', 'AI Response'])
    
    # Write chat data
    for chat in chats:
        csv_writer.writerow([
            chat.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            chat.nlp_technique or '',
            chat.mood or '',
            chat.user_message,
            chat.ai_response
        ])
    
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}.csv'
    return response


def export_as_json(chats, filename):
    """Export chat history as a JSON file."""
    from flask import jsonify
    
    chat_data = []
    
    for chat in chats:
        chat_data.append({
            'date': chat.created_at.isoformat(),
            'technique': chat.nlp_technique,
            'mood': chat.mood,
            'user_message': chat.user_message,
            'ai_response': chat.ai_response
        })
    
    response = jsonify(chat_data)
    response.headers['Content-Disposition'] = f'attachment; filename={filename}.json'
    return response


def export_as_pdf(chats, filename):
    """Export chat history as a PDF file."""
    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from flask import Response
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title="Chat History")
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Create custom styles
    styles.add(ParagraphStyle(
        name='UserMessage',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
    ))
    
    styles.add(ParagraphStyle(
        name='AIResponse',
        parent=styles['Normal'],
        leftIndent=20,
    ))
    
    # Build document content
    content = []
    
    # Add title
    content.append(Paragraph("The Inner Architect - Chat History", title_style))
    content.append(Spacer(1, 12))
    
    # Add chat entries
    for chat in chats:
        # Add date and metadata
        date_str = chat.created_at.strftime('%Y-%m-%d %H:%M:%S')
        content.append(Paragraph(f"Date: {date_str}", heading_style))
        
        # Add technique and mood
        meta_data = [
            ["Technique:", chat.nlp_technique or "None"],
            ["Mood:", chat.mood or "Not specified"]
        ]
        meta_table = Table(meta_data, colWidths=[80, 400])
        meta_table.setStyle(TableStyle([
            ('TEXTCOLOR', (0, 0), (0, -1), colors.gray),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        content.append(meta_table)
        content.append(Spacer(1, 6))
        
        # Add user message
        content.append(Paragraph("You:", styles['UserMessage']))
        content.append(Paragraph(chat.user_message.replace('\n', '<br/>'), normal_style))
        content.append(Spacer(1, 6))
        
        # Add AI response
        content.append(Paragraph("Inner Architect:", styles['UserMessage']))
        content.append(Paragraph(chat.ai_response.replace('\n', '<br/>'), styles['AIResponse']))
        
        # Add separator
        content.append(Spacer(1, 12))
        content.append(Paragraph("_" * 65, normal_style))
        content.append(Spacer(1, 12))
    
    # Build PDF
    doc.build(content)
    
    # Prepare response
    pdf_data = buffer.getvalue()
    buffer.close()
    
    response = Response(pdf_data, mimetype='application/pdf')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}.pdf'
    return response

# Email Authentication Routes
@app.route('/email-login', methods=['GET', 'POST'])
def email_login():
    """
    Handle email-based login.
    """
    # If user is already logged in, redirect to index
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    form = LoginForm()
    
    if form.validate_on_submit():
        user = login_with_email(form.email.data, form.password.data, form.remember_me.data)
        
        if user:
            # Set session ID for the user if it doesn't exist
            if 'session_id' not in session:
                session['session_id'] = str(uuid.uuid4())
                
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Login failed. Please check your email and password.', 'danger')
            
    return render_template('email_login.html', form=form)

@app.route('/email-register', methods=['GET', 'POST'])
def email_register():
    """
    Handle email-based registration.
    """
    # If user is already logged in, redirect to index
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    form = RegistrationForm()
    
    if form.validate_on_submit():
        user, token = register_user(
            form.email.data,
            form.password.data,
            form.first_name.data,
            form.last_name.data
        )
        
        if user and token:
            # Send verification email
            base_url = request.host_url.rstrip('/')
            email_sent = send_verification_email(user, token, base_url)
            
            if email_sent:
                flash('Your account has been created! Please check your email to verify your account.', 'success')
            else:
                # For development, allow login without verification
                flash('Your account has been created! Email verification is currently unavailable, but you can still log in.', 'warning')
                # In development, auto-verify the email
                user.email_verified = True
                db.session.commit()
                
            return redirect(url_for('email_login'))
        else:
            flash('Registration failed. Please try again.', 'danger')
            
    return render_template('email_register.html', form=form)

@app.route('/verify-email/<token>')
def verify_email_route(token):
    """
    Verify a user's email address.
    """
    if verify_email(token):
        flash('Your email has been verified! You can now log in.', 'success')
    else:
        flash('The verification link is invalid or has expired.', 'danger')
        
    return redirect(url_for('email_login'))

@app.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    """
    Handle password reset requests.
    """
    # If user is already logged in, redirect to index
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    form = RequestResetForm()
    
    if form.validate_on_submit():
        # Form validation should ensure email is not None
        # WTForms EmailField validator will ensure this is a valid email
        email = form.email.data or ""
        email = email.strip().lower()  # Normalize email
        user, token = request_password_reset(email)
        
        if user and token:
            try:
                # Send password reset email
                base_url = request.host_url.rstrip('/')
                email_sent = send_password_reset_email(user, token, base_url)
                
                if email_sent:
                    app.logger.info(f"Password reset email sent to {user.email}")
                    flash('An email has been sent with instructions to reset your password. Please check your inbox.', 'info')
                else:
                    app.logger.error(f"Failed to send password reset email to {user.email}")
                    flash('We could not send the reset email at this time. Please try again later.', 'warning')
                
                # Don't reveal whether a user with this email exists or not
                # Always show success message even if sending fails to avoid email enumeration
                return redirect(url_for('email_login'))
            except Exception as e:
                app.logger.error(f"Error sending password reset email: {str(e)}")
                app.logger.exception("Full exception details:")
                flash('An error occurred while processing your request. Please try again later.', 'danger')
        else:
            # Generic message - don't reveal whether this email exists in system
            app.logger.info(f"Password reset requested for non-existent or non-email user: {email}")
            flash('If your email is registered with us, you will receive a reset link shortly.', 'info')
            return redirect(url_for('email_login'))
            
    return render_template('reset_password_request.html', form=form)

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password_route(token):
    """
    Handle password reset form.
    """
    # If user is already logged in, redirect to index
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    # Validate token format before processing
    if not token or len(token) != 64:
        flash('Invalid reset link. Please request a new one.', 'danger')
        return redirect(url_for('reset_password_request'))
        
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        try:
            if reset_password(token, form.password.data):
                app.logger.info(f"Password reset successfully completed for token: {token[:6]}...")
                flash('Your password has been reset! You can now log in with your new password.', 'success')
                return redirect(url_for('email_login'))
            else:
                app.logger.warning(f"Password reset failed for token: {token[:6]}...")
                flash('The reset link is invalid or has expired. Please request a new one.', 'danger')
                return redirect(url_for('reset_password_request'))
        except Exception as e:
            app.logger.error(f"Error during password reset: {str(e)}")
            app.logger.exception("Full exception details:")
            flash('An error occurred while processing your request. Please try again later.', 'danger')
            return redirect(url_for('reset_password_request'))
            
    return render_template('reset_password.html', form=form, token=token)

@app.route('/email-logout')
def email_logout():
    """
    Handle email-based logout.
    """
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('landing'))


# Checkout route for subscription plans
@app.route('/checkout/<plan>')
@require_login
def create_checkout(plan):
    """
    Create a Stripe checkout session for subscription plans.
    
    Args:
        plan (str): The subscription plan ('premium' or 'professional')
    """
    from subscription_manager import create_stripe_checkout_session
    
    # Check if Stripe API key is configured
    if not os.environ.get('STRIPE_SECRET_KEY'):
        error("STRIPE_SECRET_KEY environment variable is not set")
        flash(g.translate('stripe_not_configured', 
            "Payment system is not properly configured. Please contact support."), "danger")
        return redirect(url_for('profile'))
    
    # Validate plan
    valid_plans = ['premium', 'professional']
    if plan not in valid_plans:
        warning(f"Invalid subscription plan requested: {plan}")
        flash(g.translate('invalid_plan', f"Invalid plan: {plan}"), "danger")
        return redirect(url_for('landing'))
    
    # Check if user has an email address (required for Stripe)
    if not current_user.email:
        warning(f"User {current_user.id} attempted checkout without email address")
        flash(g.translate('email_required', 
            "An email address is required for subscription. Please update your profile."), "warning")
        return redirect(url_for('profile'))
    
    try:
        # Log checkout attempt
        info(f"User {current_user.id} initiating checkout for plan: {plan}")
        
        # Use the subscription manager to create a checkout session
        checkout_url = create_stripe_checkout_session(current_user.id, plan)
        
        if checkout_url:
            # Redirect to Stripe checkout page
            info(f"Redirecting user {current_user.id} to Stripe checkout for {plan} plan")
            return redirect(checkout_url)
        else:
            # Handle failure to create checkout session
            error(f"Failed to create checkout session for user {current_user.id}, plan {plan}")
            flash(g.translate('checkout_error', 
                "An error occurred while setting up your subscription. Please try again later."), 
                "danger")
            return redirect(url_for('manage_subscription'))
            
    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        
        # Handle card errors (specific Stripe errors are imported as constants)
        if "CardError" in error_type:
            # Card errors
            error(f"Card error for user {current_user.id}, plan {plan}: {error_message}")
            flash(g.translate('card_error', f"Card error: {error_message}"), "danger")
            return redirect(url_for('manage_subscription'))
            
        # Rate limit errors    
        elif "RateLimitError" in error_type:
            # Too many requests
            error(f"Rate limit error for user {current_user.id}, plan {plan}")
            flash(g.translate('rate_limit_error', 
                "Too many requests to the payment system. Please try again in a few minutes."), "warning")
            return redirect(url_for('manage_subscription'))
            
        # Invalid request errors
        elif "InvalidRequestError" in error_type:
            # Invalid parameters
            error(f"Invalid request error for user {current_user.id}, plan {plan}: {error_message}")
            if "price" in error_message.lower():
                flash(g.translate('invalid_price', 
                    "This subscription plan is currently unavailable. Please contact support."), "danger")
            else:
                flash(g.translate('invalid_request', 
                    "There was an error with your request. Please try again."), "danger")
            return redirect(url_for('manage_subscription'))
            
        # Authentication errors
        elif "AuthenticationError" in error_type:
            # Authentication with Stripe's API failed
            error(f"Stripe authentication error for user {current_user.id}, plan {plan}")
            flash(g.translate('auth_error', 
                "We're having trouble connecting to our payment provider. Please try again later."), "danger")
            return redirect(url_for('profile'))
            
        # Connection errors
        elif "APIConnectionError" in error_type:
            # Network error
            error(f"Stripe API connection error for user {current_user.id}, plan {plan}")
            flash(g.translate('connection_error', 
                "We're having trouble connecting to our payment provider. Please check your internet connection and try again."), "warning")
            return redirect(url_for('manage_subscription'))
            
        # Generic Stripe errors
        elif "StripeError" in error_type:
            # Generic Stripe error
            error(f"Stripe error for user {current_user.id}, plan {plan}: {error_message}")
            flash(g.translate('stripe_error', 
                "An error occurred with our payment processor. Please try again later."), "danger")
            return redirect(url_for('manage_subscription'))
            
        # Any other unexpected errors
        else:
            # Log unexpected error
            error(f"Unexpected error ({error_type}) creating checkout session for user {current_user.id}, plan {plan}: {error_message}")
            
            # Log traceback for detailed debugging
            import traceback
            debug(f"Checkout error traceback: {traceback.format_exc()}")
            
            flash(g.translate('checkout_error', 
                "An unexpected error occurred while processing your request. Please try again later."), 
                "danger")
            return redirect(url_for('profile'))


# Subscription success route
@app.route('/subscription/success')
@require_login
def subscription_success():
    """
    Handle successful subscription checkout.
    Updates the user's subscription record after successful payment.
    """
    from subscription_manager import handle_checkout_success
    
    # Get the Stripe session ID from URL query parameters
    session_id = request.args.get('session_id')
    if not session_id:
        warning(f"Missing session_id in subscription success callback for user {current_user.id}")
        flash(g.translate('invalid_session', "Invalid checkout session."), "danger")
        return redirect(url_for('manage_subscription'))
        
    try:
        # Log the checkout success attempt
        info(f"Processing successful checkout for session {session_id}, user {current_user.id}")
        
        # Use subscription manager to handle the checkout success
        result = handle_checkout_success(session_id)
        
        if result:
            # Successfully processed the subscription
            # Fetch subscription details to display the correct plan name
            from subscription_manager import get_subscription_details
            subscription_details = get_subscription_details(current_user.id)
            plan_name = subscription_details.get('plan_name', 'premium').capitalize()
            
            # Show success message
            info(f"Subscription activated successfully for user {current_user.id}, plan: {plan_name}")
            flash(g.translate('subscription_activated', 
                f"Thank you! Your {plan_name} subscription has been activated."), "success")
            
            # Redirect to subscription management page
            return redirect(url_for('manage_subscription'))
        else:
            # Failed to process the subscription
            error(f"Failed to activate subscription for session {session_id}, user {current_user.id}")
            flash(g.translate('subscription_error', 
                "An error occurred while activating your subscription. Please try again or contact support."), "danger")
            return redirect(url_for('manage_subscription'))
            
    except Exception as e:
        # Handle unexpected errors
        error(f"Error processing subscription success for user {current_user.id}: {str(e)}")
        flash(g.translate('subscription_error', 
            "An error occurred while processing your subscription. Please contact support."), "danger")
        return redirect(url_for('manage_subscription'))


# Subscription cancel route
@app.route('/subscription/cancel')
@require_login
def subscription_cancel():
    """
    Handle canceled subscription checkout.
    User canceled the checkout process before completing payment.
    """
    # Log the cancellation
    info(f"Subscription checkout canceled by user {current_user.id}")
    
    # Show informational message
    flash(g.translate('checkout_canceled', 
        "Your subscription checkout was canceled. You can try again anytime."), "info")
    
    # Redirect to subscription management page
    return redirect(url_for('manage_subscription'))


# Stripe webhook handler
@app.route('/webhooks/stripe', methods=['POST'])
def stripe_webhook():
    """
    Handle Stripe webhook events.
    
    This endpoint receives and processes events from Stripe's webhook system.
    It verifies the signature of incoming webhooks when a webhook secret is configured,
    and routes the events to appropriate handlers in the subscription_manager module.
    
    Events handled include:
    - checkout.session.completed: When a customer completes the checkout process
    - invoice.paid: When an invoice is paid, activating or renewing a subscription
    - customer.subscription.updated: When a subscription is modified
    - customer.subscription.deleted: When a subscription is canceled or ends
    
    Returns:
        JSON response indicating success or providing error details
    """
    from subscription_manager import handle_webhook_event
    
    # Get request details
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    request_id = request.headers.get('X-Request-Id', 'unknown')
    
    # Log the webhook receipt
    info(f"Received Stripe webhook - Request ID: {request_id}, Content Length: {len(payload)}")
    
    # Verify webhook signature if secret is available
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    if not webhook_secret:
        warning("STRIPE_WEBHOOK_SECRET not set. Webhook signature verification disabled.")
    
    try:
        # Extract the event data
        if webhook_secret and sig_header:
            try:
                # Verify the webhook signature using the secret
                event = stripe.Webhook.construct_event(
                    payload, sig_header, webhook_secret
                )
                info(f"Webhook signature verified - Event ID: {event.get('id', 'unknown')}, Type: {event.get('type', 'unknown')}")
            except stripe.SignatureVerificationError as sig_err:
                # Invalid signature
                error(f"Invalid webhook signature: {str(sig_err)}")
                return jsonify({
                    'status': 'error', 
                    'message': 'Invalid signature',
                    'request_id': request_id
                }), 400
        else:
            # For development, we can parse the payload directly
            # Note: In production, always use webhook signatures for security
            try:
                data = json.loads(payload)
                event = data
                warning(f"Processing webhook without signature verification (development mode) - Event type: {event.get('type', 'unknown')}")
            except json.JSONDecodeError as json_err:
                error(f"Failed to parse webhook payload as JSON: {str(json_err)}")
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid JSON payload',
                    'request_id': request_id
                }), 400
        
        # Log detailed event information
        event_id = event.get('id', 'unknown')
        event_type = event.get('type', 'unknown')
        created_timestamp = event.get('created', 0)
        created_time = datetime.fromtimestamp(created_timestamp).strftime('%Y-%m-%d %H:%M:%S') if created_timestamp else 'unknown'
        
        info(f"Processing Stripe webhook - ID: {event_id}, Type: {event_type}, Created: {created_time}")
        
        # Additional logging for specific event types
        if event_type == 'checkout.session.completed':
            session = event.get('data', {}).get('object', {})
            customer_id = session.get('customer', 'unknown')
            subscription_id = session.get('subscription', 'unknown')
            info(f"Checkout completed - Customer: {customer_id}, Subscription: {subscription_id}")
        elif event_type.startswith('customer.subscription'):
            subscription = event.get('data', {}).get('object', {})
            customer_id = subscription.get('customer', 'unknown')
            status = subscription.get('status', 'unknown')
            plan = subscription.get('plan', {}).get('nickname', 'unknown')
            info(f"Subscription event - Customer: {customer_id}, Status: {status}, Plan: {plan}")
            
        # Process the event with detailed logging
        processing_start_time = time.time()
        success = handle_webhook_event(event)
        processing_time = time.time() - processing_start_time
        
        if success:
            info(f"Successfully processed webhook event: {event_type} in {processing_time:.2f}s")
            return jsonify({
                'status': 'success',
                'message': f'Processed {event_type} event',
                'event_id': event_id,
                'request_id': request_id
            }), 200
        else:
            error(f"Failed to process webhook event: {event_type}")
            return jsonify({
                'status': 'error', 
                'message': 'Event processing failed',
                'event_id': event_id,
                'request_id': request_id
            }), 500
            
    except ValueError as e:
        # Invalid payload
        error(f"Invalid webhook payload: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': 'Invalid payload',
            'error': str(e),
            'request_id': request_id
        }), 400
        
    except Exception as e:
        # Catch-all for unexpected errors
        error_details = str(e)
        error_type = type(e).__name__
        error(f"Unexpected error processing webhook: {error_type}: {error_details}")
        
        # Log traceback for debugging
        import traceback
        error(f"Traceback: {traceback.format_exc()}")
        
        return jsonify({
            'status': 'error', 
            'message': 'Internal server error',
            'error_type': error_type,
            'request_id': request_id
        }), 500


# User subscription management
@app.route('/subscription/manage')
@require_login
def manage_subscription():
    """
    Render the subscription management page.
    Shows the current subscription status, usage limits, and available plans.
    
    This page also allows users to:
    - Start a free trial
    - Cancel their subscription
    - Upgrade or downgrade their plan
    """
    from subscription_manager import get_subscription_details, get_usage_quota
    
    try:
        # Get subscription details
        subscription_details = get_subscription_details(current_user.id)
        
        # Get current usage quotas
        usage = get_usage_quota(user_id=current_user.id)
        
        # Prepare subscription context for template
        subscription_context = {
            'plan_name': subscription_details.get('plan_name', 'free'),
            'status': subscription_details.get('status', 'active'),
            'current_period_start': subscription_details.get('current_period_start'),
            'current_period_end': subscription_details.get('current_period_end'),
            'cancel_at_period_end': subscription_details.get('cancel_at_period_end', False),
            'quotas': {
                'daily_messages': subscription_details.get('quotas', {}).get('daily_messages', 10),
                'daily_exercises': subscription_details.get('quotas', {}).get('daily_exercises', 3),
                'monthly_analyses': subscription_details.get('quotas', {}).get('monthly_analyses', 1),
            },
            'usage': {
                'messages_used_today': usage.messages_used_today if usage else 0,
                'exercises_used_today': usage.exercises_used_today if usage else 0,
                'analyses_used_this_month': usage.analyses_used_this_month if usage else 0,
            }
        }
        
        info(f"Rendering subscription page for user: {current_user.id}")
        return render_template('subscription_manage.html', subscription=subscription_context)
    
    except Exception as e:
        error(f"Error retrieving subscription information: {str(e)}")
        flash("An error occurred while retrieving your subscription information. Please try again later.", "danger")
        return redirect(url_for('index'))


# Trial management
@app.route('/subscription/start-trial', methods=['POST'])
@require_login
def start_trial():
    """
    Start a free trial for the user.
    
    Allows users to try premium or professional features before committing to a paid subscription.
    Trial length is controlled by the DEFAULT_TRIAL_DAYS constant in subscription_manager.py.
    """
    from subscription_manager import create_trial, DEFAULT_TRIAL_DAYS
    
    # Get trial plan from form data (default to premium if not specified)
    trial_plan = request.form.get('trial_plan', 'premium')
    
    # Validate trial plan
    if trial_plan not in ['premium', 'professional']:
        flash(g.translate('invalid_trial_plan', "Invalid trial plan selected."), "danger")
        return redirect(url_for('manage_subscription'))
    
    # Create the trial
    try:
        success, message, subscription = create_trial(current_user.id, trial_plan)
        
        if success:
            # Trial created successfully
            info(f"Trial created for user {current_user.id}: {trial_plan} for {DEFAULT_TRIAL_DAYS} days")
            flash(g.translate('trial_started', f"Your {trial_plan} trial has been activated! You now have access to all {trial_plan} features for the next {DEFAULT_TRIAL_DAYS} days."), "success")
        else:
            # Failed to create trial
            warning(f"Failed to create trial for user {current_user.id}: {message}")
            flash(g.translate('trial_error', f"Couldn't start trial: {message}"), "danger")
    except Exception as e:
        # Exception during trial creation
        error(f"Error creating trial for user {current_user.id}: {str(e)}")
        flash(g.translate('trial_error', "An error occurred while starting your trial. Please try again later."), "danger")
    
    return redirect(url_for('manage_subscription'))


@app.route('/subscription/end-trial', methods=['POST'])
@require_login
def end_user_trial():
    """
    End the user's trial subscription.
    
    Users can choose to end their trial early or convert it to a paid subscription.
    """
    from subscription_manager import end_trial
    
    # Check if the user wants to convert to paid
    convert_to_paid = request.form.get('convert_to_paid') == 'true'
    
    try:
        success, message = end_trial(current_user.id, convert_to_paid)
        
        if success:
            if convert_to_paid:
                info(f"Trial converted to paid subscription for user {current_user.id}")
                flash(g.translate('trial_converted', "Your trial has been converted to a paid subscription. Thank you for your support!"), "success")
            else:
                info(f"Trial ended for user {current_user.id}")
                flash(g.translate('trial_ended', "Your trial has been ended. Thank you for trying our premium features!"), "info")
        else:
            warning(f"Failed to end trial for user {current_user.id}: {message}")
            flash(g.translate('trial_end_error', f"Couldn't end trial: {message}"), "danger")
    except Exception as e:
        error(f"Error ending trial for user {current_user.id}: {str(e)}")
        flash(g.translate('trial_end_error', "An error occurred while ending your trial. Please try again later."), "danger")
    
    return redirect(url_for('manage_subscription'))


# Cancel subscription
@app.route('/subscription/cancel-subscription', methods=['POST'])
@require_login
def cancel_user_subscription():
    """
    Cancel the user's subscription.
    This doesn't immediately end the subscription, but prevents renewal at the end of the current period.
    """
    from subscription_manager import cancel_subscription
    
    try:
        # Log the cancellation attempt
        info(f"Cancellation request received for user: {current_user.id}")
        
        # Attempt to cancel the subscription
        result = cancel_subscription(current_user.id)
        
        if result:
            # Successful cancellation
            info(f"Subscription successfully canceled for user: {current_user.id}")
            flash(g.translate('subscription_canceled_message', 
                "Your subscription has been canceled. You will still have access until the end of your billing period."), 
                "success")
        else:
            # Cancellation failed for some reason
            warning(f"Subscription cancellation failed for user: {current_user.id}")
            flash(g.translate('cancellation_failed', 
                "Unable to cancel subscription. Please try again later."), 
                "danger")
    except Exception as e:
        # Exception occurred during cancellation
        error(f"Error canceling subscription for user {current_user.id}: {str(e)}")
        flash(g.translate('cancellation_error', 
            "An error occurred while processing your request. Please try again later."), 
            "danger")
    
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
    
    # Get subscription information for feature gating
    from subscription_manager import get_subscription_details, check_feature_access
    
    # Get detailed subscription information
    subscription_details = get_subscription_details(current_user.id)
    
    # Prepare feature access flags
    features = {
        'has_premium': subscription_details['plan_name'] in ['premium', 'professional'],
        'has_professional': subscription_details['plan_name'] == 'professional',
        'advanced_nlp': check_feature_access(current_user.id, 'advanced_nlp'),
        'progress_tracking': check_feature_access(current_user.id, 'progress_tracking'),
        'communication_analysis': check_feature_access(current_user.id, 'communication_analysis'),
        'voice_practice': check_feature_access(current_user.id, 'voice_practice'),
        'personalized_journeys': check_feature_access(current_user.id, 'personalized_journeys'),
        'belief_change': check_feature_access(current_user.id, 'belief_change'),
        'reminders': check_feature_access(current_user.id, 'reminders')
    }
    
    return render_template('index.html', subscription=subscription_details, features=features)

# Route to get NLP technique recommendations
@app.route('/recommend_technique', methods=['POST'])
def get_technique_recommendation():
    """
    Endpoint for recommending the most appropriate NLP technique
    based on the user's message and mood.
    """
    # Get the user message and mood from the request
    data = get_request_json()
    message = data.get('message', '')
    mood = data.get('mood', 'neutral')
    
    # Log the received request
    debug(f"Technique recommendation request: Message={message}, Mood={mood}")
    
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
    
    Enforces usage quotas based on the user's subscription tier.
    Returns error response when quota is exceeded with quota_exceeded flag set to true.
    """
    # Get the user message, mood, and NLP technique from the request
    data = get_request_json()
    message = data.get('message', '')
    mood = data.get('mood', 'neutral')
    technique = data.get('technique', 'reframing')
    
    # Get session ID for tracking the conversation
    session_id = session.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        info(f"Created new session ID: {session_id}")
    
    # Check usage quotas based on subscription tier
    user_id = None
    if current_user.is_authenticated:
        user_id = current_user.id
        info(f"Chat request from authenticated user: {user_id}")
    else:
        info(f"Chat request from anonymous user with session: {session_id}")
    
    # Import subscription manager functions for quota management
    from subscription_manager import check_quota_available, increment_usage_quota, get_subscription_details
    
    # Get subscription details for logging/debugging
    subscription_tier = "free"
    if user_id:
        try:
            subscription = get_subscription_details(user_id)
            subscription_tier = subscription.get('plan_name', 'free')
            info(f"User subscription tier: {subscription_tier}")
        except Exception as e:
            error(f"Error retrieving subscription details: {str(e)}")
    
    # Check if user has reached their daily message limit
    try:
        quota_available, quota_message = check_quota_available(
            user_id=user_id, 
            browser_session_id=session_id,
            quota_type='daily_messages',
            amount=1
        )
        
        if not quota_available:
            warning(f"Quota exceeded for {'user '+user_id if user_id else 'session '+session_id}")
            return jsonify({
                'response': g.translate('quota_exceeded_message',
                    "You've reached your daily message limit. Please upgrade your subscription for unlimited conversations or wait until tomorrow."),
                'quota_exceeded': True,
                'error': quota_message,
                'subscription_tier': subscription_tier
            })
    except Exception as e:
        error(f"Error checking quota: {str(e)}")
        # Continue processing the request even if quota check fails
    
    # Log the received message for debugging
    debug(f"Received message: {message} (Mood: {mood}, Technique: {technique}, Session: {session_id})")
    
    # Check if OpenAI API key is available
    if not OPENAI_API_KEY:
        error("OpenAI API key is missing")
        return jsonify({
            'response': "I'm sorry, but I'm not fully configured yet. Please provide an OpenAI API key to enable AI responses."
        })
    
    try:
        # Prepare the base system prompt for OpenAI with NLP techniques
        base_system_prompt = f"""You are The Inner Architect, a supportive self-help guide with expertise in Neuro-Linguistic Programming (NLP).
        
Your goal is to help users reframe negative thoughts and build more positive mental patterns using NLP techniques including:

1. Reframing: Help users see situations from different perspectives.
2. Pattern interruption: Suggest ways to break negative thought cycles.
3. Anchoring: Associate positive emotions with specific triggers.
4. Future pacing: Guide users to visualize positive future outcomes.
5. Sensory-based language: Use visual, auditory, and kinesthetic language matching the user's communication style.
6. Meta model questioning: Ask questions that challenge limiting beliefs and generalizations.

For this response, focus primarily on using the '{technique}' technique.

Based on the user's mood and message:
1. Acknowledge their current emotional state with empathy
2. Identify any limiting beliefs or negative patterns
3. Apply the '{technique}' NLP technique to help reframe their thinking
4. Provide a practical, actionable suggestion they can implement immediately

Keep responses concise (2-3 short paragraphs maximum) and conversational. Use the user's name if available.
"""
        
        # Enhance the system prompt with conversation context
        context_id = None
        try:
            # Get enhanced prompt with context and the context ID
            enhanced_prompt, context_id = enhance_prompt_with_context(
                user_id, 
                session_id, 
                message, 
                base_system_prompt
            )
            system_prompt = enhanced_prompt
            
            if context_id:
                debug(f"Using conversation context ID: {context_id}")
        except Exception as context_error:
            # Log the error but continue with the base prompt
            error(f"Error enhancing prompt with context: {str(context_error)}")
            system_prompt = base_system_prompt
        
        # Make the API call to OpenAI
        # Check if OpenAI client is initialized
        if openai_client is None:
            error("OpenAI API key not configured")
            return jsonify({
                'error': 'OpenAI API not configured. Please contact support.',
                'technique': technique
            }), 500
            
        # Import the API error handling tools
        from api_fallback import with_retry_and_timeout, APIError, get_fallback_response, show_user_friendly_error
        
        # Get the response from OpenAI with error handling
        ai_response = ""
        response = None
        try:
            # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            @with_retry_and_timeout(timeout=20, retries=2)
            def get_openai_response(prompt, user_content, model="gpt-4o", max_tokens=500, timeout=20):
                return openai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": user_content}
                    ],
                    max_tokens=max_tokens,
                    timeout=timeout  # Pass through timeout parameter
                )
            
            # Call the enhanced function with retry logic
            response = get_openai_response(
                prompt=system_prompt,
                user_content=f"User mood: {mood}\nUser message: {message}\nRequested NLP technique: {technique}"
            )
            
            # Extract the AI response with proper null checking
            if response and hasattr(response, 'choices') and response.choices:
                message_content = getattr(response.choices[0].message, 'content', None)
                if message_content is not None:
                    ai_response = message_content.strip()
            debug(f"AI response: {ai_response}")
            
        except APIError as api_err:
            # Handle specific API errors with appropriate fallbacks
            error(f"API error in chat endpoint: {str(api_err)}")
            
            # Get the error type from the exception
            error_type = "response"
            if "timeout" in str(api_err).lower():
                error_type = "timeout"
            elif "connection" in str(api_err).lower():
                error_type = "connection"
                
            # Get a fallback response
            context = {
                "user_message": message,
                "endpoint": "chat",
                "technique": technique,
                "mood": mood
            }
            fallback = get_fallback_response(error_type, context)
            
            # Use the fallback message as the AI response
            ai_response = fallback["message"]
            
            # Show a user-friendly error message
            show_user_friendly_error(error_type, context)
            
        except Exception as e:
            # Handle any other errors
            error(f"Unexpected error in chat endpoint: {str(e)}")
            ai_response = "I'm having trouble processing your request right now. Please try again in a moment."
        
        # Save the chat history to the database
        try:
            # Associate with user if authenticated
            user_id_for_chat = None
            if current_user.is_authenticated:
                user_id_for_chat = current_user.id
                
            # Create chat history entry using the database helper function
            from database import create_model
            
            chat_data = {
                'user_id': user_id_for_chat,
                'session_id': session_id,
                'user_message': message,
                'ai_response': ai_response,
                'mood': mood,
                'nlp_technique': technique,
                'context_id': context_id  # Link to the conversation context
            }
            chat_entry = create_model(ChatHistory, chat_data)
            
            if chat_entry:
                info(f"Chat history saved with ID: {chat_entry.id}")
                
                # Add to conversation context and extract memories
                if context_id and chat_entry:
                    try:
                        # We don't need to wait for these operations to complete
                        add_message_to_context(context_id, chat_entry.id)
                        
                        # Update context summary after a few messages
                        message_count = ChatHistory.query.filter_by(context_id=context_id).count()
                        if message_count % 3 == 0:  # Update every 3 messages
                            update_context_summary(context_id)
                    except Exception as ctx_error:
                        # Log but continue
                        error(f"Error updating conversation context: {str(ctx_error)}")
            else:
                warning("Failed to save chat history")
            
            # Increment usage quota counter for user
            try:
                success, quota_message = increment_usage_quota(
                    user_id=user_id,
                    browser_session_id=session_id,
                    quota_type='daily_messages',
                    amount=1
                )
                if success:
                    info(f"Usage quota incremented for {'user '+user_id if user_id else 'session '+session_id}")
                else:
                    warning(f"Failed to increment usage quota: {quota_message}")
            except Exception as quota_error:
                # Log the error but don't interrupt user experience
                error(f"Error incrementing usage quota: {str(quota_error)}")
            
        except Exception as db_error:
            # Log the error but don't interrupt user experience
            error(f"Error saving chat history: {str(db_error)}")
            db.session.rollback()
        
        # Return the AI response to the frontend
        return jsonify({
            'response': ai_response
        })
        
    except Exception as e:
        # Enhanced error logging with error type information
        error_type = type(e).__name__
        error(f"Error ({error_type}) calling OpenAI API: {str(e)}")
        
        # Add more detailed error logging for specific error types
        if "APIConnectionError" in error_type or "Timeout" in error_type:
            error("Network connection issue with OpenAI API")
            return jsonify({
                'response': "I'm having trouble connecting to my thinking engine right now. This could be due to network issues. Please check your connection and try again in a moment.",
                'error_type': 'connection'
            })
        elif "RateLimitError" in error_type:
            error("OpenAI API rate limit exceeded")
            return jsonify({
                'response': "I'm currently handling too many conversations. Please try again in a few minutes.",
                'error_type': 'rate_limit'
            })
        elif "AuthenticationError" in error_type:
            error("Authentication error with OpenAI API")
            return jsonify({
                'response': "I'm having trouble accessing my thinking engine. This is a configuration issue that requires attention from support staff.",
                'error_type': 'auth'
            })
        else:
            # Generic error response for other types of errors
            exception(f"Unhandled OpenAI API error: {str(e)}")
            return jsonify({
                'response': "I'm sorry, I encountered an error while processing your message. Please try again later.",
                'error_type': 'general'
            })

# NLP Exercise routes
@app.route('/exercises/<technique>', methods=['GET'])
def get_technique_exercises(technique):
    """
    Get exercises for a specific NLP technique.
    """
    # Get exercises and handle type annotations for LSP
    exercises = get_exercises_by_technique(technique)
    
    # Convert to a format suitable for JSON
    exercise_data = []
    for ex in exercises:
        # Type checking for LSP
        ex_dict = {
            'id': getattr(ex, 'id', None),
            'title': getattr(ex, 'title', ''),
            'description': getattr(ex, 'description', ''),
            'difficulty': getattr(ex, 'difficulty', 'beginner'),
            'estimated_time': getattr(ex, 'estimated_time', 5)
        }
        exercise_data.append(ex_dict)
    
    return jsonify(exercise_data)

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
    
    Enforces usage quotas based on the user's subscription tier.
    Returns error response when quota is exceeded with quota_exceeded flag set to true.
    """
    # Get session ID for tracking
    session_id = session.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        info(f"Created new session ID: {session_id}")
    
    # Get user ID if logged in
    user_id = None
    subscription_tier = "free"
    if current_user.is_authenticated:
        user_id = current_user.id
        info(f"Exercise start request from authenticated user: {user_id}")
    else:
        info(f"Exercise start request from anonymous user with session: {session_id}")
    
    # Import subscription manager functions
    from subscription_manager import check_quota_available, increment_usage_quota, get_subscription_details
    
    # Get subscription details for logging/debugging
    if user_id:
        try:
            subscription = get_subscription_details(user_id)
            subscription_tier = subscription.get('plan_name', 'free')
            info(f"User subscription tier: {subscription_tier}")
        except Exception as e:
            error(f"Error retrieving subscription details: {str(e)}")
    
    # Check if user has reached their daily exercise limit
    try:
        quota_available, quota_message = check_quota_available(
            user_id=user_id,
            browser_session_id=session_id,
            quota_type='daily_exercises',
            amount=1
        )
        
        if not quota_available:
            warning(f"Exercise quota exceeded for {'user '+user_id if user_id else 'session '+session_id}")
            return jsonify({
                'error': g.translate('exercise_quota_exceeded',
                    "You've reached your daily exercise limit. Please upgrade your subscription for more exercises or wait until tomorrow."),
                'quota_exceeded': True,
                'subscription_tier': subscription_tier
            }), 403
    except Exception as e:
        error(f"Error checking exercise quota: {str(e)}")
        # Continue processing the request even if quota check fails
    
    # Start the exercise
    try:
        # Create exercise progress entry
        progress = start_exercise(exercise_id, session_id, user_id)
        if not progress:
            error(f"Failed to start exercise {exercise_id}")
            return jsonify({'error': 'Could not start exercise. Please try again later.'}), 500
        
        # Increment usage quota counter for exercises
        try:
            success, message = increment_usage_quota(
                user_id=user_id,
                browser_session_id=session_id,
                quota_type='daily_exercises',
                amount=1
            )
            if success:
                info(f"Exercise quota incremented for {'user '+user_id if user_id else 'session '+session_id}")
            else:
                warning(f"Failed to increment exercise quota: {message}")
        except Exception as quota_error:
            # Log but don't interrupt experience
            error(f"Error incrementing exercise quota: {str(quota_error)}")
        
        # Return the exercise progress data
        return jsonify({
            'progress_id': progress.id,
            'exercise_id': progress.exercise_id,
            'current_step': progress.current_step,
            'completed': progress.completed,
            'message': g.translate('exercise_started', "Exercise started successfully.")
        })
        
    except Exception as e:
        # Log any errors
        error(f"Error starting exercise {exercise_id}: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred. Please try again later.'}), 500

@app.route('/exercise/progress/<int:progress_id>', methods=['PUT'])
def update_progress(progress_id):
    """
    Update the progress of an exercise.
    """
    data = get_request_json()
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

# Premium Features Page
@app.route('/premium-features')
def premium_features_route():
    """
    Display information about premium features.
    Serves as a gateway to premium features, with explanations and subscription options.
    """
    return render_template('premium_features.html')

# Progress Dashboard Routes
@app.route('/progress/dashboard', methods=['GET'])
@require_premium
def progress_dashboard():
    """
    Render the progress dashboard page.
    Premium feature: Requires premium or professional subscription.
    """
    # Get session ID
    session_id = session.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    
    # Get subscription information for feature gating
    from subscription_manager import get_subscription_details, check_feature_access
    
    # Get detailed subscription information
    subscription_details = get_subscription_details(current_user.id)
    
    # Check if user has access to full progress tracking
    has_full_tracking = check_feature_access(current_user.id, 'progress_tracking')
    
    # Render the dashboard template with subscription details
    return render_template('dashboard.html', 
                         subscription=subscription_details,
                         has_full_tracking=has_full_tracking)

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
    data = get_request_json()
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
    data = get_request_json()
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
    data = get_request_json()
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
    data = get_request_json()
    
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
    data = get_request_json()
    
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
    data = get_request_json()
    
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
    
    # Prepare submission data using a dictionary approach for better LSP compatibility
    submission_data = {
        'submission_id': None,  # Will be generated by save_submission
        'exercise_id': exercise_id if exercise else None,
        'audio_data': audio_data,
        'transcript': transcript,
        'session_id': session_id,
        # Initialize with empty JSON objects that will be set properly later
        'feedback': '{}',
        'metrics': '{}'
    }
    
    # Create the submission object
    submission = VoiceSubmission(**submission_data)
    
    # Convert feedback and metrics to JSON strings for storage
    # This avoids type issues with direct dictionary assignment
    import json
    
    feedback_data = {
        'vocal_delivery': analysis.get('feedback', {}),
        'technique_application': technique_evaluation if technique_evaluation else None
    }
    submission.feedback = json.dumps(feedback_data)
    
    metrics_data = {
        'vocal_delivery': analysis.get('metrics', {}),
        'technique_application': {
            'score': technique_evaluation.get('application_score') if technique_evaluation else None
        }
    }
    submission.metrics = json.dumps(metrics_data)
    
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
    data = get_request_json()
    
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
    data = get_request_json()
    
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
    data = get_request_json()
    
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
    data = get_request_json()
    
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
    data = get_request_json()
    
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
    data = get_request_json()
    
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
            # Create a new subscription using dictionary to prevent LSP errors
            subscription_data = {
                'user_id': current_user.id,
                'stripe_customer_id': f"dev_customer_{current_user.id}",
                'stripe_subscription_id': f"dev_subscription_{current_user.id}",
                'plan_name': 'professional',
                'status': 'active',
                'current_period_start': current_time,
                'current_period_end': one_year_later
            }
            subscription = Subscription(**subscription_data)
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


# Route to reset conversation context
@app.route('/reset-context', methods=['POST'])
def reset_context():
    """
    Reset the conversation context to start fresh.
    This allows users to explicitly start a new conversation thread.
    """
    # Get session ID
    session_id = session.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    
    # Get user ID if authenticated
    user_id = None
    if current_user.is_authenticated:
        user_id = current_user.id
    
    try:
        # Create a new context
        new_context = create_new_context(user_id, session_id)
        if new_context:
            info(f"Conversation context reset for {'user '+user_id if user_id else 'session '+session_id}")
            return jsonify({
                'success': True,
                'message': "Conversation context has been reset. You can start a fresh conversation."
            })
        else:
            warning("Failed to reset conversation context")
            return jsonify({
                'success': False,
                'message': "Unable to reset conversation context. Please try again."
            })
    except Exception as e:
        error_type = type(e).__name__
        error(f"Error ({error_type}) resetting conversation context: {str(e)}")
        return jsonify({
            'success': False,
            'message': "An error occurred while resetting the conversation context."
        })


# Guided onboarding routes
@app.route('/onboarding', defaults={'step': 1}, methods=['GET', 'POST'])
@app.route('/onboarding/<int:step>', methods=['GET', 'POST'])
def onboarding_route(step):
    """
    Guided onboarding process for new users.
    
    This multi-step process collects user preferences, goals, and customizes
    the experience based on their inputs. The data is saved to the UserPreferences
    model associated with the user's account.
    
    Args:
        step: The current onboarding step (1-5)
    """
    from forms import OnboardingForm
    from models import UserPreferences
    
    # Validate step number
    if step < 1 or step > 5:
        flash('Invalid step. Starting from the beginning.', 'warning')
        return redirect(url_for('onboarding_route', step=1))
    
    # Check if user has already completed onboarding
    if current_user.is_authenticated and hasattr(current_user, 'preferences') and current_user.preferences:
        preferences = current_user.preferences
        if preferences.onboarding_completed:
            # Only redirect if they're starting from step 1 (allow returning to specific steps)
            if step == 1:
                flash('You have already completed the onboarding process.', 'info')
                return redirect(url_for('index'))
    else:
        # Create preferences object if it doesn't exist
        preferences = None
        if current_user.is_authenticated:
            preferences = UserPreferences.query.filter_by(user_id=current_user.id).first()
            if not preferences:
                preferences = UserPreferences(user_id=current_user.id, onboarding_step=step)
                db.session.add(preferences)
                db.session.commit()
    
    # Create form
    form = OnboardingForm()
    
    # Handle form submission
    if form.validate_on_submit():
        try:
            # Save form data based on current step
            if current_user.is_authenticated and preferences:
                if step == 1:  # Goals
                    preferences.primary_goal = form.goals.data
                    preferences.custom_goal = form.custom_goal.data
                    preferences.onboarding_step = 2
                
                elif step == 2:  # Experience Level
                    preferences.experience_level = form.experience_level.data
                    preferences.onboarding_step = 3
                
                elif step == 3:  # Communication Preferences
                    preferences.communication_style = form.communication_style.data
                    preferences.show_explanations = form.show_explanations.data
                    preferences.onboarding_step = 4
                
                elif step == 4:  # First Challenge
                    preferences.first_challenge = form.challenge_description.data
                    preferences.challenge_intensity = form.challenge_intensity.data
                    preferences.onboarding_step = 5
                
                elif step == 5:  # Reminders
                    preferences.enable_reminders = form.enable_reminders.data
                    if preferences.enable_reminders:
                        preferences.reminder_frequency = form.reminder_frequency.data
                        preferences.preferred_time = form.preferred_time.data
                    
                    # Mark onboarding as completed
                    preferences.onboarding_completed = True
                    
                    # Flash success message
                    flash('Thank you for completing the onboarding process! Your preferences have been saved.', 'success')
                    
                    # Redirect to index after completion
                    db.session.commit()
                    return redirect(url_for('index'))
                
                # Save changes
                db.session.commit()
            
            # Guest users or unsuccessful save - still allow navigation
            if step < 5:
                # Proceed to next step
                return redirect(url_for('onboarding_route', step=step+1))
            else:
                # Redirect to index after completion even if not logged in
                flash('Thank you for completing the onboarding process!', 'success')
                return redirect(url_for('index'))
                
        except Exception as e:
            # Log error and flash message
            error(f"Error saving onboarding preferences: {str(e)}")
            db.session.rollback()
            flash('An error occurred while saving your preferences. Please try again.', 'danger')
    
    # Pre-fill form with existing data if available
    if current_user.is_authenticated and preferences:
        if step == 1 and preferences.primary_goal:
            form.goals.data = preferences.primary_goal
            form.custom_goal.data = preferences.custom_goal
        elif step == 2 and preferences.experience_level:
            form.experience_level.data = preferences.experience_level
        elif step == 3 and preferences.communication_style:
            form.communication_style.data = preferences.communication_style
            form.show_explanations.data = preferences.show_explanations
        elif step == 4 and preferences.first_challenge:
            form.challenge_description.data = preferences.first_challenge
            form.challenge_intensity.data = preferences.challenge_intensity
        elif step == 5:
            form.enable_reminders.data = preferences.enable_reminders
            form.reminder_frequency.data = preferences.reminder_frequency
            form.preferred_time.data = preferences.preferred_time
    
    # Render the appropriate step template
    return render_template(
        'onboarding.html',
        form=form,
        current_step=step,
        total_steps=5
    )


# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    error_details = {
        'error_type': 'empty_state',
        'title': g.translate('page_not_found', 'Page Not Found'),
        'message': g.translate('page_not_found_message', 'The page you are looking for doesn\'t exist or has been moved.'),
        'retry_action': None,
        'help_link': None
    }
    return render_template('error.html', **error_details), 404

@app.errorhandler(500)
def internal_server_error(e):
    error_details = {
        'error_type': 'general',
        'title': g.translate('server_error', 'Server Error'),
        'message': g.translate('server_error_message', 'Something went wrong on our end. Our team has been notified.'),
        'retry_action': f"window.location.href='{request.referrer or url_for('index')}'",
        'help_link': None
    }
    return render_template('error.html', **error_details), 500

@app.errorhandler(403)
def forbidden(e):
    error_details = {
        'error_type': 'auth',
        'error_title': 'Access Denied',
        'error_message': 'You don\'t have permission to access this resource.',
        'retry_action': None,
        'alternative_action': {
            'text': 'Go to Home',
            'url': url_for('index')
        }
    }
    return render_template('error.html', **error_details), 403
    
@app.errorhandler(429)
def too_many_requests(e):
    error_details = {
        'error_type': 'rate_limit',
        'error_title': 'Too Many Requests',
        'error_message': 'You\'ve made too many requests. Please try again later.',
        'retry_action': None,
        'alternative_action': {
            'text': 'Go to Home',
            'url': url_for('index')
        }
    }
    return render_template('error.html', **error_details), 429


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
