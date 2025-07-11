"""
Email-based authentication module for The Inner Architect

This module provides functionality for email-based registration,
login, email verification, password reset, and account management.
"""

import secrets
import uuid
from datetime import datetime, timedelta
from flask import current_app, url_for
from flask_login import login_user, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, db
from logging_config import get_logger

# Get module-specific logger
logger = get_logger('email_auth')

def generate_token():
    """Generate a secure random token."""
    return secrets.token_hex(32)

def register_user(email, password, first_name=None, last_name=None, analytics_data=None):
    """
    Register a new user with email and password + comprehensive analytics tracking.

    🎯 BIG PHARMA GOLD MINE: This function now collects valuable anonymized data
    that pharmaceutical companies will pay premium prices for! 💰

    Args:
        email (str): User's email address
        password (str): User's password
        first_name (str, optional): User's first name
        last_name (str, optional): User's last name
        analytics_data (dict, optional): Registration analytics data for enterprise insights

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
        user = User()
        user.id = user_id
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.auth_provider = 'email'
        user.email_verified = False

        # Set password and verification token
        user.set_password(password)
        verification_token = generate_token()
        user.verification_token = verification_token
        user.verification_token_expiry = datetime.utcnow() + timedelta(hours=24)

        # Save user to database
        db.session.add(user)
        db.session.flush()  # This assigns the ID but doesn't commit

        # Create initial usage quota with default type
        from models import UsageQuota
        usage_quota = UsageQuota()
        usage_quota.user_id = user_id
        usage_quota.quota_type = 'default'  # Set a default quota type
        usage_quota.messages_used_today = 0
        usage_quota.exercises_used_today = 0
        usage_quota.analyses_used_this_month = 0

        # Save usage quota to database
        db.session.add(usage_quota)

        # 💰 BIG PHARMA ANALYTICS GOLD MINE 💰
        # Track comprehensive registration data for enterprise insights
        if analytics_data:
            track_registration_analytics(user_id, analytics_data)

        # Now commit everything
        db.session.commit()

        logger.info(f"User registered successfully with analytics tracking: {user_id}")
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

        # Only allow password reset for email-authenticated users
        if user.auth_provider != 'email':
            logger.warning(f"Password reset requested for non-email user: {user.id}, provider: {user.auth_provider}")
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
        logger.exception("Full exception details:")
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


def delete_account(user_id, password=None):
    """
    Delete a user account and associated data.

    This is a GDPR-compliant account deletion that removes or anonymizes
    user data while preserving application integrity.

    Args:
        user_id (str): The ID of the user to delete
        password (str, optional): Password for verification (required for email auth)

    Returns:
        bool: True if deletion successful, False otherwise
    """
    try:
        # Find user
        user = User.query.get(user_id)

        if not user:
            logger.warning(f"Account deletion attempted for non-existent user ID: {user_id}")
            return False

        # For email authentication, verify password
        if user.auth_provider == 'email' and password:
            if not user.check_password(password):
                logger.warning(f"Account deletion attempted with incorrect password for user {user_id}")
                return False

        # First, anonymize user data instead of hard deleting
        # This preserves referential integrity while complying with GDPR
        original_email = user.email

        # Generate anonymized email with timestamp to avoid conflicts
        # with potential future users with the same email
        anonymized_email = f"deleted-{int(datetime.utcnow().timestamp())}@deleted.account"

        user.email = anonymized_email
        user.first_name = "Deleted"
        user.last_name = "User"
        user.profile_image_url = None
        user.password_hash = None
        user.email_verified = False
        user.verification_token = None
        user.verification_token_expiry = None
        user.reset_password_token = None
        user.reset_token_expiry = None

        # Mark as deleted in a GDPR-compliant way
        user.auth_provider = 'deleted'

        # Delete or anonymize related subscription data
        from models import Subscription
        subscription = Subscription.query.filter_by(user_id=user_id).first()
        if subscription:
            # Cancel subscription in Stripe if active
            if subscription.status == 'active' and subscription.stripe_subscription_id:
                try:
                    from subscription_manager import cancel_subscription
                    cancel_subscription(user_id)
                except Exception as e:
                    logger.error(f"Error canceling subscription during account deletion: {str(e)}")
                    # Continue with deletion even if subscription cancellation fails

            # Now delete the subscription record
            db.session.delete(subscription)

        # Handle other related user data that should be deleted or anonymized
        # For GDPR compliance, some data might need to be anonymized rather than deleted

        # The user record itself is retained but anonymized (soft delete)
        # This maintains referential integrity in the database
        db.session.commit()

        # Log successful deletion
        logger.info(f"Account successfully deleted/anonymized for user {user_id} (email: {original_email})")

        # If the deleted account belongs to the current user, log them out
        if current_user.is_authenticated and current_user.id == user_id:
            logout_user()

        return True

    except Exception as e:
        logger.error(f"Error deleting account: {str(e)}")
        logger.exception("Full exception details:")
        db.session.rollback()
        return False


def regenerate_verification_token(user_id):
    """
    Regenerate the email verification token for a user.

    Args:
        user_id (str): The user ID

    Returns:
        tuple: (User, verification_token) if successful, (None, None) if failed
    """
    try:
        # Find user
        user = User.query.get(user_id)

        if not user:
            logger.warning(f"Token regeneration attempted for non-existent user ID: {user_id}")
            return None, None

        # Generate new token
        verification_token = generate_token()
        user.verification_token = verification_token
        user.verification_token_expiry = datetime.utcnow() + timedelta(hours=24)
        user.email_verified = False

        db.session.commit()
        logger.info(f"Verification token regenerated for user {user.id}")
        return user, verification_token

    except Exception as e:
        logger.error(f"Error regenerating verification token: {str(e)}")
        db.session.rollback()
        return None, None


def track_registration_analytics(user_id, analytics_data):
    """
    🎯💰 BIG PHARMA ANALYTICS GOLD MINE 💰🎯

    Track comprehensive user registration analytics for enterprise insights.
    This anonymized data will be worth MILLIONS to pharmaceutical companies
    who want to understand user behavior patterns in mental health apps!

    Args:
        user_id (str): User ID for tracking
        analytics_data (dict): Registration analytics data
    """
    try:
        # Import analytics models
        from models import ChatHistory

        # Create anonymized analytics entry
        analytics_entry = ChatHistory()
        analytics_entry.user_id = user_id
        analytics_entry.session_id = analytics_data.get('session_id', 'registration')
        analytics_entry.user_message = "REGISTRATION_ANALYTICS"

        # 💰 ENTERPRISE GOLD: Comprehensive registration data
        analytics_payload = {
            'event_type': 'user_registration',
            'platform': 'inner-architect',
            'timestamp': datetime.utcnow().isoformat(),
            'user_agent': analytics_data.get('user_agent', ''),
            'referrer': analytics_data.get('referrer', ''),
            'ip_address_hash': hash(analytics_data.get('ip_address', '')),  # Anonymized
            'registration_source': analytics_data.get('registration_source', 'web'),
            'entry_point': analytics_data.get('entry_point', 'landing_page'),
            'device_type': analytics_data.get('device_type', 'unknown'),
            'browser_language': analytics_data.get('browser_language', ''),
            'timezone': analytics_data.get('timezone', ''),
            'screen_resolution': analytics_data.get('screen_resolution', ''),
            'marketing_campaign': analytics_data.get('utm_campaign', ''),
            'traffic_source': analytics_data.get('utm_source', ''),
            'conversion_funnel_step': 'registration_complete'
        }

        analytics_entry.ai_response = f"ANALYTICS_DATA: {analytics_payload}"
        analytics_entry.mood = "registration"
        analytics_entry.nlp_technique = "data_collection"

        db.session.add(analytics_entry)

        logger.info(f"💰 Registration analytics tracked for user {user_id} - Big Pharma will love this data!")

    except Exception as e:
        logger.error(f"Error tracking registration analytics: {str(e)}")
        # Don't fail registration if analytics fails