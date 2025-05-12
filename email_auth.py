"""
Email-based authentication module for The Inner Architect

This module provides functionality for email-based registration,
login, email verification, and password reset.
"""

import secrets
import uuid
from datetime import datetime, timedelta
from flask import current_app, url_for
from flask_login import login_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, db
from logging_config import get_logger

# Get module-specific logger
logger = get_logger('email_auth')

def generate_token():
    """Generate a secure random token."""
    return secrets.token_hex(32)

def register_user(email, password, first_name=None, last_name=None):
    """
    Register a new user with email and password.
    
    Args:
        email (str): User's email address
        password (str): User's password
        first_name (str, optional): User's first name
        last_name (str, optional): User's last name
        
    Returns:
        tuple: (User, verification_token) if successful, (None, None) if failed
    """
    try:
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            logger.warning(f"Registration attempt with existing email: {email}")
            return None, None
            
        # Generate a unique user ID
        user_id = str(uuid.uuid4())
        
        # Create new user
        user = User(
            id=user_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            auth_provider='email',
            email_verified=False
        )
        
        # Set password and verification token
        user.set_password(password)
        verification_token = generate_token()
        user.verification_token = verification_token
        user.verification_token_expiry = datetime.utcnow() + timedelta(hours=24)
        
        # Save to database
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"User registered successfully: {user_id}")
        return user, verification_token
        
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        db.session.rollback()
        return None, None

def verify_email(token):
    """
    Verify a user's email using the verification token.
    
    Args:
        token (str): Email verification token
        
    Returns:
        bool: True if verified successfully, False otherwise
    """
    try:
        # Find user with matching token
        user = User.query.filter_by(verification_token=token).first()
        
        if not user:
            logger.warning(f"Email verification attempted with invalid token")
            return False
            
        # Check if token has expired
        if user.verification_token_expiry < datetime.utcnow():
            logger.warning(f"Email verification attempted with expired token for user {user.id}")
            return False
            
        # Mark email as verified
        user.email_verified = True
        user.verification_token = None
        user.verification_token_expiry = None
        
        db.session.commit()
        logger.info(f"Email verified for user {user.id}")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying email: {str(e)}")
        db.session.rollback()
        return False

def login_with_email(email, password, remember=False):
    """
    Log in a user with email and password.
    
    Args:
        email (str): User's email
        password (str): User's password
        remember (bool): Whether to remember the user session
        
    Returns:
        User: User object if login successful, None otherwise
    """
    try:
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            logger.warning(f"Failed login attempt for email: {email}")
            return None
            
        # Check if email is verified (optional - can be enforced or not)
        if not user.email_verified:
            logger.warning(f"Login attempt with unverified email: {email}")
            # We're still allowing login, but this could be changed to return None
            
        # Log the user in
        login_user(user, remember=remember)
        logger.info(f"User logged in successfully: {user.id}")
        return user
        
    except Exception as e:
        logger.error(f"Error logging in user: {str(e)}")
        return None

def request_password_reset(email):
    """
    Create a password reset token for a user.
    
    Args:
        email (str): User's email address
        
    Returns:
        tuple: (User, reset_token) if successful, (None, None) if failed
    """
    try:
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        if not user:
            logger.warning(f"Password reset requested for non-existent email: {email}")
            return None, None
            
        # Generate reset token
        reset_token = generate_token()
        user.reset_password_token = reset_token
        user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
        
        db.session.commit()
        logger.info(f"Password reset token generated for user {user.id}")
        return user, reset_token
        
    except Exception as e:
        logger.error(f"Error requesting password reset: {str(e)}")
        db.session.rollback()
        return None, None

def reset_password(token, new_password):
    """
    Reset a user's password using a reset token.
    
    Args:
        token (str): Password reset token
        new_password (str): New password
        
    Returns:
        bool: True if reset successful, False otherwise
    """
    try:
        # Find user with matching token
        user = User.query.filter_by(reset_password_token=token).first()
        
        if not user:
            logger.warning(f"Password reset attempted with invalid token")
            return False
            
        # Check if token has expired
        if user.reset_token_expiry < datetime.utcnow():
            logger.warning(f"Password reset attempted with expired token for user {user.id}")
            return False
            
        # Update password
        user.set_password(new_password)
        user.reset_password_token = None
        user.reset_token_expiry = None
        
        db.session.commit()
        logger.info(f"Password reset successful for user {user.id}")
        return True
        
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}")
        db.session.rollback()
        return False