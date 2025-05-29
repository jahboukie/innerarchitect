"""
HIPAA-Compliant Security Routes for The Inner Architect

This module defines routes for security-related functionality including
MFA, access elevation, and security management.
"""

import pyotp
import json
import time
from io import BytesIO
from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    flash, current_app, session, jsonify, g, abort, Response
)
from flask_login import current_user, login_required
from werkzeug.security import check_password_hash

security_blueprint = Blueprint('security', __name__, url_prefix='/security')


@security_blueprint.route('/mfa/setup', methods=['GET', 'POST'])
@login_required
def mfa_setup():
    """Set up Multi-Factor Authentication"""
    # Get security manager
    security = current_app.extensions.get('security')
    if not security:
        current_app.logger.error("Security manager not initialized")
        abort(500, "Security system unavailable")
    
    # Check if MFA is already set up
    if hasattr(current_user, 'mfa_enabled') and current_user.mfa_enabled:
        flash("MFA is already enabled for your account.", "info")
        return redirect(url_for('profile.settings'))
    
    if request.method == 'POST':
        # Verify the setup code
        secret = session.get('mfa_setup_secret')
        if not secret:
            flash("MFA setup session expired. Please try again.", "danger")
            return redirect(url_for('security.mfa_setup'))
        
        code = request.form.get('code')
        if not code:
            flash("Please enter the verification code from your authenticator app.", "warning")
            return render_template('security/mfa_setup.html')
        
        # Verify the code
        if not security.verify_mfa_code(secret, code):
            flash("Invalid verification code. Please try again.", "danger")
            return render_template('security/mfa_setup.html')
        
        # Generate recovery codes
        recovery_codes = security.get_recovery_codes()
        hashed_codes = security.hash_recovery_codes(recovery_codes)
        
        # Save MFA configuration to user
        from models import User
        user = User.query.get(current_user.id)
        user.mfa_secret = secret
        user.mfa_enabled = True
        user.mfa_recovery_codes = hashed_codes
        
        # Save to database
        from database import db
        db.session.add(user)
        db.session.commit()
        
        # Log the event
        security.log_security_event('mfa_setup', {
            'method': 'totp'
        })
        
        # Clear setup session
        session.pop('mfa_setup_secret', None)
        
        # Set MFA as verified for this session
        session['mfa_verified'] = True
        session['mfa_verified_at'] = int(time.time())
        
        # Show recovery codes to user
        return render_template('security/mfa_recovery_codes.html', 
                              recovery_codes=recovery_codes)
    else:
        # Generate a new MFA secret
        secret = security.generate_mfa_secret()
        
        # Store in session for verification
        session['mfa_setup_secret'] = secret
        
        # Generate QR code
        qr_buffer = security.get_mfa_qr_code(current_user, secret)
        qr_data = qr_buffer.read()
        
        # Return setup page with QR code
        return render_template('security/mfa_setup.html', 
                              secret=secret,
                              qr_code=qr_data)


@security_blueprint.route('/mfa/verify', methods=['GET', 'POST'])
@login_required
def mfa_verify():
    """Verify MFA for sensitive operations"""
    # Get security manager
    security = current_app.extensions.get('security')
    if not security:
        current_app.logger.error("Security manager not initialized")
        abort(500, "Security system unavailable")
    
    # Check if user has MFA enabled
    if not hasattr(current_user, 'mfa_enabled') or not current_user.mfa_enabled:
        # If this is a high-risk operation, use alternative verification
        risk_score = security.calculate_risk_score(current_user, 'view_phi')
        if risk_score <= 7:
            # Low risk, no MFA needed
            session['mfa_verified'] = True
            session['mfa_verified_at'] = int(time.time())
            
            # Redirect to original destination
            next_url = session.pop('next_url', url_for('main.index'))
            return redirect(next_url)
        
        # For high-risk operations without MFA, require password verification
        if request.method == 'POST':
            password = request.form.get('password')
            if check_password_hash(current_user.password, password):
                # Password verified
                session['mfa_verified'] = True
                session['mfa_verified_at'] = int(time.time())
                
                security.log_security_event('password_verification', {
                    'success': True
                })
                
                # Redirect to original destination
                next_url = session.pop('next_url', url_for('main.index'))
                return redirect(next_url)
            else:
                flash("Invalid password. Please try again.", "danger")
                security.log_security_event('password_verification', {
                    'success': False
                })
                
        return render_template('security/password_verify.html')
    
    if request.method == 'POST':
        # Verify the MFA code
        code = request.form.get('code')
        recovery = request.form.get('recovery_code')
        
        if code:
            # Verify TOTP code
            if security.verify_mfa_code(current_user.mfa_secret, code):
                # MFA verified
                session['mfa_verified'] = True
                session['mfa_verified_at'] = int(time.time())
                
                security.log_security_event('mfa_success', {
                    'method': 'totp'
                })
                
                # Redirect to original destination
                next_url = session.pop('next_url', url_for('main.index'))
                return redirect(next_url)
            else:
                flash("Invalid verification code. Please try again.", "danger")
                security.log_security_event('mfa_failure', {
                    'method': 'totp'
                })
        elif recovery:
            # Verify recovery code
            valid, updated_codes = security.verify_recovery_code(
                recovery, current_user.mfa_recovery_codes
            )
            
            if valid:
                # Update recovery codes
                from models import User
                from database import db
                
                user = User.query.get(current_user.id)
                user.mfa_recovery_codes = updated_codes
                db.session.add(user)
                db.session.commit()
                
                # MFA verified
                session['mfa_verified'] = True
                session['mfa_verified_at'] = int(time.time())
                
                security.log_security_event('mfa_success', {
                    'method': 'recovery_code'
                })
                
                flash("Recovery code accepted. You have used 1 of your recovery codes.", "warning")
                
                # Redirect to original destination
                next_url = session.pop('next_url', url_for('main.index'))
                return redirect(next_url)
            else:
                flash("Invalid recovery code. Please try again.", "danger")
                security.log_security_event('mfa_failure', {
                    'method': 'recovery_code'
                })
        else:
            flash("Please enter a verification code or recovery code.", "warning")
    
    return render_template('security/mfa_verify.html')


@security_blueprint.route('/mfa/disable', methods=['GET', 'POST'])
@login_required
def mfa_disable():
    """Disable MFA for a user account"""
    # Get security manager
    security = current_app.extensions.get('security')
    if not security:
        current_app.logger.error("Security manager not initialized")
        abort(500, "Security system unavailable")
    
    # Check if MFA is enabled
    if not hasattr(current_user, 'mfa_enabled') or not current_user.mfa_enabled:
        flash("MFA is not enabled for your account.", "info")
        return redirect(url_for('profile.settings'))
    
    if request.method == 'POST':
        # Verify password
        password = request.form.get('password')
        if not password:
            flash("Please enter your password to disable MFA.", "warning")
            return render_template('security/mfa_disable.html')
        
        if not check_password_hash(current_user.password, password):
            flash("Invalid password. Please try again.", "danger")
            security.log_security_event('mfa_disable_attempt', {
                'success': False,
                'reason': 'invalid_password'
            })
            return render_template('security/mfa_disable.html')
        
        # Disable MFA
        from models import User
        from database import db
        
        user = User.query.get(current_user.id)
        user.mfa_secret = None
        user.mfa_enabled = False
        user.mfa_recovery_codes = None
        
        db.session.add(user)
        db.session.commit()
        
        # Log the event
        security.log_security_event('mfa_disable', {
            'success': True
        })
        
        # Clear MFA session
        session.pop('mfa_verified', None)
        session.pop('mfa_verified_at', None)
        
        flash("Multi-Factor Authentication has been disabled for your account.", "success")
        return redirect(url_for('profile.settings'))
    
    return render_template('security/mfa_disable.html')


@security_blueprint.route('/elevate', methods=['GET', 'POST'])
@login_required
def elevate_access():
    """Elevate access for sensitive operations"""
    # Get security manager
    security = current_app.extensions.get('security')
    if not security:
        current_app.logger.error("Security manager not initialized")
        abort(500, "Security system unavailable")
    
    if request.method == 'POST':
        # Verify password and MFA if enabled
        password = request.form.get('password')
        mfa_code = request.form.get('code')
        
        # Check password
        if not check_password_hash(current_user.password, password):
            flash("Invalid password. Please try again.", "danger")
            security.log_security_event('access_elevation_attempt', {
                'success': False,
                'reason': 'invalid_password'
            })
            return render_template('security/elevate_access.html')
        
        # Check MFA if enabled
        if hasattr(current_user, 'mfa_enabled') and current_user.mfa_enabled:
            if not mfa_code:
                flash("Please enter your MFA verification code.", "warning")
                return render_template('security/elevate_access.html')
                
            if not security.verify_mfa_code(current_user.mfa_secret, mfa_code):
                flash("Invalid verification code. Please try again.", "danger")
                security.log_security_event('access_elevation_attempt', {
                    'success': False,
                    'reason': 'invalid_mfa'
                })
                return render_template('security/elevate_access.html')
        
        # Grant elevated access
        session['elevated_access_until'] = int(time.time()) + ELEVATED_ACCESS_DURATION
        
        # Log the event
        security.log_security_event('access_elevation', {
            'success': True,
            'duration_minutes': ELEVATED_ACCESS_DURATION // 60
        })
        
        # Redirect to original destination
        next_url = session.pop('next_url', url_for('main.index'))
        return redirect(next_url)
    
    return render_template('security/elevate_access.html')


@security_blueprint.route('/break-glass/init', methods=['GET', 'POST'])
@login_required
def break_glass_init():
    """Initialize break-glass emergency access protocol"""
    # Get security manager
    security = current_app.extensions.get('security')
    if not security:
        current_app.logger.error("Security manager not initialized")
        abort(500, "Security system unavailable")
    
    # Check if user is authorized for break-glass
    if not security.has_permission(current_user, 'break_glass'):
        flash("You are not authorized for emergency access.", "danger")
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # Verify password
        password = request.form.get('password')
        reason = request.form.get('reason')
        
        if not reason or len(reason) < 10:
            flash("Please provide a detailed reason for emergency access.", "warning")
            return render_template('security/break_glass.html')
        
        if not check_password_hash(current_user.password, password):
            flash("Invalid password. Please try again.", "danger")
            security.log_security_event('break_glass_attempt', {
                'success': False,
                'reason': 'invalid_password'
            })
            return render_template('security/break_glass.html')
        
        # Grant break-glass access
        session['break_glass_active'] = True
        session['break_glass_reason'] = reason
        session['break_glass_start'] = int(time.time())
        
        # Log the event
        security.log_security_event('break_glass', {
            'success': True,
            'reason': reason
        })
        
        # Send alert to administrators (would be implemented in a real system)
        # notify_administrators('break_glass', current_user.id, reason)
        
        # Redirect to original destination
        next_url = session.pop('next_url', url_for('main.index'))
        flash("EMERGENCY ACCESS ACTIVATED. All actions will be extensively audited.", "danger")
        return redirect(next_url)
    
    return render_template('security/break_glass.html')


@security_blueprint.route('/break-glass/end', methods=['POST'])
@login_required
def break_glass_end():
    """End break-glass emergency access"""
    # Get security manager
    security = current_app.extensions.get('security')
    if not security:
        current_app.logger.error("Security manager not initialized")
        abort(500, "Security system unavailable")
    
    # Check if break-glass is active
    if not session.get('break_glass_active'):
        flash("Emergency access is not currently active.", "info")
        return redirect(url_for('main.index'))
    
    # Record end time and duration
    start_time = session.get('break_glass_start', int(time.time()))
    duration = int(time.time()) - start_time
    reason = session.get('break_glass_reason', 'No reason provided')
    
    # Clear break-glass session
    session.pop('break_glass_active', None)
    session.pop('break_glass_reason', None)
    session.pop('break_glass_start', None)
    
    # Log the event
    security.log_security_event('break_glass_end', {
        'success': True,
        'duration_seconds': duration,
        'original_reason': reason
    })
    
    flash("Emergency access has been deactivated.", "success")
    return redirect(url_for('main.index'))


# Create routes for security templates
@security_blueprint.route('/templates/mfa_setup')
@login_required
def mfa_setup_template():
    """Route for MFA setup template for the analytics dashboard to use"""
    return render_template('security/mfa_setup.html')


@security_blueprint.route('/templates/mfa_verify')
@login_required
def mfa_verify_template():
    """Route for MFA verification template for the analytics dashboard to use"""
    return render_template('security/mfa_verify.html')


@security_blueprint.route('/templates/elevate_access')
@login_required
def elevate_access_template():
    """Route for access elevation template for the analytics dashboard to use"""
    return render_template('security/elevate_access.html')


@security_blueprint.route('/templates/break_glass')
@login_required
def break_glass_template():
    """Route for break glass template for the analytics dashboard to use"""
    return render_template('security/break_glass.html')