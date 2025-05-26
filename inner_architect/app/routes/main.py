import os
import uuid
import json
from datetime import datetime
from flask import (
    Blueprint, render_template, request, jsonify, session, flash, 
    redirect, url_for, g, current_app, send_from_directory
)
from flask_login import current_user, login_required

from app import db
from app.models import User, Subscription, ConversationContext
from app.nlp.techniques import get_all_techniques
from app.utils.subscription import get_subscription_details, check_feature_access

# Create blueprint
main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Home page route."""
    if current_user.is_authenticated:
        # Get user's subscription details
        subscription = get_subscription_details(current_user.id)
        
        # Get active conversation context
        active_context = None
        if 'session_id' in session:
            active_context = ConversationContext.query.filter_by(
                user_id=current_user.id,
                session_id=session['session_id'],
                is_active=True
            ).first()
        
        return render_template(
            'index.html', 
            subscription=subscription,
            active_context=active_context,
            techniques=get_all_techniques()
        )
    else:
        return render_template('landing.html')

@main.route('/manifest.json')
def manifest():
    """Progressive Web App manifest route."""
    return send_from_directory(
        os.path.join(current_app.root_path, 'static'), 
        'manifest.json'
    )

@main.route('/offline')
def offline():
    """Offline page for Progressive Web App."""
    return render_template('offline.html')

@main.route('/dashboard')
@login_required
def dashboard():
    """User dashboard route."""
    # Get user's subscription details
    subscription = get_subscription_details(current_user.id)
    
    return render_template('dashboard.html', subscription=subscription)

@main.route('/techniques')
def techniques():
    """NLP techniques information page."""
    techniques_data = get_all_techniques()
    
    # Check if premium features are accessible
    has_premium = False
    if current_user.is_authenticated:
        has_premium = check_feature_access(current_user.id, 'advanced_nlp')
    
    return render_template(
        'techniques.html', 
        techniques=techniques_data, 
        has_premium=has_premium
    )

@main.route('/technique/<technique_id>')
def technique_detail(technique_id):
    """Detailed page for a specific NLP technique."""
    # Import original technique details
    import sys
    import os
    sys.path.append('/workspace/InnerArchitect')
    from nlp_techniques import TECHNIQUE_DETAILS, get_technique_details as get_original_technique_details
    
    # Get technique data from Claude-specific implementation
    techniques_data = get_all_techniques()
    
    if technique_id not in techniques_data:
        flash('Technique not found', 'warning')
        return redirect(url_for('main.techniques'))
    
    technique = techniques_data[technique_id]
    
    # Get detailed information from original technique implementation
    technique_details = get_original_technique_details(technique_id)
    
    # Filter out the current technique from the list to get "other techniques"
    other_techniques = {k: v for k, v in techniques_data.items() if k != technique_id}
    
    # Check if this is a premium technique
    premium_techniques = ['pattern_interruption', 'anchoring', 'future_pacing', 'sensory_language', 'meta_model']
    is_premium = technique_id in premium_techniques
    
    # Check if user has premium access
    has_premium = False
    if current_user.is_authenticated:
        has_premium = check_feature_access(current_user.id, 'advanced_nlp')
    
    return render_template(
        'technique_detail.html', 
        technique_id=technique_id,
        technique=technique,
        technique_details=technique_details,
        other_techniques=other_techniques,
        is_premium=is_premium,
        has_premium=has_premium
    )

@main.route('/premium-features')
def premium_features_route():
    """Premium features information page."""
    # Get subscription plans information
    from app.utils.subscription import SUBSCRIPTION_PLANS
    
    # Check if user has premium access
    has_premium = False
    if current_user.is_authenticated:
        subscription = get_subscription_details(current_user.id)
        has_premium = subscription.get('has_premium_access', False)
    
    return render_template(
        'premium_features.html', 
        plans=SUBSCRIPTION_PLANS,
        has_premium=has_premium
    )

@main.route('/set-language/<lang_code>')
def set_language(lang_code):
    """Set the user's preferred language."""
    available_languages = ['en', 'es', 'fr', 'de']
    
    if lang_code in available_languages:
        session['language'] = lang_code
        
        # Update user preference if logged in
        if current_user.is_authenticated:
            # In a real app, you'd store this in the user's preferences
            pass
    
    # Redirect back to the referring page or home
    return redirect(request.referrer or url_for('main.index'))

@main.route('/profile')
@login_required
def profile():
    """User profile page."""
    # Get subscription details
    subscription = get_subscription_details(current_user.id)
    
    return render_template('profile.html', subscription=subscription)

@main.route('/privacy-settings', methods=['GET', 'POST'])
@login_required
def privacy_settings():
    """User privacy settings page."""
    from app.models import PrivacySettings
    
    # Get or create privacy settings
    privacy = PrivacySettings.query.filter_by(user_id=current_user.id).first()
    if not privacy:
        privacy = PrivacySettings(user_id=current_user.id)
        db.session.add(privacy)
        db.session.commit()
    
    if request.method == 'POST':
        # Update privacy settings
        privacy.data_collection = 'data_collection' in request.form
        privacy.progress_tracking = 'progress_tracking' in request.form
        privacy.personalization = 'personalization' in request.form
        privacy.email_notifications = 'email_notifications' in request.form
        privacy.marketing_emails = 'marketing_emails' in request.form
        
        db.session.commit()
        flash('Privacy settings updated successfully', 'success')
        return redirect(url_for('main.profile'))
    
    return render_template('privacy_settings.html', privacy=privacy)

@main.route('/onboarding', methods=['GET', 'POST'])
@login_required
def onboarding():
    """User onboarding process."""
    from app.models import UserPreferences
    
    # Get or create user preferences
    preferences = UserPreferences.query.filter_by(user_id=current_user.id).first()
    if not preferences:
        preferences = UserPreferences(user_id=current_user.id)
        db.session.add(preferences)
        db.session.commit()
    
    if request.method == 'POST':
        # Get current step and process accordingly
        current_step = preferences.onboarding_step
        
        if current_step == 1:
            # Process step 1: Primary goal
            preferences.primary_goal = request.form.get('primary_goal')
            preferences.custom_goal = request.form.get('custom_goal')
            preferences.onboarding_step = 2
            
        elif current_step == 2:
            # Process step 2: Experience level
            preferences.experience_level = request.form.get('experience_level')
            preferences.onboarding_step = 3
            
        elif current_step == 3:
            # Process step 3: Communication style
            preferences.communication_style = request.form.get('communication_style')
            preferences.show_explanations = 'show_explanations' in request.form
            preferences.onboarding_step = 4
            
        elif current_step == 4:
            # Process step 4: First challenge
            preferences.first_challenge = request.form.get('first_challenge')
            preferences.challenge_intensity = int(request.form.get('challenge_intensity', 5))
            preferences.onboarding_step = 5
            
        elif current_step == 5:
            # Process step 5: Reminder preferences
            preferences.enable_reminders = 'enable_reminders' in request.form
            preferences.reminder_frequency = request.form.get('reminder_frequency')
            preferences.preferred_time = datetime.strptime(request.form.get('preferred_time', '09:00'), '%H:%M').time()
            
            # Complete onboarding
            preferences.onboarding_completed = True
            flash('Onboarding completed successfully!', 'success')
            
            # Redirect to dashboard or chat
            db.session.commit()
            return redirect(url_for('main.dashboard'))
        
        db.session.commit()
        
        # Reload the page to show the next step
        return redirect(url_for('main.onboarding'))
    
    return render_template('onboarding.html', preferences=preferences)