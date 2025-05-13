"""
Improved Replit Authentication module with better error handling and transaction management.
This module handles the authentication flow for the Replit Auth OpenID Connect provider.
"""
import jwt
import os
import uuid
from functools import wraps
from urllib.parse import urlencode
from typing import Optional, Dict, Any, Union, cast

from flask import g, session, redirect, request, render_template, url_for, flash
from flask_dance.consumer import (
    OAuth2ConsumerBlueprint,
    oauth_authorized,
    oauth_error,
)
from flask_dance.consumer.storage import BaseStorage
from flask_login import LoginManager, login_user, logout_user, current_user
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
from sqlalchemy.exc import NoResultFound, SQLAlchemyError, IntegrityError
from werkzeug.local import LocalProxy

from app import app, db
from models import OAuth, User
from logging_config import get_logger, info, error, debug, warning

# Initialize login manager
login_manager = LoginManager(app)
# Note: login_view is nullable in newer versions but we need it for proper redirects
setattr(login_manager, 'login_view', "login")  # Redirect to login page when login_required fails
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"

@login_manager.user_loader
def load_user(user_id):
    """Load a user from the database by ID."""
    if not user_id:
        return None
    try:
        return User.query.get(user_id)
    except Exception as e:
        error(f"Error loading user {user_id}: {str(e)}")
        return None

class ReplitSessionStorage(BaseStorage):
    """
    Storage for OAuth tokens in the database.
    This class manages the storage of OAuth tokens in the database,
    associated with the current user and browser session.
    """
    def get(self, blueprint):
        """Get the OAuth token for the current user and browser session."""
        # Important: This method must return None or a dict to satisfy BaseStorage API
        token_dict = None
        
        if not current_user or not current_user.is_authenticated:
            return token_dict
            
        # Get user ID and browser session key
        user_id = current_user.get_id()
        if not user_id or not hasattr(g, 'browser_session_key'):
            return token_dict
            
        try:
            # Query the database for the token
            oauth = db.session.query(OAuth).filter_by(
                user_id=user_id,
                browser_session_key=g.browser_session_key,
                provider=blueprint.name,
            ).one_or_none()
            
            if oauth and hasattr(oauth, 'token'):
                # Cast to dict to ensure proper type returned
                token_dict = dict(oauth.token) if oauth.token else None
            
            return token_dict
            
        except SQLAlchemyError as e:
            error(f"Database error retrieving OAuth token: {str(e)}")
            db.session.rollback()
            return token_dict
            
    def set(self, blueprint, token):
        """Store the OAuth token for the current user and browser session."""
        if not current_user or not current_user.is_authenticated:
            return
            
        # Get user ID and browser session key
        user_id = current_user.get_id()
        if not user_id or not hasattr(g, 'browser_session_key'):
            return
            
        try:
            # Begin a transaction
            db.session.begin_nested()
            
            # Delete any existing tokens
            db.session.query(OAuth).filter_by(
                user_id=user_id,
                browser_session_key=g.browser_session_key,
                provider=blueprint.name,
            ).delete()
            
            # Create a new token
            oauth = OAuth()
            oauth.user_id = user_id
            oauth.browser_session_key = g.browser_session_key
            oauth.provider = blueprint.name
            oauth.token = token
            db.session.add(oauth)
            db.session.commit()
        except SQLAlchemyError as e:
            error(f"Database error storing OAuth token: {str(e)}")
            db.session.rollback()
            
    def delete(self, blueprint):
        """Delete the OAuth token for the current user and browser session."""
        if not current_user or not current_user.is_authenticated:
            return
            
        # Get user ID and browser session key
        user_id = current_user.get_id()
        if not user_id or not hasattr(g, 'browser_session_key'):
            return
            
        try:
            # Delete the token
            db.session.query(OAuth).filter_by(
                user_id=user_id,
                browser_session_key=g.browser_session_key,
                provider=blueprint.name,
            ).delete()
            db.session.commit()
        except SQLAlchemyError as e:
            error(f"Database error deleting OAuth token: {str(e)}")
            db.session.rollback()

def create_replit_blueprint():
    """Create the Flask-Dance blueprint for Replit Auth."""
    try:
        # Get the Replit ID from environment variables
        repl_id = os.environ.get('REPL_ID')
        if not repl_id:
            error("REPL_ID environment variable is not set")
            raise RuntimeError("REPL_ID environment variable must be set")
            
        # Get the issuer URL
        issuer_url = os.environ.get('ISSUER_URL', "https://replit.com/oidc")
        
        # Create the blueprint
        blueprint = OAuth2ConsumerBlueprint(
            "replit_auth",
            __name__,
            client_id=repl_id,
            client_secret=None,
            base_url=issuer_url,
            authorization_url_params={
                "prompt": "login consent",
            },
            token_url=issuer_url + "/token",
            token_url_params={
                "auth": (),
                "include_client_id": True,
            },
            auto_refresh_url=issuer_url + "/token",
            auto_refresh_kwargs={
                "client_id": repl_id,
            },
            authorization_url=issuer_url + "/auth",
            use_pkce=True,
            code_challenge_method="S256",
            scope=["openid", "profile", "email", "offline_access"],
            storage=ReplitSessionStorage(),
        )
        
        # Set up browser session key
        @blueprint.before_app_request
        def set_browser_session():
            if '_browser_session_key' not in session:
                session['_browser_session_key'] = uuid.uuid4().hex
            g.browser_session_key = session['_browser_session_key']
            g.flask_dance_replit = blueprint.session
            
        # Handle logout
        @blueprint.route("/logout")
        def logout():
            # Delete the token
            try:
                if hasattr(blueprint, 'token'):
                    del blueprint.token
            except:
                pass
                
            # Log out the user
            if current_user and current_user.is_authenticated:
                logout_user()
                
            # Redirect to the OIDC logout endpoint
            end_session_url = f"{issuer_url}/session/end"
            params = urlencode({
                "client_id": repl_id,
                "post_logout_redirect_uri": request.url_root,
            })
            logout_url = f"{end_session_url}?{params}"
            
            flash("You have been logged out.", "info")
            return redirect(logout_url)
            
        # Handle authentication errors
        @blueprint.route("/error")
        def error_page():
            return render_template("403.html"), 403
            
        return blueprint
        
    except Exception as e:
        error(f"Error creating Replit blueprint: {str(e)}")
        raise

def save_user_from_claims(user_claims):
    """
    Save a user from OIDC claims.
    
    This function creates a new user or updates an existing one
    based on the claims from the ID token.
    
    Args:
        user_claims: Dictionary of user claims from the ID token
        
    Returns:
        User object
        
    Raises:
        ValueError: If required claims are missing
        SQLAlchemyError: On database errors
    """
    # Validate required claims
    if 'sub' not in user_claims:
        raise ValueError("Missing required 'sub' claim")
        
    try:
        # Find or create the user
        user = User.query.filter_by(id=user_claims['sub']).first()
        
        if not user:
            # Create a new user
            user = User()
            user.id = user_claims['sub']
            user.auth_provider = 'replit_auth'
            info(f"Creating new user with id {user.id}")
        else:
            info(f"Updating existing user with id {user.id}")
            
        # Update user data
        user.email = user_claims.get('email')
        user.first_name = user_claims.get('first_name')
        user.last_name = user_claims.get('last_name')
        user.profile_image_url = user_claims.get('profile_image_url')
        
        # Don't change auth_provider if it's set to email_auth
        if user.auth_provider != 'email_auth':
            user.auth_provider = 'replit_auth'
            
        # Merge the user and return
        return db.session.merge(user)
    
    except SQLAlchemyError as e:
        error(f"Database error saving user: {str(e)}")
        db.session.rollback()
        raise

# Handle successful authentication
@oauth_authorized.connect
def handle_successful_auth(blueprint, token):
    """
    Handle successful OAuth authentication.
    
    This function is called when a user successfully authenticates
    with the OAuth provider. It extracts the user claims from the
    ID token, saves the user to the database, and logs them in.
    
    Args:
        blueprint: The Flask-Dance blueprint
        token: The OAuth token
        
    Returns:
        Redirect to the next URL or None
    """
    try:
        # Validate the token
        if not token or 'id_token' not in token:
            flash("Authentication failed: Invalid token", "danger")
            return redirect(url_for('replit_auth.error_page'))
            
        # Decode the ID token
        try:
            user_claims = jwt.decode(
                token['id_token'],
                options={"verify_signature": False}
            )
        except Exception as e:
            error(f"Failed to decode ID token: {str(e)}")
            flash("Authentication failed: Invalid token data", "danger")
            return redirect(url_for('replit_auth.error_page'))
            
        # Handle account linking
        if session.get('linking_accounts') and session.get('original_user_id'):
            try:
                # Store the token
                blueprint.token = token
                return redirect(url_for('complete_account_linking'))
            except Exception as e:
                error(f"Error during account linking: {str(e)}")
                flash("Account linking failed", "danger")
                return redirect(url_for('replit_auth.error_page'))
                
        # Save the user
        try:
            db.session.begin()
            user = save_user_from_claims(user_claims)
            db.session.commit()
        except Exception as e:
            error(f"Error saving user: {str(e)}")
            db.session.rollback()
            flash("Authentication failed: Unable to save user data", "danger")
            return redirect(url_for('replit_auth.error_page'))
            
        # Log in the user
        login_user(user)
        
        # Store the token
        blueprint.token = token
        
        # Redirect to the next URL
        next_url = session.pop('next_url', None)
        if next_url:
            return redirect(next_url)
            
    except Exception as e:
        error(f"Unexpected error during authentication: {str(e)}")
        flash("An unexpected error occurred during login", "danger")
        return redirect(url_for('replit_auth.error_page'))

# Handle authentication errors
@oauth_error.connect
def handle_auth_error(blueprint, auth_error, error_description=None, error_uri=None):
    """
    Handle OAuth authentication errors.
    
    This function is called when an error occurs during the OAuth
    authentication flow.
    
    Args:
        blueprint: The Flask-Dance blueprint
        auth_error: The error code
        error_description: Human-readable error description
        error_uri: URI with more information about the error
        
    Returns:
        Redirect to the error page
    """
    # Log the error
    error(f"OAuth error: {auth_error}, Description: {error_description}, URI: {error_uri}")
    
    # Show a user-friendly error message
    if error_description:
        flash(f"Authentication error: {error_description}", "danger")
    else:
        flash(f"Authentication error: {auth_error}", "danger")
        
    return redirect(url_for('replit_auth.error_page'))

def require_auth(f):
    """
    Decorator to require authentication for a route.
    
    This decorator checks if the user is authenticated and
    redirects to the login page if not.
    
    Args:
        f: The function to decorate
        
    Returns:
        Decorated function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if the user is authenticated
        if not current_user.is_authenticated:
            # Store the current URL for redirect after login
            session['next_url'] = request.url
            flash("Please log in to access this page.", "info")
            return redirect(url_for('replit_auth.login'))
            
        # Check if the token needs refreshing
        try:
            replit = g.flask_dance_replit
            if replit and hasattr(replit, 'token') and 'expires_in' in replit.token:
                expires_in = replit.token['expires_in']
                if expires_in < 60:  # Refresh if less than 60 seconds left
                    debug("Refreshing token")
                    try:
                        issuer_url = os.environ.get('ISSUER_URL', "https://replit.com/oidc")
                        token = replit.refresh_token(
                            token_url=f"{issuer_url}/token",
                            client_id=os.environ.get('REPL_ID')
                        )
                        replit.token = token
                    except InvalidGrantError:
                        # If refresh fails, logout and redirect to login
                        session['next_url'] = request.url
                        logout_user()
                        flash("Your session has expired. Please log in again.", "info")
                        return redirect(url_for('replit_auth.login'))
        except Exception as e:
            debug(f"Error refreshing token: {str(e)}")
            # Continue with the request even if token refresh fails
            
        # Call the original function
        return f(*args, **kwargs)
        
    return decorated_function

# Make the blueprint available as a variable
replit = LocalProxy(lambda: g.flask_dance_replit if hasattr(g, 'flask_dance_replit') else None)