#!/usr/bin/env python
"""
Script to check database entries and fix duplicate email issues.
"""

from app import app, db
from models import User
from logging_config import get_logger, info, error

logger = get_logger("check_db")

def main():
    """
    Check for duplicate emails and fix the Replit Auth issue.
    """
    with app.app_context():
        # Get the user with the conflicting email
        email = 'team.mobileweb@gmail.com'
        email_user = User.query.filter_by(email=email).first()
        
        if email_user:
            info(f"Found existing user with email {email}: id={email_user.id}, auth_provider={email_user.auth_provider}")
            
            # Update the user to allow both auth methods
            email_user.auth_provider = 'replit_auth'
            db.session.commit()
            info(f"Updated user {email_user.id} auth_provider to {email_user.auth_provider}")
            
            # Check if there's a conflicting Replit auth user
            replit_id = '39948227'
            replit_user = User.query.filter_by(id=replit_id).first()
            
            if replit_user and replit_user.id != email_user.id:
                info(f"Found Replit user: id={replit_user.id}, email={replit_user.email}")
                
                # Update the Replit user's email to avoid conflicts
                replit_user.email = None
                db.session.commit()
                info(f"Removed email from Replit user {replit_user.id}")
                
                # You could also delete this user if appropriate
                # db.session.delete(replit_user)
                # db.session.commit()
                # info(f"Deleted Replit user {replit_id}")
            else:
                info(f"No conflicting Replit user found with id {replit_id}")
        else:
            info(f"No user found with email {email}")

        # List all users
        users = User.query.all()
        info(f"Found {len(users)} users in database")
        for user in users:
            info(f"User id={user.id}, email={user.email}, auth_provider={user.auth_provider}")

if __name__ == "__main__":
    main()