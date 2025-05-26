from datetime import datetime, timedelta
from app import db
from flask_login import UserMixin
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from sqlalchemy import ForeignKey, UniqueConstraint
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

class User(UserMixin, db.Model):
    """User model for authentication and profile information."""
    __tablename__ = 'users'
    
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)
    
    # Fields for email auth
    password_hash = db.Column(db.String(256), nullable=True)
    email_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), nullable=True)
    verification_token_expiry = db.Column(db.DateTime, nullable=True)
    reset_password_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    
    # Authentication provider (replit_auth, email, etc.)
    auth_provider = db.Column(db.String(20), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chats = db.relationship('ChatHistory', backref='user', lazy='dynamic')
    exercise_progress = db.relationship('NLPExerciseProgress', backref='user', lazy='dynamic')
    technique_ratings = db.relationship('TechniqueEffectiveness', backref='user', lazy='dynamic')
    privacy_settings = db.relationship('PrivacySettings', backref='user', uselist=False, lazy='joined', cascade='all, delete-orphan')
    preferences = db.relationship('UserPreferences', backref='user', uselist=False, lazy='joined', cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        if 'id' not in kwargs:
            kwargs['id'] = str(uuid.uuid4())
        super(User, self).__init__(**kwargs)
    
    def __repr__(self):
        return f'<User {self.id}>'
        
    def set_password(self, password):
        """Set the password hash for the user."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the provided password matches the hash."""
        if self.password_hash:
            return check_password_hash(self.password_hash, password)
        return False

class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.String, db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)
    
    __table_args__ = (
        db.UniqueConstraint(
            'user_id',
            'browser_session_key',
            'provider',
            name='uq_user_browser_session_key_provider',
        ),
    )

class PrivacySettings(db.Model):
    """Model for user privacy settings and preferences."""
    __tablename__ = 'privacy_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    data_collection = db.Column(db.Boolean, default=True)
    progress_tracking = db.Column(db.Boolean, default=True)
    personalization = db.Column(db.Boolean, default=True)
    email_notifications = db.Column(db.Boolean, default=True)
    marketing_emails = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<PrivacySettings {self.id} for user {self.user_id}>'

class UserPreferences(db.Model):
    """Model for storing user preferences collected during onboarding."""
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=True)
    
    # Onboarding data
    primary_goal = db.Column(db.String(50), nullable=True)
    custom_goal = db.Column(db.String(200), nullable=True)
    experience_level = db.Column(db.String(20), nullable=True)
    communication_style = db.Column(db.String(20), nullable=True)
    show_explanations = db.Column(db.Boolean, default=True)
    first_challenge = db.Column(db.Text, nullable=True)
    challenge_intensity = db.Column(db.Integer, nullable=True)
    
    # Reminder preferences
    enable_reminders = db.Column(db.Boolean, default=False)
    reminder_frequency = db.Column(db.String(20), nullable=True)
    preferred_time = db.Column(db.Time, nullable=True)
    
    # Onboarding status
    onboarding_completed = db.Column(db.Boolean, default=False)
    onboarding_step = db.Column(db.Integer, default=1)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserPreferences {self.id}>'