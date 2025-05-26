import os
from flask import Flask, g, request, session
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_migrate import Migrate

# Define base class for models
class Base(DeclarativeBase):
    pass

# Create SQLAlchemy instance
db = SQLAlchemy(model_class=Base)

# Create Migration instance
migrate = Migrate()

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    
    # Apply proxy fix for production environments
    app.wsgi_app = ProxyFix(app.wsgi_app)
    
    # Configure logging
    from app.utils.logging_setup import configure_logging, setup_request_logging
    configure_logging(app)
    setup_request_logging(app)
    
    # Default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///inner_architect.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        ANTHROPIC_API_KEY=os.environ.get('ANTHROPIC_API_KEY'),
        OPENAI_API_KEY=os.environ.get('OPENAI_API_KEY'),
        STRIPE_SECRET_KEY=os.environ.get('STRIPE_SECRET_KEY'),
        STRIPE_PUBLISHABLE_KEY=os.environ.get('STRIPE_PUBLISHABLE_KEY'),
        SENDGRID_API_KEY=os.environ.get('SENDGRID_API_KEY'),
        DEFAULT_FROM_EMAIL=os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@example.com'),
    )
    
    # Override with test config if provided
    if test_config:
        app.config.update(test_config)
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # Register CLI commands
    from app.cli import register_commands
    register_commands(app)
    
    # Register blueprints
    from app.routes.main import main
    app.register_blueprint(main)
    
    from app.routes.auth import auth
    app.register_blueprint(auth, url_prefix='/auth')
    
    from app.routes.chat import chat
    app.register_blueprint(chat, url_prefix='/chat')
    
    from app.routes.api_test import api_test
    app.register_blueprint(api_test)
    
    from app.routes.admin import admin
    app.register_blueprint(admin)
    
    # Import models to ensure they're registered with SQLAlchemy
    from app.models import User, Subscription, ChatHistory, ConversationContext
    from app.models.subscription import UsageQuota
    
    # Initialize subscription utility
    from app.utils.subscription import init_models
    with app.app_context():
        init_models(User, Subscription, UsageQuota)
        
    # Initialize AI client factory
    from app.services.ai_client_factory import ai_client_factory
    from app.services.claude_client import claude_client
    app.logger.info(f"AI client factory initialized with active provider: {ai_client_factory.active_provider}")
    
    # Import and register user loader
    from app.models.user import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)
    
    # Set up language handling
    @app.before_request
    def before_request():
        # Set default language
        g.language = session.get('language', 'en')
        g.languages = {
            'en': 'English',
            'es': 'Español',
            'fr': 'Français',
            'de': 'Deutsch',
        }
        g.is_rtl = g.language in ['ar', 'he']
        
        # Set up translation function (simplified version)
        def translate(key, default):
            # In a full implementation, this would load translations from files
            return default
        
        g.translate = translate
        
        # Ensure we have a browser session ID for auth
        if '_browser_session_id' not in session:
            import uuid
            session['_browser_session_id'] = str(uuid.uuid4())
    
    return app