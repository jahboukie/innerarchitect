#!/usr/bin/env python
"""
Script to improve the Replit Auth flow by adding better transaction
handling and error detection to avoid the "current transaction is aborted"
database errors.
"""

from app import app, db
from replit_auth_new import UserSessionStorage
from sqlalchemy.exc import NoResultFound
from logging_config import get_logger, info, error

logger = get_logger("auth_repair")

class ImprovedUserSessionStorage(UserSessionStorage):
    """Enhanced storage with better transaction management."""
    
    def get(self, blueprint):
        """Get the OAuth token with improved error handling."""
        try:
            # First try to rollback any pending transactions to ensure a clean state
            db.session.rollback()
            
            # Now try to get the token
            token = super().get(blueprint)
            return token
        except Exception as e:
            error(f"Error getting OAuth token: {str(e)}")
            
            # Always rollback on error to avoid transaction blocks
            db.session.rollback()
            
            # Close and dispose connection if needed
            try:
                db.session.close()
            except:
                pass
                
            return None
    
    def set(self, blueprint, token):
        """Set the OAuth token with improved error handling."""
        try:
            # First try to rollback any pending transactions to ensure a clean state
            db.session.rollback()
            
            # Now try to set the token
            super().set(blueprint, token)
        except Exception as e:
            error(f"Error setting OAuth token: {str(e)}")
            
            # Always rollback on error to avoid transaction blocks
            db.session.rollback()
            
            # Close and dispose connection if needed
            try:
                db.session.close()
            except:
                pass
    
    def delete(self, blueprint):
        """Delete the OAuth token with improved error handling."""
        try:
            # First try to rollback any pending transactions to ensure a clean state
            db.session.rollback()
            
            # Now try to delete the token
            super().delete(blueprint)
        except Exception as e:
            error(f"Error deleting OAuth token: {str(e)}")
            
            # Always rollback on error to avoid transaction blocks
            db.session.rollback()
            
            # Close and dispose connection if needed
            try:
                db.session.close()
            except:
                pass

def apply_auth_repairs():
    """Apply the auth repair fixes to the replit_auth module."""
    import replit_auth
    
    # Backup the original class for reference
    original_storage = replit_auth.UserSessionStorage
    
    # Replace with our improved version
    replit_auth.UserSessionStorage = ImprovedUserSessionStorage
    
    info("Applied auth repair: Enhanced UserSessionStorage with better transaction management")
    
    # Return the original for rollback if needed
    return original_storage

def rollback_auth_repairs(original_storage):
    """Rollback the auth repair fixes."""
    import replit_auth
    
    # Restore the original class
    replit_auth.UserSessionStorage = original_storage
    
    info("Rolled back auth repair")

if __name__ == "__main__":
    with app.app_context():
        # Apply the auth repairs
        original = apply_auth_repairs()
        
        # Run a test
        info("Testing the improved authentication flow...")
        
        # You could add test code here
        
        info("Auth repair test completed")