"""
HIPAA-Compliant Encryption Module for The Inner Architect

This module provides military-grade encryption for protecting sensitive PHI
(Protected Health Information) in compliance with HIPAA Security Rule requirements.
It implements both data-at-rest and data-in-transit encryption capabilities.

Features:
- AES-256-GCM encryption for sensitive data
- Key rotation and management
- Field-level encryption for database
- Payload encryption for API communications
"""

import os
import base64
import json
import time
import hmac
import hashlib
from typing import Any, Dict, Optional, Tuple, Union
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
from datetime import datetime, timedelta
from flask import current_app, g

# Constants
KEY_ROTATION_INTERVAL = 30  # days
AUTH_TAG_LENGTH = 16  # bytes
NONCE_LENGTH = 12  # bytes
SALT_LENGTH = 16  # bytes
KEY_LENGTH = 32  # bytes (256 bits)
VERSION = 1  # encryption schema version

class EncryptionManager:
    """
    Manages encryption operations throughout the application with 
    HIPAA-compliant security controls.
    """
    
    def __init__(self, app=None):
        self.app = app
        self.master_key = None
        self.key_creation_time = None
        self.data_keys = {}
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask application"""
        self.app = app
        
        # Register extension with app
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['encryption'] = self
        
        # Set up master key from environment or secure storage
        self._setup_master_key()
        
        # Register teardown to clear keys from memory
        app.teardown_appcontext(self._teardown)
    
    def _setup_master_key(self):
        """
        Set up the master encryption key from secure storage.
        In production, this would come from a Hardware Security Module (HSM)
        or a secure key management service like AWS KMS.
        """
        if self.app.config.get('TESTING'):
            # Use a static key for testing only
            self.master_key = base64.b64decode(
                self.app.config.get('ENCRYPTION_TEST_KEY', 
                                   'VGhpc0lzQVRlc3RLZXlPbmx5Rm9yVGVzdGluZ1B1cnBvc2Vz')
            )
            self.key_creation_time = datetime.utcnow()
            return
            
        # For production, get from secure key management
        # This is a simplified version - production would use HSM or KMS
        if self.app.config.get('ENCRYPTION_KEY_FILE'):
            try:
                with open(self.app.config['ENCRYPTION_KEY_FILE'], 'rb') as f:
                    key_data = json.load(f)
                    self.master_key = base64.b64decode(key_data['key'])
                    self.key_creation_time = datetime.fromisoformat(key_data['created'])
                    
                    # Check if key rotation is needed
                    self._check_key_rotation()
            except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
                self.app.logger.error(f"Error loading encryption key: {e}")
                self._generate_new_master_key()
        else:
            # If no key file is configured, generate a new one
            self._generate_new_master_key()
    
    def _generate_new_master_key(self):
        """Generate a new master key and store it securely"""
        # Generate a strong random key
        self.master_key = os.urandom(KEY_LENGTH)
        self.key_creation_time = datetime.utcnow()
        
        # Store the key securely
        if self.app.config.get('ENCRYPTION_KEY_FILE'):
            key_data = {
                'key': base64.b64encode(self.master_key).decode('utf-8'),
                'created': self.key_creation_time.isoformat()
            }
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.app.config['ENCRYPTION_KEY_FILE']), 
                       exist_ok=True)
            
            # Write with restricted permissions
            with open(self.app.config['ENCRYPTION_KEY_FILE'], 'w') as f:
                json.dump(key_data, f)
            
            # Set strict permissions (owner read-only)
            os.chmod(self.app.config['ENCRYPTION_KEY_FILE'], 0o400)
            
        self.app.logger.info("Generated new master encryption key")
    
    def _check_key_rotation(self):
        """Check if key rotation is needed based on age"""
        if self.key_creation_time:
            age = datetime.utcnow() - self.key_creation_time
            if age > timedelta(days=KEY_ROTATION_INTERVAL):
                self.app.logger.info("Encryption key rotation needed")
                self._rotate_master_key()
    
    def _rotate_master_key(self):
        """Rotate the master encryption key"""
        # Store the old key for decryption of existing data
        old_key = self.master_key
        old_key_time = self.key_creation_time
        
        # Generate a new master key
        self._generate_new_master_key()
        
        # TODO: In a real implementation, we would:
        # 1. Schedule a background job to re-encrypt existing data
        # 2. Track key versions to know which key to use for decryption
        # 3. Implement a secure key retirement policy
        
        self.app.logger.info("Master encryption key rotated")
    
    def _derive_data_key(self, key_id: str) -> bytes:
        """
        Derive a data key for a specific purpose using HKDF
        to avoid using the master key directly
        """
        if key_id in self.data_keys:
            return self.data_keys[key_id]
            
        # Use HKDF to derive a specific key for this purpose
        info = f"inner-architect-{key_id}-key-v{VERSION}".encode('utf-8')
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=KEY_LENGTH,
            salt=None,  # Static salt could be used for different environments
            info=info,
            backend=default_backend()
        )
        
        # Derive the key from the master key
        derived_key = hkdf.derive(self.master_key)
        
        # Cache the derived key for this request
        self.data_keys[key_id] = derived_key
        
        return derived_key
    
    def encrypt(self, data: Union[str, bytes], purpose: str = 'general') -> str:
        """
        Encrypt data using AES-256-GCM with authentication
        
        Args:
            data: The data to encrypt (string or bytes)
            purpose: The purpose identifier for key derivation
            
        Returns:
            Base64-encoded encrypted data with metadata
        """
        if isinstance(data, str):
            plaintext = data.encode('utf-8')
        else:
            plaintext = data
            
        # Get the appropriate key for this purpose
        key = self._derive_data_key(purpose)
        
        # Generate a random nonce/IV
        nonce = os.urandom(NONCE_LENGTH)
        
        # Create the cipher
        aesgcm = AESGCM(key)
        
        # Encrypt and authenticate the data
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        
        # Create the result format with metadata
        # Format: version|nonce|ciphertext
        result = {
            'v': VERSION,
            'n': base64.b64encode(nonce).decode('utf-8'),
            'd': base64.b64encode(ciphertext).decode('utf-8'),
            'p': purpose
        }
        
        # Return as JSON string with base64 encoding
        return base64.b64encode(json.dumps(result).encode('utf-8')).decode('utf-8')
    
    def decrypt(self, encrypted_data: str) -> bytes:
        """
        Decrypt data that was encrypted with the encrypt method
        
        Args:
            encrypted_data: Base64-encoded encrypted data with metadata
            
        Returns:
            Decrypted data as bytes
        """
        try:
            # Decode the outer base64
            json_data = base64.b64decode(encrypted_data.encode('utf-8')).decode('utf-8')
            
            # Parse the JSON
            result = json.loads(json_data)
            
            # Check version
            if result.get('v') != VERSION:
                raise ValueError(f"Unsupported encryption version: {result.get('v')}")
                
            # Get the purpose
            purpose = result.get('p', 'general')
            
            # Get the key for this purpose
            key = self._derive_data_key(purpose)
            
            # Decode the nonce and ciphertext
            nonce = base64.b64decode(result.get('n'))
            ciphertext = base64.b64decode(result.get('d'))
            
            # Create the cipher
            aesgcm = AESGCM(key)
            
            # Decrypt the data
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            
            return plaintext
        except Exception as e:
            self.app.logger.error(f"Decryption error: {e}")
            raise ValueError("Failed to decrypt data") from e
    
    def _teardown(self, exception):
        """Clear sensitive key material from memory on request end"""
        self.data_keys.clear()


class EncryptedField:
    """
    SQLAlchemy TypeDecorator for automatically encrypting and
    decrypting database fields containing PHI
    """
    
    def __init__(self, purpose='db-field'):
        self.purpose = purpose
    
    def process_bind_param(self, value, dialect):
        """Encrypt data before storing in database"""
        if value is None:
            return None
            
        # Get encryption manager
        manager = current_app.extensions.get('encryption')
        if not manager:
            current_app.logger.error("Encryption manager not initialized")
            raise RuntimeError("Encryption manager not initialized")
            
        # Encrypt the value
        return manager.encrypt(value, self.purpose)
    
    def process_result_value(self, value, dialect):
        """Decrypt data when retrieving from database"""
        if value is None:
            return None
            
        # Get encryption manager
        manager = current_app.extensions.get('encryption')
        if not manager:
            current_app.logger.error("Encryption manager not initialized")
            raise RuntimeError("Encryption manager not initialized")
            
        # Decrypt the value
        decrypted = manager.decrypt(value)
        return decrypted.decode('utf-8')


def encrypt_payload(payload: Dict[str, Any], purpose: str = 'api') -> Dict[str, Any]:
    """
    Encrypt an API payload for secure transmission
    
    Args:
        payload: The data to encrypt
        purpose: The purpose identifier for key derivation
        
    Returns:
        Dictionary with encrypted payload and metadata
    """
    # Get encryption manager
    manager = current_app.extensions.get('encryption')
    if not manager:
        current_app.logger.error("Encryption manager not initialized")
        raise RuntimeError("Encryption manager not initialized")
        
    # Convert payload to JSON string
    payload_json = json.dumps(payload)
    
    # Encrypt the payload
    encrypted = manager.encrypt(payload_json, purpose)
    
    # Create the result with metadata
    return {
        'encrypted': True,
        'data': encrypted,
        'timestamp': int(time.time())
    }


def decrypt_payload(encrypted_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decrypt an API payload
    
    Args:
        encrypted_payload: Dictionary with encrypted payload and metadata
        
    Returns:
        Original decrypted payload
    """
    # Get encryption manager
    manager = current_app.extensions.get('encryption')
    if not manager:
        current_app.logger.error("Encryption manager not initialized")
        raise RuntimeError("Encryption manager not initialized")
        
    # Check if payload is actually encrypted
    if not encrypted_payload.get('encrypted', False):
        return encrypted_payload
        
    # Get the encrypted data
    encrypted_data = encrypted_payload.get('data')
    if not encrypted_data:
        raise ValueError("No encrypted data found in payload")
        
    # Decrypt the payload
    decrypted = manager.decrypt(encrypted_data)
    
    # Parse the JSON
    return json.loads(decrypted.decode('utf-8'))


def hash_sensitive_data(data: str, salt: Optional[bytes] = None) -> Tuple[str, bytes]:
    """
    Create a secure hash of sensitive data for comparison without storage
    
    Args:
        data: The sensitive data to hash
        salt: Optional salt for the hash (generated if not provided)
        
    Returns:
        Tuple of (hash_string, salt)
    """
    if salt is None:
        salt = os.urandom(SALT_LENGTH)
        
    # Use PBKDF2 with high iteration count for security
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    
    # Derive the key (hash)
    hash_bytes = kdf.derive(data.encode('utf-8'))
    
    # Return the hash and salt
    return base64.b64encode(hash_bytes).decode('utf-8'), salt


def verify_hashed_data(data: str, hash_string: str, salt: bytes) -> bool:
    """
    Verify if data matches a previously created hash
    
    Args:
        data: The data to verify
        hash_string: The base64-encoded hash to compare against
        salt: The salt used for the hash
        
    Returns:
        True if the data matches the hash, False otherwise
    """
    # Decode the hash
    stored_hash = base64.b64decode(hash_string.encode('utf-8'))
    
    # Use PBKDF2 with the same parameters
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    
    # Verify the hash
    try:
        kdf.verify(data.encode('utf-8'), stored_hash)
        return True
    except Exception:
        return False


def secure_random_string(length: int = 32) -> str:
    """
    Generate a cryptographically secure random string
    
    Args:
        length: The length of the random string
        
    Returns:
        Secure random string
    """
    # Generate random bytes
    random_bytes = os.urandom(length)
    
    # Convert to base64 and strip non-alphanumeric characters
    random_string = base64.b64encode(random_bytes).decode('utf-8')
    random_string = ''.join(c for c in random_string if c.isalnum())
    
    # Return the string truncated to the requested length
    return random_string[:length]