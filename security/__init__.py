"""
HIPAA-Compliant Security Module for The Inner Architect

This package provides comprehensive security features to ensure
HIPAA compliance and protect sensitive user data.

Components:
- Encryption: Data protection at rest and in transit
- Access Control: Fine-grained permissions and MFA
- Audit: Comprehensive audit logging and monitoring
- Breach: Breach detection and notification
- Policy: Security policy enforcement
"""

from security.encryption import EncryptionManager, EncryptedField
from security.access_control import SecurityManager
from security.audit import AuditManager, AuditLog

__all__ = [
    'EncryptionManager',
    'EncryptedField',
    'SecurityManager',
    'AuditManager',
    'AuditLog',
    'init_app'
]

def init_app(app):
    """
    Initialize all security components with the Flask application
    
    Args:
        app: Flask application instance
    """
    # Initialize encryption
    encryption = EncryptionManager(app)
    
    # Initialize security manager
    security = SecurityManager(app)
    
    # Initialize audit manager
    audit = AuditManager(app)
    
    return {
        'encryption': encryption,
        'security': security,
        'audit': audit
    }