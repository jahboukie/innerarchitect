"""
Subscription Manager module for The Inner Architect

This module handles subscription management, feature access control,
and usage quota tracking for the application.
"""

import os
import uuid
from datetime import datetime, timezone
from functools import wraps

import stripe

# We'll handle Stripe errors generically to avoid LSP issues
# This is more future-proof against Stripe library updates
from flask import flash, redirect, url_for, session
from flask_login import current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship

from logging_config import get_logger, info, error, debug, warning, critical, exception

# Get module-specific logger
logger = get_logger('subscription_manager')

# Import database object - we'll use a function to avoid circular imports
# This will be called after app initialization
from database import db as _db  # Import but rename to avoid confusion

# For type annotations
from typing import Any, Optional, Dict, List, Union, Type

# Define references that will be set during initialization
db = _db  # Use the imported db as default to prevent LSP errors

# Define types to help LSP with model references
# These type annotations help LSP understand that these variables will be SQLAlchemy models
# Using Any for query class to satisfy the type checker
# We can ignore LSP errors like "Cannot access member "filter_by" for type "function""
# as these are false positives due to the dynamic class creation in Flask-SQLAlchemy

class QueryClass:
    """Type stub for SQLAlchemy query class"""
    def filter_by(self, **kwargs) -> 'QueryClass': ...
    def first(self) -> Any: ...
    def all(self) -> List[Any]: ...
    def count(self) -> int: ...

class SQLABase:
    """Generic SQLAlchemy model base class for LSP"""
    # query is actually a property that returns a new query object
    query: Any  # Using Any instead of QueryClass to avoid LSP warnings
    
    @staticmethod
    def filter_by(**kwargs) -> Any: ...
    
    @staticmethod
    def get(id) -> Any: ...

class UserModel(SQLABase):
    """Type stub for User model to help LSP"""
    id: str
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    profile_image_url: Optional[str]
    
class SubscriptionModel(SQLABase):
    """Type stub for Subscription model to help LSP"""
    id: int
    user_id: str
    plan_name: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    stripe_customer_id: Optional[str]
    stripe_subscription_id: Optional[str]
    
class UsageQuotaModel(SQLABase):
    """Type stub for UsageQuota model to help LSP"""
    id: int
    user_id: Optional[str]
    browser_session_id: Optional[str]
    session_id: Optional[str]
    quota_type: Optional[str]  # Added to match models.py
    messages_used_today: int
    exercises_used_today: int  
    analyses_used_this_month: int
    last_reset_date: datetime
    last_monthly_reset_date: datetime

# Initialize with dummy classes that match the expected interface
# This is just for the LSP to be happy - these will be replaced with real models at runtime
# Type stub and placeholder classes - these will be replaced at runtime
# but help the LSP analysis until then

# Adding a comment to explain the LSP errors
# The LSP errors about functions and method calls can be safely ignored.
# These are expected because we're dynamically replacing these classes at runtime.

class User(UserModel):
    """Placeholder for the real User model that will be set at runtime"""
    # A static query property used only for type checking
    query = QueryClass()

class Subscription(SubscriptionModel):
    """Placeholder for the real Subscription model that will be set at runtime"""
    # A static query property used only for type checking
    query = QueryClass()

class UsageQuota(UsageQuotaModel):
    """Placeholder for the real UsageQuota model that will be set at runtime"""
    # A static query property used only for type checking
    query = QueryClass()

# These global variables will be properly set in init_models

def init_db(app_db):
    """Initialize database connection for subscription manager"""
    global db
    db = app_db
    # Now that we have the db object, create tables
    init_tables()

def init_models(user_model, subscription_model, usage_quota_model):
    """
    Initialize model classes with proper type checking
    
    This function is called by app.py after the database and models are initialized
    to provide the subscription manager with references to the actual model classes.
    
    Args:
        user_model: The User model class
        subscription_model: The Subscription model class
        usage_quota_model: The UsageQuota model class
    """
    global User, Subscription, UsageQuota
    
    # We need to actually replace the global references since we can't modify class __dict__
    # LSP will still show errors but the runtime will work correctly
    
    # Log the initialization for debugging purposes
    info(f"Initializing User model with {user_model.__name__}")
    info(f"Initializing Subscription model with {subscription_model.__name__}")
    info(f"Initializing UsageQuota model with {usage_quota_model.__name__}")
    
    # Simply assign the models directly
    User = user_model
    Subscription = subscription_model
    UsageQuota = usage_quota_model

# Initialize Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Constants
UNLIMITED_QUOTA = 9999999  # Represents unlimited quota (instead of infinity)

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
            'daily_messages': UNLIMITED_QUOTA,
            'daily_exercises': UNLIMITED_QUOTA,
            'monthly_analyses': UNLIMITED_QUOTA
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

# Note: Subscription class is imported from models.py

# Note: UsageQuota class is imported from models.py

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
        subscription = Subscription()
        subscription.user_id = user_id
        subscription.plan_name = 'free'
        subscription.status = 'active'
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
    try:
        # Log the feature access check attempt for debugging
        info(f"Checking feature access for user {user_id}, feature: {feature}")
        
        # Get the subscription details
        subscription = get_subscription(user_id)
        if not subscription:
            warning(f"No subscription found for user {user_id}")
            return False
        
        # Get the plan name from the subscription
        plan_name = subscription.plan_name
        if not plan_name:
            warning(f"Subscription found for user {user_id} but plan_name is empty")
            return False
            
        # Get the list of plans that have access to this feature
        allowed_plans = FEATURE_ACCESS.get(feature, [])
        if not allowed_plans:
            warning(f"No plans have access to feature: {feature}")
            return False
        
        # Check if the user's plan has access to this feature
        has_access = plan_name in allowed_plans
        info(f"Feature access check result: user {user_id} with plan '{plan_name}' {'has' if has_access else 'does not have'} access to {feature}")
        
        return has_access
        
    except Exception as e:
        error(f"Error checking feature access for user {user_id}, feature {feature}: {str(e)}")
        # Default to False on error to prevent unauthorized access
        return False

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
    usage = UsageQuota()
    usage.user_id = user_id
    usage.browser_session_id = browser_session_id
    # Set quota type directly now that we've added it to UsageQuotaModel
    usage.quota_type = 'default'  # Set a default quota type to prevent NULL constraint violation
    
    # Initialize with default values
    usage.messages_used_today = 0
    usage.exercises_used_today = 0
    usage.analyses_used_this_month = 0
    
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
    try:
        # Log the quota increment attempt for debugging
        user_identifier = f"user {user_id}" if user_id else f"session {browser_session_id}"
        info(f"Incrementing usage quota for {user_identifier}, quota type: {quota_type}, amount: {amount}")
        
        # Get the usage quota
        usage = get_usage_quota(user_id, browser_session_id)
        if not usage:
            warning(f"No usage record found for {user_identifier}, creating new record")
            
        # Get subscription details to check quota limits
        subscription_details = None
        subscription_plan = "free"
        
        if user_id:
            try:
                subscription_details = get_subscription_details(user_id)
                subscription_plan = subscription_details.get('plan_name', 'free')
                info(f"User {user_id} has subscription plan: {subscription_plan}")
            except Exception as sub_error:
                error(f"Error retrieving subscription details for {user_id}: {str(sub_error)}")
                # Default to free plan on error
                subscription_details = {
                    'plan_name': 'free',
                    'quotas': SUBSCRIPTION_PLANS['free']['quotas']
                }
        else:
            # For anonymous users, use free plan limits
            subscription_details = {
                'plan_name': 'free',
                'quotas': SUBSCRIPTION_PLANS['free']['quotas']
            }
            info(f"Anonymous session {browser_session_id} using free plan quotas")
        
        # Get the quota limit for this user's subscription plan
        quota_limit = subscription_details.get('quotas', {}).get(quota_type, 0)
        info(f"Quota limit for {quota_type} on {subscription_plan} plan: {quota_limit}")
        
        # Get the corresponding database field for this quota type
        quota_field = QUOTA_FIELDS.get(quota_type)
        if not quota_field:
            error_msg = f"Unknown quota type: {quota_type}"
            error(error_msg)
            return False, error_msg
        
        # Get current usage from the usage object
        current_usage = getattr(usage, quota_field, 0) or 0  # Handle None values
        info(f"Current usage for {quota_type} before increment: {current_usage}/{quota_limit}")
        
        # Check if unlimited quota
        if quota_limit == UNLIMITED_QUOTA:
            info(f"Unlimited quota for {quota_type} on {subscription_plan} plan")
            # Still increment the counter for tracking purposes
            new_usage = current_usage + amount
            setattr(usage, quota_field, new_usage)
            db.session.commit()
            info(f"Unlimited quota incremented to {new_usage}")
            return True, "Unlimited quota incremented successfully."
        
        # Check if quota would be exceeded
        if current_usage + amount > quota_limit:
            message = f"Quota exceeded for {quota_type}. Current usage: {current_usage}/{quota_limit}. Upgrade your subscription for higher limits."
            warning(f"Quota increment failed: {message}")
            return False, message
        
        # Increment the quota in the database
        new_usage = current_usage + amount
        setattr(usage, quota_field, new_usage)
        db.session.commit()
        
        # Success message
        remaining = quota_limit - new_usage
        message = f"Quota incremented successfully. New usage: {new_usage}/{quota_limit}. Remaining: {remaining}."
        info(f"Quota increment successful: {message}")
        return True, message
        
    except Exception as e:
        error_msg = f"Error incrementing usage quota: {str(e)}"
        error(error_msg)
        
        # Try to roll back any failed database changes
        try:
            db.session.rollback()
        except Exception as rollback_error:
            error(f"Error rolling back database session: {str(rollback_error)}")
            
        # Default to False on error
        return False, error_msg

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
    try:
        # Log the quota check for debugging
        user_identifier = f"user {user_id}" if user_id else f"session {browser_session_id}"
        info(f"Checking quota availability for {user_identifier}, quota type: {quota_type}, amount: {amount}")
        
        # Get the usage quota
        usage = get_usage_quota(user_id, browser_session_id)
        if not usage:
            warning(f"No usage record found for {user_identifier}, creating new record")
            
        # Get subscription details to check quota limits
        subscription_details = None
        subscription_plan = "free"
        
        if user_id:
            try:
                subscription_details = get_subscription_details(user_id)
                subscription_plan = subscription_details.get('plan_name', 'free')
                info(f"User {user_id} has subscription plan: {subscription_plan}")
            except Exception as sub_error:
                error(f"Error retrieving subscription details for {user_id}: {str(sub_error)}")
                # Default to free plan on error
                subscription_details = {
                    'plan_name': 'free',
                    'quotas': SUBSCRIPTION_PLANS['free']['quotas']
                }
        else:
            # For anonymous users, use free plan limits
            subscription_details = {
                'plan_name': 'free',
                'quotas': SUBSCRIPTION_PLANS['free']['quotas']
            }
            info(f"Anonymous session {browser_session_id} using free plan quotas")
        
        # Get the quota limit for this user's subscription plan
        quota_limit = subscription_details.get('quotas', {}).get(quota_type, 0)
        info(f"Quota limit for {quota_type} on {subscription_plan} plan: {quota_limit}")
        
        # Get the corresponding database field for this quota type
        quota_field = QUOTA_FIELDS.get(quota_type)
        if not quota_field:
            error_msg = f"Unknown quota type: {quota_type}"
            error(error_msg)
            return False, error_msg
        
        # Get current usage from the usage object
        current_usage = getattr(usage, quota_field, 0) or 0  # Handle None values
        info(f"Current usage for {quota_type}: {current_usage}/{quota_limit}")
        
        # Check if unlimited quota
        if quota_limit == UNLIMITED_QUOTA:
            info(f"Unlimited quota for {quota_type} on {subscription_plan} plan")
            return True, "Unlimited quota available."
        
        # Check if quota would be exceeded
        if current_usage + amount > quota_limit:
            message = f"Quota exceeded for {quota_type}. Current usage: {current_usage}/{quota_limit}. Upgrade your subscription for higher limits."
            warning(f"Quota check failed: {message}")
            return False, message
        
        # Quota is available
        remaining = quota_limit - current_usage
        message = f"Quota available. Current usage: {current_usage}/{quota_limit}. Remaining: {remaining}."
        info(f"Quota check passed: {message}")
        return True, message
        
    except Exception as e:
        error_msg = f"Error checking quota availability: {str(e)}"
        error(error_msg)
        # Default to False on error to prevent abuse
        return False, error_msg

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
        error(f"Missing price ID for plan {plan_name}")
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
            # Handle all Stripe exceptions in a generic way
            error_message = str(e)
            error_type = type(e).__name__
            error(f"Stripe error ({error_type}) creating customer: {error_message}")
            
            # Customize user feedback based on error type
            if "CardError" in error_type:
                # Card error (declined, etc.)
                try:
                    card_message = getattr(e, 'error', {}).get('message', error_message)
                    flash(f"Payment error: {card_message}", "danger")
                except:
                    flash("Your card was declined or there was an issue with your payment method. Please try again with a different card.", "danger")
            elif "RateLimitError" in error_type:
                # Too many requests
                flash("Our payment system is experiencing heavy load. Please try again in a few minutes.", "warning")
            elif "InvalidRequestError" in error_type:
                # Invalid parameters
                flash("There was an error with your payment information. Please try again.", "danger")
            elif "AuthenticationError" in error_type:
                # Authentication with Stripe's API failed
                flash("We're having trouble connecting to our payment provider. Please try again later.", "danger")
            elif "APIConnectionError" in error_type:
                # Network error
                flash("We're having trouble connecting to our payment provider. Please check your internet connection and try again.", "warning")
            else:
                # Generic error
                flash("An unexpected error occurred with our payment system. Please try again later.", "danger")
            
            return None
    
    # Get the domain for success and cancel URLs
    domain = None
    if os.environ.get('REPLIT_DEPLOYMENT'):
        domain = os.environ.get('REPLIT_DEV_DOMAIN')
    elif os.environ.get('REPLIT_DOMAINS'):
        replit_domains = os.environ.get('REPLIT_DOMAINS')
        if replit_domains:  # Ensure it's not None before splitting
            domain = replit_domains.split(',')[0]
    
    # Default to localhost if no domain found
    if not domain:
        domain = 'localhost:5000'
        
    # Ensure it has https:// prefix
    if domain and not domain.startswith('http'):
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
        # Handle all Stripe exceptions in a generic way
        error_message = str(e)
        error_type = type(e).__name__
        error(f"Stripe error ({error_type}) creating checkout session: {error_message}")
        
        # Customize user feedback based on error type
        if "CardError" in error_type:
            # Card error (declined, etc.)
            try:
                card_message = getattr(e, 'error', {}).get('message', error_message)
                flash(f"Payment error: {card_message}", "danger")
            except:
                flash("Your card was declined or there was an issue with your payment method. Please try again with a different card.", "danger")
        elif "RateLimitError" in error_type:
            # Too many requests
            flash("Our payment system is experiencing heavy load. Please try again in a few minutes.", "warning")
        elif "InvalidRequestError" in error_type:
            # Invalid parameters
            if "price" in error_message.lower():
                flash("This subscription plan is currently unavailable. Please contact support.", "danger")
            else:
                flash("There was an error with your payment information. Please try again.", "danger")
        elif "AuthenticationError" in error_type:
            # Authentication with Stripe's API failed
            flash("We're having trouble connecting to our payment provider. Please try again later.", "danger")
        elif "APIConnectionError" in error_type:
            # Network error
            flash("We're having trouble connecting to our payment provider. Please check your internet connection and try again.", "warning")
        else:
            # Generic error
            flash("An unexpected error occurred with our payment system. Please try again later.", "danger")
        
        return None

def handle_checkout_success(checkout_session_id):
    """
    Handle successful checkout session.
    
    Args:
        checkout_session_id (str): The Stripe checkout session ID
        
    Returns:
        bool: Success or failure
    """
    if not checkout_session_id:
        error("Empty checkout session ID provided")
        return False
        
    try:
        # Retrieve the session
        checkout_session = stripe.checkout.Session.retrieve(checkout_session_id)
        
        # Get user ID and plan from metadata
        metadata = checkout_session.get('metadata', {})
        user_id = metadata.get('user_id') if metadata else None
        plan_name = metadata.get('plan_name') if metadata else None
        
        if not user_id or not plan_name:
            error("Missing user_id or plan_name in checkout session metadata")
            return False
        
        # Get stripe subscription ID
        subscription_id = checkout_session.get('subscription')
        if not subscription_id:
            error("No subscription ID found in checkout session")
            return False
        
        # Get or create subscription record
        subscription = get_subscription(user_id)
        if not subscription:
            # Create new subscription
            subscription = Subscription()
            subscription.user_id = user_id
            db.session.add(subscription)
        
        # Update subscription details
        subscription.stripe_subscription_id = str(subscription_id)
        subscription.plan_name = plan_name
        subscription.status = 'active'
        
        # Get subscription period details
        try:
            stripe_subscription = stripe.Subscription.retrieve(str(subscription_id))
            
            # Safely extract period data
            current_period_start = stripe_subscription.get('current_period_start')
            current_period_end = stripe_subscription.get('current_period_end')
            
            if current_period_start:
                subscription.current_period_start = datetime.fromtimestamp(current_period_start, tz=timezone.utc)
            
            if current_period_end:
                subscription.current_period_end = datetime.fromtimestamp(current_period_end, tz=timezone.utc)
                
            cancel_at_period_end = stripe_subscription.get('cancel_at_period_end', False)
            subscription.cancel_at_period_end = cancel_at_period_end
            
        except Exception as e:
            # Handle all exceptions in a generic way
            error_message = str(e)
            error_type = type(e).__name__
            error(f"Error ({error_type}) retrieving subscription details: {error_message}")
            # Still allow the subscription to be created even if details can't be fetched
        
        db.session.commit()
        info(f"Successfully processed subscription for user {user_id} with plan {plan_name}")
        return True
        
    except Exception as e:
        # Handle all exceptions in a generic way
        error_message = str(e)
        error_type = type(e).__name__
        error(f"Error ({error_type}) handling checkout success: {error_message}")
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
        error(f"Error canceling subscription: {str(e)}")
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
            info(f"Received unhandled webhook event: {event_type}")
            return True
    except Exception as e:
        # Handle all exceptions in a generic way
        error_message = str(e)
        error_type = type(e).__name__
        error(f"Error ({error_type}) handling webhook event {event_type}: {error_message}")
        
        # Add more detailed logging for troubleshooting
        if event and isinstance(event, dict):
            # Log the event ID but not the full event content for security
            event_id = event.get('id', 'unknown')
            error(f"Failed webhook event ID: {event_id}")
        
        return False

def _handle_subscription_created(event):
    """Handle subscription created event."""
    subscription_object = event['data']['object']
    stripe_subscription_id = subscription_object['id']
    customer_id = subscription_object['customer']
    
    # Find subscription by customer ID
    subscription = Subscription.query.filter_by(stripe_customer_id=customer_id).first()
    if not subscription:
        warning(f"No subscription found for customer {customer_id}")
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
        warning(f"No subscription found with ID {stripe_subscription_id}")
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
        warning(f"No subscription found with ID {stripe_subscription_id}")
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
        warning(f"No subscription found with ID {subscription_id}")
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
        warning(f"No subscription found with ID {subscription_id}")
        return False
    
    # Update subscription status
    subscription.status = 'past_due'
    db.session.commit()
    
    return True

# Create tables if they don't exist
def init_tables():
    """Create subscription-related tables if they don't exist."""
    if db is None:
        warning("Database not initialized yet - tables will be created later")
        return
        
    try:
        # Check if we're already inside an application context
        if hasattr(db, 'app') and db.app:
            # We're running within Flask, use the app context
            with db.app.app_context():
                db.create_all()
                info("Created subscription management tables")
        else:
            # We're being imported directly, tables will be created when app starts
            debug("Database available but no app context - tables will be created at app startup")
    except AttributeError as ae:
        warning(f"Database object not ready for creating tables: {str(ae)}")
    except Exception as e:
        error(f"Error creating subscription tables: {str(e)}")
        exception("Full traceback for subscription table creation error:")