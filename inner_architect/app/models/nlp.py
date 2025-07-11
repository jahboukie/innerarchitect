from datetime import datetime
from app import db
from app.models.user import User

class NLPExercise(db.Model):
    """Model for NLP technique exercises."""
    __tablename__ = 'nlp_exercise'
    
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
    __tablename__ = 'nlp_exercise_progress'
    
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
    __tablename__ = 'technique_effectiveness'
    
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
    __tablename__ = 'technique_usage_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), nullable=False, index=True)
    technique = db.Column(db.String(30), nullable=False, index=True)
    usage_count = db.Column(db.Integer, default=0)
    avg_rating = db.Column(db.Float, default=0.0)
    last_used = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('session_id', 'technique', name='_session_technique_uc'),)
    
    def __repr__(self):
        return f'<TechniqueUsageStats {self.technique} - Count: {self.usage_count}>'