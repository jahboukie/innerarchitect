#!/usr/bin/env python3
"""
Simple database initialization script for Inner Architect
Creates SQLite database with basic tables for testing
"""

import sqlite3
import os
from datetime import datetime

def create_database():
    """Create SQLite database with basic tables"""
    db_path = 'inner_architect.db'
    
    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing database: {db_path}")
    
    # Create new database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email VARCHAR(120) UNIQUE NOT NULL,
            first_name VARCHAR(80) NOT NULL,
            last_name VARCHAR(80) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            email_verified BOOLEAN DEFAULT FALSE,
            verification_token VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
    ''')
    
    # Create chat_history table
    cursor.execute('''
        CREATE TABLE chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_id VARCHAR(255),
            user_message TEXT NOT NULL,
            ai_response TEXT NOT NULL,
            mood VARCHAR(50),
            nlp_technique VARCHAR(100),
            context_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user (id)
        )
    ''')
    
    # Create nlp_exercise table
    cursor.execute('''
        CREATE TABLE nlp_exercise (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            technique VARCHAR(100) NOT NULL,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            difficulty VARCHAR(20) DEFAULT 'beginner',
            estimated_time INTEGER DEFAULT 5,
            steps TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create nlp_exercise_progress table
    cursor.execute('''
        CREATE TABLE nlp_exercise_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercise_id INTEGER NOT NULL,
            user_id INTEGER,
            session_id VARCHAR(255),
            current_step INTEGER DEFAULT 0,
            completed BOOLEAN DEFAULT FALSE,
            notes TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (exercise_id) REFERENCES nlp_exercise (id),
            FOREIGN KEY (user_id) REFERENCES user (id)
        )
    ''')
    
    # Create technique_effectiveness table
    cursor.execute('''
        CREATE TABLE technique_effectiveness (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_id VARCHAR(255),
            technique VARCHAR(100) NOT NULL,
            effectiveness_rating INTEGER,
            mood_before VARCHAR(50),
            mood_after VARCHAR(50),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user (id)
        )
    ''')
    
    # Create subscription table
    cursor.execute('''
        CREATE TABLE subscription (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_name VARCHAR(50) NOT NULL,
            status VARCHAR(20) DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user (id)
        )
    ''')
    
    # Insert some sample data for testing
    
    # Sample NLP exercises
    exercises = [
        ('reframing', 'Basic Reframing Exercise', 'Learn to reframe negative thoughts into positive ones', 'beginner', 10, 
         '["Step 1: Identify the negative thought", "Step 2: Challenge the thought", "Step 3: Create a positive reframe"]'),
        ('anchoring', 'Confidence Anchor', 'Create a physical anchor for confidence', 'intermediate', 15,
         '["Step 1: Recall a confident moment", "Step 2: Create physical anchor", "Step 3: Practice the anchor"]'),
        ('visualization', 'Success Visualization', 'Visualize achieving your goals', 'beginner', 12,
         '["Step 1: Relax and close eyes", "Step 2: Visualize success in detail", "Step 3: Feel the emotions"]')
    ]
    
    cursor.executemany('''
        INSERT INTO nlp_exercise (technique, title, description, difficulty, estimated_time, steps)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', exercises)
    
    # Sample chat history
    sample_chats = [
        (None, 'test_session_1', 'I feel anxious about my presentation tomorrow', 
         'I understand you\'re feeling anxious about your presentation. Let\'s use a reframing technique to help you see this differently. Instead of focusing on what could go wrong, let\'s think about what you\'ve prepared well and how this is an opportunity to share your knowledge.', 
         'anxious', 'reframing'),
        (None, 'test_session_2', 'I keep procrastinating on important tasks',
         'Procrastination often comes from feeling overwhelmed. Let\'s break this down using anchoring. Think of a time when you felt motivated and productive. What was different about that situation? We can create an anchor to help you access that state when you need it.',
         'frustrated', 'anchoring')
    ]
    
    cursor.executemany('''
        INSERT INTO chat_history (user_id, session_id, user_message, ai_response, mood, nlp_technique)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', sample_chats)
    
    # Commit changes and close
    conn.commit()
    conn.close()
    
    print(f"✅ Database created successfully: {db_path}")
    print(f"📊 Created tables: user, chat_history, nlp_exercise, nlp_exercise_progress, technique_effectiveness, subscription")
    print(f"🎯 Added sample data: {len(exercises)} exercises, {len(sample_chats)} chat entries")
    
    return db_path

if __name__ == "__main__":
    print("🚀 Initializing Inner Architect Database...")
    db_path = create_database()
    print(f"🎉 Database initialization complete! Database file: {db_path}")
