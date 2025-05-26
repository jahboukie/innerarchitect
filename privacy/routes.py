"""
Privacy Routes for The Inner Architect

This module defines the Flask routes for privacy-related functionality,
including PIPEDA compliance for Canadian users.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Tuple
from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    flash, g, jsonify, current_app, session
)
from flask_login import current_user, login_required
from werkzeug.security import check_password_hash

from privacy.pipeda_compliance import (
    PipedaCompliance, PurposeCategory, ConsentType, 
    record_flask_consent, get_pipeda_consent_text
)

# Initialize blueprint
privacy_bp = Blueprint('privacy', __name__, url_prefix='/privacy')

# Initialize PIPEDA compliance module
pipeda = PipedaCompliance()

# Helper function to check consent
def has_consent(purpose_str: str) -> bool:
    """
    Check if the current user has consent for a specific purpose.
    
    Args:
        purpose_str: String representation of the purpose
        
    Returns:
        True if the user has consent, False otherwise
    """
    if not current_user.is_authenticated:
        return False
    
    try:
        # Convert string to PurposeCategory enum
        purpose = PurposeCategory(purpose_str)
        return pipeda.has_valid_consent(str(current_user.id), purpose)
    except (ValueError, KeyError):
        return False

@privacy_bp.route('/consent', methods=['GET'])
@login_required
def consent_form():
    """
    Display the privacy consent form.
    """
    return render_template(
        'privacy/consent_form.html',
        has_consent=has_consent
    )

@privacy_bp.route('/update-consent', methods=['POST'])
@login_required
def update_consent():
    """
    Update the user's privacy consent preferences.
    """
    # Check CSRF token
    if request.form.get('csrf_token') != session.get('csrf_token'):
        flash('Invalid request. Please try again.', 'danger')
        return redirect(url_for('privacy.consent_form'))
    
    # Get selected purposes
    selected_purposes = request.form.getlist('consent_purposes[]')
    
    # Convert to PurposeCategory enums
    purposes = []
    for purpose_str in selected_purposes:
        try:
            purposes.append(PurposeCategory(purpose_str))
        except ValueError:
            continue
    
    # Ensure core_service is included (required)
    if PurposeCategory.CORE_SERVICE not in purposes:
        flash('Core service consent is required to use the application.', 'danger')
        return redirect(url_for('privacy.consent_form'))
    
    # Record consent
    success = record_flask_consent(
        pipeda=pipeda,
        user_id=str(current_user.id),
        purposes=purposes,
        request=request
    )
    
    if success:
        flash('Your privacy preferences have been updated.', 'success')
    else:
        flash('There was an error updating your privacy preferences. Please try again.', 'danger')
    
    return redirect(url_for('profile'))

@privacy_bp.route('/data-request', methods=['GET'])
@login_required
def data_request():
    """
    Display the data request form.
    """
    # Get previous requests for this user
    previous_requests = []
    
    try:
        # Get the requests directory path
        requests_dir = os.path.join(os.path.dirname(__file__), 'data', 'requests')
        
        # Ensure the directory exists
        if os.path.exists(requests_dir):
            # Get all request files for this user
            for filename in os.listdir(requests_dir):
                if filename.endswith('_request.json'):
                    try:
                        with open(os.path.join(requests_dir, filename), 'r', encoding='utf-8') as f:
                            request_data = json.load(f)
                            
                            # Check if this request belongs to the current user
                            if request_data.get('user_id') == str(current_user.id):
                                # Convert string dates to datetime objects
                                request_data['timestamp'] = datetime.fromisoformat(request_data['timestamp'])
                                if request_data.get('completion_date'):
                                    request_data['completion_date'] = datetime.fromisoformat(request_data['completion_date'])
                                
                                previous_requests.append(request_data)
                    except (json.JSONDecodeError, IOError) as e:
                        current_app.logger.error(f"Error loading request file {filename}: {e}")
            
            # Sort by timestamp (newest first)
            previous_requests.sort(key=lambda x: x['timestamp'], reverse=True)
    except Exception as e:
        current_app.logger.error(f"Error getting previous requests: {e}")
    
    return render_template(
        'privacy/data_request.html',
        previous_requests=previous_requests
    )

@privacy_bp.route('/create-data-request', methods=['POST'])
@login_required
def create_data_request():
    """
    Create a new data access, correction, or deletion request.
    """
    # Check CSRF token
    if request.form.get('csrf_token') != session.get('csrf_token'):
        flash('Invalid request. Please try again.', 'danger')
        return redirect(url_for('privacy.data_request'))
    
    # Get request type
    request_type = request.form.get('request_type')
    if request_type not in ['access', 'correction', 'deletion']:
        flash('Invalid request type.', 'danger')
        return redirect(url_for('privacy.data_request'))
    
    # Check confirmation
    if not request.form.get('confirmation'):
        flash('You must confirm the request.', 'danger')
        return redirect(url_for('privacy.data_request'))
    
    # For deletion requests, check password
    if request_type == 'deletion':
        password = request.form.get('password')
        if not password or not check_password_hash(current_user.password_hash, password):
            flash('Incorrect password. Please try again.', 'danger')
            return redirect(url_for('privacy.data_request'))
    
    # Get request details
    request_details = {}
    for key, value in request.form.items():
        if key.startswith('request_details[') and key.endswith(']'):
            detail_key = key[len('request_details['):-1]
            request_details[detail_key] = value
    
    # Create the request
    request_id = pipeda.create_data_request(
        user_id=str(current_user.id),
        request_type=request_type,
        details=request_details
    )
    
    if request_id:
        flash(f'Your {request_type} request has been submitted. We will process it within 30 days as required by PIPEDA.', 'success')
    else:
        flash('There was an error submitting your request. Please try again.', 'danger')
    
    return redirect(url_for('privacy.data_request'))

@privacy_bp.route('/withdraw-consent', methods=['POST'])
@login_required
def withdraw_consent():
    """
    Withdraw consent for specific purposes.
    """
    # Check CSRF token
    if request.form.get('csrf_token') != session.get('csrf_token'):
        return jsonify({'success': False, 'message': 'Invalid request. Please try again.'})
    
    # Get purposes to withdraw
    purposes_data = request.json.get('purposes', [])
    
    # Convert to PurposeCategory enums
    purposes = []
    for purpose_str in purposes_data:
        try:
            purposes.append(PurposeCategory(purpose_str))
        except ValueError:
            continue
    
    # Check if core_service is included
    if PurposeCategory.CORE_SERVICE in purposes:
        return jsonify({
            'success': False, 
            'message': 'Core service consent cannot be withdrawn. If you wish to stop using the service, please request account deletion.'
        })
    
    # Get reason
    reason = request.json.get('reason', '')
    
    # Record withdrawal
    success = pipeda.withdraw_consent(
        user_id=str(current_user.id),
        purposes=purposes,
        request_details={'reason': reason}
    )
    
    if success:
        return jsonify({
            'success': True, 
            'message': 'Your consent preferences have been updated.'
        })
    else:
        return jsonify({
            'success': False, 
            'message': 'There was an error updating your consent preferences. Please try again.'
        })

@privacy_bp.route('/consent-status', methods=['GET'])
@login_required
def consent_status():
    """
    Get the current consent status for the user.
    """
    status = {}
    
    for purpose in PurposeCategory:
        status[purpose.value] = pipeda.has_valid_consent(str(current_user.id), purpose)
    
    return jsonify({
        'consent_status': status
    })

# Make consent checking function available in templates
@privacy_bp.app_context_processor
def inject_consent_checker():
    """Make consent checker available in templates."""
    return {'has_consent': has_consent}


def init_app(app):
    """
    Initialize the privacy module with the Flask app.
    """
    # Register the blueprint
    app.register_blueprint(privacy_bp)
    
    # Make sure data directories exist
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(os.path.join(data_dir, 'consents'), exist_ok=True)
    os.makedirs(os.path.join(data_dir, 'requests'), exist_ok=True)
    
    # Add consent checking to global context
    app.context_processor(inject_consent_checker)
    
    return app