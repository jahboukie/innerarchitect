#!/usr/bin/env python
"""
Production configuration for The Inner Architect.
This file contains settings specific to production deployment.
"""

import os
import secrets
from logging import INFO, WARNING, ERROR

# Flask application settings
FLASK_ENV = "production"
DEBUG = False
TESTING = False
SECRET_KEY = os.environ.get("SESSION_SECRET") or secrets.token_hex(32)

# Security settings
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
PERMANENT_SESSION_LIFETIME = 86400 * 14  # 14 days

# CSRF protection
WTF_CSRF_ENABLED = True
WTF_CSRF_SSL_STRICT = True

# Database settings
SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_size": 10,
    "max_overflow": 20
}

# API keys
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")

# Authentication settings
REPL_ID = os.environ.get("REPL_ID")
ISSUER_URL = os.environ.get("ISSUER_URL", "https://replit.com/oidc")

# Logging configuration
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

# Logging level mapping
LOG_LEVEL_MAP = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50
}

# Email settings
DEFAULT_FROM_EMAIL = "noreply@yourapp.com"
DEFAULT_FROM_NAME = "The Inner Architect"

# Cache settings
CACHE_TYPE = "SimpleCache"
CACHE_DEFAULT_TIMEOUT = 300

# Rate limiting
RATELIMIT_ENABLED = True
RATELIMIT_DEFAULTS_PER_METHOD = True
RATELIMIT_HEADERS_ENABLED = True
RATELIMIT_STORAGE_URL = "memory://"
RATELIMIT_STRATEGY = "fixed-window"

# Rate limit for auth endpoints
AUTH_RATE_LIMIT = "20/hour"

# Rate limit for API endpoints
API_RATE_LIMIT = "100/minute"

# Content Security Policy
CONTENT_SECURITY_POLICY = {
    'default-src': "'self'",
    'script-src': ["'self'", "https://js.stripe.com"],
    'style-src': ["'self'", "'unsafe-inline'", "https://cdn.replit.com"],
    'font-src': ["'self'", "https://cdn.replit.com"],
    'img-src': ["'self'", "data:", "https:"],
    'connect-src': ["'self'", "https://api.openai.com", "https://api.stripe.com"],
    'frame-src': ["'self'", "https://js.stripe.com"],
    'object-src': "'none'"
}

# PWA settings
PWA_CACHE_VERSION = "v1.0.0"
PWA_STATIC_FILES = [
    "/static/css/styles.css",
    "/static/js/app.js",
    "/static/manifest.json",
    "/static/icons/app-icon.svg",
    "/static/offline.html"
]

# AI model configuration
DEFAULT_AI_MODEL = "gpt-4o"
AI_TIMEOUT_SECONDS = 15
AI_MAX_TOKENS = 1000
AI_TEMPERATURE = 0.7

# Application feature flags
FEATURE_FLAGS = {
    "enable_voice_features": True,
    "enable_personalized_journeys": True,
    "enable_belief_change": True,
    "enable_pwa_install": True,
    "enable_account_linking": True,
    "enable_multilingual": True
}

# Performance tuning
GUNICORN_WORKERS = 2
GUNICORN_THREADS = 4
GUNICORN_TIMEOUT = 120
GUNICORN_KEEPALIVE = 65

def apply_production_config(app):
    """
    Apply production configuration to the Flask application.
    
    Args:
        app: Flask application instance
    """
    # Set Flask config values
    app.config["ENV"] = FLASK_ENV
    app.config["DEBUG"] = DEBUG
    app.config["TESTING"] = TESTING
    app.config["SECRET_KEY"] = SECRET_KEY
    
    # Security settings
    app.config["SESSION_COOKIE_SECURE"] = SESSION_COOKIE_SECURE
    app.config["SESSION_COOKIE_HTTPONLY"] = SESSION_COOKIE_HTTPONLY
    app.config["SESSION_COOKIE_SAMESITE"] = SESSION_COOKIE_SAMESITE
    app.config["PERMANENT_SESSION_LIFETIME"] = PERMANENT_SESSION_LIFETIME
    
    # Database settings
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = SQLALCHEMY_ENGINE_OPTIONS
    
    # Configure logging
    log_level = LOG_LEVEL_MAP.get(LOG_LEVEL, INFO)
    app.logger.setLevel(log_level)
    
    # Set up monitoring endpoints
    from monitoring_config import setup_monitoring_endpoints
    setup_monitoring_endpoints(app)
    
    # Set up Content Security Policy
    @app.after_request
    def set_secure_headers(response):
        # Build CSP header string
        csp_parts = []
        for directive, sources in CONTENT_SECURITY_POLICY.items():
            if isinstance(sources, list):
                csp_parts.append(f"{directive} {' '.join(sources)}")
            else:
                csp_parts.append(f"{directive} {sources}")
        
        response.headers["Content-Security-Policy"] = "; ".join(csp_parts)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        return response
    
    return app