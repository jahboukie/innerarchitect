"""
Push Notifications API for The Inner Architect

This module provides the API endpoints for managing push notifications,
including subscription, unsubscription, and sending notifications.
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

from flask import Blueprint, request, jsonify, current_app, g
from pywebpush import webpush, WebPushException

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
push_api = Blueprint('push_api', __name__, url_prefix='/api/push')

# In-memory store for subscriptions (would be in database in production)
# Key: subscription.endpoint, Value: {"subscription": {}, "preferences": {}, "user_id": ""}
subscriptions = {}

# VAPID keys - in production, these would be stored securely
VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY', 'vapid_private_key.pem')
VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY', 'vapid_public_key.pem')
VAPID_CLAIMS = {
    "sub": "mailto:admin@innerarchitect.app"
}

def generate_vapid_keys():
    """Generate VAPID keys if they don't exist."""
    from py_vapid import Vapid
    
    vapid = Vapid()
    
    # Generate and save keys if they don't exist
    if not os.path.exists(VAPID_PRIVATE_KEY):
        vapid.generate_keys()
        vapid.save_key(VAPID_PRIVATE_KEY)
        
        # Save public key separately
        with open(VAPID_PUBLIC_KEY, 'w') as f:
            f.write(vapid.public_key.decode('utf8'))
        
        logger.info("Generated new VAPID keys")
    else:
        # Load existing keys
        vapid.from_file(VAPID_PRIVATE_KEY)
        logger.info("Loaded existing VAPID keys")
    
    return {
        "private_key": vapid.private_key.decode('utf8'),
        "public_key": vapid.public_key.decode('utf8')
    }

# Initialize VAPID keys on module load
try:
    vapid_keys = generate_vapid_keys()
except Exception as e:
    logger.error(f"Failed to initialize VAPID keys: {e}")
    vapid_keys = {"private_key": "", "public_key": ""}

@push_api.route('/vapid-public-key', methods=['GET'])
def get_vapid_public_key():
    """Return the VAPID public key for the client to use."""
    return jsonify({"key": vapid_keys.get("public_key", "")})

@push_api.route('/subscribe', methods=['POST'])
def subscribe():
    """
    Subscribe to push notifications.
    
    Expected request body:
    {
        "subscription": {
            "endpoint": "...",
            "keys": {
                "p256dh": "...",
                "auth": "..."
            }
        },
        "preferences": {
            "practiceReminders": true,
            "journeyUpdates": true,
            "exerciseRecommendations": true,
            "systemAnnouncements": true
        }
    }
    """
    try:
        data = request.json
        
        if not data or not data.get('subscription'):
            return jsonify({"success": False, "error": "Invalid subscription data"}), 400
        
        subscription_data = data.get('subscription')
        preferences = data.get('preferences', {})
        user_id = g.user.id if hasattr(g, 'user') and g.user else None
        
        # Store subscription (in a real app, this would go to a database)
        subscriptions[subscription_data['endpoint']] = {
            "subscription": subscription_data,
            "preferences": preferences,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
        
        logger.info(f"New push subscription added for user {user_id}")
        
        # Send a welcome notification
        send_notification(
            subscription_data,
            "Welcome to Push Notifications",
            "You will now receive updates and reminders from The Inner Architect."
        )
        
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error in subscription: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@push_api.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    """
    Unsubscribe from push notifications.
    
    Expected request body:
    {
        "subscription": {
            "endpoint": "..."
        }
    }
    """
    try:
        data = request.json
        
        if not data or not data.get('subscription'):
            return jsonify({"success": False, "error": "Invalid subscription data"}), 400
        
        subscription_data = data.get('subscription')
        endpoint = subscription_data.get('endpoint')
        
        # Remove subscription
        if endpoint in subscriptions:
            del subscriptions[endpoint]
            logger.info(f"Push subscription removed: {endpoint}")
            return jsonify({"success": True})
        else:
            logger.warning(f"Subscription not found for removal: {endpoint}")
            return jsonify({"success": False, "error": "Subscription not found"}), 404
            
    except Exception as e:
        logger.error(f"Error in unsubscribe: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@push_api.route('/preferences', methods=['POST'])
def update_preferences():
    """
    Update preferences for push notifications.
    
    Expected request body:
    {
        "subscription": {
            "endpoint": "..."
        },
        "preferences": {
            "practiceReminders": true,
            "journeyUpdates": true,
            "exerciseRecommendations": true,
            "systemAnnouncements": true
        }
    }
    """
    try:
        data = request.json
        
        if not data or not data.get('subscription') or not data.get('preferences'):
            return jsonify({"success": False, "error": "Invalid data"}), 400
        
        subscription_data = data.get('subscription')
        preferences = data.get('preferences')
        endpoint = subscription_data.get('endpoint')
        
        # Update preferences
        if endpoint in subscriptions:
            subscriptions[endpoint]['preferences'] = preferences
            subscriptions[endpoint]['last_updated'] = datetime.now().isoformat()
            logger.info(f"Updated preferences for subscription: {endpoint}")
            return jsonify({"success": True})
        else:
            logger.warning(f"Subscription not found for preference update: {endpoint}")
            return jsonify({"success": False, "error": "Subscription not found"}), 404
            
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@push_api.route('/send', methods=['POST'])
def send_notification_endpoint():
    """
    Send a push notification (admin only).
    
    Expected request body:
    {
        "title": "Notification Title",
        "body": "Notification body text",
        "type": "practiceReminders", // Optional, filter by preference type
        "user_id": "user123", // Optional, send to specific user
        "url": "/techniques/reframing", // Optional, URL to open when clicked
        "ttl": 86400, // Optional, Time-To-Live in seconds
        "actions": [ // Optional, notification actions
            {
                "action": "view",
                "title": "View"
            },
            {
                "action": "dismiss",
                "title": "Dismiss"
            }
        ]
    }
    """
    try:
        # Check if user is admin (in a real app)
        if not hasattr(g, 'user') or not g.user or not g.user.is_admin:
            return jsonify({"success": False, "error": "Unauthorized"}), 403
        
        data = request.json
        
        if not data or not data.get('title') or not data.get('body'):
            return jsonify({"success": False, "error": "Missing required fields"}), 400
        
        title = data.get('title')
        body = data.get('body')
        notification_type = data.get('type')
        user_id = data.get('user_id')
        url = data.get('url')
        ttl = data.get('ttl', 86400)  # Default TTL: 1 day
        actions = data.get('actions')
        
        # Find subscriptions that match the criteria
        matching_subscriptions = []
        
        for endpoint, sub_data in subscriptions.items():
            # Filter by user_id if specified
            if user_id and sub_data.get('user_id') != user_id:
                continue
                
            # Filter by notification type if specified
            if notification_type:
                preferences = sub_data.get('preferences', {})
                if not preferences.get(notification_type, True):
                    continue
            
            matching_subscriptions.append(sub_data['subscription'])
        
        # Send notifications
        success_count = 0
        failure_count = 0
        
        for subscription in matching_subscriptions:
            try:
                send_notification(
                    subscription,
                    title,
                    body,
                    url=url,
                    ttl=ttl,
                    actions=actions
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to send notification to {subscription.get('endpoint')}: {e}")
                failure_count += 1
        
        return jsonify({
            "success": True,
            "total": len(matching_subscriptions),
            "sent": success_count,
            "failed": failure_count
        })
        
    except Exception as e:
        logger.error(f"Error sending notifications: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

def send_notification(
    subscription: Dict,
    title: str,
    body: str,
    url: Optional[str] = None,
    ttl: int = 86400,
    actions: Optional[List[Dict]] = None
) -> bool:
    """
    Send a push notification to a specific subscription.
    
    Args:
        subscription: The subscription data including endpoint and keys
        title: Notification title
        body: Notification body
        url: URL to open when notification is clicked
        ttl: Time-To-Live in seconds
        actions: Notification action buttons
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Construct the notification payload
        payload = {
            "title": title,
            "body": body,
            "timestamp": int(time.time()),
            "url": url or "/"
        }
        
        if actions:
            payload["actions"] = actions
            
        # Convert payload to JSON string
        payload_json = json.dumps(payload)
        
        # Send the notification
        webpush(
            subscription_info=subscription,
            data=payload_json,
            vapid_private_key=vapid_keys.get("private_key"),
            vapid_claims=VAPID_CLAIMS,
            ttl=ttl
        )
        
        logger.info(f"Notification sent to {subscription.get('endpoint')}")
        return True
        
    except WebPushException as e:
        # Handle expired subscriptions
        if e.response and e.response.status_code == 410:
            logger.warning(f"Subscription expired: {subscription.get('endpoint')}")
            # Remove expired subscription
            if subscription.get('endpoint') in subscriptions:
                del subscriptions[subscription.get('endpoint')]
        else:
            logger.error(f"WebPush error: {e}")
        return False
        
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return False

def send_reminder_notification(reminder):
    """
    Send a push notification for a reminder.
    
    Args:
        reminder: The reminder object
        
    Returns:
        int: Number of notifications successfully sent
    """
    user_id = reminder.get('user_id')
    title = f"Practice Reminder: {reminder.get('title')}"
    body = reminder.get('description') or "It's time for your practice session."
    
    # Determine URL based on linked content
    url = "/"
    if reminder.get('linked_content_id'):
        content_type = reminder.get('linked_content_type')
        content_id = reminder.get('linked_content_id')
        
        if content_type == 'technique':
            url = f"/techniques/{content_id}"
        elif content_type == 'voice_exercise':
            url = f"/voice-practice/{content_id}"
        elif content_type == 'nlp_exercise':
            url = f"/exercises/{content_id}"
        elif content_type == 'journey':
            url = f"/personalized-journeys/{content_id}"
    
    # Define actions
    actions = [
        {
            "action": "complete",
            "title": "Mark Complete"
        },
        {
            "action": "snooze",
            "title": "Snooze"
        }
    ]
    
    # Find matching subscriptions
    matching_subscriptions = []
    
    for endpoint, sub_data in subscriptions.items():
        # Filter by user_id if specified
        if user_id and sub_data.get('user_id') != user_id:
            continue
            
        # Check if practice reminders are enabled
        preferences = sub_data.get('preferences', {})
        if not preferences.get('practiceReminders', True):
            continue
        
        matching_subscriptions.append(sub_data['subscription'])
    
    # Send notifications
    success_count = 0
    
    for subscription in matching_subscriptions:
        try:
            success = send_notification(
                subscription,
                title,
                body,
                url=url,
                actions=actions
            )
            if success:
                success_count += 1
        except Exception as e:
            logger.error(f"Failed to send reminder notification: {e}")
    
    return success_count

def check_due_reminders():
    """
    Check for due reminders and send notifications.
    This would typically be called by a scheduler.
    
    Returns:
        int: Number of notifications sent
    """
    from practice_reminders import get_due_reminders
    
    try:
        # Get session ID for the API call
        # In a real app, this would iterate through all users
        session_id = "system_check"
        
        # Get due reminders
        due_reminders = get_due_reminders(session_id)
        
        notification_count = 0
        
        # Send notifications for each reminder
        for reminder in due_reminders:
            sent = send_reminder_notification(reminder.to_dict())
            notification_count += sent
            
        logger.info(f"Sent {notification_count} reminder notifications")
        return notification_count
        
    except Exception as e:
        logger.error(f"Error checking due reminders: {e}")
        return 0