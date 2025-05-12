"""
Email service module for The Inner Architect

This module provides functionality for sending emails using SendGrid.
"""

import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from logging_config import get_logger

# Get module-specific logger
logger = get_logger('email_service')

def send_email(to_email, subject, html_content, text_content=None):
    """
    Send an email using SendGrid.
    
    Args:
        to_email (str): Recipient's email address
        subject (str): Email subject
        html_content (str): HTML content of the email
        text_content (str, optional): Plain text content of the email
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        # Get API key from environment variables
        api_key = os.environ.get('SENDGRID_API_KEY')
        
        if not api_key:
            logger.error("SendGrid API key not found in environment variables")
            return False
            
        # Get from email address
        from_email = os.environ.get('FROM_EMAIL', 'noreply@innerarchitect.app')
        
        # Create message
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content,
            plain_text_content=text_content or ''
        )
        
        # Send message
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        
        # Log result
        logger.info(f"Email sent to {to_email}, status code: {response.status_code}")
        return response.status_code in (200, 201, 202)
        
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False

def send_verification_email(user, token, base_url):
    """
    Send an email verification email.
    
    Args:
        user (User): User object
        token (str): Verification token
        base_url (str): Base URL of the application
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    verify_url = f"{base_url}/verify-email/{token}"
    
    subject = "Verify Your Email - The Inner Architect"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Welcome to The Inner Architect!</h2>
        <p>Thank you for registering. Please verify your email address by clicking the button below:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{verify_url}" style="background-color: #635bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
                Verify Email Address
            </a>
        </div>
        <p>If the button doesn't work, copy and paste the following link into your browser:</p>
        <p><a href="{verify_url}">{verify_url}</a></p>
        <p>This link will expire in 24 hours.</p>
        <p>If you didn't register for an account, you can safely ignore this email.</p>
        <hr style="margin: 30px 0;">
        <p style="color: #666; font-size: 12px;">© 2025 The Inner Architect</p>
    </div>
    """
    
    text_content = f"""
    Welcome to The Inner Architect!
    
    Thank you for registering. Please verify your email address by visiting the following link:
    
    {verify_url}
    
    This link will expire in 24 hours.
    
    If you didn't register for an account, you can safely ignore this email.
    
    © 2025 The Inner Architect
    """
    
    return send_email(user.email, subject, html_content, text_content)

def send_password_reset_email(user, token, base_url):
    """
    Send a password reset email.
    
    Args:
        user (User): User object
        token (str): Password reset token
        base_url (str): Base URL of the application
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    reset_url = f"{base_url}/reset-password/{token}"
    
    subject = "Reset Your Password - The Inner Architect"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Password Reset Request</h2>
        <p>You recently requested to reset your password for your Inner Architect account. Click the button below to reset it:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" style="background-color: #635bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
                Reset Password
            </a>
        </div>
        <p>If the button doesn't work, copy and paste the following link into your browser:</p>
        <p><a href="{reset_url}">{reset_url}</a></p>
        <p>This link will expire in 1 hour.</p>
        <p>If you didn't request a password reset, you can safely ignore this email.</p>
        <hr style="margin: 30px 0;">
        <p style="color: #666; font-size: 12px;">© 2025 The Inner Architect</p>
    </div>
    """
    
    text_content = f"""
    Password Reset Request
    
    You recently requested to reset your password for your Inner Architect account. Please visit the following link to reset it:
    
    {reset_url}
    
    This link will expire in 1 hour.
    
    If you didn't request a password reset, you can safely ignore this email.
    
    © 2025 The Inner Architect
    """
    
    return send_email(user.email, subject, html_content, text_content)