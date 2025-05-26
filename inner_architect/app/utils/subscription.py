import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, List, Union

import stripe

from app import db
from app.models.subscription import Subscription, UsageQuota
from app.models.user import User

# Get logger
logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Constants
UNLIMITED_QUOTA = 9999999  # Represents unlimited quota (instead of infinity)

# Trial constants
DEFAULT_TRIAL_DAYS = 7  # Default 7-day trial period
MAX_TRIAL_DAYS = 30  # Maximum allowed trial period

# Define subscription plans and features
SUBSCRIPTION_PLANS = {
    'free': {
        'name': 'Free',
        'price_id': 'price_1RO13ZELGHd3NbdJjXnzAZr0',  # Stripe price ID for free tier
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
        'price_id': 'price_1RO14rELGHd3NbdJ5euGu2lB',  # Stripe price ID for premium tier
        'amount': 999,  # $9.99 in cents
        'interval': 'month',
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
        'price_id': 'price_1RO16hELGHd3NbdJZqnOKIzW',  # Stripe price ID for professional tier
        'amount': 1999,  # $19.99 in cents
        'interval': 'month',
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

# Model references - these will be set by init_models
_User = None
_Subscription = None
_UsageQuota = None

def init_models(User, Subscription, UsageQuota):
    """
    Initialize model references.
    
    Args:
        User: The User model class
        Subscription: The Subscription model class
        UsageQuota: The UsageQuota model class
    """
    global _User, _Subscription, _UsageQuota
    
    _User = User
    _Subscription = Subscription
    _UsageQuota = UsageQuota
    
    logger.info("Initialized model references in subscription manager")

def get_subscription(user_id: str) -> Optional[Subscription]:
    """
    Get a user's subscription.
    
    Args:
        user_id: The user ID
        
    Returns:
        The subscription or None if not found
    """
    global _Subscription
    if _Subscription is None:
        logger.error("Subscription model not initialized")
        return None
        
    return _Subscription.query.filter_by(user_id=user_id).first()

def get_subscription_details(user_id: str) -> Dict[str, Any]:
    """
    Get detailed subscription information for a user.
    
    Args:
        user_id: The user ID
        
    Returns:
        Subscription details including plan features and quotas
    """
    global _Subscription
    if _Subscription is None:
        logger.error("Subscription model not initialized")
        return {
            'plan_name': 'free',
            'status': 'active',
            'features': SUBSCRIPTION_PLANS['free']['features'],
            'quotas': SUBSCRIPTION_PLANS['free']['quotas'],
            'has_premium_access': False,
            'has_professional_access': False
        }
        
    subscription = get_subscription(user_id)
    
    # If no subscription record exists, create one with the free plan
    if not subscription:
        subscription = _Subscription(
            user_id=user_id,
            plan_name='free',
            status='active'
        )
        db.session.add(subscription)
        db.session.commit()
    
    # Get plan details
    plan_name = subscription.plan_name
    
    # Check if user has an active trial
    if subscription.has_active_trial:
        # Use the trial plan for details
        plan_name = subscription.trial_plan
    
    plan_details = SUBSCRIPTION_PLANS.get(plan_name, SUBSCRIPTION_PLANS['free'])
    
    # Get usage quotas
    usage = get_usage_quota(user_id)
    
    # Return combined details
    return {
        'subscription_id': subscription.id,
        'plan_name': plan_name,
        'effective_plan': plan_name,  # For API consistency
        'status': subscription.status,
        'has_active_trial': subscription.has_active_trial,
        'trial_days_remaining': subscription.trial_days_remaining,
        'trial_plan': subscription.trial_plan if subscription.has_active_trial else None,
        'is_trial': subscription.has_active_trial,
        'cancel_at_period_end': subscription.cancel_at_period_end,
        'current_period_end': subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        'features': plan_details.get('features', []),
        'quotas': plan_details.get('quotas', {}),
        'usage': {
            'messages_used_today': usage.messages_used_today,
            'exercises_used_today': usage.exercises_used_today,
            'analyses_used_this_month': usage.analyses_used_this_month
        },
        'has_premium_access': subscription.has_premium_access,
        'has_professional_access': subscription.has_professional_access
    }

def check_feature_access(user_id: str, feature: str) -> bool:
    """
    Check if a user has access to a specific feature based on their subscription.
    
    Args:
        user_id: The user ID
        feature: The feature identifier
        
    Returns:
        True if the user has access, False otherwise
    """
    try:
        # Get the subscription details
        subscription = get_subscription(user_id)
        if not subscription:
            logger.warning(f"No subscription found for user {user_id}")
            return False
        
        # Check for active trial
        if subscription.has_active_trial:
            # Use the trial plan for access checks
            effective_plan = subscription.trial_plan
            logger.info(f"User {user_id} has active trial for {effective_plan} plan")
        else:
            # Use the regular subscription plan
            effective_plan = subscription.plan_name
        
        if not effective_plan:
            logger.warning(f"Subscription found for user {user_id} but effective_plan is empty")
            return False
            
        # Get the list of plans that have access to this feature
        allowed_plans = FEATURE_ACCESS.get(feature, [])
        if not allowed_plans:
            logger.warning(f"No plans have access to feature: {feature}")
            return False
        
        # Check if the user's plan has access to this feature
        has_access = effective_plan in allowed_plans
        logger.info(f"Feature access check result: user {user_id} with {'trial ' if subscription.has_active_trial else ''}plan '{effective_plan}' {'has' if has_access else 'does not have'} access to {feature}")
        
        return has_access
        
    except Exception as e:
        logger.error(f"Error checking feature access for user {user_id}, feature {feature}: {str(e)}")
        # Default to False on error to prevent unauthorized access
        return False

def create_trial(user_id: str, trial_plan: str = 'premium', trial_days: int = DEFAULT_TRIAL_DAYS) -> Tuple[bool, str, Optional[Subscription]]:
    """
    Create a trial subscription for a user.
    
    Args:
        user_id: The user ID
        trial_plan: The plan to trial ('premium' or 'professional')
        trial_days: Number of days for the trial (default: 7)
        
    Returns:
        Tuple of (success, message, subscription)
    """
    global _Subscription
    if _Subscription is None:
        logger.error("Subscription model not initialized")
        return False, "System error: Subscription model not initialized", None
        
    logger.info(f"Creating {trial_plan} trial for user {user_id} for {trial_days} days")
    
    # Validate parameters
    if trial_plan not in ['premium', 'professional']:
        error_msg = f"Invalid trial plan: {trial_plan}"
        logger.error(error_msg)
        return False, error_msg, None
    
    # Limit trial days to reasonable range
    if trial_days <= 0:
        error_msg = "Trial days must be greater than 0"
        logger.error(error_msg)
        return False, error_msg, None
    
    if trial_days > MAX_TRIAL_DAYS:
        logger.warning(f"Trial days {trial_days} exceeds maximum {MAX_TRIAL_DAYS}, limiting to {MAX_TRIAL_DAYS}")
        trial_days = MAX_TRIAL_DAYS
    
    try:
        # Check if user already has a subscription
        subscription = get_subscription(user_id)
        
        # If user already has a paid subscription, don't create a trial
        if subscription and subscription.plan_name in ['premium', 'professional']:
            if subscription.is_active:
                logger.warning(f"User {user_id} already has an active {subscription.plan_name} subscription, trial not created")
                return False, f"User already has an active {subscription.plan_name} subscription", subscription
        
        # If user has an active trial, don't create another one
        if subscription and subscription.is_trial and subscription.has_active_trial:
            logger.warning(f"User {user_id} already has an active trial for {subscription.trial_plan}")
            return False, f"User already has an active trial for {subscription.trial_plan}", subscription
        
        current_time = datetime.now(timezone.utc)
        trial_end = current_time + timedelta(days=trial_days)
        
        # Create or update subscription with trial
        if subscription:
            logger.info(f"Updating existing subscription for user {user_id} with trial")
            
            # Update subscription with trial details
            subscription.is_trial = True
            subscription.trial_started_at = current_time
            subscription.trial_ends_at = trial_end
            subscription.trial_plan = trial_plan
            subscription.trial_converted = False
            
            db.session.commit()
            logger.info(f"Updated subscription to {trial_plan} trial until {trial_end}")
        else:
            logger.info(f"Creating new subscription for user {user_id} with trial")
            
            # Create a new subscription with trial
            subscription = _Subscription(
                user_id=user_id,
                plan_name='free',  # Base plan is still free
                status='active',
                is_trial=True,
                trial_started_at=current_time,
                trial_ends_at=trial_end,
                trial_plan=trial_plan,
                trial_converted=False
            )
            
            db.session.add(subscription)
            db.session.commit()
            logger.info(f"Created new subscription with {trial_plan} trial until {trial_end}")
        
        # Return success
        return True, f"{trial_plan.capitalize()} trial activated for {trial_days} days", subscription
        
    except Exception as e:
        logger.error(f"Error creating trial for user {user_id}: {str(e)}")
        db.session.rollback()
        return False, f"Error creating trial: {str(e)}", None

def end_trial(user_id: str, convert_to_paid: bool = False) -> Tuple[bool, str]:
    """
    End a user's trial subscription.
    
    Args:
        user_id: The user ID
        convert_to_paid: Whether to convert the trial to a paid subscription
        
    Returns:
        Tuple of (success, message)
    """
    logger.info(f"Ending trial for user {user_id}, convert to paid: {convert_to_paid}")
    
    try:
        # Get the subscription
        subscription = get_subscription(user_id)
        
        if not subscription:
            error_msg = f"No subscription found for user {user_id}"
            logger.error(error_msg)
            return False, error_msg
        
        if not subscription.is_trial:
            logger.warning(f"User {user_id} doesn't have a trial subscription")
            return False, "User doesn't have a trial subscription"
        
        if convert_to_paid:
            # Convert to paid subscription
            subscription.is_trial = False
            subscription.trial_converted = True
            subscription.plan_name = subscription.trial_plan
            subscription.status = 'active'
            subscription.current_period_start = datetime.now(timezone.utc)
            subscription.current_period_end = subscription.current_period_start + timedelta(days=30)
            
            db.session.commit()
            logger.info(f"Converted trial to paid {subscription.plan_name} subscription")
            return True, f"Trial converted to paid {subscription.plan_name} subscription"
        else:
            # Just end the trial
            subscription.is_trial = False
            subscription.trial_converted = False
            
            db.session.commit()
            logger.info(f"Trial ended without conversion")
            return True, "Trial ended"
        
    except Exception as e:
        logger.error(f"Error ending trial for user {user_id}: {str(e)}")
        db.session.rollback()
        return False, f"Error ending trial: {str(e)}"

def get_usage_quota(user_id: Optional[str] = None, browser_session_id: Optional[str] = None) -> UsageQuota:
    """
    Get a user's usage quota.
    
    Args:
        user_id: The user ID (optional)
        browser_session_id: The browser session ID for anonymous users (optional)
        
    Returns:
        The usage quota object
    """
    global _UsageQuota
    if _UsageQuota is None:
        logger.error("UsageQuota model not initialized")
        # Return a dummy object with default values
        class DummyQuota:
            messages_used_today = 0
            exercises_used_today = 0
            analyses_used_this_month = 0
        return DummyQuota()
        
    # First try to find by user_id if provided
    if user_id:
        usage = _UsageQuota.query.filter_by(user_id=user_id).first()
        if usage:
            # Check if daily/monthly reset is needed
            _check_reset_quotas(usage)
            return usage
    
    # If not found by user_id or user_id not provided, try browser_session_id
    if browser_session_id:
        usage = _UsageQuota.query.filter_by(browser_session_id=browser_session_id).first()
        if usage:
            # Check if daily/monthly reset is needed
            _check_reset_quotas(usage)
            return usage
    
    # If no quota record found, create a new one
    usage = _UsageQuota(
        user_id=user_id,
        browser_session_id=browser_session_id,
        quota_type='default',  # Set a default quota type
        messages_used_today=0,
        exercises_used_today=0,
        analyses_used_this_month=0,
        last_reset_date=datetime.utcnow(),
        last_monthly_reset_date=datetime.utcnow()
    )
    
    db.session.add(usage)
    db.session.commit()
    
    return usage

def _check_reset_quotas(usage) -> None:
    """
    Check if daily or monthly quota reset is needed and perform the reset.
    
    Args:
        usage: The usage quota object
    """
    now = datetime.utcnow()
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

def increment_usage_quota(
    user_id: Optional[str] = None, 
    browser_session_id: Optional[str] = None,
    quota_type: str = 'daily_messages',
    amount: int = 1
) -> Tuple[bool, str]:
    """
    Increment a specific usage quota.
    
    Args:
        user_id: The user ID (optional)
        browser_session_id: The browser session ID for anonymous users (optional)
        quota_type: The type of quota to increment ('daily_messages', 'daily_exercises', 'monthly_analyses')
        amount: The amount to increment by
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Log the quota increment attempt for debugging
        user_identifier = f"user {user_id}" if user_id else f"session {browser_session_id}"
        logger.info(f"Incrementing usage quota for {user_identifier}, quota type: {quota_type}, amount: {amount}")
        
        # Get the usage quota
        usage = get_usage_quota(user_id, browser_session_id)
        if not usage:
            logger.warning(f"No usage record found for {user_identifier}, creating new record")
            
        # Get subscription details to check quota limits
        subscription_details = None
        subscription_plan = "free"
        
        if user_id:
            try:
                subscription_details = get_subscription_details(user_id)
                subscription_plan = subscription_details.get('plan_name', 'free')
                logger.info(f"User {user_id} has subscription plan: {subscription_plan}")
            except Exception as sub_error:
                logger.error(f"Error retrieving subscription details for {user_id}: {str(sub_error)}")
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
            logger.info(f"Anonymous session {browser_session_id} using free plan quotas")
        
        # Get the quota limit for this user's subscription plan
        quota_limit = subscription_details.get('quotas', {}).get(quota_type, 0)
        logger.info(f"Quota limit for {quota_type} on {subscription_plan} plan: {quota_limit}")
        
        # Get the corresponding database field for this quota type
        quota_field = QUOTA_FIELDS.get(quota_type)
        if not quota_field:
            error_msg = f"Unknown quota type: {quota_type}"
            logger.error(error_msg)
            return False, error_msg
        
        # Get current usage from the usage object
        current_usage = getattr(usage, quota_field, 0) or 0  # Handle None values
        logger.info(f"Current usage for {quota_type} before increment: {current_usage}/{quota_limit}")
        
        # Check if unlimited quota
        if quota_limit == UNLIMITED_QUOTA:
            logger.info(f"Unlimited quota for {quota_type} on {subscription_plan} plan")
            # Still increment the counter for tracking purposes
            new_usage = current_usage + amount
            setattr(usage, quota_field, new_usage)
            db.session.commit()
            logger.info(f"Unlimited quota incremented to {new_usage}")
            return True, "Unlimited quota incremented successfully."
        
        # Check if quota would be exceeded
        if current_usage + amount > quota_limit:
            message = f"Quota exceeded for {quota_type}. Current usage: {current_usage}/{quota_limit}. Upgrade your subscription for higher limits."
            logger.warning(f"Quota increment failed: {message}")
            return False, message
        
        # Increment the quota in the database
        new_usage = current_usage + amount
        setattr(usage, quota_field, new_usage)
        db.session.commit()
        
        # Success message
        remaining = quota_limit - new_usage
        message = f"Quota incremented successfully. New usage: {new_usage}/{quota_limit}. Remaining: {remaining}."
        logger.info(f"Quota increment successful: {message}")
        return True, message
        
    except Exception as e:
        error_msg = f"Error incrementing usage quota: {str(e)}"
        logger.error(error_msg)
        
        # Try to roll back any failed database changes
        try:
            db.session.rollback()
        except Exception as rollback_error:
            logger.error(f"Error rolling back database session: {str(rollback_error)}")
            
        # Default to False on error
        return False, error_msg

def check_quota_available(
    user_id: Optional[str] = None,
    browser_session_id: Optional[str] = None,
    quota_type: str = 'daily_messages',
    amount: int = 1
) -> Tuple[bool, str]:
    """
    Check if a specific quota is available without incrementing it.
    
    Args:
        user_id: The user ID (optional)
        browser_session_id: The browser session ID for anonymous users (optional)
        quota_type: The type of quota to check ('daily_messages', 'daily_exercises', 'monthly_analyses')
        amount: The amount to check for
        
    Returns:
        Tuple of (available, message)
    """
    try:
        # Log the quota check for debugging
        user_identifier = f"user {user_id}" if user_id else f"session {browser_session_id}"
        logger.info(f"Checking quota availability for {user_identifier}, quota type: {quota_type}, amount: {amount}")
        
        # Get the usage quota
        usage = get_usage_quota(user_id, browser_session_id)
        if not usage:
            logger.warning(f"No usage record found for {user_identifier}, creating new record")
            
        # Get subscription details to check quota limits
        subscription_details = None
        subscription_plan = "free"
        
        if user_id:
            try:
                subscription_details = get_subscription_details(user_id)
                subscription_plan = subscription_details.get('plan_name', 'free')
                logger.info(f"User {user_id} has subscription plan: {subscription_plan}")
            except Exception as sub_error:
                logger.error(f"Error retrieving subscription details for {user_id}: {str(sub_error)}")
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
            logger.info(f"Anonymous session {browser_session_id} using free plan quotas")
        
        # Get the quota limit for this user's subscription plan
        quota_limit = subscription_details.get('quotas', {}).get(quota_type, 0)
        logger.info(f"Quota limit for {quota_type} on {subscription_plan} plan: {quota_limit}")
        
        # Get the corresponding database field for this quota type
        quota_field = QUOTA_FIELDS.get(quota_type)
        if not quota_field:
            error_msg = f"Unknown quota type: {quota_type}"
            logger.error(error_msg)
            return False, error_msg
        
        # Get current usage from the usage object
        current_usage = getattr(usage, quota_field, 0) or 0  # Handle None values
        logger.info(f"Current usage for {quota_type}: {current_usage}/{quota_limit}")
        
        # Check if unlimited quota
        if quota_limit == UNLIMITED_QUOTA:
            logger.info(f"Unlimited quota for {quota_type} on {subscription_plan} plan")
            return True, "Unlimited quota available."
        
        # Check if quota would be exceeded
        if current_usage + amount > quota_limit:
            message = f"Quota exceeded for {quota_type}. Current usage: {current_usage}/{quota_limit}. Upgrade your subscription for higher limits."
            logger.warning(f"Quota check failed: {message}")
            return False, message
        
        # Quota is available
        remaining = quota_limit - current_usage
        message = f"Quota available. Current usage: {current_usage}/{quota_limit}. Remaining: {remaining}."
        logger.info(f"Quota check passed: {message}")
        return True, message
        
    except Exception as e:
        error_msg = f"Error checking quota availability: {str(e)}"
        logger.error(error_msg)
        # Default to False on error to prevent abuse
        return False, error_msg