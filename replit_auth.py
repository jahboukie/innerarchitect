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
    """Load a user from the database by ID."""
    if not user_id:
        return None
    try:
        return User.query.filter_by(id=user_id).one_or_none()
    except Exception as e:
        error(f"Error loading user {user_id}: {str(e)}")
        return None


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
    """
    Storage interface for OAuth tokens in the database.

    This implementation stores tokens in the database, associated with the current user
    and browser session.
    """
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

            # Get token using a direct query to avoid return type issues
            try:
                oauth_entry = db.session.query(OAuth).filter_by(
                    user_id=user_id,
                    browser_session_key=g.browser_session_key,
                    provider=blueprint.name,
                ).one_or_none()

                if oauth_entry and hasattr(oauth_entry, 'token'):
                    # Return the token directly without type casting - Flask-Dance will handle it
                    return oauth_entry.token
                return None
            except NoResultFound:
                return None

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

    Args:
        user_claims: Dictionary containing user claims from JWT token

    Returns:
        User object after saving to database

    Raises:
        ValueError: If required claims are missing
        Exception: On database errors
    """
    # Validate required claims
    if 'sub' not in user_claims:
        error("Missing 'sub' in user claims")
        raise ValueError("Missing required user identifier in authentication data")

    try:
        # First check if the email from claims already exists
        email = user_claims.get('email')
        email_user = None

        if email:
            email_user = User.query.filter_by(email=email).first()

        # Check if user with this sub ID already exists
        user = User.query.filter_by(id=user_claims['sub']).first()

        # Handle email collision - if email exists for different user
        if email_user and (not user or email_user.id != user.id):
            info(f"Email {email} already exists for user {email_user.id}, linking with Replit user {user_claims['sub']}")

            # Solution: Use the existing email user account and update its ID
            # This essentially links the accounts while preserving preferences, history, etc.
            if user:
                # Existing Replit user - need to migrate data to email user account
                warning(f"User ID conflict: {user.id} vs {email_user.id} for email {email}")
                # We'll keep the email user as the primary and update Replit tokens
                user = email_user
                # Keep email_user.auth_provider as is
            else:
                # No existing Replit user - just use email user
                user = email_user
                user.auth_provider = 'replit_auth'  # Update to allow both login methods

            # Skip email update below to avoid constraint violation
            email = None
        elif not user:
            # No existing user with this ID or email - create new
            user = User()
            user.id = user_claims['sub']
            user.auth_provider = 'replit_auth'  # Set auth provider for new users
            info(f"Creating new user with id {user_claims['sub']}")
        else:
            info(f"Updating existing user with id {user_claims['sub']}")

        # Update user data
        if email:  # Only update email if it's safe (no collision)
            user.email = email
        user.first_name = user_claims.get('first_name')
        user.last_name = user_claims.get('last_name')
        user.profile_image_url = user_claims.get('profile_image_url')

        # For existing users, don't change the auth_provider if already set to email_auth
        # This prevents accidentally changing it during a refresh or re-login
        if user.auth_provider == 'email_auth':
            debug(f"Preserving email_auth provider for user {user.id}")
        else:
            user.auth_provider = 'replit_auth'

        # Note: The actual commit happens in the calling function's transaction
        # Save to database using merge to handle detached instances
        merged_user = db.session.merge(user)

        return merged_user

    except Exception as e:
        error(f"Error in save_user: {str(e)}")
        db.session.rollback()
        raise Exception(f"Failed to save user data: {str(e)}")


@oauth_authorized.connect
def logged_in(blueprint, token):
    try:
        # Validate token contains id_token
        if not token or 'id_token' not in token:
            error("Invalid OAuth token received: missing id_token")
            flash("Authentication failed: invalid token received", "danger")
            return redirect(url_for('replit_auth.error'))

        # Decode user claims with error handling
        try:
            user_claims = jwt.decode(token['id_token'], 
                                    options={"verify_signature": False})
        except Exception as e:
            error(f"Failed to decode JWT token: {str(e)}")
            flash("Authentication failed: could not validate login information", "danger")
            return redirect(url_for('replit_auth.error'))

        # Validate required claim exists
        if 'sub' not in user_claims:
            error("Missing 'sub' claim in user token")
            flash("Authentication failed: missing user identifier", "danger")
            return redirect(url_for('replit_auth.error'))

        # Check if we're in the process of linking accounts
        if session.get('linking_accounts') and session.get('original_user_id'):
            try:
                # We're linking accounts - store the token
                blueprint.token = token

                # Redirect to the account linking completion handler
                return redirect(url_for('complete_account_linking'))
            except Exception as e:
                error(f"Error during account linking: {str(e)}")
                flash("Account linking failed", "danger")
                return redirect(url_for('replit_auth.error'))

        # Normal login flow with transaction management
        try:
            # Save user data within transaction
            with db.session.begin():
                user = save_user(user_claims)

                # Set auth provider
                user.auth_provider = 'replit_auth'

                # Commit handled by with block

            # Login the user
            login_user(user)

            # Store token
            blueprint.token = token

            # Redirect to next URL or default
            next_url = session.pop("next_url", None)
            if next_url is not None:
                return redirect(next_url)

        except Exception as e:
            error(f"Error during login flow: {str(e)}")
            db.session.rollback()
            flash("Login failed: could not complete authentication", "danger")
            return redirect(url_for('replit_auth.error'))

    except Exception as e:
        # Global exception handler
        error(f"Unexpected error in OAuth login flow: {str(e)}")
        flash("An unexpected error occurred during login", "danger")
        return redirect(url_for('replit_auth.error'))


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