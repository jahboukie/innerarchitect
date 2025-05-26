import os
import uuid
import secrets
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlencode

from flask import (
    Blueprint, render_template, request, jsonify, session, flash,
    redirect, url_for, g, current_app
)
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from app import db
from app.models.user import User, PrivacySettings, UserPreferences
from app.utils.email import send_verification_email, send_password_reset_email

# Create blueprint
auth = Blueprint('auth', __name__)

# Form definitions (would usually be in a separate forms.py file)
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        'Confirm Password', validators=[DataRequired(), EqualTo('password')]
    )
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    agree_terms = BooleanField('I agree to the Terms and Conditions', validators=[DataRequired()])
    submit = SubmitField('Register')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different email or sign in.')

class RequestResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if not user:
            raise ValidationError('No account found with that email. Please register first.')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        'Confirm Password', validators=[DataRequired(), EqualTo('password')]
    )
    submit = SubmitField('Reset Password')

class DeleteAccountForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    confirm = BooleanField('I understand this action cannot be undone', validators=[DataRequired()])
    submit = SubmitField('Delete My Account')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        'Confirm New Password', validators=[DataRequired(), EqualTo('new_password')]
    )
    submit = SubmitField('Change Password')

class ResendVerificationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Resend Verification Email')

# Auth routes
@auth.route('/login-check')
def login_check():
    """Check if user is already logged in and redirect appropriately."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    return redirect(url_for('auth.login'))

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        if user and user.check_password(form.password.data):
            # Check if email is verified
            if not user.email_verified:
                flash('Please verify your email before logging in.', 'warning')
                return redirect(url_for('auth.resend_verification'))
            
            # Log in the user
            login_user(user, remember=form.remember_me.data)
            
            # Redirect to the next page or dashboard
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('main.index')
            
            return redirect(next_page)
        else:
            flash('Invalid email or password. Please try again.', 'danger')
    
    return render_template('auth/login.html', form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Create a new user
        user = User(
            id=str(uuid.uuid4()),
            email=form.email.data.lower(),
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            auth_provider='email',
            email_verified=False
        )
        
        # Set password
        user.set_password(form.password.data)
        
        # Generate verification token
        token = secrets.token_hex(32)
        user.verification_token = token
        user.verification_token_expiry = datetime.utcnow() + timedelta(hours=24)
        
        # Save user to database
        db.session.add(user)
        
        # Create privacy settings
        privacy = PrivacySettings(user_id=user.id)
        db.session.add(privacy)
        
        # Create user preferences
        preferences = UserPreferences(user_id=user.id)
        db.session.add(preferences)
        
        db.session.commit()
        
        # Send verification email
        send_verification_email(user)
        
        flash('Registration successful! Please check your email to verify your account.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)

@auth.route('/logout')
def logout():
    """Log out the current user."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@auth.route('/verify-email/<token>')
def verify_email(token):
    """Verify a user's email using the verification token."""
    if current_user.is_authenticated and current_user.email_verified:
        flash('Your email is already verified.', 'info')
        return redirect(url_for('main.index'))
    
    # Find user with matching token
    user = User.query.filter_by(verification_token=token).first()
    
    if not user:
        flash('Invalid or expired verification link.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Check if token has expired
    if user.verification_token_expiry < datetime.utcnow():
        flash('Verification link has expired. Please request a new one.', 'warning')
        return redirect(url_for('auth.resend_verification'))
    
    # Mark email as verified
    user.email_verified = True
    user.verification_token = None
    user.verification_token_expiry = None
    
    db.session.commit()
    
    flash('Email verified successfully! You can now log in.', 'success')
    return redirect(url_for('auth.login'))

@auth.route('/resend-verification', methods=['GET', 'POST'])
def resend_verification():
    """Resend verification email to user."""
    if current_user.is_authenticated and current_user.email_verified:
        flash('Your email is already verified.', 'info')
        return redirect(url_for('main.index'))
    
    form = ResendVerificationForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        if user:
            if user.email_verified:
                flash('Your email is already verified. Please log in.', 'info')
                return redirect(url_for('auth.login'))
            
            # Generate new verification token
            token = secrets.token_hex(32)
            user.verification_token = token
            user.verification_token_expiry = datetime.utcnow() + timedelta(hours=24)
            
            db.session.commit()
            
            # Send verification email
            send_verification_email(user)
            
            flash('A new verification email has been sent. Please check your inbox.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('No account found with that email address.', 'danger')
    
    return render_template('auth/resend_verification.html', form=form)

@auth.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    """Request a password reset."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RequestResetForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        if user:
            # Generate reset token
            token = secrets.token_hex(32)
            user.reset_password_token = token
            user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
            
            db.session.commit()
            
            # Send password reset email
            send_password_reset_email(user)
            
            flash('A password reset email has been sent. Please check your inbox.', 'info')
            return redirect(url_for('auth.login'))
        else:
            flash('No account found with that email address.', 'danger')
    
    return render_template('auth/reset_password_request.html', form=form)

@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password using a reset token."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    # Find user with matching token
    user = User.query.filter_by(reset_password_token=token).first()
    
    if not user:
        flash('Invalid or expired reset link.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Check if token has expired
    if user.reset_token_expiry < datetime.utcnow():
        flash('Reset link has expired. Please request a new one.', 'warning')
        return redirect(url_for('auth.reset_password_request'))
    
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        # Update password
        user.set_password(form.password.data)
        user.reset_password_token = None
        user.reset_token_expiry = None
        
        db.session.commit()
        
        flash('Your password has been reset! You can now log in with your new password.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', form=form)

@auth.route('/delete-account', methods=['GET', 'POST'])
@login_required
def delete_account():
    """Delete user account page."""
    form = DeleteAccountForm()
    
    if form.validate_on_submit():
        if current_user.check_password(form.password.data):
            # Get email for flash message
            email = current_user.email
            
            # Mark account as deleted (anonymize data)
            current_user.email = f"deleted-{int(datetime.utcnow().timestamp())}@example.com"
            current_user.first_name = "Deleted"
            current_user.last_name = "User"
            current_user.profile_image_url = None
            current_user.password_hash = None
            current_user.email_verified = False
            current_user.verification_token = None
            current_user.verification_token_expiry = None
            current_user.reset_password_token = None
            current_user.reset_token_expiry = None
            current_user.auth_provider = 'deleted'
            
            db.session.commit()
            
            # Log out the user
            logout_user()
            
            flash(f'Your account ({email}) has been deleted.', 'info')
            return redirect(url_for('main.index'))
        else:
            flash('Incorrect password. Account deletion canceled.', 'danger')
    
    return render_template('auth/delete_account.html', form=form)

@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password page."""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            # Update password
            current_user.set_password(form.new_password.data)
            db.session.commit()
            
            flash('Your password has been updated!', 'success')
            return redirect(url_for('main.profile'))
        else:
            flash('Incorrect current password. Password change canceled.', 'danger')
    
    return render_template('auth/change_password.html', form=form)

@auth.route('/link-account', methods=['GET', 'POST'])
def link_account():
    """Link different authentication methods to the same account."""
    # This would be implemented based on the specific auth providers
    flash('Account linking is not yet implemented.', 'info')
    return redirect(url_for('main.profile'))

@auth.route('/unlink-provider/<provider>', methods=['POST'])
@login_required
def unlink_provider(provider):
    """Unlink an authentication provider from the account."""
    # This would be implemented based on the specific auth providers
    flash(f'Unlinking provider {provider} is not yet implemented.', 'info')
    return redirect(url_for('main.profile'))