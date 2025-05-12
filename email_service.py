"""
Email Service module for The Inner Architect

This module provides email sending capabilities for user authentication,
notifications, and other application features.
"""

import os
from flask import render_template
from logging_config import get_logger
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Get module-specific logger
logger = get_logger('email_service')

# Default sender email
DEFAULT_SENDER = 'noreply@theinnerarchitect.app'

def send_email(to_email, subject, html_content, text_content=None):
    """
    Send an email using SendGrid.
    
    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        html_content (str): HTML content of the email
        text_content (str, optional): Plain text content of the email
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    # Get API key from environment
    api_key = os.environ.get('SENDGRID_API_KEY')
    
    if not api_key:
        logger.warning("SendGrid API key not found. Email functionality is disabled.")
        # For development, we'll return True to not block the application flow
        # In production, you'd want to configure fallback email provider or retry mechanism
        logger.info(f"Would have sent email to: {to_email}, Subject: {subject}")
        return True
    
    try:
        # Create message
        from sendgrid.helpers.mail import Content
        
        message = Mail(
            from_email=DEFAULT_SENDER,
            to_emails=to_email,
            subject=subject,
            html_content=Content("text/html", html_content)
        )
        
        if text_content:
            # Add plain text content as a separate content
            message.add_content(Content("text/plain", text_content))
        
        # Send message
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        
        # Check response
        if response.status_code in (200, 201, 202):
            logger.info(f"Email sent successfully to {to_email}")
            return True
        else:
            logger.error(f"SendGrid API error: {response.status_code} - {response.body}")
            # Log the full response for debugging
            logger.error(f"Full response: {response}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        logger.exception("Full exception details:")
        return False

def send_verification_email(user, token, base_url):
    """
    Send an email verification email.
    
    Args:
        user (User): User object
        token (str): Verification token
        base_url (str): Base URL of the application
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    verify_url = f"{base_url}/verify-email/{token}"
    
    subject = "The Inner Architect - Verify Your Email"
    
    # HTML content
    html_content = f"""
    <div>
        <h2>Welcome to The Inner Architect!</h2>
        <p>Thank you for registering. Please verify your email address by clicking the link below:</p>
        <p><a href="{verify_url}">Verify Email Address</a></p>
        <p>This link will expire in 24 hours.</p>
        <p>If you did not create an account, please ignore this email.</p>
    </div>
    """
    
    # Plain text content
    text_content = f"""
    Welcome to The Inner Architect!
    
    Thank you for registering. Please verify your email address by clicking the link below:
    {verify_url}
    
    This link will expire in 24 hours.
    
    If you did not create an account, please ignore this email.
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
        bool: True if email sent successfully, False otherwise
    """
    reset_url = f"{base_url}/reset-password/{token}"
    
    subject = "The Inner Architect - Password Reset Request"
    
    # HTML content
    html_content = f"""
    <div>
        <h2>Password Reset Request</h2>
        <p>You recently requested to reset your password. Click the link below to reset it:</p>
        <p><a href="{reset_url}">Reset Your Password</a></p>
        <p>This link will expire in 1 hour.</p>
        <p>If you did not request a password reset, please ignore this email.</p>
    </div>
    """
    
    # Plain text content
    text_content = f"""
    Password Reset Request
    
    You recently requested to reset your password. Click the link below to reset it:
    {reset_url}
    
    This link will expire in 1 hour.
    
    If you did not request a password reset, please ignore this email.
    """
    
    return send_email(user.email, subject, html_content, text_content)

def send_practice_reminder(user, reminder_type, technique_name=None):
    """
    Send a practice reminder email.
    
    Args:
        user (User): User object
        reminder_type (str): Type of reminder
        technique_name (str, optional): Name of the technique to practice
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    subject = "The Inner Architect - Practice Reminder"
    
    # HTML content
    html_content = f"""
    <div>
        <h2>Practice Reminder</h2>
        <p>This is a reminder to practice your {reminder_type}.</p>
    """
    
    if technique_name:
        html_content += f"<p>Today's technique: <strong>{technique_name}</strong></p>"
    
    html_content += """
        <p>Regular practice is key to developing new mental habits!</p>
        <p><a href="#">Log in to The Inner Architect</a> to continue your practice.</p>
    </div>
    """
    
    # Plain text content
    text_content = f"""
    Practice Reminder
    
    This is a reminder to practice your {reminder_type}.
    """
    
    if technique_name:
        text_content += f"\nToday's technique: {technique_name}"
    
    text_content += """
    
    Regular practice is key to developing new mental habits!
    
    Log in to The Inner Architect to continue your practice.
    """
    
    return send_email(user.email, subject, html_content, text_content)

def send_subscription_confirmation(user, plan_name, amount, next_billing_date):
    """
    Send a subscription confirmation email.
    
    Args:
        user (User): User object
        plan_name (str): Name of the subscription plan
        amount (float): Subscription amount
        next_billing_date (datetime): Next billing date
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    next_billing_str = next_billing_date.strftime('%B %d, %Y')
    formatted_amount = f"${amount:.2f}"
    
    subject = "The Inner Architect - Subscription Confirmation"
    
    # HTML content
    html_content = f"""
    <div>
        <h2>Subscription Confirmation</h2>
        <p>Thank you for subscribing to The Inner Architect {plan_name} plan!</p>
        <p>Subscription details:</p>
        <ul>
            <li>Plan: <strong>{plan_name}</strong></li>
            <li>Amount: <strong>{formatted_amount}</strong></li>
            <li>Next billing date: <strong>{next_billing_str}</strong></li>
        </ul>
        <p>You can manage your subscription anytime from your account settings.</p>
        <p>We're excited to have you as a subscriber and hope you enjoy all the premium features!</p>
    </div>
    """
    
    # Plain text content
    text_content = f"""
    Subscription Confirmation
    
    Thank you for subscribing to The Inner Architect {plan_name} plan!
    
    Subscription details:
    - Plan: {plan_name}
    - Amount: {formatted_amount}
    - Next billing date: {next_billing_str}
    
    You can manage your subscription anytime from your account settings.
    
    We're excited to have you as a subscriber and hope you enjoy all the premium features!
    """
    
    return send_email(user.email, subject, html_content, text_content)