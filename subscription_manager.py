"""
Subscription Manager module for The Inner Architect

This module handles subscription management, feature access control,
and usage quota tracking for the application.
"""

import os
import logging
import uuid
from datetime import datetime, timezone
from functools import wraps

import stripe
from flask import flash, redirect, url_for, session
from flask_login import current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship

from app import db
from models import User

# Initialize Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Define subscription plans and features
SUBSCRIPTION_PLANS = {
    'free': {
        'name': 'Free',
        'features': [
            'Basic cognitive reframing',
            'Limited chat interactions (10 per day)',
            'Basic dashboard'
        ],
        'quotas': {
            'daily_messages': 10,
            'daily_exercises': 3,
            'monthly_analyses': 2
        }
    },
    'premium': {
        'name': 'Premium',
        'price_id': 'price_premium',  # Replace with actual Stripe price ID
        'amount': 999,  # $9.99 in cents
        'features': [
            'All NLP techniques',
            'Unlimited chat interactions',
            'Full progress tracking',
            'Communication analysis',
            'Priority support'
        ],
        'quotas': {
            'daily_messages': 100,
            'daily_exercises': 20,
            'monthly_analyses': 30
        }
    },
    'professional': {
        'name': 'Professional',
        'price_id': 'price_professional',  # Replace with actual Stripe price ID
        'amount': 1999,  # $19.99 in cents
        'features': [
            'Everything in Premium',
            'Voice practice features',
            'Personalized journeys',
            'Belief change protocol',
            'Practice reminders',
            'Priority support'
        ],
        'quotas': {
            'daily_messages': float('inf'),
            'daily_exercises': float('inf'),
            'monthly_analyses': float('inf')
        }
    }
}

# Mapping of features to plan levels
FEATURE_ACCESS = {
    'advanced_nlp': ['premium', 'professional'],
    'progress_tracking': ['premium', 'professional'],
    'communication_analysis': ['premium', 'professional'],
    'voice_practice': ['professional'],
    'personalized_journeys': ['professional'],
    'belief_change': ['professional'],
    'reminders': ['professional']
}

# Mapping of quota types to database fields
QUOTA_FIELDS = {
    'daily_messages': 'messages_used_today',
    'daily_exercises': 'exercises_used_today',
    'monthly_analyses': 'analyses_used_this_month'
}

class Subscription(db.Model):
    """Model for storing user subscription details."""
    __tablename__ = 'subscriptions'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    plan_name = Column(String, nullable=False, default='free')
    status = Column(String, nullable=False, default='active')
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationship with User model
    user = relationship('User', backref='subscription')
    
    def __repr__(self):
        return f'<Subscription {self.id} - User: {self.user_id} - Plan: {self.plan_name}>'
    
    def to_dict(self):
        """Convert subscription to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'plan_name': self.plan_name,
            'status': self.status,
            'current_period_start': self.current_period_start.isoformat() if self.current_period_start else None,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None,
            'cancel_at_period_end': self.cancel_at_period_end,
            'features': SUBSCRIPTION_PLANS.get(self.plan_name, {}).get('features', []),
            'quotas': SUBSCRIPTION_PLANS.get(self.plan_name, {}).get('quotas', {})
        }

class UsageQuota(db.Model):
    """Model for tracking usage quotas."""
    __tablename__ = 'usage_quotas'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=True)
    browser_session_id = Column(String, nullable=True)
    messages_used_today = Column(Integer, default=0)
    exercises_used_today = Column(Integer, default=0)
    analyses_used_this_month = Column(Integer, default=0)
    last_reset_date = Column(DateTime, default=datetime.now)
    last_monthly_reset_date = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationship with User model
    user = relationship('User', backref='usage_quota')
    
    def __repr__(self):
        return f'<UsageQuota - User: {self.user_id or "Anonymous"} - Messages: {self.messages_used_today}>'
    
    def to_dict(self):
        """Convert usage quota to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'browser_session_id': self.browser_session_id,
            'messages_used_today': self.messages_used_today,
            'exercises_used_today': self.exercises_used_today,
            'analyses_used_this_month': self.analyses_used_this_month,
            'last_reset_date': self.last_reset_date.isoformat() if self.last_reset_date else None,
            'last_monthly_reset_date': self.last_monthly_reset_date.isoformat() if self.last_monthly_reset_date else None
        }

def get_subscription(user_id):
    """
    Get a user's subscription.
    
    Args:
        user_id (str): The user ID
        
    Returns:
        Subscription: The subscription or None if not found
    """
    return Subscription.query.filter_by(user_id=user_id).first()

def get_subscription_details(user_id):
    """
    Get detailed subscription information for a user.
    
    Args:
        user_id (str): The user ID
        
    Returns:
        dict: Subscription details including plan features and quotas
    """
    subscription = get_subscription(user_id)
    
    # If no subscription record exists, create one with the free plan
    if not subscription:
        subscription = Subscription(
            user_id=user_id,
            plan_name='free',
            status='active'
        )
        db.session.add(subscription)
        db.session.commit()
    
    # Get plan details
    plan_name = subscription.plan_name
    plan_details = SUBSCRIPTION_PLANS.get(plan_name, SUBSCRIPTION_PLANS['free'])
    
    # Get usage quotas
    usage = get_usage_quota(user_id)
    
    # Return combined details
    return {
        'subscription_id': subscription.id,
        'plan_name': plan_name,
        'status': subscription.status,
        'cancel_at_period_end': subscription.cancel_at_period_end,
        'current_period_end': subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        'features': plan_details.get('features', []),
        'quotas': plan_details.get('quotas', {}),
        'usage': {
            'messages_used_today': usage.messages_used_today,
            'exercises_used_today': usage.exercises_used_today,
            'analyses_used_this_month': usage.analyses_used_this_month
        }
    }

def check_feature_access(user_id, feature):
    """
    Check if a user has access to a specific feature based on their subscription.
    
    Args:
        user_id (str): The user ID
        feature (str): The feature identifier
        
    Returns:
        bool: True if the user has access, False otherwise
    """
    subscription = get_subscription(user_id)
    if not subscription:
        return False
    
    plan_name = subscription.plan_name
    allowed_plans = FEATURE_ACCESS.get(feature, [])
    
    return plan_name in allowed_plans

def get_usage_quota(user_id=None, browser_session_id=None):
    """
    Get a user's usage quota.
    
    Args:
        user_id (str, optional): The user ID
        browser_session_id (str, optional): The browser session ID for anonymous users
        
    Returns:
        UsageQuota: The usage quota object
    """
    # First try to find by user_id if provided
    if user_id:
        usage = UsageQuota.query.filter_by(user_id=user_id).first()
        if usage:
            # Check if daily/monthly reset is needed
            _check_reset_quotas(usage)
            return usage
    
    # If not found by user_id or user_id not provided, try browser_session_id
    if browser_session_id:
        usage = UsageQuota.query.filter_by(browser_session_id=browser_session_id).first()
        if usage:
            # Check if daily/monthly reset is needed
            _check_reset_quotas(usage)
            return usage
    
    # If no quota record found, create a new one
    usage = UsageQuota(
        user_id=user_id,
        browser_session_id=browser_session_id
    )
    db.session.add(usage)
    db.session.commit()
    
    return usage

def _check_reset_quotas(usage):
    """
    Check if daily or monthly quota reset is needed and perform the reset.
    
    Args:
        usage (UsageQuota): The usage quota object
    """
    now = datetime.now()
    today = now.date()
    
    # Check if last reset was on a different day
    if usage.last_reset_date and usage.last_reset_date.date() < today:
        # Reset daily quotas
        usage.messages_used_today = 0
        usage.exercises_used_today = 0
        usage.last_reset_date = now
    
    # Check if last monthly reset was in a different month
    if usage.last_monthly_reset_date and (
            usage.last_monthly_reset_date.year != now.year or 
            usage.last_monthly_reset_date.month != now.month):
        # Reset monthly quotas
        usage.analyses_used_this_month = 0
        usage.last_monthly_reset_date = now
    
    # Save changes if needed
    if db.session.is_modified(usage):
        db.session.commit()

def increment_usage_quota(user_id=None, browser_session_id=None, quota_type='daily_messages', amount=1):
    """
    Increment a specific usage quota.
    
    Args:
        user_id (str, optional): The user ID
        browser_session_id (str, optional): The browser session ID for anonymous users
        quota_type (str): The type of quota to increment ('daily_messages', 'daily_exercises', 'monthly_analyses')
        amount (int): The amount to increment by
        
    Returns:
        tuple: (success, message) indicating if the quota was successfully incremented
    """
    # Get the usage quota
    usage = get_usage_quota(user_id, browser_session_id)
    
    # Get subscription details to check quota limits
    subscription_details = None
    if user_id:
        subscription_details = get_subscription_details(user_id)
    else:
        # For anonymous users, use free plan limits
        subscription_details = {
            'plan_name': 'free',
            'quotas': SUBSCRIPTION_PLANS['free']['quotas']
        }
    
    # Get the quota limit and current usage
    quota_limit = subscription_details['quotas'].get(quota_type, 0)
    quota_field = QUOTA_FIELDS.get(quota_type)
    
    if not quota_field:
        return False, f"Unknown quota type: {quota_type}"
    
    current_usage = getattr(usage, quota_field, 0)
    
    # Check if quota would be exceeded
    if quota_limit != float('inf') and current_usage + amount > quota_limit:
        return False, f"Quota exceeded for {quota_type}. Upgrade your subscription for higher limits."
    
    # Increment the quota
    setattr(usage, quota_field, current_usage + amount)
    db.session.commit()
    
    return True, "Quota incremented successfully."

def check_quota_available(user_id=None, browser_session_id=None, quota_type='daily_messages', amount=1):
    """
    Check if a specific quota is available without incrementing it.
    
    Args:
        user_id (str, optional): The user ID
        browser_session_id (str, optional): The browser session ID for anonymous users
        quota_type (str): The type of quota to check ('daily_messages', 'daily_exercises', 'monthly_analyses')
        amount (int): The amount to check for
        
    Returns:
        tuple: (available, message) indicating if the quota is available
    """
    # Get the usage quota
    usage = get_usage_quota(user_id, browser_session_id)
    
    # Get subscription details to check quota limits
    subscription_details = None
    if user_id:
        subscription_details = get_subscription_details(user_id)
    else:
        # For anonymous users, use free plan limits
        subscription_details = {
            'plan_name': 'free',
            'quotas': SUBSCRIPTION_PLANS['free']['quotas']
        }
    
    # Get the quota limit and current usage
    quota_limit = subscription_details['quotas'].get(quota_type, 0)
    quota_field = QUOTA_FIELDS.get(quota_type)
    
    if not quota_field:
        return False, f"Unknown quota type: {quota_type}"
    
    current_usage = getattr(usage, quota_field, 0)
    
    # Check if quota would be exceeded
    if quota_limit != float('inf') and current_usage + amount > quota_limit:
        return False, f"Quota exceeded for {quota_type}. Upgrade your subscription for higher limits."
    
    return True, "Quota available."

def create_stripe_checkout_session(user_id, plan_name):
    """
    Create a Stripe checkout session for subscription.
    
    Args:
        user_id (str): The user ID
        plan_name (str): The subscription plan name
        
    Returns:
        str: The checkout session URL or None if failed
    """
    # Get plan details
    plan_details = SUBSCRIPTION_PLANS.get(plan_name)
    if not plan_details:
        return None
    
    price_id = plan_details.get('price_id')
    if not price_id:
        logging.error(f"Missing price ID for plan {plan_name}")
        return None
    
    user = User.query.get(user_id)
    if not user:
        return None
    
    # Get existing subscription if any
    subscription = get_subscription(user_id)
    
    # Get or create Stripe customer
    stripe_customer_id = None
    if subscription and subscription.stripe_customer_id:
        stripe_customer_id = subscription.stripe_customer_id
    else:
        # Create a new Stripe customer
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name or ''} {user.last_name or ''}".strip(),
                metadata={
                    'user_id': user_id
                }
            )
            stripe_customer_id = customer.id
            
            # Update subscription record with customer ID
            if subscription:
                subscription.stripe_customer_id = stripe_customer_id
                db.session.commit()
        except Exception as e:
            logging.error(f"Error creating Stripe customer: {str(e)}")
            return None
    
    # Get the domain for success and cancel URLs
    domain = os.environ.get('REPLIT_DEV_DOMAIN') if os.environ.get('REPLIT_DEPLOYMENT') else os.environ.get('REPLIT_DOMAINS', 'localhost').split(',')[0]
    if not domain.startswith('http'):
        domain = f"https://{domain}"
    
    try:
        checkout_session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            payment_method_types=['card'],
            line_items=[
                {
                    'price': price_id,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=f"{domain}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{domain}/subscription/cancel",
            metadata={
                'user_id': user_id,
                'plan_name': plan_name
            }
        )
        return checkout_session.url
    except Exception as e:
        logging.error(f"Error creating checkout session: {str(e)}")
        return None

def handle_checkout_success(checkout_session_id):
    """
    Handle successful checkout session.
    
    Args:
        checkout_session_id (str): The Stripe checkout session ID
        
    Returns:
        bool: Success or failure
    """
    try:
        # Retrieve the session
        checkout_session = stripe.checkout.Session.retrieve(checkout_session_id)
        
        # Get user ID and plan from metadata
        user_id = checkout_session.metadata.get('user_id')
        plan_name = checkout_session.metadata.get('plan_name')
        
        if not user_id or not plan_name:
            logging.error("Missing user_id or plan_name in checkout session metadata")
            return False
        
        # Get stripe subscription ID
        subscription_id = checkout_session.subscription
        
        # Get or create subscription record
        subscription = get_subscription(user_id)
        if not subscription:
            subscription = Subscription(
                user_id=user_id
            )
            db.session.add(subscription)
        
        # Update subscription details
        subscription.stripe_subscription_id = subscription_id
        subscription.plan_name = plan_name
        subscription.status = 'active'
        
        # Get subscription period details
        try:
            stripe_subscription = stripe.Subscription.retrieve(subscription_id)
            current_period_start = datetime.fromtimestamp(stripe_subscription.current_period_start, tz=timezone.utc)
            current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end, tz=timezone.utc)
            
            subscription.current_period_start = current_period_start
            subscription.current_period_end = current_period_end
            subscription.cancel_at_period_end = stripe_subscription.cancel_at_period_end
        except Exception as e:
            logging.error(f"Error retrieving subscription details: {str(e)}")
        
        db.session.commit()
        return True
    except Exception as e:
        logging.error(f"Error handling checkout success: {str(e)}")
        return False

def cancel_subscription(user_id):
    """
    Cancel a user's subscription.
    
    Args:
        user_id (str): The user ID
        
    Returns:
        bool: Success or failure
    """
    subscription = get_subscription(user_id)
    if not subscription or not subscription.stripe_subscription_id:
        return False
    
    try:
        # Cancel the subscription at the end of the current period
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        # Update local record
        subscription.cancel_at_period_end = True
        db.session.commit()
        
        return True
    except Exception as e:
        logging.error(f"Error canceling subscription: {str(e)}")
        return False

def handle_webhook_event(event):
    """
    Handle Stripe webhook events.
    
    Args:
        event (dict): The webhook event data
        
    Returns:
        bool: Success or failure
    """
    event_type = event['type']
    
    try:
        if event_type == 'customer.subscription.created':
            return _handle_subscription_created(event)
        elif event_type == 'customer.subscription.updated':
            return _handle_subscription_updated(event)
        elif event_type == 'customer.subscription.deleted':
            return _handle_subscription_deleted(event)
        elif event_type == 'invoice.payment_succeeded':
            return _handle_payment_succeeded(event)
        elif event_type == 'invoice.payment_failed':
            return _handle_payment_failed(event)
        else:
            # Log but don't process other event types
            logging.info(f"Received unhandled webhook event: {event_type}")
            return True
    except Exception as e:
        logging.error(f"Error handling webhook event {event_type}: {str(e)}")
        return False

def _handle_subscription_created(event):
    """Handle subscription created event."""
    subscription_object = event['data']['object']
    stripe_subscription_id = subscription_object['id']
    customer_id = subscription_object['customer']
    
    # Find subscription by customer ID
    subscription = Subscription.query.filter_by(stripe_customer_id=customer_id).first()
    if not subscription:
        logging.warning(f"No subscription found for customer {customer_id}")
        return False
    
    # Update subscription details
    subscription.stripe_subscription_id = stripe_subscription_id
    subscription.status = subscription_object['status']
    
    current_period_start = datetime.fromtimestamp(subscription_object['current_period_start'], tz=timezone.utc)
    current_period_end = datetime.fromtimestamp(subscription_object['current_period_end'], tz=timezone.utc)
    
    subscription.current_period_start = current_period_start
    subscription.current_period_end = current_period_end
    subscription.cancel_at_period_end = subscription_object['cancel_at_period_end']
    
    db.session.commit()
    return True

def _handle_subscription_updated(event):
    """Handle subscription updated event."""
    subscription_object = event['data']['object']
    stripe_subscription_id = subscription_object['id']
    
    # Find subscription by stripe subscription ID
    subscription = Subscription.query.filter_by(stripe_subscription_id=stripe_subscription_id).first()
    if not subscription:
        logging.warning(f"No subscription found with ID {stripe_subscription_id}")
        return False
    
    # Update subscription details
    subscription.status = subscription_object['status']
    
    current_period_start = datetime.fromtimestamp(subscription_object['current_period_start'], tz=timezone.utc)
    current_period_end = datetime.fromtimestamp(subscription_object['current_period_end'], tz=timezone.utc)
    
    subscription.current_period_start = current_period_start
    subscription.current_period_end = current_period_end
    subscription.cancel_at_period_end = subscription_object['cancel_at_period_end']
    
    # Check for plan changes
    if 'items' in subscription_object and 'data' in subscription_object['items']:
        for item in subscription_object['items']['data']:
            price_id = item.get('price', {}).get('id')
            if price_id:
                # Map price ID to plan name
                for plan_name, plan_details in SUBSCRIPTION_PLANS.items():
                    if plan_details.get('price_id') == price_id:
                        subscription.plan_name = plan_name
                        break
    
    db.session.commit()
    return True

def _handle_subscription_deleted(event):
    """Handle subscription deleted event."""
    subscription_object = event['data']['object']
    stripe_subscription_id = subscription_object['id']
    
    # Find subscription by stripe subscription ID
    subscription = Subscription.query.filter_by(stripe_subscription_id=stripe_subscription_id).first()
    if not subscription:
        logging.warning(f"No subscription found with ID {stripe_subscription_id}")
        return False
    
    # Update subscription details
    subscription.status = 'canceled'
    subscription.plan_name = 'free'  # Downgrade to free plan
    
    db.session.commit()
    return True

def _handle_payment_succeeded(event):
    """Handle invoice payment succeeded event."""
    invoice = event['data']['object']
    subscription_id = invoice.get('subscription')
    
    if not subscription_id:
        return True  # Not a subscription invoice
    
    # Find subscription by stripe subscription ID
    subscription = Subscription.query.filter_by(stripe_subscription_id=subscription_id).first()
    if not subscription:
        logging.warning(f"No subscription found with ID {subscription_id}")
        return False
    
    # Update subscription status if needed
    if subscription.status != 'active':
        subscription.status = 'active'
        db.session.commit()
    
    return True

def _handle_payment_failed(event):
    """Handle invoice payment failed event."""
    invoice = event['data']['object']
    subscription_id = invoice.get('subscription')
    
    if not subscription_id:
        return True  # Not a subscription invoice
    
    # Find subscription by stripe subscription ID
    subscription = Subscription.query.filter_by(stripe_subscription_id=subscription_id).first()
    if not subscription:
        logging.warning(f"No subscription found with ID {subscription_id}")
        return False
    
    # Update subscription status
    subscription.status = 'past_due'
    db.session.commit()
    
    return True

# Create tables if they don't exist
def init_tables():
    """Create subscription-related tables if they don't exist."""
    try:
        with db.app.app_context():
            db.create_all()
            logging.info("Created subscription management tables")
    except Exception as e:
        logging.error(f"Error creating subscription tables: {str(e)}")

# Initialize tables when module is imported
init_tables()