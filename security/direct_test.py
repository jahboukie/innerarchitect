#!/usr/bin/env python3
"""
Direct Security Component Testing for The Inner Architect

This script directly tests the security components without requiring
a running Flask application or additional dependencies.
"""

import os
import sys
import time
import json
import uuid
import base64
import hashlib
import logging
import datetime
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("security_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("security_test")

class SecurityComponentTest:
    """Direct testing of security components"""
    
    def __init__(self):
        self.results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'vulnerabilities': []
        }
        
    def run_all_tests(self):
        """Run all direct security component tests"""
        logger.info("Starting direct security component tests")
        
        # Test encryption
        self.test_encryption()
        
        # Test password hashing
        self.test_password_hashing()
        
        # Test crypto primitives
        self.test_crypto_primitives()
        
        # Generate report
        self.generate_report()
        
    def test_encryption(self):
        """Test encryption primitives"""
        logger.info("Testing encryption primitives")
        
        try:
            # Test AES-256-GCM encryption directly
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            
            # Generate a key
            password = b"test_password"
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = kdf.derive(password)
            
            # Generate a nonce
            nonce = os.urandom(12)
            
            # Create an AESGCM object with the key
            aesgcm = AESGCM(key)
            
            # Encrypt data
            plaintext = b"This is a secret message for testing encryption"
            associated_data = b"authenticated but not encrypted"
            ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
            
            # Decrypt data
            decrypted = aesgcm.decrypt(nonce, ciphertext, associated_data)
            
            if decrypted != plaintext:
                self._log_vulnerability(
                    'critical',
                    'AES-GCM encryption failure',
                    'Data was not correctly decrypted after encryption',
                    'Verify cryptography library installation'
                )
            else:
                logger.info("✓ AES-GCM encryption/decryption test passed")
                self.results['passed'] += 1
            
            # Test tamper resistance
            try:
                # Tamper with the ciphertext
                tampered_ciphertext = bytearray(ciphertext)
                tampered_ciphertext[5] ^= 0xFF  # Flip some bits
                
                # Try to decrypt
                aesgcm.decrypt(nonce, bytes(tampered_ciphertext), associated_data)
                
                self._log_vulnerability(
                    'critical',
                    'AES-GCM tamper detection failure',
                    'Tampered ciphertext was decrypted without error',
                    'Verify AES-GCM implementation'
                )
            except Exception:
                # This is expected - tampered data should fail
                logger.info("✓ AES-GCM tamper detection test passed")
                self.results['passed'] += 1
                
            # Test HKDF
            from cryptography.hazmat.primitives.kdf.hkdf import HKDF
            
            # Derive a key using HKDF
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                info=b"test-key-derivation",
            )
            
            derived_key = hkdf.derive(key)
            
            if len(derived_key) != 32:
                self._log_vulnerability(
                    'high',
                    'HKDF key derivation failure',
                    'Derived key has incorrect length',
                    'Verify HKDF implementation'
                )
            else:
                logger.info("✓ HKDF key derivation test passed")
                self.results['passed'] += 1
                
        except Exception as e:
            self._log_vulnerability(
                'critical',
                'Encryption testing error',
                f'Exception during encryption testing: {str(e)}',
                'Verify cryptography library installation'
            )
            logger.error(f"Error testing encryption: {e}")
    
    def test_password_hashing(self):
        """Test password hashing functions"""
        logger.info("Testing password hashing functions")
        
        try:
            # Test PBKDF2 for password hashing
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            from cryptography.hazmat.primitives import hashes
            
            password = b"secure_password"
            salt = os.urandom(16)
            
            # Create a PBKDF2HMAC object
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            
            # Derive a key from the password
            key = kdf.derive(password)
            
            # Verify the password
            kdf_verify = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            
            try:
                kdf_verify.verify(password, key)
                logger.info("✓ PBKDF2 password verification test passed")
                self.results['passed'] += 1
            except Exception:
                self._log_vulnerability(
                    'critical',
                    'PBKDF2 password verification failure',
                    'Password verification failed for correct password',
                    'Verify PBKDF2 implementation'
                )
            
            # Test incorrect password
            wrong_password = b"wrong_password"
            try:
                kdf_verify = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                kdf_verify.verify(wrong_password, key)
                
                self._log_vulnerability(
                    'critical',
                    'PBKDF2 incorrect password accepted',
                    'Verification succeeded for incorrect password',
                    'Verify PBKDF2 implementation'
                )
            except Exception:
                # This is expected - wrong password should fail
                logger.info("✓ PBKDF2 incorrect password rejection test passed")
                self.results['passed'] += 1
                
        except Exception as e:
            self._log_vulnerability(
                'critical',
                'Password hashing testing error',
                f'Exception during password hashing testing: {str(e)}',
                'Verify cryptography library installation'
            )
            logger.error(f"Error testing password hashing: {e}")
    
    def test_crypto_primitives(self):
        """Test cryptographic primitives"""
        logger.info("Testing cryptographic primitives")
        
        try:
            # Test secure random generation
            random_bytes = os.urandom(32)
            if len(random_bytes) != 32:
                self._log_vulnerability(
                    'high',
                    'Secure random generation failure',
                    'Generated random bytes have incorrect length',
                    'Verify os.urandom implementation'
                )
            else:
                logger.info("✓ Secure random generation test passed")
                self.results['passed'] += 1
            
            # Test different random calls produce different results
            random_bytes2 = os.urandom(32)
            if random_bytes == random_bytes2:
                self._log_vulnerability(
                    'critical',
                    'Secure random generation weakness',
                    'Multiple calls to os.urandom produced identical results',
                    'Verify system entropy sources'
                )
            else:
                logger.info("✓ Secure random uniqueness test passed")
                self.results['passed'] += 1
            
            # Test cryptographic hash functions
            from cryptography.hazmat.primitives import hashes
            
            # Test SHA-256
            digest = hashes.Hash(hashes.SHA256())
            digest.update(b"test message")
            hash_value = digest.finalize()
            
            if len(hash_value) != 32:  # SHA-256 is 32 bytes
                self._log_vulnerability(
                    'high',
                    'SHA-256 hash failure',
                    'SHA-256 hash has incorrect length',
                    'Verify hash implementation'
                )
            else:
                logger.info("✓ SHA-256 hash test passed")
                self.results['passed'] += 1
            
            # Test HMAC
            import hmac
            
            key = os.urandom(32)
            message = b"authenticate this message"
            
            # Create HMAC
            mac = hmac.new(key, message, hashlib.sha256).digest()
            
            # Verify HMAC
            hmac_obj = hmac.new(key, message, hashlib.sha256)
            if hmac_obj.digest() != mac:
                self._log_vulnerability(
                    'critical',
                    'HMAC verification failure',
                    'HMAC verification failed for correct message',
                    'Verify HMAC implementation'
                )
            else:
                logger.info("✓ HMAC generation and verification test passed")
                self.results['passed'] += 1
            
            # Test HMAC with modified message
            modified_message = b"authenticate this modified message"
            hmac_obj = hmac.new(key, modified_message, hashlib.sha256)
            if hmac_obj.digest() == mac:
                self._log_vulnerability(
                    'critical',
                    'HMAC collision',
                    'HMAC produced same result for different messages',
                    'Verify HMAC implementation'
                )
            else:
                logger.info("✓ HMAC modified message detection test passed")
                self.results['passed'] += 1
            
            # Test constant-time comparison
            if not hmac.compare_digest(b"test", b"test"):
                self._log_vulnerability(
                    'high',
                    'Constant-time comparison failure',
                    'Equal strings not recognized as equal',
                    'Verify hmac.compare_digest implementation'
                )
            else:
                logger.info("✓ Constant-time comparison equality test passed")
                self.results['passed'] += 1
            
            if hmac.compare_digest(b"test", b"different"):
                self._log_vulnerability(
                    'high',
                    'Constant-time comparison failure',
                    'Different strings recognized as equal',
                    'Verify hmac.compare_digest implementation'
                )
            else:
                logger.info("✓ Constant-time comparison inequality test passed")
                self.results['passed'] += 1
                
        except Exception as e:
            self._log_vulnerability(
                'critical',
                'Cryptographic primitives testing error',
                f'Exception during crypto primitives testing: {str(e)}',
                'Verify cryptography library installation'
            )
            logger.error(f"Error testing crypto primitives: {e}")
    
    def _log_vulnerability(self, severity, title, description, recommendation):
        """Log a discovered vulnerability"""
        vulnerability = {
            'severity': severity,
            'title': title,
            'description': description,
            'recommendation': recommendation,
            'timestamp': datetime.datetime.utcnow().isoformat()
        }
        
        logger.warning(f"VULNERABILITY FOUND: {severity} - {title}")
        self.results['vulnerabilities'].append(vulnerability)
        self.results['failed'] += 1
    
    def generate_report(self):
        """Generate a comprehensive security test report"""
        logger.info("Generating security test report")
        
        report = {
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'summary': {
                'passed': self.results['passed'],
                'failed': self.results['failed'],
                'warnings': self.results['warnings'],
                'total': self.results['passed'] + self.results['failed'] + self.results['warnings']
            },
            'vulnerabilities': self.results['vulnerabilities']
        }
        
        # Calculate overall security score
        total = report['summary']['total']
        if total > 0:
            score = (report['summary']['passed'] / total) * 100
            report['summary']['score'] = round(score, 1)
        else:
            report['summary']['score'] = 0
        
        # Determine overall security rating
        if report['summary']['failed'] == 0:
            if report['summary']['warnings'] == 0:
                rating = 'A+'
            else:
                rating = 'A'
        elif report['summary']['failed'] <= 2:
            rating = 'B'
        elif report['summary']['failed'] <= 5:
            rating = 'C'
        else:
            rating = 'F'
        
        report['summary']['rating'] = rating
        
        # Output report
        report_file = 'security_component_test_report.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Security component test report saved to {report_file}")
        
        # Print summary
        print("\n" + "="*50)
        print("SECURITY COMPONENT TEST REPORT SUMMARY")
        print("="*50)
        print(f"Tests passed:  {report['summary']['passed']}")
        print(f"Tests failed:  {report['summary']['failed']}")
        print(f"Warnings:      {report['summary']['warnings']}")
        print(f"Total tests:   {report['summary']['total']}")
        print(f"Security score: {report['summary']['score']}% (Rating: {rating})")
        print("="*50)
        
        if report['vulnerabilities']:
            print("\nVULNERABILITIES FOUND:")
            for vuln in report['vulnerabilities']:
                print(f"- {vuln['severity'].upper()}: {vuln['title']}")
                print(f"  {vuln['description']}")
                print(f"  Recommendation: {vuln['recommendation']}")
                print()
        
        return report


if __name__ == '__main__':
    # Run tests
    test = SecurityComponentTest()
    test.run_all_tests()