"""
Test configuration for The Inner Architect.

This module provides fixtures and configuration for pytest.
"""

import os
import tempfile
import pytest
from app import create_app, db
from app.models.user import User
from app.models.subscription import Subscription
from app.models.chat import ChatHistory, ConversationContext
from app.models.nlp import NLPExercise

@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    # Create a temporary file to isolate the database for each test
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test',
        # Mock API keys for testing
        'ANTHROPIC_API_KEY': 'test_api_key',
        'STRIPE_SECRET_KEY': 'test_stripe_key',
        'STRIPE_PUBLISHABLE_KEY': 'test_stripe_publishable_key',
        'SENDGRID_API_KEY': 'test_sendgrid_key'
    })
    
    # Create the database and the database tables
    with app.app_context():
        db.create_all()
        
        # Add test data
        _populate_test_data()
    
    yield app
    
    # Close and remove the temporary database
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()

@pytest.fixture
def auth(client):
    """Authentication helper for tests."""
    class AuthActions:
        def __init__(self, client):
            self._client = client
            
        def login(self, email='test@example.com', password='password'):
            return self._client.post(
                '/auth/login',
                data={'email': email, 'password': password}
            )
            
        def logout(self):
            return self._client.get('/auth/logout')
    
    return AuthActions(client)

@pytest.fixture
def logged_in_client(client, auth):
    """A test client that is logged in."""
    auth.login()
    return client

@pytest.fixture
def mock_claude_client(monkeypatch):
    """Mock the Claude client to avoid actual API calls."""
    class MockClaudeResponse:
        def __init__(self, content):
            self.content = [type('obj', (object,), {'text': content})]
    
    class MockClaudeClient:
        def __init__(self, api_key=None, model=None):
            self.api_key = api_key
            self.model = model
            
        def generate_response(self, messages, system_prompt=None, temperature=0.7, max_tokens=None):
            # Return a predetermined response based on the message content
            if system_prompt and "analyze this conversation" in system_prompt.lower():
                return '{"summary": "Test conversation summary", "themes": ["test theme 1", "test theme 2"]}'
            
            return "Mock Claude response"
            
        def chat_completion(self, user_message, conversation_history=None, system_prompt=None, temperature=0.7):
            # Return a predetermined response based on the technique
            if system_prompt and "reframing" in system_prompt.lower():
                return "This is a reframed perspective: try to see the positive side."
            elif system_prompt and "pattern interruption" in system_prompt.lower():
                return "Let's break that pattern by considering a completely different approach."
            elif system_prompt and "anchoring" in system_prompt.lower():
                return "Think of a time when you felt confident and anchor that feeling to a specific gesture."
            elif system_prompt and "future pacing" in system_prompt.lower():
                return "Imagine yourself successfully handling this situation in the future."
            elif system_prompt and "sensory language" in system_prompt.lower():
                return "I can see how this feels heavy for you. Let's clarify what sounds right and looks appropriate."
            elif system_prompt and "meta model" in system_prompt.lower():
                return "What specifically do you mean by that? According to whom is that always true?"
            else:
                return "I understand your concerns. Let's explore this further."
            
        def analyze_text(self, text, task_description, temperature=0.3):
            # Return a predetermined response based on the task
            if "identify the primary emotional state" in task_description.lower():
                return "happy"
            elif "determine the most appropriate NLP technique" in task_description.lower():
                return "reframing"
            elif "generate a concise title" in task_description.lower():
                return "Test Conversation Title"
            else:
                return "Analysis result"
            
        def extract_insights(self, conversation, extraction_type="themes"):
            # Return a predetermined response based on the extraction type
            if extraction_type == "themes":
                return {"result": "Theme 1, Theme 2, Theme 3"}
            elif extraction_type == "memories":
                return {"result": "Memory 1, Memory 2, Memory 3"}
            elif extraction_type == "summary":
                return {"result": "This is a summary of the conversation."}
            else:
                return {"result": "Extraction result"}
            
        def messages(self):
            return type('obj', (object,), {'create': lambda **kwargs: MockClaudeResponse("Mock Claude response")})
    
    # Patch the ClaudeClient class
    from app.nlp.claude_client import ClaudeClient
    monkeypatch.setattr("app.nlp.claude_client.ClaudeClient", MockClaudeClient)
    monkeypatch.setattr("app.nlp.claude_client.claude_client", MockClaudeClient())
    
    return MockClaudeClient()

def _populate_test_data():
    """Add test data to the database."""
    # Create test user
    user = User(
        id='test-user-id',
        email='test@example.com',
        first_name='Test',
        last_name='User',
        auth_provider='email'
    )
    user.set_password('password')
    user.email_verified = True
    db.session.add(user)
    
    # Create premium user
    premium_user = User(
        id='premium-user-id',
        email='premium@example.com',
        first_name='Premium',
        last_name='User',
        auth_provider='email'
    )
    premium_user.set_password('password')
    premium_user.email_verified = True
    db.session.add(premium_user)
    
    # Create subscriptions
    free_subscription = Subscription(
        user_id='test-user-id',
        plan_name='free',
        status='active'
    )
    db.session.add(free_subscription)
    
    premium_subscription = Subscription(
        user_id='premium-user-id',
        plan_name='premium',
        status='active'
    )
    db.session.add(premium_subscription)
    
    # Create conversation contexts
    context1 = ConversationContext(
        id=1,
        user_id='test-user-id',
        session_id='test-session-id',
        title='Test Conversation',
        is_active=True
    )
    db.session.add(context1)
    
    context2 = ConversationContext(
        id=2,
        user_id='premium-user-id',
        session_id='premium-session-id',
        title='Premium Conversation',
        is_active=True
    )
    db.session.add(context2)
    
    # Create chat history
    message1 = ChatHistory(
        user_id='test-user-id',
        session_id='test-session-id',
        context_id=1,
        user_message='Hello, I need help with anxiety.',
        ai_response='I understand anxiety can be challenging. Let\'s explore some reframing techniques.',
        mood='anxious',
        nlp_technique='reframing'
    )
    db.session.add(message1)
    
    message2 = ChatHistory(
        user_id='premium-user-id',
        session_id='premium-session-id',
        context_id=2,
        user_message='I keep falling into the same patterns.',
        ai_response='Let\'s work on interrupting those patterns. What specifically happens?',
        mood='frustrated',
        nlp_technique='pattern_interruption'
    )
    db.session.add(message2)
    
    # Create NLP exercises
    exercise1 = NLPExercise(
        technique='reframing',
        title='Reframing Negative Thoughts',
        description='Learn to reframe negative thoughts into more positive and constructive ones.',
        steps='["Step 1: Identify the negative thought", "Step 2: Question its accuracy", "Step 3: Find alternative perspectives", "Step 4: Choose a more balanced viewpoint"]',
        difficulty='beginner'
    )
    db.session.add(exercise1)
    
    exercise2 = NLPExercise(
        technique='anchoring',
        title='Creating a Confidence Anchor',
        description='Establish a physical anchor to quickly access feelings of confidence.',
        steps='["Step 1: Recall a time of peak confidence", "Step 2: Intensify the feeling", "Step 3: Create a physical anchor", "Step 4: Test the anchor"]',
        difficulty='intermediate'
    )
    db.session.add(exercise2)
    
    db.session.commit()