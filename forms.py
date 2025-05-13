"""
Forms module for The Inner Architect

This module defines WTForms classes for various forms used in the application.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField, HiddenField, RadioField, TimeField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional, NumberRange
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


class OnboardingForm(FlaskForm):
    """Form for user onboarding process with multiple steps."""
    
    # Step 1: Goals
    goals_choices = [
        ('anxiety', 'Reduce Anxiety: I want to feel calmer and more in control'),
        ('confidence', 'Build Confidence: I want to believe in myself more'),
        ('relationships', 'Improve Relationships: I want better connections with others'),
        ('performance', 'Enhance Performance: I want to achieve more in my work/studies'),
        ('happiness', 'Increase Happiness: I want to enjoy life more fully'),
        ('other', 'Something Else: I have another goal in mind')
    ]
    goals = RadioField('Primary Goal', choices=goals_choices, validators=[Optional()])
    custom_goal = StringField('Custom Goal', validators=[Optional(), Length(max=200)])
    
    # Step 2: Experience Level
    experience_choices = [
        ('beginner', 'Complete Beginner: I know nothing about NLP techniques'),
        ('intermediate', 'Some Knowledge: I understand the basics but haven\'t practiced much'),
        ('advanced', 'Experienced User: I\'ve used NLP techniques regularly'),
        ('professional', 'Professional: I\'m certified or trained in NLP'),
        ('unsure', 'Not Sure: I don\'t know if I\'ve used NLP before')
    ]
    experience_level = RadioField('Experience Level', choices=experience_choices, validators=[Optional()])
    
    # Step 3: Communication Preferences
    communication_choices = [
        ('direct', 'Direct & Concise: Keep it brief and to the point'),
        ('detailed', 'Detailed & Thorough: I like complete explanations'),
        ('supportive', 'Supportive & Encouraging: I benefit from positive reinforcement'),
        ('challenging', 'Challenging & Growth-focused: Push me to improve')
    ]
    communication_style = RadioField('Communication Style', choices=communication_choices, validators=[Optional()])
    show_explanations = BooleanField('Show Technique Explanations')
    
    # Step 4: First Challenge
    challenge_description = TextAreaField('Challenge Description', validators=[Optional(), Length(max=500)])
    challenge_intensity = IntegerField('Intensity (1-10)', validators=[Optional(), NumberRange(min=1, max=10)])
    
    # Step 5: Reminders
    enable_reminders = BooleanField('Enable Reminders')
    frequency_choices = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('custom', 'Custom')
    ]
    reminder_frequency = RadioField('Reminder Frequency', choices=frequency_choices, validators=[Optional()])
    preferred_time = TimeField('Preferred Time', validators=[Optional()])
    
    # Common fields for all steps
    step = HiddenField('Current Step')
    submit = SubmitField('Continue')