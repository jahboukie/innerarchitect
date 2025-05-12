from datetime import datetime, timedelta
from database import db
from flask_login import UserMixin
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from sqlalchemy import ForeignKey, UniqueConstraint

class User(UserMixin, db.Model):
    """User model for authentication and profile information."""
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with ChatHistory
    chats = db.relationship('ChatHistory', backref='user', lazy='dynamic')
    
    # Relationship with NLPExerciseProgress
    exercise_progress = db.relationship('NLPExerciseProgress', backref='user', lazy='dynamic')
    
    # Relationship with TechniqueEffectiveness
    technique_ratings = db.relationship('TechniqueEffectiveness', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.id}>'
        
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


class Subscription(db.Model):
    """Model for user subscription information."""
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey(User.id), nullable=False)
    stripe_customer_id = db.Column(db.String, unique=True, nullable=True)
    stripe_subscription_id = db.Column(db.String, unique=True, nullable=True)
    plan_name = db.Column(db.String, nullable=False)  # 'free', 'premium', 'professional'
    status = db.Column(db.String, nullable=False, default='active')  # 'active', 'canceled', 'past_due'
    current_period_start = db.Column(db.DateTime, nullable=True)
    current_period_end = db.Column(db.DateTime, nullable=True)
    cancel_at_period_end = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to User
    user = db.relationship('User', backref=db.backref('subscription', uselist=False))
    
    def __repr__(self):
        return f'<Subscription {self.id} - {self.plan_name} - {self.status}>'
        
    @property
    def is_active(self):
        """Check if subscription is active."""
        return self.status == 'active'
        
    @property
    def has_premium_access(self):
        """Check if the user has premium or better access."""
        return self.is_active and self.plan_name in ['premium', 'professional']
        
    @property
    def has_professional_access(self):
        """Check if the user has professional access."""
        return self.is_active and self.plan_name == 'professional'
        
    def to_dict(self):
        """Convert subscription to dictionary for JSON serialization."""
        # Import here to avoid circular import
        from subscription_manager import SUBSCRIPTION_PLANS
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'plan_name': self.plan_name,
            'status': self.status,
            'current_period_start': self.current_period_start.isoformat() if self.current_period_start else None,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None,
            'cancel_at_period_end': getattr(self, 'cancel_at_period_end', False),
            'features': SUBSCRIPTION_PLANS.get(self.plan_name, {}).get('features', []),
            'quotas': SUBSCRIPTION_PLANS.get(self.plan_name, {}).get('quotas', {})
        }


class ChatHistory(db.Model):
    """Model to store chat history between users and the AI."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=True)
    session_id = db.Column(db.String(64), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    ai_response = db.Column(db.Text, nullable=False)
    mood = db.Column(db.String(20), nullable=True)
    nlp_technique = db.Column(db.String(30), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with conversation contexts
    context_id = db.Column(db.Integer, db.ForeignKey('conversation_context.id'), nullable=True)
    
    def __repr__(self):
        return f'<ChatHistory {self.id}>'


class ConversationContext(db.Model):
    """Model for storing conversation context and themes over time."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=True)
    session_id = db.Column(db.String(64), nullable=False)
    title = db.Column(db.String(100), nullable=True)  # Auto-generated title for the conversation
    is_active = db.Column(db.Boolean, default=True)  # Whether this is the active context for the session
    summary = db.Column(db.Text, nullable=True)  # AI-generated summary of the conversation
    themes = db.Column(db.Text, nullable=True)  # JSON array of identified themes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = db.relationship('ChatHistory', backref='context', lazy='dynamic')
    memory_items = db.relationship('ConversationMemoryItem', backref='context', lazy='dynamic', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<ConversationContext {self.id}: {self.title}>'


class ConversationMemoryItem(db.Model):
    """Model for storing specific memory items extracted from conversations."""
    id = db.Column(db.Integer, primary_key=True)
    context_id = db.Column(db.Integer, db.ForeignKey('conversation_context.id'), nullable=False)
    memory_type = db.Column(db.String(30), nullable=False)  # 'fact', 'preference', 'concern', 'goal', etc.
    content = db.Column(db.Text, nullable=False)  # The actual memory content
    source_message_id = db.Column(db.Integer, db.ForeignKey('chat_history.id'), nullable=True)  # Original message
    confidence = db.Column(db.Float, nullable=False, default=1.0)  # Confidence score (0-1)
    relevance = db.Column(db.Float, nullable=False, default=1.0)  # Current relevance score (0-1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)  # Last time this memory was used in a response
    
    def __repr__(self):
        return f'<ConversationMemoryItem {self.id}: {self.memory_type}>'


class JournalEntry(db.Model):
    """Model for user journal entries and reflections."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    mood = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<JournalEntry {self.id}>'


class NLPExercise(db.Model):
    """Model for NLP technique exercises."""
    id = db.Column(db.Integer, primary_key=True)
    technique = db.Column(db.String(30), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    steps = db.Column(db.Text, nullable=False)  # JSON-formatted steps
    difficulty = db.Column(db.String(20), nullable=False, default='beginner')  # beginner, intermediate, advanced
    estimated_time = db.Column(db.Integer, nullable=False, default=5)  # in minutes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with user progress
    progress = db.relationship('NLPExerciseProgress', backref='exercise', lazy='dynamic')
    
    def __repr__(self):
        return f'<NLPExercise {self.technique}: {self.title}>'


class NLPExerciseProgress(db.Model):
    """Model to track user progress with NLP exercises."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=True)
    exercise_id = db.Column(db.Integer, db.ForeignKey('nlp_exercise.id'), nullable=False)
    session_id = db.Column(db.String(64), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    current_step = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        status = "completed" if self.completed else f"step {self.current_step}"
        return f'<NLPExerciseProgress {self.exercise_id} - {status}>'


class TechniqueEffectiveness(db.Model):
    """Model to track the effectiveness of NLP techniques for a user."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=True)
    session_id = db.Column(db.String(64), nullable=False)
    technique = db.Column(db.String(30), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # Scale of 1-5
    notes = db.Column(db.Text, nullable=True)
    situation = db.Column(db.String(100), nullable=True)  # Brief context/situation description
    entry_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<TechniqueEffectiveness {self.technique} - Rating: {self.rating}>'


class TechniqueUsageStats(db.Model):
    """Model to track aggregated statistics about technique usage."""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), nullable=False, index=True)
    technique = db.Column(db.String(30), nullable=False, index=True)
    usage_count = db.Column(db.Integer, default=0)
    avg_rating = db.Column(db.Float, default=0.0)
    last_used = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('session_id', 'technique', name='_session_technique_uc'),)
    
    def __repr__(self):
        return f'<TechniqueUsageStats {self.technique} - Count: {self.usage_count}>'


class UsageQuota(db.Model):
    """Model to track usage quotas for subscription limits."""
    __tablename__ = 'usage_quota'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=True)
    session_id = db.Column(db.String(64), nullable=True)  # Session ID for non-logged-in users
    browser_session_id = db.Column(db.String(64), nullable=True)  # For backward compatibility
    quota_type = db.Column(db.String(30), nullable=True)  # e.g., 'messages_per_day', 'exercises_per_week'
    usage_count = db.Column(db.Integer, default=0)
    
    # Fields used in subscription_manager.py
    messages_used_today = db.Column(db.Integer, default=0)
    exercises_used_today = db.Column(db.Integer, default=0)
    analyses_used_this_month = db.Column(db.Integer, default=0)
    last_reset_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_monthly_reset_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # For specific quota periods
    date = db.Column(db.Date, nullable=True, index=True)  # For daily quotas
    week_start = db.Column(db.Date, nullable=True, index=True)  # For weekly quotas
    month_start = db.Column(db.Date, nullable=True, index=True)  # For monthly quotas
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with User
    user = db.relationship('User', backref=db.backref('usage_quotas', lazy='dynamic'))
    
    def __repr__(self):
        return f'<UsageQuota {self.quota_type} - {self.usage_count}>'
        
    @classmethod
    def get_or_create_daily(cls, user_id, session_id, quota_type):
        """Get or create a daily quota record."""
        today = datetime.utcnow().date()
        
        # Try to find existing record
        if user_id:
            record = cls.query.filter_by(
                user_id=user_id,
                quota_type=quota_type,
                date=today
            ).first()
        else:
            record = cls.query.filter_by(
                session_id=session_id,
                quota_type=quota_type,
                date=today
            ).first()
            
        if not record:
            # Create new record
            record = cls(
                user_id=user_id,
                session_id=session_id,
                quota_type=quota_type,
                date=today,
                usage_count=0
            )
            db.session.add(record)
            db.session.commit()
            
        return record
        
    @classmethod
    def get_or_create_weekly(cls, user_id, session_id, quota_type):
        """Get or create a weekly quota record."""
        today = datetime.utcnow().date()
        week_start = today - timedelta(days=today.weekday())
        
        # Try to find existing record
        if user_id:
            record = cls.query.filter_by(
                user_id=user_id,
                quota_type=quota_type,
                week_start=week_start
            ).first()
        else:
            record = cls.query.filter_by(
                session_id=session_id,
                quota_type=quota_type,
                week_start=week_start
            ).first()
            
        if not record:
            # Create new record
            record = cls(
                user_id=user_id,
                session_id=session_id,
                quota_type=quota_type,
                week_start=week_start,
                usage_count=0
            )
            db.session.add(record)
            db.session.commit()
            
        return record