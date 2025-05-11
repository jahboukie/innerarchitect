"""
Subscription Manager module for The Inner Architect

This module handles all subscription-related functionality, including:
- Stripe webhook processing
- Subscription status tracking
- Usage limit enforcement
- Subscription notifications
"""
import os
import logging
from datetime import datetime, timedelta
import stripe
from flask import current_app, flash
from database import db
from models import User, Subscription

# Initialize Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Constants
FREE_TIER_LIMITS = {
    'messages_per_day': 20,
    'exercises_per_week': 3,
    'techniques_accessible': 3
}

PREMIUM_TIER_LIMITS = {
    'messages_per_day': 100,
    'exercises_per_week': 15,
    'techniques_accessible': 'unlimited'
}

PROFESSIONAL_TIER_LIMITS = {
    'messages_per_day': 'unlimited',
    'exercises_per_week': 'unlimited',
    'techniques_accessible': 'unlimited'
}

def process_webhook_event(event):
    """
    Process Stripe webhook events.
    
    Args:
        event (dict): The Stripe event object
        
    Returns:
        bool: Success or failure
    """
    event_type = event['type']
    logging.info(f"Processing Stripe webhook: {event_type}")
    
    try:
        if event_type == 'customer.subscription.created':
            return handle_subscription_created(event)
        elif event_type == 'customer.subscription.updated':
            return handle_subscription_updated(event)
        elif event_type == 'customer.subscription.deleted':
            return handle_subscription_deleted(event)
        elif event_type == 'invoice.payment_succeeded':
            return handle_payment_succeeded(event)
        elif event_type == 'invoice.payment_failed':
            return handle_payment_failed(event)
        else:
            logging.info(f"Unhandled event type: {event_type}")
            return True
    except Exception as e:
        logging.error(f"Error processing webhook {event_type}: {str(e)}")
        return False

def handle_subscription_created(event):
    """
    Handle subscription created event.
    
    Args:
        event (dict): The Stripe event object
        
    Returns:
        bool: Success or failure
    """
    data = event['data']['object']
    subscription_id = data['id']
    customer_id = data['customer']
    status = data['status']
    
    # Find the user by Stripe customer ID
    subscription = Subscription.query.filter_by(stripe_customer_id=customer_id).first()
    
    if not subscription:
        logging.error(f"No user found for customer {customer_id}")
        return False
    
    # Update subscription details
    subscription.stripe_subscription_id = subscription_id
    subscription.status = status
    subscription.current_period_start = datetime.fromtimestamp(data['current_period_start'])
    subscription.current_period_end = datetime.fromtimestamp(data['current_period_end'])
    
    # Determine the plan name from the price ID
    if len(data['items']['data']) > 0:
        price_id = data['items']['data'][0]['price']['id']
        for plan, plan_data in current_app.config.get('SUBSCRIPTION_PLANS', {}).items():
            if plan_data.get('price_id') == price_id:
                subscription.plan_name = plan
                break
    
    db.session.commit()
    return True

def handle_subscription_updated(event):
    """
    Handle subscription updated event.
    
    Args:
        event (dict): The Stripe event object
        
    Returns:
        bool: Success or failure
    """
    data = event['data']['object']
    subscription_id = data['id']
    status = data['status']
    
    # Find the subscription
    subscription = Subscription.query.filter_by(stripe_subscription_id=subscription_id).first()
    
    if not subscription:
        logging.error(f"No subscription found with ID {subscription_id}")
        return False
    
    # Update subscription details
    subscription.status = status
    subscription.current_period_start = datetime.fromtimestamp(data['current_period_start'])
    subscription.current_period_end = datetime.fromtimestamp(data['current_period_end'])
    
    # If canceled, update accordingly
    if status == 'canceled':
        subscription.canceled_at = datetime.utcnow()
    
    db.session.commit()
    return True

def handle_subscription_deleted(event):
    """
    Handle subscription deleted event.
    
    Args:
        event (dict): The Stripe event object
        
    Returns:
        bool: Success or failure
    """
    data = event['data']['object']
    subscription_id = data['id']
    
    # Find the subscription
    subscription = Subscription.query.filter_by(stripe_subscription_id=subscription_id).first()
    
    if not subscription:
        logging.error(f"No subscription found with ID {subscription_id}")
        return False
    
    # Update subscription to free plan
    subscription.status = 'canceled'
    subscription.plan_name = 'free'
    subscription.canceled_at = datetime.utcnow()
    
    db.session.commit()
    return True

def handle_payment_succeeded(event):
    """
    Handle payment succeeded event.
    
    Args:
        event (dict): The Stripe event object
        
    Returns:
        bool: Success or failure
    """
    data = event['data']['object']
    customer_id = data['customer']
    
    # Only process subscription invoices
    if not data.get('subscription'):
        return True
    
    # Find the subscription
    subscription = Subscription.query.filter_by(stripe_customer_id=customer_id).first()
    
    if not subscription:
        logging.error(f"No subscription found for customer {customer_id}")
        return False
    
    # Update subscription status to active if it was past_due
    if subscription.status == 'past_due':
        subscription.status = 'active'
        db.session.commit()
    
    return True

def handle_payment_failed(event):
    """
    Handle payment failed event.
    
    Args:
        event (dict): The Stripe event object
        
    Returns:
        bool: Success or failure
    """
    data = event['data']['object']
    customer_id = data['customer']
    attempt_count = data.get('attempt_count', 0)
    
    # Find the subscription
    subscription = Subscription.query.filter_by(stripe_customer_id=customer_id).first()
    
    if not subscription:
        logging.error(f"No subscription found for customer {customer_id}")
        return False
    
    # Update subscription status
    if attempt_count >= 3:
        subscription.status = 'past_due'
        db.session.commit()
    
    return True

def check_feature_access(user_id, feature):
    """
    Check if a user has access to a specific feature.
    
    Args:
        user_id (str): The user ID
        feature (str): The feature to check
        
    Returns:
        bool: True if the user has access, False otherwise
    """
    # Ensure user exists
    user = User.query.get(user_id)
    if not user:
        return False
    
    # Get user's subscription
    subscription = Subscription.query.filter_by(user_id=user_id).first()
    
    # Default to free tier if no subscription found
    plan_name = 'free'
    if subscription and subscription.is_active:
        plan_name = subscription.plan_name
    
    # Check feature access based on subscription tier
    if feature in ['chat', 'basic_nlp', 'mood_tracking']:
        # These features are available to all tiers
        return True
    elif feature in ['advanced_nlp', 'progress_tracking', 'communication_analysis']:
        # These features require premium or professional
        return plan_name in ['premium', 'professional']
    elif feature in ['voice_practice', 'personalized_journeys', 'belief_change', 'reminders']:
        # These features require professional
        return plan_name == 'professional'
    else:
        # Unknown feature
        return False

def get_usage_limits(user_id):
    """
    Get usage limits for a user based on their subscription tier.
    
    Args:
        user_id (str): The user ID
        
    Returns:
        dict: Usage limits
    """
    # Get user's subscription
    subscription = Subscription.query.filter_by(user_id=user_id).first()
    
    # Default to free tier if no subscription found
    plan_name = 'free'
    if subscription and subscription.is_active:
        plan_name = subscription.plan_name
    
    # Return limits based on plan
    if plan_name == 'professional':
        return PROFESSIONAL_TIER_LIMITS
    elif plan_name == 'premium':
        return PREMIUM_TIER_LIMITS
    else:
        return FREE_TIER_LIMITS

def check_usage_quota(user_id, quota_type):
    """
    Check if a user has exceeded their usage quota.
    
    Args:
        user_id (str): The user ID
        quota_type (str): The type of quota to check (e.g., 'messages_per_day')
        
    Returns:
        bool: True if user has remaining quota, False if exceeded
    """
    # Get limits for the user
    limits = get_usage_limits(user_id)
    
    # If unlimited, always return True
    if limits.get(quota_type) == 'unlimited':
        return True
    
    # Get current usage from tracking table or session
    # This would need to be implemented based on your specific tracking mechanism
    
    # For now, return True (not exceeded)
    return True

def create_subscription(user_id, plan_name='free'):
    """
    Create a new subscription for a user.
    
    Args:
        user_id (str): The user ID
        plan_name (str): The subscription plan name
        
    Returns:
        Subscription: The created subscription object
    """
    try:
        # Check if subscription already exists
        existing = Subscription.query.filter_by(user_id=user_id).first()
        if existing:
            return existing
        
        # Create new subscription
        subscription = Subscription(
            user_id=user_id,
            plan_name=plan_name,
            status='active',
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=365 if plan_name == 'free' else 30)
        )
        
        db.session.add(subscription)
        db.session.commit()
        
        return subscription
    
    except Exception as e:
        logging.error(f"Error creating subscription: {str(e)}")
        db.session.rollback()
        return None

def cancel_subscription(user_id):
    """
    Cancel a user's subscription in Stripe and the database.
    
    Args:
        user_id (str): The user ID
        
    Returns:
        bool: Success or failure
    """
    try:
        # Get the subscription
        subscription = Subscription.query.filter_by(user_id=user_id).first()
        
        if not subscription or not subscription.stripe_subscription_id:
            return False
        
        # Cancel in Stripe
        stripe.Subscription.delete(subscription.stripe_subscription_id)
        
        # Update in database
        subscription.status = 'canceled'
        subscription.canceled_at = datetime.utcnow()
        
        db.session.commit()
        return True
    
    except Exception as e:
        logging.error(f"Error canceling subscription: {str(e)}")
        db.session.rollback()
        return False

def get_subscription_details(user_id):
    """
    Get detailed subscription information for a user.
    
    Args:
        user_id (str): The user ID
        
    Returns:
        dict: Subscription details
    """
    # Get the subscription
    subscription = Subscription.query.filter_by(user_id=user_id).first()
    
    if not subscription:
        return {
            'has_subscription': False,
            'plan_name': 'free',
            'status': 'active',
            'is_active': True,
            'current_period_end': None,
            'canceled': False,
            'limits': FREE_TIER_LIMITS,
            'features': get_available_features('free')
        }
    
    # Determine limits based on plan
    if subscription.plan_name == 'professional':
        limits = PROFESSIONAL_TIER_LIMITS
    elif subscription.plan_name == 'premium':
        limits = PREMIUM_TIER_LIMITS
    else:
        limits = FREE_TIER_LIMITS
    
    return {
        'has_subscription': True,
        'plan_name': subscription.plan_name,
        'status': subscription.status,
        'is_active': subscription.is_active,
        'current_period_end': subscription.current_period_end,
        'canceled': subscription.status == 'canceled',
        'limits': limits,
        'features': get_available_features(subscription.plan_name)
    }

def get_available_features(plan_name):
    """
    Get a list of features available for a subscription plan.
    
    Args:
        plan_name (str): The subscription plan name
        
    Returns:
        list: Available features
    """
    features = [
        'chat',
        'basic_nlp',
        'mood_tracking'
    ]
    
    if plan_name in ['premium', 'professional']:
        features.extend([
            'advanced_nlp',
            'progress_tracking',
            'communication_analysis'
        ])
    
    if plan_name == 'professional':
        features.extend([
            'voice_practice',
            'personalized_journeys',
            'belief_change',
            'reminders'
        ])
    
    return features