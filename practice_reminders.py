"""
NLP Practice Reminders module for The Inner Architect

This module provides functionality for scheduling practice reminders,
managing notification preferences, and tracking practice consistency.
"""

import logging
from datetime import datetime, timedelta, time
import uuid
import json

# Reminder frequencies
REMINDER_FREQUENCIES = {
    'daily': 'Daily',
    'every_other_day': 'Every Other Day',
    'twice_weekly': 'Twice Weekly', 
    'weekly': 'Weekly',
    'custom': 'Custom Schedule'
}

# Reminder types
REMINDER_TYPES = {
    'exercise': 'Practice Exercise',
    'technique': 'Specific Technique',
    'journey_milestone': 'Journey Milestone',
    'reflection': 'Reflection Session',
    'custom': 'Custom Reminder'
}

# Default reminder times (hours in 24-hour format)
DEFAULT_REMINDER_TIMES = [8, 12, 18, 21]

class PracticeReminder:
    """Class representing a practice reminder."""
    
    def __init__(self, reminder_id=None, user_id=None, session_id=None, 
                title=None, description=None, reminder_type=None,
                frequency=None, time_preferences=None, days_of_week=None,
                active=True, linked_content_id=None):
        self.reminder_id = reminder_id or str(uuid.uuid4())
        self.user_id = user_id
        self.session_id = session_id
        self.title = title
        self.description = description
        self.reminder_type = reminder_type
        self.frequency = frequency
        self.time_preferences = time_preferences or []
        self.days_of_week = days_of_week or []
        self.active = active
        self.linked_content_id = linked_content_id
        self.created_at = datetime.now()
        self.last_notified = None
        self.next_notification = None
        self.notification_count = 0
        self.streak = 0
        
    def to_dict(self):
        """Convert reminder to dictionary for JSON serialization."""
        return {
            'reminder_id': self.reminder_id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'title': self.title,
            'description': self.description,
            'reminder_type': self.reminder_type,
            'reminder_type_display': REMINDER_TYPES.get(self.reminder_type, 'Custom Reminder'),
            'frequency': self.frequency,
            'frequency_display': REMINDER_FREQUENCIES.get(self.frequency, 'Custom'),
            'time_preferences': self.time_preferences,
            'time_preferences_formatted': [format_time(t) for t in self.time_preferences],
            'days_of_week': self.days_of_week,
            'days_of_week_formatted': format_days_of_week(self.days_of_week),
            'active': self.active,
            'linked_content_id': self.linked_content_id,
            'linked_content_type': get_linked_content_type(self.linked_content_id),
            'created_at': self.created_at.isoformat(),
            'last_notified': self.last_notified.isoformat() if self.last_notified else None,
            'next_notification': self.next_notification.isoformat() if self.next_notification else None,
            'notification_count': self.notification_count,
            'streak': self.streak
        }
        
def create_reminder(user_id, session_id, title, description, reminder_type, 
                   frequency, time_preferences=None, days_of_week=None, 
                   linked_content_id=None):
    """
    Create a new practice reminder.
    
    Args:
        user_id (int, optional): The user ID if logged in
        session_id (str): The session identifier
        title (str): Reminder title
        description (str): Reminder description
        reminder_type (str): Type of reminder ('exercise', 'technique', etc.)
        frequency (str): Reminder frequency ('daily', 'weekly', etc.)
        time_preferences (list, optional): Preferred reminder times (hours in 24-hour format)
        days_of_week (list, optional): Days of week for reminder (0=Monday, 6=Sunday)
        linked_content_id (str, optional): ID of linked content (exercise, technique, etc.)
        
    Returns:
        PracticeReminder: The created reminder object
    """
    # Validate inputs
    if not title or not reminder_type or not frequency:
        logging.error("Missing required fields for reminder creation")
        return None
    
    # Set defaults for time preferences if not provided
    if not time_preferences:
        if frequency == 'daily':
            time_preferences = [18]  # Default to 6 PM for daily reminders
        else:
            time_preferences = [10]  # Default to 10 AM for other frequencies
    
    # Set defaults for days of week if not provided
    if not days_of_week:
        if frequency == 'daily':
            days_of_week = list(range(7))  # All days of the week
        elif frequency == 'every_other_day':
            days_of_week = [0, 2, 4, 6]  # Mon, Wed, Fri, Sun
        elif frequency == 'twice_weekly':
            days_of_week = [1, 4]  # Tue, Fri
        elif frequency == 'weekly':
            days_of_week = [0]  # Monday
        else:
            days_of_week = [0, 2, 4]  # Mon, Wed, Fri
    
    # Create reminder
    reminder = PracticeReminder(
        user_id=user_id,
        session_id=session_id,
        title=title,
        description=description,
        reminder_type=reminder_type,
        frequency=frequency,
        time_preferences=time_preferences,
        days_of_week=days_of_week,
        linked_content_id=linked_content_id
    )
    
    # Calculate next notification time
    update_next_notification(reminder)
    
    # In a real application, this would save to a database
    # For now, we'll just pretend it worked and return the reminder
    return reminder

def update_reminder(reminder_id, session_id, updates):
    """
    Update an existing reminder.
    
    Args:
        reminder_id (str): The reminder ID
        session_id (str): The session identifier
        updates (dict): Fields to update
        
    Returns:
        PracticeReminder: The updated reminder or None if not found
    """
    # In a real application, this would fetch from and save to a database
    # For now, we'll just return None as if it wasn't found
    return None

def delete_reminder(reminder_id, session_id):
    """
    Delete a reminder.
    
    Args:
        reminder_id (str): The reminder ID
        session_id (str): The session identifier
        
    Returns:
        bool: Success or failure
    """
    # In a real application, this would delete from a database
    # For now, we'll just return True as if it worked
    return True

def get_reminder(reminder_id, session_id):
    """
    Get a specific reminder.
    
    Args:
        reminder_id (str): The reminder ID
        session_id (str): The session identifier
        
    Returns:
        PracticeReminder: The reminder object or None
    """
    # In a real application, this would fetch from a database
    # For now, we'll return None as if it wasn't found
    return None

def get_reminders(session_id, active_only=True, reminder_type=None):
    """
    Get reminders for a session.
    
    Args:
        session_id (str): The session identifier
        active_only (bool): Whether to return only active reminders
        reminder_type (str, optional): Filter by reminder type
        
    Returns:
        list: List of reminder objects
    """
    # In a real application, this would fetch from a database
    # For demonstration, we'll create some sample reminders
    reminders = get_demo_reminders(session_id)
    
    # Apply filters
    if active_only:
        reminders = [r for r in reminders if r.active]
    
    if reminder_type:
        reminders = [r for r in reminders if r.reminder_type == reminder_type]
    
    return reminders

def get_demo_reminders(session_id):
    """
    Get demonstration reminders for UI testing.
    
    Args:
        session_id (str): The session identifier
        
    Returns:
        list: List of sample reminder objects
    """
    # Create some sample reminders for demonstration
    reminders = [
        PracticeReminder(
            reminder_id="rem_daily_ex",
            session_id=session_id,
            title="Daily Reframing Practice",
            description="Practice reframing negative thoughts into positive ones",
            reminder_type="exercise",
            frequency="daily",
            time_preferences=[18],  # 6 PM
            days_of_week=list(range(7)),  # All days
            linked_content_id="voice_ex_2"  # Reframing exercise
        ),
        PracticeReminder(
            reminder_id="rem_weekly_tech",
            session_id=session_id,
            title="Weekly Sensory Language",
            description="Enhance your descriptions with vivid sensory details",
            reminder_type="technique",
            frequency="weekly",
            time_preferences=[10],  # 10 AM
            days_of_week=[5],  # Saturday
            linked_content_id="sensory_language"
        ),
        PracticeReminder(
            reminder_id="rem_journey",
            session_id=session_id,
            title="Journey Milestone Check-in",
            description="Check your progress on your personalized NLP journey",
            reminder_type="journey_milestone",
            frequency="twice_weekly",
            time_preferences=[9, 17],  # 9 AM and 5 PM
            days_of_week=[1, 4],  # Tuesday and Friday
            linked_content_id=None
        )
    ]
    
    # Update next notification times
    for reminder in reminders:
        update_next_notification(reminder)
    
    return reminders

def mark_reminder_complete(reminder_id, session_id):
    """
    Mark a reminder as completed for today.
    
    Args:
        reminder_id (str): The reminder ID
        session_id (str): The session identifier
        
    Returns:
        PracticeReminder: The updated reminder or None
    """
    # In a real application, this would fetch from and update a database
    # For now, we'll just return None as if it wasn't found
    return None

def update_next_notification(reminder):
    """
    Calculate and update the next notification time for a reminder.
    
    Args:
        reminder (PracticeReminder): The reminder to update
        
    Returns:
        None
    """
    now = datetime.now()
    
    # Set last_notified to now if it's None and notification_count > 0
    if reminder.notification_count > 0 and reminder.last_notified is None:
        reminder.last_notified = now
    
    # Initialize next notification date as today
    next_date = now.date()
    
    # Find the next valid day of week
    days_checked = 0
    while days_checked < 8:  # Maximum 7 days plus today
        # Check if this day of the week is in the reminder's days_of_week
        current_weekday = next_date.weekday()
        if current_weekday in reminder.days_of_week:
            # Find the next valid time for today
            valid_time_found = False
            
            if next_date == now.date():
                # For today, only use times that haven't passed yet
                for hour in sorted(reminder.time_preferences):
                    reminder_time = time(hour=hour)
                    reminder_datetime = datetime.combine(next_date, reminder_time)
                    
                    if reminder_datetime > now:
                        reminder.next_notification = reminder_datetime
                        valid_time_found = True
                        break
            else:
                # For future dates, use the earliest time preference
                hour = min(reminder.time_preferences)
                reminder_time = time(hour=hour)
                reminder.next_notification = datetime.combine(next_date, reminder_time)
                valid_time_found = True
            
            if valid_time_found:
                break
                
        # Move to next day
        next_date += timedelta(days=1)
        days_checked += 1
    
    # If no valid day/time found, default to tomorrow at the earliest time
    if reminder.next_notification is None:
        tomorrow = (now + timedelta(days=1)).date()
        hour = min(reminder.time_preferences)
        reminder_time = time(hour=hour)
        reminder.next_notification = datetime.combine(tomorrow, reminder_time)

def get_due_reminders(session_id):
    """
    Get reminders that are due for notification.
    
    Args:
        session_id (str): The session identifier
        
    Returns:
        list: List of due reminder objects
    """
    now = datetime.now()
    reminders = get_reminders(session_id)
    
    due_reminders = []
    for reminder in reminders:
        if reminder.active and reminder.next_notification and reminder.next_notification <= now:
            due_reminders.append(reminder)
    
    return due_reminders

def get_reminder_streak(reminder_id, session_id):
    """
    Get the completion streak for a reminder.
    
    Args:
        reminder_id (str): The reminder ID
        session_id (str): The session identifier
        
    Returns:
        int: Number of consecutive completions
    """
    # In a real application, this would calculate from a database
    # For now, we'll just return a random number
    import random
    return random.randint(0, 10)

def get_reminder_statistics(session_id):
    """
    Get statistics about reminder completion.
    
    Args:
        session_id (str): The session identifier
        
    Returns:
        dict: Statistics about reminder completion
    """
    # In a real application, this would calculate from a database
    # For now, we'll just return some made-up statistics
    reminders = get_reminders(session_id)
    
    return {
        'total_reminders': len(reminders),
        'active_reminders': sum(1 for r in reminders if r.active),
        'completion_rate': 0.7,  # 70% completion rate
        'longest_streak': 12
    }

def get_linked_content_type(content_id):
    """
    Determine the type of linked content from its ID.
    
    Args:
        content_id (str): The content ID
        
    Returns:
        str: The content type ('exercise', 'technique', 'journey', etc.)
    """
    if not content_id:
        return None
        
    if content_id.startswith('voice_ex_'):
        return 'voice_exercise'
    elif content_id in ['reframing', 'anchoring', 'pattern_interruption', 
                       'future_pacing', 'sensory_language', 'meta_model']:
        return 'technique'
    elif content_id.startswith('nlp_ex_'):
        return 'nlp_exercise'
    elif content_id.startswith(('sess_', 'session_')):
        return 'journey'
    
    return 'custom'

def format_time(hour):
    """
    Format hour in 24-hour format to 12-hour format.
    
    Args:
        hour (int): Hour in 24-hour format
        
    Returns:
        str: Formatted time string
    """
    if hour == 0:
        return '12:00 AM'
    elif hour < 12:
        return f'{hour}:00 AM'
    elif hour == 12:
        return '12:00 PM'
    else:
        return f'{hour-12}:00 PM'

def format_days_of_week(days):
    """
    Format list of days of week (0=Monday, 6=Sunday) to readable string.
    
    Args:
        days (list): List of day indices
        
    Returns:
        str: Formatted days string
    """
    if not days:
        return 'No days selected'
        
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    if len(days) == 7:
        return 'Every day'
    elif sorted(days) == [0, 1, 2, 3, 4]:
        return 'Weekdays'
    elif sorted(days) == [5, 6]:
        return 'Weekends'
    else:
        day_list = [day_names[day] for day in sorted(days)]
        
        if len(day_list) == 1:
            return day_list[0]
        elif len(day_list) == 2:
            return f'{day_list[0]} and {day_list[1]}'
        else:
            return ', '.join(day_list[:-1]) + f', and {day_list[-1]}'

def get_reminder_frequencies():
    """
    Get available reminder frequencies.
    
    Returns:
        dict: Frequency options
    """
    return REMINDER_FREQUENCIES

def get_reminder_types():
    """
    Get available reminder types.
    
    Returns:
        dict: Reminder type options
    """
    return REMINDER_TYPES