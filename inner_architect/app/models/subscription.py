from datetime import datetime, timedelta
from app import db
from app.models.user import User

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
    
    # Fields for trial functionality
    is_trial = db.Column(db.Boolean, default=False)
    trial_plan = db.Column(db.String, nullable=True)
    trial_started_at = db.Column(db.DateTime, nullable=True)
    trial_ends_at = db.Column(db.DateTime, nullable=True)
    trial_converted = db.Column(db.Boolean, default=False)
    
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
    def has_active_trial(self):
        """Check if user has an active trial."""
        if not self.is_trial or not self.trial_ends_at:
            return False
        return self.trial_ends_at > datetime.utcnow()
    
    @property
    def trial_days_remaining(self):
        """Get days remaining in trial or 0 if no active trial."""
        if not self.has_active_trial:
            return 0
        remaining = self.trial_ends_at - datetime.utcnow()
        return max(0, remaining.days + (1 if remaining.seconds > 0 else 0))
        
    @property
    def has_premium_access(self):
        """Check if the user has premium or better access."""
        if self.has_active_trial and self.trial_plan in ['premium', 'professional']:
            return True
        return self.is_active and self.plan_name in ['premium', 'professional']
        
    @property
    def has_professional_access(self):
        """Check if the user has professional access."""
        if self.has_active_trial and self.trial_plan == 'professional':
            return True
        return self.is_active and self.plan_name == 'professional'
        
    @property
    def is_premium_trial(self):
        """Check if the user has an active premium trial."""
        return self.has_active_trial and self.trial_plan == 'premium'
    
    @property
    def is_professional_trial(self):
        """Check if the user has an active professional trial."""
        return self.has_active_trial and self.trial_plan == 'professional'

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