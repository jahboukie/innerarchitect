from datetime import datetime
from app import db
from app.models.user import User

class ChatHistory(db.Model):
    """Model to store chat history between users and the AI."""
    __tablename__ = 'chat_history'
    
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
    __tablename__ = 'conversation_context'
    
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
    __tablename__ = 'conversation_memory_item'
    
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
    __tablename__ = 'journal_entry'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    mood = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<JournalEntry {self.id}>'