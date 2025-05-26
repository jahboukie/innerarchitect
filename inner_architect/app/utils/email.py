import os
import logging
from typing import Optional, Dict, Any, List

from flask import current_app, render_template, url_for
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

# Set up logger
logger = logging.getLogger(__name__)

def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    from_email: Optional[str] = None
) -> bool:
    """
    Send an email using SendGrid.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML content of the email
        from_email: Sender email address (defaults to app config)
        
    Returns:
        Success flag
    """
    try:
        # Get SendGrid API key
        api_key = current_app.config.get('SENDGRID_API_KEY') or os.environ.get('SENDGRID_API_KEY')
        if not api_key:
            logger.error("SendGrid API key not configured")
            return False
        
        # Get default from email
        from_email = from_email or current_app.config.get('DEFAULT_FROM_EMAIL') or os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@example.com')
        
        # Create mail message
        message = Mail(
            from_email=Email(from_email),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_content)
        )
        
        # Send email
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        
        # Log result
        status_code = response.status_code
        logger.info(f"Email sent to {to_email}, subject: {subject}, status: {status_code}")
        
        return status_code >= 200 and status_code < 300
        
    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {str(e)}")
        return False

def send_verification_email(user) -> bool:
    """
    Send an email verification link to a user.
    
    Args:
        user: User object with email and verification_token
        
    Returns:
        Success flag
    """
    try:
        # Generate verification URL
        verify_url = url_for('auth.verify_email', token=user.verification_token, _external=True)
        
        # Render email template
        html_content = render_template(
            'email/verify_email.html',
            user=user,
            verify_url=verify_url
        )
        
        # Send email
        return send_email(
            to_email=user.email,
            subject="Verify Your Email - The Inner Architect",
            html_content=html_content
        )
        
    except Exception as e:
        logger.error(f"Error sending verification email to {user.email}: {str(e)}")
        return False

def send_password_reset_email(user) -> bool:
    """
    Send a password reset link to a user.
    
    Args:
        user: User object with email and reset_password_token
        
    Returns:
        Success flag
    """
    try:
        # Generate reset URL
        reset_url = url_for('auth.reset_password', token=user.reset_password_token, _external=True)
        
        # Render email template
        html_content = render_template(
            'email/reset_password.html',
            user=user,
            reset_url=reset_url
        )
        
        # Send email
        return send_email(
            to_email=user.email,
            subject="Reset Your Password - The Inner Architect",
            html_content=html_content
        )
        
    except Exception as e:
        logger.error(f"Error sending password reset email to {user.email}: {str(e)}")
        return False

def send_welcome_email(user) -> bool:
    """
    Send a welcome email to a newly registered user.
    
    Args:
        user: User object with email
        
    Returns:
        Success flag
    """
    try:
        # Render email template
        html_content = render_template(
            'email/welcome.html',
            user=user
        )
        
        # Send email
        return send_email(
            to_email=user.email,
            subject="Welcome to The Inner Architect!",
            html_content=html_content
        )
        
    except Exception as e:
        logger.error(f"Error sending welcome email to {user.email}: {str(e)}")
        return False