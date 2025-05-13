import jwt
import os
import uuid
from functools import wraps
from urllib.parse import urlencode
from typing import Optional, Dict, Any, Union, cast

from logging_config import get_logger, info, error, debug, warning

from flask import g, session, redirect, request, render_template, url_for, flash
from flask_dance.consumer import (
    OAuth2ConsumerBlueprint,
    oauth_authorized,
    oauth_error,
)
from flask_dance.consumer.storage import BaseStorage
from flask_login import LoginManager, login_user, logout_user, current_user
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
from sqlalchemy.exc import NoResultFound
from werkzeug.local import LocalProxy

from app import app, db
from models import OAuth, User

login_manager = LoginManager(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


# Helper function to safely get OAuth token
def get_oauth_token(user_id, browser_session_key, provider_name):
    """
    Safely get an OAuth token from the database.
    
    Args:
        user_id: The user ID
        browser_session_key: The browser session key
        provider_name: The provider name
        
    Returns:
        The token or None if not found
    """
    if not user_id or not browser_session_key:
        debug("Missing user_id or browser_session_key for OAuth token retrieval")
        return None
        
    try:
        # Create a fresh scoped session
        with db.session.begin():
            oauth_entry = db.session.query(OAuth).filter_by(
                user_id=user_id,
                browser_session_key=browser_session_key,
                provider=provider_name,
            ).one()
            
            # Extract token from oauth_entry
            if oauth_entry and hasattr(oauth_entry, 'token'):
                # Cast to match expected return type
                return cast(Dict[str, Any], oauth_entry.token)
        return None
    except NoResultFound:
        debug(f"No OAuth token found for user {user_id} and provider {provider_name}")
        return None
    except Exception as e:
        error(f"Error retrieving OAuth token: {str(e)}")
        # Ensure session is rolled back on error
        db.session.rollback()
        return None

class UserSessionStorage(BaseStorage):

    def get(self, blueprint):
        """
        Get the OAuth token from storage for the specified blueprint.
        
        Args:
            blueprint: The OAuth blueprint
            
        Returns:
            The token or None if not found
        """
        # Create a fresh session for this query to avoid transaction issues
        try:
            # Return early if no authenticated user
            if not current_user or not current_user.is_authenticated:
                debug("No authenticated user for OAuth token retrieval")
                return None
                
            user_id = current_user.get_id()
            if not user_id or not hasattr(g, 'browser_session_key'):
                debug("Missing user_id or browser_session_key for OAuth token retrieval")
                return None
            
            # Get token using the helper function
            token = get_oauth_token(
                user_id=user_id,
                browser_session_key=g.browser_session_key,
                provider_name=blueprint.name
            )
            
            # We can safely return the token here as the helper already handles type casting
            return token
        except Exception as e:
            error(f"Error in OAuth get: {str(e)}")
            # Make sure to rollback any failed transaction
            db.session.rollback()
            return None

    def set(self, blueprint, token):
        """
        Set the OAuth token in storage for the specified blueprint.
        
        Args:
            blueprint: The OAuth blueprint
            token: The token to store
        """
        try:
            # Check if user is authenticated
            if not current_user or not current_user.is_authenticated:
                return
                
            user_id = current_user.get_id()
            if not user_id or not hasattr(g, 'browser_session_key'):
                return
                
            # Use a transaction to ensure consistency
            with db.session.begin():
                # Delete any existing tokens for this user/session/provider
                db.session.query(OAuth).filter_by(
                    user_id=user_id,
                    browser_session_key=g.browser_session_key,
                    provider=blueprint.name,
                ).delete()
                
                # Create a new token record
                new_model = OAuth()
                new_model.user_id = user_id
                new_model.browser_session_key = g.browser_session_key
                new_model.provider = blueprint.name
                new_model.token = token
                db.session.add(new_model)
                # Commit is handled by the with block
        except Exception as e:
            error(f"Error in OAuth set: {str(e)}")
            # Ensure rollback on error
            db.session.rollback()

    def delete(self, blueprint):
        """
        Delete the OAuth token from storage for the specified blueprint.
        
        Args:
            blueprint: The OAuth blueprint
        """
        try:
            # Check if user is authenticated
            if not current_user or not current_user.is_authenticated:
                return
                
            user_id = current_user.get_id()
            if not user_id or not hasattr(g, 'browser_session_key'):
                return
                
            # Use a transaction to ensure consistency
            with db.session.begin():
                # Delete the tokens for this user/session/provider
                db.session.query(OAuth).filter_by(
                    user_id=user_id,
                    browser_session_key=g.browser_session_key,
                    provider=blueprint.name
                ).delete()
                # Commit is handled by the with block
        except Exception as e:
            error(f"Error in OAuth delete: {str(e)}")
            # Ensure rollback on error
            db.session.rollback()


def make_replit_blueprint():
    try:
        repl_id = os.environ['REPL_ID']
    except KeyError:
        raise SystemExit("the REPL_ID environment variable must be set")

    issuer_url = os.environ.get('ISSUER_URL', "https://replit.com/oidc")

    replit_bp = OAuth2ConsumerBlueprint(
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
        storage=UserSessionStorage(),
    )

    @replit_bp.before_app_request
    def set_applocal_session():
        if '_browser_session_key' not in session:
            session['_browser_session_key'] = uuid.uuid4().hex
        session.modified = True
        g.browser_session_key = session['_browser_session_key']
        g.flask_dance_replit = replit_bp.session

    # We'll use another approach to handle this issue
    
    @replit_bp.route("/logout")
    def logout():
        del replit_bp.token
        logout_user()

        end_session_endpoint = issuer_url + "/session/end"
        encoded_params = urlencode({
            "client_id":
            repl_id,
            "post_logout_redirect_uri":
            request.url_root,
        })
        logout_url = f"{end_session_endpoint}?{encoded_params}"

        return redirect(logout_url)

    @replit_bp.route("/error")
    def error():
        flash("There was an error during authentication. Please try again.", "danger")
        return render_template("403.html"), 403

    return replit_bp


def save_user(user_claims):
    """
    Save user data from OAuth claims.
    Will create a new user or update an existing one based on the sub ID.
    """
    # Check if user already exists
    user = User.query.filter_by(id=user_claims['sub']).first()
    
    if not user:
        # Create a new user
        user = User()
        user.id = user_claims['sub']
        user.auth_provider = 'replit_auth'  # Set auth provider for new users
    
    # Update user data
    user.email = user_claims.get('email')
    user.first_name = user_claims.get('first_name')
    user.last_name = user_claims.get('last_name')
    user.profile_image_url = user_claims.get('profile_image_url')
    
    # For existing users, don't change the auth_provider if already set
    # This prevents accidentally changing it during a refresh or re-login
    
    # Save to database
    merged_user = db.session.merge(user)
    db.session.commit()
    
    return merged_user


@oauth_authorized.connect
def logged_in(blueprint, token):
    user_claims = jwt.decode(token['id_token'],
                             options={"verify_signature": False})
    
    # Check if we're in the process of linking accounts
    if session.get('linking_accounts') and session.get('original_user_id'):
        # We're linking accounts - store the token
        blueprint.token = token
        
        # Redirect to the account linking completion handler
        return redirect(url_for('complete_account_linking'))
    
    # Normal login flow
    user = save_user(user_claims)
    
    # Set auth provider
    user.auth_provider = 'replit_auth'
    db.session.commit()
    
    login_user(user)
    blueprint.token = token
    
    next_url = session.pop("next_url", None)
    if next_url is not None:
        return redirect(next_url)


@oauth_error.connect
def handle_error(blueprint, error, error_description=None, error_uri=None):
    # Log the error details
    error(f"OAuth error: {error}, Description: {error_description}, URI: {error_uri}")
    
    # Show a specific error message
    if error_description:
        flash(f"Authentication error: {error_description}", "danger")
    else:
        flash(f"Authentication error: {error}", "danger")
    
    return redirect(url_for('replit_auth.error'))


def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            # Store the full URL for better redirection
            session["next_url"] = get_next_navigation_url(request)
            
            # Redirect to login page
            return redirect(url_for('replit_auth.login'))

        # Check if token needs refresh
        issuer_url = os.environ.get('ISSUER_URL', "https://replit.com/oidc")
        try:
            expires_in = replit.token.get('expires_in', 0)
            if expires_in < 0:
                refresh_token_url = issuer_url + "/token"
                try:
                    token = replit.refresh_token(token_url=refresh_token_url,
                                            client_id=os.environ['REPL_ID'])
                except InvalidGrantError:
                    # If the refresh token is invalid, re-login is needed
                    flash("Your session has expired. Please log in again.", "info")
                    session["next_url"] = get_next_navigation_url(request)
                    return redirect(url_for('replit_auth.login'))
                
                # Update token if successfully refreshed
                replit.token_updater(token)
        except Exception as e:
            # Log the error but continue with the request
            error(f"Error refreshing token: {str(e)}")
            pass

        return f(*args, **kwargs)

    return decorated_function


def get_next_navigation_url(request):
    is_navigation_url = request.headers.get(
        'Sec-Fetch-Mode') == 'navigate' and request.headers.get(
            'Sec-Fetch-Dest') == 'document'
    if is_navigation_url:
        return request.url
    return request.referrer or request.url


replit = LocalProxy(lambda: g.flask_dance_replit)