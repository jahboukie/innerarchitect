"""
Forms module for The Inner Architect

This module defines WTForms classes for various forms used in the application.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from models import User

class LoginForm(FlaskForm):
    """Form for user login."""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Log In')

class RegistrationForm(FlaskForm):
    """Form for user registration."""
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name')
    last_name = StringField('Last Name')
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Register')
    
    def validate_email(self, email):
        """Validate that the email is not already registered."""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('This email is already registered. Please use a different email or log in.')

class RequestResetForm(FlaskForm):
    """Form for requesting a password reset."""
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')
    
    def validate_email(self, email):
        """Validate that the email exists in the database."""
        user = User.query.filter_by(email=email.data).first()
        if not user:
            raise ValidationError('There is no account with that email. Please register first.')

class ResetPasswordForm(FlaskForm):
    """Form for resetting password after receiving reset link."""
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    password2 = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Reset Password')

class ContactForm(FlaskForm):
    """Form for contacting support."""
    name = StringField('Your Name', validators=[DataRequired()])
    email = StringField('Your Email', validators=[DataRequired(), Email()])
    subject = StringField('Subject', validators=[DataRequired()])
    message = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Send Message')

class FeedbackForm(FlaskForm):
    """Form for collecting user feedback."""
    rating = SelectField('How would you rate your experience?', 
                        choices=[(str(i), str(i)) for i in range(1, 6)],
                        validators=[DataRequired()])
    comment = TextAreaField('Comments (optional)')
    email = StringField('Email (optional, for follow-up)', validators=[Email()])
    submit = SubmitField('Submit Feedback')
    
class DeleteAccountForm(FlaskForm):
    """Form for account deletion."""
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_text = StringField('Type "DELETE" to confirm', validators=[
        DataRequired(),
        Length(min=6, max=6, message='Please type "DELETE" to confirm')
    ])
    submit = SubmitField('Permanently Delete Account')
    
    def validate_confirm_text(self, confirm_text):
        """Validate that the confirm text is exactly 'DELETE'."""
        if confirm_text.data != 'DELETE':
            raise ValidationError('You must type "DELETE" (all uppercase) to confirm account deletion.')
            
class ResendVerificationForm(FlaskForm):
    """Form for resending email verification."""
    submit = SubmitField('Resend Verification Email')
    
class ChangePasswordForm(FlaskForm):
    """Form for changing password."""
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Change Password')
    
class PrivacySettingsForm(FlaskForm):
    """Form for privacy settings."""
    data_collection = BooleanField('Allow usage data collection')
    progress_tracking = BooleanField('Track exercise progress')
    personalization = BooleanField('Use data for personalization')
    email_notifications = BooleanField('Email notifications')
    marketing_emails = BooleanField('Marketing emails')
    submit = SubmitField('Save Privacy Settings')