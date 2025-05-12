"""
Database initialization script for The Inner Architect

This script updates the database schema to include new columns required
for email authentication and other features.
"""

import logging
from app import app, db
from models import User
from logging_config import get_logger

# Set up logging
logger = get_logger('db_init')

def add_column_if_not_exists(table_name, column_name, column_type):
    """
    Add a column to a table if it doesn't already exist.
    
    Args:
        table_name (str): Name of the table
        column_name (str): Name of the column to add
        column_type (str): SQL type of the column
    """
    try:
        with db.engine.connect() as conn:
            # Check if column exists
            query = f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}' 
                AND column_name = '{column_name}'
            """
            result = conn.execute(db.text(query))
            column_exists = result.fetchone() is not None
            
            if not column_exists:
                logger.info(f"Adding column {column_name} to {table_name}")
                alter_query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                conn.execute(db.text(alter_query))
                conn.commit()
                logger.info(f"Added column {column_name} to {table_name}")
            else:
                logger.info(f"Column {column_name} already exists in {table_name}")
                
    except Exception as e:
        logger.error(f"Error adding column {column_name} to {table_name}: {str(e)}")
        raise

def update_database_schema():
    """Update the database schema to include all required columns."""
    try:
        logger.info("Updating database schema...")
        
        # Add email authentication columns to users table
        add_column_if_not_exists('users', 'password_hash', 'VARCHAR(256)')
        add_column_if_not_exists('users', 'email_verified', 'BOOLEAN DEFAULT FALSE')
        add_column_if_not_exists('users', 'verification_token', 'VARCHAR(100)')
        add_column_if_not_exists('users', 'verification_token_expiry', 'TIMESTAMP')
        add_column_if_not_exists('users', 'reset_password_token', 'VARCHAR(100)')
        add_column_if_not_exists('users', 'reset_token_expiry', 'TIMESTAMP')
        add_column_if_not_exists('users', 'auth_provider', 'VARCHAR(20)')
        
        logger.info("Database schema update completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error updating database schema: {str(e)}")
        return False

if __name__ == "__main__":
    with app.app_context():
        update_database_schema()