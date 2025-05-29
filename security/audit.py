"""
HIPAA-Compliant Audit System for The Inner Architect

This module implements a comprehensive audit system to track all access and
modifications to PHI in compliance with HIPAA Security Rule requirements.
It provides immutable audit logs and monitoring capabilities.

Features:
- Immutable audit logging for all PHI access
- Tamper-evident design with cryptographic verification
- Comprehensive tracking of user activities
- HIPAA-compliant audit trail generation
- Real-time monitoring and alerting for suspicious activities
"""

import json
import time
import hashlib
import hmac
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from flask import current_app, request, g
from flask_login import current_user
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, ForeignKey

# Import database instance
from database import db

# Audit event types
PHI_ACCESS = 'phi_access'
PHI_MODIFICATION = 'phi_modification'
PHI_DELETION = 'phi_deletion'
AUTH_SUCCESS = 'authentication_success'
AUTH_FAILURE = 'authentication_failure'
MFA_SUCCESS = 'mfa_success'
MFA_FAILURE = 'mfa_failure'
ADMIN_ACTION = 'admin_action'
SECURITY_EVENT = 'security_event'
PERMISSION_DENIED = 'permission_denied'
BREAK_GLASS = 'break_glass'


class AuditLog(db.Model):
    """
    HIPAA-compliant audit log model for tracking all PHI access and modifications
    """
    __tablename__ = 'audit_logs'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=True)
    event_type = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True, index=True)
    resource_id = Column(String(36), nullable=True, index=True)
    action = Column(String(50), nullable=False)
    ip_address = Column(String(45), nullable=True)  # IPv6-compatible length
    user_agent = Column(String(255), nullable=True)
    details = Column(Text, nullable=True)  # JSON stored as text for SQLite compatibility
    success = Column(Boolean, nullable=False, default=True)
    entry_hash = Column(String(64), nullable=False, index=True)
    previous_hash = Column(String(64), nullable=True, index=True)

    def __repr__(self):
        return f'<AuditLog {self.id} {self.event_type}>'


class AuditManager:
    """
    Manages audit logging and monitoring throughout the application
    with HIPAA-compliant security controls.
    """

    def __init__(self, app=None):
        self.app = app
        self.last_hash = None

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize with Flask application"""
        self.app = app

        # Register extension with app
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['audit'] = self

        # Set up request handlers
        app.before_request(self._before_request)
        app.after_request(self._after_request)

        # Initialize last hash from database (handle missing table gracefully)
        with app.app_context():
            try:
                last_log = AuditLog.query.order_by(AuditLog.timestamp.desc()).first()
                if last_log:
                    self.last_hash = last_log.entry_hash
            except Exception as e:
                # Table might not exist yet during initial setup
                app.logger.info(f"Audit table not yet available during initialization: {e}")
                self.last_hash = None

        app.logger.info("Audit manager initialized")

    def _before_request(self):
        """
        Log request start time for performance monitoring
        and set unique request ID
        """
        g.request_start_time = time.time()
        g.request_id = str(uuid.uuid4())

    def _after_request(self, response):
        """
        Log request completion and performance metrics
        """
        # Skip for static files
        if request.path.startswith('/static'):
            return response

        if hasattr(g, 'request_start_time'):
            duration = time.time() - g.request_start_time

            # Log requests that exceed performance thresholds
            if duration > 1.0:  # Log slow requests (> 1 second)
                self.app.logger.warning(
                    f"Slow request: {request.method} {request.path} took {duration:.2f}s"
                )

        return response

    def log_event(self, event_type: str, action: str, resource_type: Optional[str] = None,
                 resource_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None,
                 success: bool = True) -> AuditLog:
        """
        Create an immutable audit log entry

        Args:
            event_type: Type of event (e.g., 'phi_access', 'authentication')
            action: Action being performed (e.g., 'read', 'update')
            resource_type: Type of resource being accessed (e.g., 'user', 'note')
            resource_id: ID of the resource being accessed
            details: Additional details about the event
            success: Whether the action was successful

        Returns:
            The created AuditLog instance
        """
        # Use current user if available
        user_id = None
        if current_user and current_user.is_authenticated:
            user_id = current_user.id

        # Create log entry
        log_entry = AuditLog(
            user_id=user_id,
            event_type=event_type,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=request.remote_addr if request else None,
            user_agent=request.user_agent.string if request and request.user_agent else None,
            details=json.dumps(details) if details else None,  # Serialize JSON for SQLite
            success=success,
            previous_hash=self.last_hash
        )

        # Generate hash for this entry
        entry_data = {
            'id': log_entry.id,
            'timestamp': log_entry.timestamp.isoformat(),
            'user_id': log_entry.user_id,
            'event_type': log_entry.event_type,
            'action': log_entry.action,
            'resource_type': log_entry.resource_type,
            'resource_id': log_entry.resource_id,
            'ip_address': log_entry.ip_address,
            'details': json.loads(log_entry.details) if log_entry.details else None,
            'success': log_entry.success,
            'previous_hash': log_entry.previous_hash
        }

        # Create a deterministic JSON string
        entry_json = json.dumps(entry_data, sort_keys=True)

        # Generate a hash of the entry including the previous hash (blockchain style)
        hash_obj = hashlib.sha256(entry_json.encode('utf-8'))
        log_entry.entry_hash = hash_obj.hexdigest()

        # Update last hash
        self.last_hash = log_entry.entry_hash

        # Save to database
        try:
            db.session.add(log_entry)
            db.session.commit()

            # For critical events, also log to application logs
            critical_events = [PHI_ACCESS, PHI_MODIFICATION, PHI_DELETION,
                              AUTH_FAILURE, MFA_FAILURE, BREAK_GLASS]

            if event_type in critical_events:
                self.app.logger.info(
                    f"AUDIT: {event_type} - {action} - User: {user_id} - "
                    f"Resource: {resource_type}/{resource_id} - Success: {success}"
                )

                # Check if this is a suspicious event that needs immediate attention
                self._check_suspicious_activity(log_entry)
        except Exception as e:
            db.session.rollback()
            self.app.logger.error(f"Failed to create audit log: {e}")

            # Fallback to application logs for critical events
            self.app.logger.warning(
                f"AUDIT FALLBACK: {event_type} - {action} - User: {user_id} - "
                f"Resource: {resource_type}/{resource_id} - Success: {success}"
            )

        return log_entry

    def _check_suspicious_activity(self, log_entry: AuditLog):
        """
        Check for suspicious activity patterns that might indicate
        security threats

        Args:
            log_entry: The most recent audit log entry
        """
        # Skip for successful authentication events
        if log_entry.event_type == AUTH_SUCCESS:
            return

        # Check for multiple authentication failures
        if log_entry.event_type == AUTH_FAILURE:
            self._check_auth_failures(log_entry)

        # Check for unusual PHI access patterns
        if log_entry.event_type == PHI_ACCESS:
            self._check_unusual_phi_access(log_entry)

        # Check for permission denied patterns
        if log_entry.event_type == PERMISSION_DENIED:
            self._check_permission_probing(log_entry)

    def _check_auth_failures(self, log_entry: AuditLog):
        """Check for brute force authentication attempts"""
        # Look for multiple failures from same IP in last 10 minutes
        ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)

        failure_count = AuditLog.query.filter(
            AuditLog.event_type == AUTH_FAILURE,
            AuditLog.ip_address == log_entry.ip_address,
            AuditLog.timestamp >= ten_minutes_ago
        ).count()

        if failure_count >= 5:
            # Potential brute force attack
            self.app.logger.critical(
                f"SECURITY ALERT: Possible brute force attack detected from IP {log_entry.ip_address} "
                f"with {failure_count} failed authentication attempts in 10 minutes."
            )

            # In a real implementation, this would trigger additional security measures
            # such as temporary IP ban, account lockout, or security team notification

    def _check_unusual_phi_access(self, log_entry: AuditLog):
        """Check for unusual PHI access patterns"""
        # Skip if no user is associated
        if not log_entry.user_id:
            return

        # Look for high volume of PHI access in short time
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)

        access_count = AuditLog.query.filter(
            AuditLog.event_type == PHI_ACCESS,
            AuditLog.user_id == log_entry.user_id,
            AuditLog.timestamp >= one_hour_ago
        ).count()

        # Threshold would be configured based on normal usage patterns
        if access_count > 50:  # Example threshold
            self.app.logger.warning(
                f"SECURITY ALERT: Unusual PHI access volume detected for user {log_entry.user_id} "
                f"with {access_count} records accessed in the last hour."
            )

        # Check for access to unusual resource types for this user
        user_common_resources = self._get_common_resources_for_user(log_entry.user_id)

        if log_entry.resource_type not in user_common_resources:
            self.app.logger.info(
                f"SECURITY NOTE: User {log_entry.user_id} accessed uncommon resource type "
                f"{log_entry.resource_type} which is outside their normal pattern."
            )

    def _check_permission_probing(self, log_entry: AuditLog):
        """Check for permission probing (attempting to access multiple restricted resources)"""
        # Look for multiple permission denied events in short time
        thirty_minutes_ago = datetime.utcnow() - timedelta(minutes=30)

        denial_count = AuditLog.query.filter(
            AuditLog.event_type == PERMISSION_DENIED,
            AuditLog.user_id == log_entry.user_id,
            AuditLog.timestamp >= thirty_minutes_ago
        ).count()

        if denial_count >= 5:  # Example threshold
            self.app.logger.critical(
                f"SECURITY ALERT: Possible permission probing detected for user {log_entry.user_id} "
                f"with {denial_count} denied access attempts in 30 minutes."
            )

            # In a real implementation, this would trigger additional security measures

    def _get_common_resources_for_user(self, user_id: str) -> List[str]:
        """Get the common resource types accessed by a user"""
        # Look at access patterns over last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        # Query for resource types and their access counts
        resource_counts = db.session.query(
            AuditLog.resource_type,
            db.func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.user_id == user_id,
            AuditLog.event_type == PHI_ACCESS,
            AuditLog.timestamp >= thirty_days_ago
        ).group_by(
            AuditLog.resource_type
        ).all()

        # Consider a resource type common if it has been accessed at least 5 times
        common_resources = [r[0] for r in resource_counts if r[1] >= 5 and r[0] is not None]

        return common_resources

    def verify_log_integrity(self, start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> bool:
        """
        Verify the integrity of the audit log chain

        Args:
            start_date: Optional start date for verification
            end_date: Optional end date for verification

        Returns:
            True if integrity is verified, False if tampering is detected
        """
        query = AuditLog.query.order_by(AuditLog.timestamp.asc())

        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)

        logs = query.all()

        if not logs:
            return True  # No logs to verify

        previous_hash = logs[0].previous_hash

        for log in logs:
            # Skip first entry if it has no previous hash
            if log.previous_hash is None and previous_hash is None:
                previous_hash = log.entry_hash
                continue

            # Verify that this log's previous hash matches the previous entry's hash
            if log.previous_hash != previous_hash:
                self.app.logger.critical(
                    f"AUDIT INTEGRITY VIOLATION: Log chain broken at log ID {log.id}, "
                    f"timestamp {log.timestamp}. Expected previous hash {previous_hash}, "
                    f"found {log.previous_hash}"
                )
                return False

            # Verify this log's hash
            entry_data = {
                'id': log.id,
                'timestamp': log.timestamp.isoformat(),
                'user_id': log.user_id,
                'event_type': log.event_type,
                'action': log.action,
                'resource_type': log.resource_type,
                'resource_id': log.resource_id,
                'ip_address': log.ip_address,
                'details': json.loads(log.details) if log.details else None,
                'success': log.success,
                'previous_hash': log.previous_hash
            }

            # Create a deterministic JSON string
            entry_json = json.dumps(entry_data, sort_keys=True)

            # Generate hash and compare
            hash_obj = hashlib.sha256(entry_json.encode('utf-8'))
            calculated_hash = hash_obj.hexdigest()

            if calculated_hash != log.entry_hash:
                self.app.logger.critical(
                    f"AUDIT INTEGRITY VIOLATION: Log content modified for ID {log.id}, "
                    f"timestamp {log.timestamp}. Expected hash {log.entry_hash}, "
                    f"calculated {calculated_hash}"
                )
                return False

            previous_hash = log.entry_hash

        return True

    def export_audit_trail(self, start_date: datetime, end_date: datetime,
                          user_id: Optional[str] = None,
                          event_types: Optional[List[str]] = None,
                          format: str = 'json') -> Union[str, Dict]:
        """
        Export an audit trail for a specified time period

        Args:
            start_date: Start date for the audit trail
            end_date: End date for the audit trail
            user_id: Optional user ID to filter by
            event_types: Optional list of event types to include
            format: Output format ('json' or 'csv')

        Returns:
            Formatted audit trail data
        """
        query = AuditLog.query.filter(
            AuditLog.timestamp >= start_date,
            AuditLog.timestamp <= end_date
        ).order_by(AuditLog.timestamp.asc())

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        if event_types:
            query = query.filter(AuditLog.event_type.in_(event_types))

        logs = query.all()

        # Format the results
        if format.lower() == 'json':
            return self._format_audit_trail_json(logs)
        elif format.lower() == 'csv':
            return self._format_audit_trail_csv(logs)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _format_audit_trail_json(self, logs: List[AuditLog]) -> Dict:
        """Format audit trail as JSON"""
        result = {
            'generated_at': datetime.utcnow().isoformat(),
            'entry_count': len(logs),
            'entries': []
        }

        for log in logs:
            entry = {
                'id': log.id,
                'timestamp': log.timestamp.isoformat(),
                'user_id': log.user_id,
                'event_type': log.event_type,
                'action': log.action,
                'resource_type': log.resource_type,
                'resource_id': log.resource_id,
                'ip_address': log.ip_address,
                'user_agent': log.user_agent,
                'details': json.loads(log.details) if log.details else None,
                'success': log.success
            }
            result['entries'].append(entry)

        return result

    def _format_audit_trail_csv(self, logs: List[AuditLog]) -> str:
        """Format audit trail as CSV"""
        csv_lines = ['timestamp,id,user_id,event_type,action,resource_type,resource_id,ip_address,success']

        for log in logs:
            line = f'{log.timestamp.isoformat()},{log.id},{log.user_id},{log.event_type},'
            line += f'{log.action},{log.resource_type},{log.resource_id},{log.ip_address},{log.success}'
            csv_lines.append(line)

        return '\n'.join(csv_lines)


# Function decorators for audit logging

def audit_phi_access(resource_type):
    """
    Decorator for logging PHI access

    Args:
        resource_type: Type of resource being accessed
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get audit manager
            audit = current_app.extensions.get('audit')
            if not audit:
                current_app.logger.error("Audit manager not initialized")
                raise RuntimeError("Audit manager not initialized")

            # Get resource ID from kwargs
            resource_id = kwargs.get('id') or kwargs.get('user_id') or kwargs.get('patient_id')

            # Log the access before processing
            audit.log_event(
                event_type=PHI_ACCESS,
                action='read',
                resource_type=resource_type,
                resource_id=resource_id,
                details={
                    'method': request.method,
                    'path': request.path,
                    'args': {k: v for k, v in kwargs.items() if k != 'password'}
                }
            )

            # Call the original function
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def audit_phi_modification(resource_type):
    """
    Decorator for logging PHI modification

    Args:
        resource_type: Type of resource being modified
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get audit manager
            audit = current_app.extensions.get('audit')
            if not audit:
                current_app.logger.error("Audit manager not initialized")
                raise RuntimeError("Audit manager not initialized")

            # Get resource ID from kwargs
            resource_id = kwargs.get('id') or kwargs.get('user_id') or kwargs.get('patient_id')

            # Determine action based on request method
            if request.method == 'POST':
                action = 'create'
            elif request.method == 'PUT':
                action = 'update'
            elif request.method == 'PATCH':
                action = 'partial_update'
            else:
                action = 'modify'

            # Log the modification
            log_entry = audit.log_event(
                event_type=PHI_MODIFICATION,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details={
                    'method': request.method,
                    'path': request.path,
                    'form_data': {k: v for k, v in request.form.items() if k != 'password'},
                    'json_data': request.get_json(silent=True)
                }
            )

            # Call the original function
            result = f(*args, **kwargs)

            # Update success status based on response
            success = True
            if hasattr(result, 'status_code') and result.status_code >= 400:
                success = False

                # Update the log entry
                log_entry.success = success
                db.session.add(log_entry)
                db.session.commit()

            return result
        return decorated_function
    return decorator