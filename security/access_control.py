"""
HIPAA-Compliant Access Control Module for The Inner Architect

This module implements comprehensive access control mechanisms to protect PHI
in accordance with HIPAA Security Rule requirements. It provides fine-grained
access controls, multi-factor authentication, and secure session management.

Features:
- Role-Based Access Control (RBAC)
- Attribute-Based Access Control (ABAC)
- Multi-Factor Authentication (MFA)
- Break-Glass Protocol for emergency access
- Just-In-Time access provisioning
- Session management with security controls
"""

import os
import time
import uuid
import base64
import hmac
import json
import pyotp
import qrcode
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Optional, Tuple, Any, Union
from flask import (
    current_app, request, session, redirect, url_for, flash, g, render_template, after_this_request
)
from flask_login import current_user, login_required
from sqlalchemy import or_, and_
from io import BytesIO

# Constants
MFA_SESSION_DURATION = 24 * 60 * 60  # 24 hours
MFA_GRACE_PERIOD = 7 * 24 * 60 * 60  # 7 days
ELEVATED_ACCESS_DURATION = 30 * 60  # 30 minutes
SESSION_EXTENSION_THRESHOLD = 5 * 60  # 5 minutes


class SecurityManager:
    """
    Manages security features including access control, MFA,
    and session management.
    """

    def __init__(self, app=None):
        self.app = app
        self.rbac_roles = {}
        self.rbac_permissions = {}
        self.risk_factors = {}

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize with Flask application"""
        self.app = app

        # Register extension with app
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['security'] = self

        # Load RBAC configuration
        self._load_rbac_config()

        # Set up request handlers
        app.before_request(self._check_session_security)

        # Register blueprint for security routes
        from security.routes import security_blueprint
        app.register_blueprint(security_blueprint, url_prefix='/security')

        app.logger.info("Security manager initialized")

    def _load_rbac_config(self):
        """Load RBAC configuration from file or database"""
        # In production, this would likely come from a database
        config_file = self.app.config.get('RBAC_CONFIG_FILE', 'security/rbac_config.json')

        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.rbac_roles = config.get('roles', {})
                self.rbac_permissions = config.get('permissions', {})
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.app.logger.warning(f"Failed to load RBAC config: {e}")

            # Set up default roles
            self.rbac_roles = {
                'admin': {
                    'description': 'Administrator with full access',
                    'permissions': ['*']
                },
                'practitioner': {
                    'description': 'Mental health practitioner',
                    'permissions': ['read:phi', 'write:phi', 'read:user', 'read:analytics']
                },
                'user': {
                    'description': 'Standard user',
                    'permissions': ['read:own', 'write:own']
                }
            }

            self.rbac_permissions = {
                'read:phi': 'Read PHI data',
                'write:phi': 'Write PHI data',
                'read:user': 'Read user data',
                'write:user': 'Write user data',
                'read:analytics': 'Read analytics data',
                'write:analytics': 'Write analytics data',
                'admin:user': 'Administer users',
                'admin:system': 'Administer system settings'
            }

    def _check_session_security(self):
        """Perform security checks before processing request"""
        if not current_user.is_authenticated:
            return

        # Check if session is expired - use the configured timeout from app config
        last_active = session.get('last_active', time.time())  # Default to current time if not set
        session_timeout = self.app.config.get('SESSION_TIMEOUT', 24 * 60 * 60)  # 24 hours default

        # Only check expiration if last_active is actually set and reasonable
        if last_active > 0 and time.time() - last_active > session_timeout:
            # Session has expired
            self.app.logger.info(f"Session expired for user {current_user.id}")

            # Clear session and redirect to login
            session.clear()
            flash("Your session has expired. Please log in again.", "warning")
            return redirect(url_for('email_login'))

        # Update last active time if we're close to session extension threshold
        if time.time() - last_active > SESSION_EXTENSION_THRESHOLD:
            session['last_active'] = int(time.time())

        # Check if client info has changed (potential session hijacking)
        if 'user_agent' in session and session['user_agent'] != request.user_agent.string:
            self.app.logger.warning(
                f"User agent changed for user {current_user.id}. "
                f"Potential session hijacking attempt."
            )

            # Clear session and redirect to login
            session.clear()
            flash("Your session has been ended due to security concerns.", "danger")
            return redirect(url_for('email_login'))

        # Set security headers for all responses
        @after_this_request
        def set_security_headers(response):
            response.headers['Content-Security-Policy'] = self.app.config.get(
                'CONTENT_SECURITY_POLICY',
                "default-src 'self'; script-src 'self'; object-src 'none'"
            )
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            return response

    def has_role(self, user, role_name: str) -> bool:
        """Check if a user has a specific role"""
        if not hasattr(user, 'roles'):
            return False

        return role_name in user.roles

    def has_permission(self, user, permission: str) -> bool:
        """Check if a user has a specific permission"""
        if not hasattr(user, 'roles'):
            return False

        # Admin role has all permissions
        if 'admin' in user.roles:
            return True

        # Check each role the user has
        for role_name in user.roles:
            if role_name in self.rbac_roles:
                role = self.rbac_roles[role_name]

                # Wildcard permission grants all access
                if '*' in role.get('permissions', []):
                    return True

                # Check specific permission
                if permission in role.get('permissions', []):
                    return True

                # Check permission pattern (e.g., 'read:*')
                if permission.endswith(':*'):
                    prefix = permission.split(':')[0] + ':'
                    for p in role.get('permissions', []):
                        if p.startswith(prefix):
                            return True

        return False

    def calculate_risk_score(self, user, action: str) -> int:
        """
        Calculate a risk score for the current request based on various factors

        Higher score indicates higher risk
        """
        score = 0

        # Base risk for different actions
        action_risks = {
            'view_phi': 5,
            'edit_phi': 8,
            'delete_phi': 10,
            'bulk_export': 8,
            'admin_action': 7
        }

        score += action_risks.get(action, 3)

        # Risk based on user factors
        if hasattr(user, 'failed_login_attempts') and user.failed_login_attempts > 3:
            score += user.failed_login_attempts

        if hasattr(user, 'last_password_change'):
            days_since_pw_change = (datetime.utcnow() - user.last_password_change).days
            if days_since_pw_change > 90:
                score += 3

        # Risk based on request factors
        if request.headers.get('X-Forwarded-For'):
            # Multiple proxies might indicate spoofing attempt
            score += len(request.headers.get('X-Forwarded-For').split(','))

        if 'user_ip' in session:
            # IP address changed
            if session['user_ip'] != request.remote_addr:
                score += 5

        # New device or location
        if not session.get('device_verified'):
            score += 4

        # Time-based factors
        hour = datetime.utcnow().hour
        if hour < 6 or hour > 22:  # Outside business hours
            score += 2

        return score

    def require_mfa(self, f):
        """Decorator to require MFA for sensitive operations"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('email_login'))

            # Check if user has completed MFA
            if not session.get('mfa_verified'):
                if hasattr(current_user, 'mfa_enabled') and current_user.mfa_enabled:
                    # Store the original destination
                    session['next_url'] = request.url
                    flash("Additional authentication required for this action.", "info")
                    return redirect(url_for('security.mfa_verify'))

                # If MFA is not enabled for this user but should be required
                # based on their role or the sensitivity of the operation
                risk_score = self.calculate_risk_score(current_user, 'view_phi')
                if risk_score > 7:
                    # High risk operation
                    session['next_url'] = request.url
                    flash("This sensitive operation requires additional verification.", "warning")
                    return redirect(url_for('security.mfa_verify'))

            return f(*args, **kwargs)
        return decorated_function

    def require_permission(self, permission: str):
        """Decorator to require a specific permission"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not current_user.is_authenticated:
                    return redirect(url_for('email_login'))

                # Check permission
                if not self.has_permission(current_user, permission):
                    flash("You do not have permission to access this resource.", "danger")
                    self.app.logger.warning(
                        f"Permission denied: {current_user.id} attempted to access {request.path} "
                        f"without required permission: {permission}"
                    )
                    return redirect(url_for('main.index'))

                return f(*args, **kwargs)
            return decorated_function
        return decorator

    def require_elevated_access(self, f):
        """
        Decorator for Just-In-Time access to sensitive operations
        Requires reauthentication and grants temporary elevated access
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('email_login'))

            # Check if user has current elevated access
            elevated_until = session.get('elevated_access_until', 0)
            if time.time() < elevated_until:
                # User has valid elevated access
                return f(*args, **kwargs)

            # Store the original destination
            session['next_url'] = request.url
            flash("This operation requires elevated access. Please reauthenticate.", "warning")
            return redirect(url_for('security.elevate_access'))

        return decorated_function

    def require_break_glass(self, f):
        """
        Decorator for emergency break-glass protocol
        For emergency access to PHI when normal authentication is not possible
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('email_login'))

            # Check if user is authorized for break-glass
            if not self.has_permission(current_user, 'break_glass'):
                flash("You are not authorized for emergency access.", "danger")
                return redirect(url_for('main.index'))

            # Check if break-glass is already active
            if session.get('break_glass_active'):
                # Log the access for compliance
                self.app.logger.critical(
                    f"BREAK-GLASS: User {current_user.id} accessing {request.path} "
                    f"under emergency protocol"
                )

                # Set a flag for audit purposes
                g.break_glass = True

                return f(*args, **kwargs)

            # If not active, redirect to break-glass initiation
            session['next_url'] = request.url
            return redirect(url_for('security.break_glass_init'))

        return decorated_function

    def generate_mfa_secret(self) -> str:
        """Generate a new MFA secret for TOTP"""
        return pyotp.random_base32()

    def get_mfa_qr_code(self, user, secret: str) -> BytesIO:
        """Generate QR code for MFA setup"""
        # Create a TOTP URI for the user
        app_name = self.app.config.get('APP_NAME', 'InnerArchitect')
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name=app_name
        )

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(totp_uri)
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")

        # Save to bytes buffer
        buffer = BytesIO()
        img.save(buffer)
        buffer.seek(0)

        return buffer

    def verify_mfa_code(self, secret: str, code: str) -> bool:
        """Verify a TOTP code against the secret"""
        totp = pyotp.TOTP(secret)
        return totp.verify(code)

    def get_recovery_codes(self, count: int = 10) -> List[str]:
        """Generate recovery codes for MFA backup"""
        codes = []
        for _ in range(count):
            # Generate a random code with good entropy
            code = base64.b32encode(os.urandom(10)).decode('utf-8')
            # Format it for easier reading
            code = '-'.join([code[i:i+5] for i in range(0, len(code), 5)])
            codes.append(code[:17])  # Trim to consistent length

        return codes

    def hash_recovery_codes(self, codes: List[str]) -> List[str]:
        """Hash recovery codes for secure storage"""
        hashed_codes = []

        for code in codes:
            # Create a unique salt for each code
            salt = os.urandom(16)

            # Hash the code with salt
            hash_obj = hashlib.pbkdf2_hmac(
                'sha256',
                code.encode('utf-8'),
                salt,
                100000  # High iteration count for security
            )

            # Store hash and salt together
            hashed_code = {
                'hash': base64.b64encode(hash_obj).decode('utf-8'),
                'salt': base64.b64encode(salt).decode('utf-8')
            }

            hashed_codes.append(json.dumps(hashed_code))

        return hashed_codes

    def verify_recovery_code(self, provided_code: str, hashed_codes: List[str]) -> Tuple[bool, List[str]]:
        """
        Verify a recovery code against the list of hashed codes

        Returns a tuple of (is_valid, updated_codes_list)
        """
        for i, hashed_code_json in enumerate(hashed_codes):
            try:
                hashed_code = json.loads(hashed_code_json)
                salt = base64.b64decode(hashed_code['salt'])
                stored_hash = base64.b64decode(hashed_code['hash'])

                # Hash the provided code with the same salt
                hash_obj = hashlib.pbkdf2_hmac(
                    'sha256',
                    provided_code.encode('utf-8'),
                    salt,
                    100000
                )

                # Compare hashes
                if hmac.compare_digest(hash_obj, stored_hash):
                    # Code is valid, remove it from the list
                    updated_codes = hashed_codes.copy()
                    updated_codes.pop(i)
                    return True, updated_codes
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        return False, hashed_codes

    def log_security_event(self, event_type: str, details: Dict[str, Any] = None):
        """
        Log a security event for audit purposes

        Args:
            event_type: Type of security event (e.g., 'mfa_success', 'mfa_failure')
            details: Additional details about the event
        """
        if details is None:
            details = {}

        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'user_id': current_user.id if current_user.is_authenticated else None,
            'ip_address': request.remote_addr,
            'user_agent': request.user_agent.string,
            'path': request.path,
            'method': request.method,
            'session_id': session.get('_id'),
            'details': details
        }

        # Log the event
        self.app.logger.info(f"SECURITY EVENT: {json.dumps(event)}")

        # Store in database for permanent audit trail
        # In a real implementation, this would call a function to store in the database

        # For critical events, trigger additional notifications
        critical_events = ['break_glass', 'mfa_failure', 'permission_denied', 'session_hijacking']
        if event_type in critical_events:
            self.app.logger.critical(f"CRITICAL SECURITY EVENT: {json.dumps(event)}")
            # In a real implementation, this would trigger notifications to security team


# Decorators for access control

def phi_access_required(f):
    """Decorator for functions that access PHI data"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('email_login'))

        # Get security manager
        security = current_app.extensions.get('security')
        if not security:
            current_app.logger.error("Security manager not initialized")
            raise RuntimeError("Security manager not initialized")

        # Check permission
        if not security.has_permission(current_user, 'read:phi'):
            security.log_security_event('permission_denied', {
                'permission': 'read:phi',
                'resource': request.path
            })
            flash("You do not have permission to access protected health information.", "danger")
            return redirect(url_for('main.index'))

        # Check if MFA is required
        if hasattr(current_user, 'mfa_enabled') and current_user.mfa_enabled:
            if not session.get('mfa_verified'):
                # Store the original destination
                session['next_url'] = request.url
                flash("Additional authentication required to access protected health information.", "info")
                return redirect(url_for('security.mfa_verify'))

        # Log PHI access for audit
        security.log_security_event('phi_access', {
            'resource_id': kwargs.get('id'),
            'resource_type': kwargs.get('type', 'unknown')
        })

        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator for admin-only functions"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('email_login'))

        # Get security manager
        security = current_app.extensions.get('security')
        if not security:
            current_app.logger.error("Security manager not initialized")
            raise RuntimeError("Security manager not initialized")

        # Check for admin role
        if not security.has_role(current_user, 'admin'):
            security.log_security_event('permission_denied', {
                'role': 'admin',
                'resource': request.path
            })
            flash("Administrator access required.", "danger")
            return redirect(url_for('main.index'))

        # Log admin action for audit
        security.log_security_event('admin_action', {
            'resource': request.path,
            'method': request.method
        })

        return f(*args, **kwargs)
    return decorated_function


def owner_or_admin_required(model, id_parameter='id'):
    """
    Decorator factory that checks if the current user is either:
    1. The owner of the resource
    2. An administrator

    Args:
        model: The model class to check ownership against
        id_parameter: The URL parameter that contains the resource ID
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('email_login'))

            # Get security manager
            security = current_app.extensions.get('security')
            if not security:
                current_app.logger.error("Security manager not initialized")
                raise RuntimeError("Security manager not initialized")

            # Check for admin role (admins can access all resources)
            if security.has_role(current_user, 'admin'):
                # Log admin access for audit
                security.log_security_event('admin_resource_access', {
                    'resource_type': model.__name__,
                    'resource_id': kwargs.get(id_parameter)
                })
                return f(*args, **kwargs)

            # Get the resource ID from URL parameters
            resource_id = kwargs.get(id_parameter)
            if not resource_id:
                flash("Resource not found.", "danger")
                return redirect(url_for('main.index'))

            # Get the resource
            resource = model.query.get(resource_id)
            if not resource:
                flash("Resource not found.", "danger")
                return redirect(url_for('main.index'))

            # Check if current user is the owner
            is_owner = False
            if hasattr(resource, 'user_id'):
                is_owner = resource.user_id == current_user.id
            elif hasattr(resource, 'owner_id'):
                is_owner = resource.owner_id == current_user.id

            if not is_owner:
                security.log_security_event('permission_denied', {
                    'resource_type': model.__name__,
                    'resource_id': resource_id,
                    'reason': 'not_owner'
                })
                flash("You do not have permission to access this resource.", "danger")
                return redirect(url_for('main.index'))

            # Log resource access for audit
            security.log_security_event('resource_access', {
                'resource_type': model.__name__,
                'resource_id': resource_id
            })

            return f(*args, **kwargs)
        return decorated_function
    return decorator