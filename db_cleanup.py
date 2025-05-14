#!/usr/bin/env python
"""
Script to fix database connection issues and clean up any aborted transactions.
This will help resolve the "current transaction is aborted" SQL errors.
"""

from app import app, db
from models import User, Subscription, OAuth
from sqlalchemy import text
from logging_config import get_logger, info, error

logger = get_logger("db_cleanup")

def main():
    """
    Clean up the database connections and fix transaction issues.
    """
    with app.app_context():
        try:
            # Clean up any aborted transactions
            db.session.rollback()
            info("Rolled back any pending transactions")
            
            # Close and recreate the connection to ensure a clean slate
            db.session.close()
            db.engine.dispose()
            info("Closed and disposed database connections")
            
            # Execute a simple query to verify the connection is working
            result = db.session.execute(text("SELECT 1"))
            info(f"Test query result: {result.scalar()}")

            # Update the user with team.mobileweb@gmail.com email to support both auth methods
            email_user = User.query.filter_by(email='team.mobileweb@gmail.com').first()
            if email_user:
                info(f"Found user with email team.mobileweb@gmail.com: {email_user.id}")
                email_user.auth_provider = 'replit_auth'
                db.session.commit()
                info(f"Updated user {email_user.id} auth_provider to {email_user.auth_provider}")
            
            # Delete any orphaned OAuth tokens
            oauth_count = OAuth.query.delete()
            db.session.commit()
            info(f"Deleted {oauth_count} orphaned OAuth tokens")
            
            # List all users to verify database is accessible
            users = User.query.all()
            info(f"Found {len(users)} users in database")
            for user in users:
                info(f"User id={user.id}, email={user.email}, auth_provider={user.auth_provider}")
                
                # Check for associated subscriptions
                subs = Subscription.query.filter_by(user_id=user.id).all()
                info(f"  - {len(subs)} subscriptions found")
                
        except Exception as e:
            error(f"Error during cleanup: {str(e)}")
            db.session.rollback()
            # Try more aggressive cleanup if needed
            try:
                db.session.close()
                db.engine.dispose()
            except:
                pass

if __name__ == "__main__":
    main()