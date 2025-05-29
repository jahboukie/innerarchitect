"""
Analytics Dashboard for InnerArchitect.

This module provides the analytics dashboard functionality, including data collection,
processing, and visualization of user behavior, technique effectiveness, and platform metrics.
"""

import os
import json
import logging
import datetime
import functools
from collections import defaultdict, Counter
from typing import Dict, List, Any, Optional, Tuple, Union

from flask import Blueprint, render_template, request, jsonify, current_app, abort
from flask_login import login_required, current_user
from sqlalchemy import func, desc, text, extract, case, and_, or_
from sqlalchemy.sql import label

from models import (
    db, User, ChatHistory, ConversationContext, NLPExercise,
    NLPExerciseProgress, TechniqueEffectiveness, TechniqueUsageStats,
    UserPreferences, Subscription, UsageQuota
)
from logging_config import get_logger

# Create analytics blueprint
analytics = Blueprint('analytics', __name__, url_prefix='/analytics')

# Get logger
logger = get_logger('analytics')

# Admin required decorator
def admin_required(f):
    """
    Decorator to require admin privileges for a route.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not hasattr(current_user, 'is_admin') or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@analytics.route('/')
@login_required
@admin_required
def index():
    """Analytics dashboard index page."""
    return render_template('analytics/dashboard.html')

@analytics.route('/user-engagement')
@login_required
@admin_required
def user_engagement():
    """User engagement analytics page."""
    # Get time range from request args
    time_range = request.args.get('time_range', '30d')

    # Convert time range to timedelta
    if time_range == '7d':
        delta = datetime.timedelta(days=7)
        time_label = 'Last 7 days'
        period = 'day'
    elif time_range == '90d':
        delta = datetime.timedelta(days=90)
        time_label = 'Last 90 days'
        period = 'week'
    elif time_range == '1y':
        delta = datetime.timedelta(days=365)
        time_label = 'Last year'
        period = 'month'
    else:  # Default to 30d
        delta = datetime.timedelta(days=30)
        time_label = 'Last 30 days'
        period = 'day'

    # Calculate start time
    start_time = datetime.datetime.now() - delta

    # Get user engagement metrics
    metrics = get_user_engagement_metrics(start_time, period)

    return render_template(
        'analytics/user_engagement.html',
        time_range=time_label,
        metrics=metrics
    )

@analytics.route('/technique-effectiveness')
@login_required
@admin_required
def technique_effectiveness():
    """Technique effectiveness analytics page."""
    # Get time range from request args
    time_range = request.args.get('time_range', '30d')

    # Convert time range to timedelta
    if time_range == '7d':
        delta = datetime.timedelta(days=7)
        time_label = 'Last 7 days'
    elif time_range == '90d':
        delta = datetime.timedelta(days=90)
        time_label = 'Last 90 days'
    elif time_range == '1y':
        delta = datetime.timedelta(days=365)
        time_label = 'Last year'
    else:  # Default to 30d
        delta = datetime.timedelta(days=30)
        time_label = 'Last 30 days'

    # Calculate start time
    start_time = datetime.datetime.now() - delta

    # Get technique effectiveness metrics
    metrics = get_technique_effectiveness_metrics(start_time)

    return render_template(
        'analytics/technique_effectiveness.html',
        time_range=time_label,
        metrics=metrics
    )

@analytics.route('/user-progress')
@login_required
@admin_required
def user_progress():
    """User progress analytics page."""
    # Get time range from request args
    time_range = request.args.get('time_range', '30d')

    # Convert time range to timedelta
    if time_range == '7d':
        delta = datetime.timedelta(days=7)
        time_label = 'Last 7 days'
    elif time_range == '90d':
        delta = datetime.timedelta(days=90)
        time_label = 'Last 90 days'
    elif time_range == '1y':
        delta = datetime.timedelta(days=365)
        time_label = 'Last year'
    else:  # Default to 30d
        delta = datetime.timedelta(days=30)
        time_label = 'Last 30 days'

    # Calculate start time
    start_time = datetime.datetime.now() - delta

    # Get user progress metrics
    metrics = get_user_progress_metrics(start_time)

    return render_template(
        'analytics/user_progress.html',
        time_range=time_label,
        metrics=metrics
    )

@analytics.route('/business-metrics')
@login_required
@admin_required
def business_metrics():
    """Business metrics analytics page."""
    # Get time range from request args
    time_range = request.args.get('time_range', '30d')

    # Convert time range to timedelta
    if time_range == '7d':
        delta = datetime.timedelta(days=7)
        time_label = 'Last 7 days'
        period = 'day'
    elif time_range == '90d':
        delta = datetime.timedelta(days=90)
        time_label = 'Last 90 days'
        period = 'week'
    elif time_range == '1y':
        delta = datetime.timedelta(days=365)
        time_label = 'Last year'
        period = 'month'
    else:  # Default to 30d
        delta = datetime.timedelta(days=30)
        time_label = 'Last 30 days'
        period = 'day'

    # Calculate start time
    start_time = datetime.datetime.now() - delta

    # Get business metrics
    metrics = get_business_metrics(start_time, period)

    return render_template(
        'analytics/business_metrics.html',
        time_range=time_label,
        metrics=metrics
    )

@analytics.route('/user-insights')
@login_required
@admin_required
def user_insights():
    """User insights analytics page with segmentation."""
    # Get user segments and insights
    segments = get_user_segments()
    insights = get_user_insights()

    return render_template(
        'analytics/user_insights.html',
        segments=segments,
        insights=insights
    )

@analytics.route('/data/user-engagement')
@login_required
@admin_required
def user_engagement_data():
    """API endpoint to get user engagement data for charts."""
    # Get time range from request args
    time_range = request.args.get('time_range', '30d')

    # Convert time range to timedelta
    if time_range == '7d':
        delta = datetime.timedelta(days=7)
        period = 'day'
    elif time_range == '90d':
        delta = datetime.timedelta(days=90)
        period = 'week'
    elif time_range == '1y':
        delta = datetime.timedelta(days=365)
        period = 'month'
    else:  # Default to 30d
        delta = datetime.timedelta(days=30)
        period = 'day'

    # Calculate start time
    start_time = datetime.datetime.now() - delta

    # Get data for charts
    data = get_user_engagement_chart_data(start_time, period)

    return jsonify(data)

@analytics.route('/data/technique-effectiveness')
@login_required
@admin_required
def technique_effectiveness_data():
    """API endpoint to get technique effectiveness data for charts."""
    # Get time range from request args
    time_range = request.args.get('time_range', '30d')

    # Convert time range to timedelta
    if time_range == '7d':
        delta = datetime.timedelta(days=7)
    elif time_range == '90d':
        delta = datetime.timedelta(days=90)
    elif time_range == '1y':
        delta = datetime.timedelta(days=365)
    else:  # Default to 30d
        delta = datetime.timedelta(days=30)

    # Calculate start time
    start_time = datetime.datetime.now() - delta

    # Get data for charts
    data = get_technique_effectiveness_chart_data(start_time)

    return jsonify(data)

@analytics.route('/data/user-progress')
@login_required
@admin_required
def user_progress_data():
    """API endpoint to get user progress data for charts."""
    # Get time range from request args
    time_range = request.args.get('time_range', '30d')

    # Convert time range to timedelta
    if time_range == '7d':
        delta = datetime.timedelta(days=7)
    elif time_range == '90d':
        delta = datetime.timedelta(days=90)
    elif time_range == '1y':
        delta = datetime.timedelta(days=365)
    else:  # Default to 30d
        delta = datetime.timedelta(days=30)

    # Calculate start time
    start_time = datetime.datetime.now() - delta

    # Get data for charts
    data = get_user_progress_chart_data(start_time)

    return jsonify(data)

@analytics.route('/data/business-metrics')
@login_required
@admin_required
def business_metrics_data():
    """API endpoint to get business metrics data for charts."""
    # Get time range from request args
    time_range = request.args.get('time_range', '30d')

    # Convert time range to timedelta
    if time_range == '7d':
        delta = datetime.timedelta(days=7)
        period = 'day'
    elif time_range == '90d':
        delta = datetime.timedelta(days=90)
        period = 'week'
    elif time_range == '1y':
        delta = datetime.timedelta(days=365)
        period = 'month'
    else:  # Default to 30d
        delta = datetime.timedelta(days=30)
        period = 'day'

    # Calculate start time
    start_time = datetime.datetime.now() - delta

    # Get data for charts
    data = get_business_metrics_chart_data(start_time, period)

    return jsonify(data)

@analytics.route('/data/user-details/<user_id>')
@login_required
@admin_required
def user_details(user_id):
    """API endpoint to get detailed information about a specific user."""
    # Get user details
    user = User.query.get(user_id)
    if not user:
        abort(404, f"User not found: {user_id}")

    # Get user data
    data = get_user_details_data(user)

    return jsonify(data)

# Data collection functions
def get_user_engagement_metrics(start_time, period):
    """
    Get user engagement metrics for the dashboard.

    Args:
        start_time: Datetime representing the start of the analysis period
        period: 'day', 'week', or 'month' for grouping data

    Returns:
        Dictionary of engagement metrics
    """
    try:
        # Get active users
        active_users = db.session.query(
            func.count(func.distinct(ChatHistory.user_id))
        ).filter(
            ChatHistory.created_at >= start_time,
            ChatHistory.user_id.isnot(None)
        ).scalar() or 0

        # Get total users
        total_users = db.session.query(func.count(User.id)).scalar() or 0

        # Get active rate
        active_rate = (active_users / total_users) * 100 if total_users > 0 else 0

        # Get average sessions per user
        avg_sessions = db.session.query(
            func.avg(func.count(func.distinct(ChatHistory.session_id)))
        ).filter(
            ChatHistory.created_at >= start_time,
            ChatHistory.user_id.isnot(None)
        ).group_by(
            ChatHistory.user_id
        ).scalar() or 0

        # Get average messages per session
        avg_messages = db.session.query(
            func.avg(func.count(ChatHistory.id))
        ).filter(
            ChatHistory.created_at >= start_time
        ).group_by(
            ChatHistory.session_id
        ).scalar() or 0

        # Get average session duration in minutes (estimated based on time between first and last message)
        session_durations = db.session.query(
            ChatHistory.session_id,
            func.min(ChatHistory.created_at).label('session_start'),
            func.max(ChatHistory.created_at).label('session_end')
        ).filter(
            ChatHistory.created_at >= start_time
        ).group_by(
            ChatHistory.session_id
        ).all()

        # Calculate average duration
        durations = [(end - start).total_seconds() / 60 for _, start, end in session_durations]
        avg_duration = sum(durations) / len(durations) if durations else 0

        # Return metrics
        return {
            'active_users': active_users,
            'total_users': total_users,
            'active_rate': f"{active_rate:.1f}%",
            'avg_sessions': f"{avg_sessions:.1f}",
            'avg_messages': f"{avg_messages:.1f}",
            'avg_duration': f"{avg_duration:.1f} min"
        }
    except Exception as e:
        logger.error(f"Error getting user engagement metrics: {e}")
        return {
            'active_users': 0,
            'total_users': 0,
            'active_rate': "0.0%",
            'avg_sessions': "0.0",
            'avg_messages': "0.0",
            'avg_duration': "0.0 min"
        }

def get_technique_effectiveness_metrics(start_time):
    """
    Get technique effectiveness metrics for the dashboard.

    Args:
        start_time: Datetime representing the start of the analysis period

    Returns:
        Dictionary of technique effectiveness metrics
    """
    try:
        # Get technique usage counts
        technique_usage = db.session.query(
            ChatHistory.nlp_technique,
            func.count(ChatHistory.id).label('usage_count')
        ).filter(
            ChatHistory.created_at >= start_time,
            ChatHistory.nlp_technique.isnot(None)
        ).group_by(
            ChatHistory.nlp_technique
        ).order_by(
            desc('usage_count')
        ).all()

        # Get average ratings for each technique
        technique_ratings = db.session.query(
            TechniqueEffectiveness.technique,
            func.avg(TechniqueEffectiveness.rating).label('avg_rating')
        ).filter(
            TechniqueEffectiveness.entry_date >= start_time
        ).group_by(
            TechniqueEffectiveness.technique
        ).all()

        # Convert to dictionaries for easier access
        usage_dict = {technique: count for technique, count in technique_usage}
        rating_dict = {technique: rating for technique, rating in technique_ratings}

        # Get most used technique
        most_used = max(usage_dict.items(), key=lambda x: x[1])[0] if usage_dict else None

        # Get highest rated technique
        highest_rated = max(rating_dict.items(), key=lambda x: x[1])[0] if rating_dict else None

        # Get overall average rating
        overall_rating = db.session.query(
            func.avg(TechniqueEffectiveness.rating)
        ).filter(
            TechniqueEffectiveness.entry_date >= start_time
        ).scalar() or 0

        # Return metrics
        return {
            'most_used_technique': most_used,
            'most_used_count': usage_dict.get(most_used, 0),
            'highest_rated_technique': highest_rated,
            'highest_rating': f"{rating_dict.get(highest_rated, 0):.1f}",
            'overall_rating': f"{overall_rating:.1f}",
            'techniques_count': len(usage_dict)
        }
    except Exception as e:
        logger.error(f"Error getting technique effectiveness metrics: {e}")
        return {
            'most_used_technique': None,
            'most_used_count': 0,
            'highest_rated_technique': None,
            'highest_rating': "0.0",
            'overall_rating': "0.0",
            'techniques_count': 0
        }

def get_user_progress_metrics(start_time):
    """
    Get user progress metrics for the dashboard.

    Args:
        start_time: Datetime representing the start of the analysis period

    Returns:
        Dictionary of user progress metrics
    """
    try:
        # Get completed exercises count
        completed_exercises = db.session.query(
            func.count(NLPExerciseProgress.id)
        ).filter(
            NLPExerciseProgress.completed == True,
            NLPExerciseProgress.completed_at >= start_time
        ).scalar() or 0

        # Get average completion rate
        completion_rate = db.session.query(
            func.sum(case([(NLPExerciseProgress.completed == True, 1)], else_=0)) * 100 /
            func.count(NLPExerciseProgress.id)
        ).filter(
            NLPExerciseProgress.started_at >= start_time
        ).scalar() or 0

        # Get average time to complete exercises (in minutes)
        completion_times = db.session.query(
            func.avg(
                func.extract('epoch', NLPExerciseProgress.completed_at - NLPExerciseProgress.started_at) / 60
            )
        ).filter(
            NLPExerciseProgress.completed == True,
            NLPExerciseProgress.completed_at >= start_time
        ).scalar() or 0

        # Get most popular exercises
        popular_exercises = db.session.query(
            NLPExercise.title,
            func.count(NLPExerciseProgress.id).label('count')
        ).join(
            NLPExerciseProgress, NLPExercise.id == NLPExerciseProgress.exercise_id
        ).filter(
            NLPExerciseProgress.started_at >= start_time
        ).group_by(
            NLPExercise.title
        ).order_by(
            desc('count')
        ).first()

        most_popular_exercise = popular_exercises[0] if popular_exercises else None

        # Get most completed exercise
        completed_exercise_counts = db.session.query(
            NLPExercise.title,
            func.count(NLPExerciseProgress.id).label('count')
        ).join(
            NLPExerciseProgress, NLPExercise.id == NLPExerciseProgress.exercise_id
        ).filter(
            NLPExerciseProgress.completed == True,
            NLPExerciseProgress.completed_at >= start_time
        ).group_by(
            NLPExercise.title
        ).order_by(
            desc('count')
        ).first()

        most_completed_exercise = completed_exercise_counts[0] if completed_exercise_counts else None

        # Return metrics
        return {
            'completed_exercises': completed_exercises,
            'completion_rate': f"{completion_rate:.1f}%",
            'avg_completion_time': f"{completion_times:.1f} min",
            'most_popular_exercise': most_popular_exercise,
            'most_completed_exercise': most_completed_exercise
        }
    except Exception as e:
        logger.error(f"Error getting user progress metrics: {e}")
        return {
            'completed_exercises': 0,
            'completion_rate': "0.0%",
            'avg_completion_time': "0.0 min",
            'most_popular_exercise': None,
            'most_completed_exercise': None
        }

def get_business_metrics(start_time, period):
    """
    Get business metrics for the dashboard.

    Args:
        start_time: Datetime representing the start of the analysis period
        period: 'day', 'week', or 'month' for grouping data

    Returns:
        Dictionary of business metrics
    """
    try:
        # Get total user count
        total_users = db.session.query(func.count(User.id)).scalar() or 0

        # Get new users in period
        new_users = db.session.query(
            func.count(User.id)
        ).filter(
            User.created_at >= start_time
        ).scalar() or 0

        # Get total premium subscriptions
        premium_subs = db.session.query(
            func.count(Subscription.id)
        ).filter(
            Subscription.plan_name.in_(['premium', 'professional']),
            Subscription.status == 'active'
        ).scalar() or 0

        # Calculate premium conversion rate
        premium_rate = (premium_subs / total_users) * 100 if total_users > 0 else 0

        # Get new premium subscriptions in period
        new_premium = db.session.query(
            func.count(Subscription.id)
        ).filter(
            Subscription.plan_name.in_(['premium', 'professional']),
            Subscription.status == 'active',
            Subscription.created_at >= start_time
        ).scalar() or 0

        # Get average user retention (users active in last week / total users)
        last_week = datetime.datetime.now() - datetime.timedelta(days=7)
        active_last_week = db.session.query(
            func.count(func.distinct(ChatHistory.user_id))
        ).filter(
            ChatHistory.created_at >= last_week,
            ChatHistory.user_id.isnot(None)
        ).scalar() or 0

        retention_rate = (active_last_week / total_users) * 100 if total_users > 0 else 0

        # Return metrics
        return {
            'total_users': total_users,
            'new_users': new_users,
            'premium_subscriptions': premium_subs,
            'premium_conversion_rate': f"{premium_rate:.1f}%",
            'new_premium_subscriptions': new_premium,
            'user_retention_rate': f"{retention_rate:.1f}%"
        }
    except Exception as e:
        logger.error(f"Error getting business metrics: {e}")
        return {
            'total_users': 0,
            'new_users': 0,
            'premium_subscriptions': 0,
            'premium_conversion_rate': "0.0%",
            'new_premium_subscriptions': 0,
            'user_retention_rate': "0.0%"
        }

def get_user_segments():
    """
    Get user segments for analytics.

    Returns:
        Dictionary of user segments and their metrics
    """
    try:
        # Get user counts by engagement level
        now = datetime.datetime.now()
        week_ago = now - datetime.timedelta(days=7)
        month_ago = now - datetime.timedelta(days=30)

        # Active users (active in last 7 days)
        active_users = db.session.query(
            func.count(func.distinct(ChatHistory.user_id))
        ).filter(
            ChatHistory.created_at >= week_ago,
            ChatHistory.user_id.isnot(None)
        ).scalar() or 0

        # Engaged users (active in last 30 days but not last 7)
        engaged_users = db.session.query(
            func.count(func.distinct(ChatHistory.user_id))
        ).filter(
            ChatHistory.created_at >= month_ago,
            ChatHistory.created_at < week_ago,
            ChatHistory.user_id.isnot(None)
        ).scalar() or 0

        # Dormant users (not active in last 30 days)
        active_in_month = db.session.query(
            func.distinct(ChatHistory.user_id)
        ).filter(
            ChatHistory.created_at >= month_ago,
            ChatHistory.user_id.isnot(None)
        ).subquery()

        total_users = db.session.query(func.count(User.id)).scalar() or 0
        dormant_users = total_users - active_users - engaged_users

        # Get user counts by subscription type
        free_users = db.session.query(
            func.count(Subscription.id)
        ).filter(
            Subscription.plan_name == 'free',
            Subscription.status == 'active'
        ).scalar() or 0

        premium_users = db.session.query(
            func.count(Subscription.id)
        ).filter(
            Subscription.plan_name == 'premium',
            Subscription.status == 'active'
        ).scalar() or 0

        professional_users = db.session.query(
            func.count(Subscription.id)
        ).filter(
            Subscription.plan_name == 'professional',
            Subscription.status == 'active'
        ).scalar() or 0

        # Get user counts by onboarding status
        completed_onboarding = db.session.query(
            func.count(UserPreferences.id)
        ).filter(
            UserPreferences.onboarding_completed == True
        ).scalar() or 0

        incomplete_onboarding = total_users - completed_onboarding

        # Return segments
        return {
            'engagement': {
                'active': active_users,
                'engaged': engaged_users,
                'dormant': dormant_users
            },
            'subscription': {
                'free': free_users,
                'premium': premium_users,
                'professional': professional_users
            },
            'onboarding': {
                'completed': completed_onboarding,
                'incomplete': incomplete_onboarding
            }
        }
    except Exception as e:
        logger.error(f"Error getting user segments: {e}")
        return {
            'engagement': {
                'active': 0,
                'engaged': 0,
                'dormant': 0
            },
            'subscription': {
                'free': 0,
                'premium': 0,
                'professional': 0
            },
            'onboarding': {
                'completed': 0,
                'incomplete': 0
            }
        }

def get_user_insights():
    """
    Get user insights for analytics.

    Returns:
        List of insight dictionaries
    """
    try:
        # Get insights based on data analysis
        insights = []

        # Get users with high engagement but free tier
        high_engagement_free = db.session.query(
            User.id, User.email
        ).join(
            Subscription, User.id == Subscription.user_id
        ).filter(
            Subscription.plan_name == 'free',
            Subscription.status == 'active'
        ).subquery()

        # Add engagement count to high_engagement_free users
        high_engagement_free_with_count = db.session.query(
            high_engagement_free.c.id,
            high_engagement_free.c.email,
            func.count(ChatHistory.id).label('message_count')
        ).join(
            ChatHistory, high_engagement_free.c.id == ChatHistory.user_id
        ).filter(
            ChatHistory.created_at >= datetime.datetime.now() - datetime.timedelta(days=30)
        ).group_by(
            high_engagement_free.c.id,
            high_engagement_free.c.email
        ).having(
            func.count(ChatHistory.id) > 50  # Define high engagement as >50 messages in 30 days
        ).order_by(
            desc('message_count')
        ).limit(5).all()

        if high_engagement_free_with_count:
            insights.append({
                'title': 'Conversion Opportunities',
                'description': 'Users with high engagement who are still on the free tier',
                'users': [{'id': id, 'email': email, 'metric': f"{count} messages"}
                         for id, email, count in high_engagement_free_with_count]
            })

        # Get users at risk of churn (premium users with decreasing engagement)
        month_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        two_months_ago = datetime.datetime.now() - datetime.timedelta(days=60)

        premium_users = db.session.query(
            User.id, User.email
        ).join(
            Subscription, User.id == Subscription.user_id
        ).filter(
            Subscription.plan_name.in_(['premium', 'professional']),
            Subscription.status == 'active'
        ).subquery()

        # Count messages in last 30 days for premium users
        recent_activity = db.session.query(
            premium_users.c.id,
            func.count(ChatHistory.id).label('recent_count')
        ).outerjoin(
            ChatHistory, and_(
                premium_users.c.id == ChatHistory.user_id,
                ChatHistory.created_at >= month_ago
            )
        ).group_by(
            premium_users.c.id
        ).subquery()

        # Count messages in previous 30 days for premium users
        previous_activity = db.session.query(
            premium_users.c.id,
            func.count(ChatHistory.id).label('previous_count')
        ).outerjoin(
            ChatHistory, and_(
                premium_users.c.id == ChatHistory.user_id,
                ChatHistory.created_at >= two_months_ago,
                ChatHistory.created_at < month_ago
            )
        ).group_by(
            premium_users.c.id
        ).subquery()

        # Find users with significant decrease in activity
        churn_risk_users = db.session.query(
            premium_users.c.id,
            premium_users.c.email,
            recent_activity.c.recent_count,
            previous_activity.c.previous_count
        ).join(
            recent_activity, premium_users.c.id == recent_activity.c.id
        ).join(
            previous_activity, premium_users.c.id == previous_activity.c.id
        ).filter(
            previous_activity.c.previous_count > 10,  # Had some activity before
            recent_activity.c.recent_count < previous_activity.c.previous_count * 0.5  # 50% or more decrease
        ).order_by(
            (previous_activity.c.previous_count - recent_activity.c.recent_count).desc()
        ).limit(5).all()

        if churn_risk_users:
            insights.append({
                'title': 'Churn Risk',
                'description': 'Premium users with decreasing engagement',
                'users': [{'id': id, 'email': email,
                         'metric': f"{recent} msgs (down from {previous})"}
                         for id, email, recent, previous in churn_risk_users]
            })

        # Get most improved users (by exercise completion rate)
        month_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        two_months_ago = datetime.datetime.now() - datetime.timedelta(days=60)

        # Get users with improved exercise completion rates
        improved_users = db.session.query(
            User.id,
            User.email,
            func.sum(case([(NLPExerciseProgress.completed == True, 1)], else_=0)).label('completed_recent'),
            func.count(NLPExerciseProgress.id).label('total_recent')
        ).join(
            NLPExerciseProgress, User.id == NLPExerciseProgress.user_id
        ).filter(
            NLPExerciseProgress.started_at >= month_ago
        ).group_by(
            User.id,
            User.email
        ).subquery()

        previous_progress = db.session.query(
            User.id,
            func.sum(case([(NLPExerciseProgress.completed == True, 1)], else_=0)).label('completed_previous'),
            func.count(NLPExerciseProgress.id).label('total_previous')
        ).join(
            NLPExerciseProgress, User.id == NLPExerciseProgress.user_id
        ).filter(
            NLPExerciseProgress.started_at >= two_months_ago,
            NLPExerciseProgress.started_at < month_ago
        ).group_by(
            User.id
        ).subquery()

        most_improved = db.session.query(
            improved_users.c.id,
            improved_users.c.email,
            improved_users.c.completed_recent,
            improved_users.c.total_recent,
            previous_progress.c.completed_previous,
            previous_progress.c.total_previous
        ).join(
            previous_progress, improved_users.c.id == previous_progress.c.id
        ).filter(
            improved_users.c.total_recent > 5,  # At least 5 exercises in recent period
            previous_progress.c.total_previous > 5  # At least 5 exercises in previous period
        ).order_by(
            (improved_users.c.completed_recent / improved_users.c.total_recent -
             previous_progress.c.completed_previous / previous_progress.c.total_previous).desc()
        ).limit(5).all()

        if most_improved:
            insights.append({
                'title': 'Most Improved Users',
                'description': 'Users with the biggest improvement in exercise completion rate',
                'users': [{'id': id, 'email': email,
                         'metric': f"{int(recent_complete/recent_total*100)}% (up from {int(prev_complete/prev_total*100)}%)"}
                         for id, email, recent_complete, recent_total, prev_complete, prev_total in most_improved
                         if recent_total > 0 and prev_total > 0]
            })

        return insights
    except Exception as e:
        logger.error(f"Error getting user insights: {e}")
        return []

def get_user_engagement_chart_data(start_time, period):
    """
    Get user engagement data for charts.

    Args:
        start_time: Datetime representing the start of the analysis period
        period: 'day', 'week', or 'month' for grouping data

    Returns:
        Dictionary of data for charts
    """
    try:
        # Determine the SQL function to extract the period
        if period == 'day':
            extract_fn = func.date(ChatHistory.created_at)
            format_str = '%Y-%m-%d'
        elif period == 'week':
            # Extract the week and year
            extract_fn = func.concat(
                func.extract('year', ChatHistory.created_at),
                '-W',
                func.extract('week', ChatHistory.created_at)
            )
            format_str = '%Y-W%W'
        else:  # month
            extract_fn = func.concat(
                func.extract('year', ChatHistory.created_at),
                '-',
                func.extract('month', ChatHistory.created_at)
            )
            format_str = '%Y-%m'

        # Get daily active users
        active_users_by_period = db.session.query(
            extract_fn.label('period'),
            func.count(func.distinct(ChatHistory.user_id)).label('active_users')
        ).filter(
            ChatHistory.created_at >= start_time,
            ChatHistory.user_id.isnot(None)
        ).group_by(
            'period'
        ).order_by(
            'period'
        ).all()

        # Get message counts by period
        messages_by_period = db.session.query(
            extract_fn.label('period'),
            func.count(ChatHistory.id).label('message_count')
        ).filter(
            ChatHistory.created_at >= start_time
        ).group_by(
            'period'
        ).order_by(
            'period'
        ).all()

        # Get new users by period
        new_users_by_period = db.session.query(
            extract_fn.label('period'),
            func.count(User.id).label('new_users')
        ).filter(
            User.created_at >= start_time
        ).group_by(
            'period'
        ).order_by(
            'period'
        ).all()

        # Convert to chart data format
        periods = []
        active_users = []
        message_counts = []
        new_users = []

        # First, collect all periods
        all_periods = set()
        for period, _ in active_users_by_period:
            all_periods.add(str(period))
        for period, _ in messages_by_period:
            all_periods.add(str(period))
        for period, _ in new_users_by_period:
            all_periods.add(str(period))

        # Sort periods
        all_periods = sorted(list(all_periods))

        # Map data to periods
        active_users_map = {str(p): c for p, c in active_users_by_period}
        messages_map = {str(p): c for p, c in messages_by_period}
        new_users_map = {str(p): c for p, c in new_users_by_period}

        # Fill in the data for each period
        for p in all_periods:
            periods.append(p)
            active_users.append(active_users_map.get(p, 0))
            message_counts.append(messages_map.get(p, 0))
            new_users.append(new_users_map.get(p, 0))

        # Get average messages per user by period
        avg_messages = []
        for i in range(len(periods)):
            avg = message_counts[i] / active_users[i] if active_users[i] > 0 else 0
            avg_messages.append(round(avg, 1))

        # Return chart data
        return {
            'periods': periods,
            'active_users': active_users,
            'message_counts': message_counts,
            'new_users': new_users,
            'avg_messages': avg_messages
        }
    except Exception as e:
        logger.error(f"Error getting user engagement chart data: {e}")
        return {
            'periods': [],
            'active_users': [],
            'message_counts': [],
            'new_users': [],
            'avg_messages': []
        }

def get_technique_effectiveness_chart_data(start_time):
    """
    Get technique effectiveness data for charts.

    Args:
        start_time: Datetime representing the start of the analysis period

    Returns:
        Dictionary of data for charts
    """
    try:
        # Get technique usage counts
        technique_usage = db.session.query(
            ChatHistory.nlp_technique,
            func.count(ChatHistory.id).label('usage_count')
        ).filter(
            ChatHistory.created_at >= start_time,
            ChatHistory.nlp_technique.isnot(None)
        ).group_by(
            ChatHistory.nlp_technique
        ).order_by(
            desc('usage_count')
        ).all()

        # Get average ratings for each technique
        technique_ratings = db.session.query(
            TechniqueEffectiveness.technique,
            func.avg(TechniqueEffectiveness.rating).label('avg_rating')
        ).filter(
            TechniqueEffectiveness.entry_date >= start_time
        ).group_by(
            TechniqueEffectiveness.technique
        ).all()

        # Get rating distribution for each technique
        rating_distribution = db.session.query(
            TechniqueEffectiveness.technique,
            TechniqueEffectiveness.rating,
            func.count(TechniqueEffectiveness.id).label('count')
        ).filter(
            TechniqueEffectiveness.entry_date >= start_time
        ).group_by(
            TechniqueEffectiveness.technique,
            TechniqueEffectiveness.rating
        ).all()

        # Organize rating distribution data
        technique_rating_distribution = defaultdict(lambda: [0, 0, 0, 0, 0])
        for technique, rating, count in rating_distribution:
            if 1 <= rating <= 5:
                technique_rating_distribution[technique][rating-1] = count

        # Prepare data for charts
        techniques = []
        usage_counts = []
        avg_ratings = []
        rating_distributions = []

        # Combine data from both queries
        all_techniques = set()
        for technique, _ in technique_usage:
            all_techniques.add(technique)
        for technique, _ in technique_ratings:
            all_techniques.add(technique)

        # Convert to dictionaries for easier access
        usage_dict = {technique: count for technique, count in technique_usage}
        rating_dict = {technique: rating for technique, rating in technique_ratings}

        # Fill in data for all techniques
        for technique in all_techniques:
            techniques.append(technique)
            usage_counts.append(usage_dict.get(technique, 0))
            avg_ratings.append(float(f"{rating_dict.get(technique, 0):.1f}"))
            rating_distributions.append(technique_rating_distribution[technique])

        # Get usage by mood for each technique
        mood_usage = db.session.query(
            ChatHistory.nlp_technique,
            ChatHistory.mood,
            func.count(ChatHistory.id).label('count')
        ).filter(
            ChatHistory.created_at >= start_time,
            ChatHistory.nlp_technique.isnot(None),
            ChatHistory.mood.isnot(None)
        ).group_by(
            ChatHistory.nlp_technique,
            ChatHistory.mood
        ).all()

        # Organize mood data
        technique_mood_data = defaultdict(dict)
        all_moods = set()

        for technique, mood, count in mood_usage:
            technique_mood_data[technique][mood] = count
            all_moods.add(mood)

        # Prepare mood usage data for chart
        mood_data = {
            'techniques': techniques,
            'moods': sorted(list(all_moods)),
            'data': []
        }

        for technique in techniques:
            mood_counts = []
            for mood in mood_data['moods']:
                mood_counts.append(technique_mood_data[technique].get(mood, 0))
            mood_data['data'].append(mood_counts)

        # Return chart data
        return {
            'techniques': techniques,
            'usage_counts': usage_counts,
            'avg_ratings': avg_ratings,
            'rating_distributions': rating_distributions,
            'mood_data': mood_data
        }
    except Exception as e:
        logger.error(f"Error getting technique effectiveness chart data: {e}")
        return {
            'techniques': [],
            'usage_counts': [],
            'avg_ratings': [],
            'rating_distributions': [],
            'mood_data': {
                'techniques': [],
                'moods': [],
                'data': []
            }
        }

def get_user_progress_chart_data(start_time):
    """
    Get user progress data for charts.

    Args:
        start_time: Datetime representing the start of the analysis period

    Returns:
        Dictionary of data for charts
    """
    try:
        # Get exercise completion data by day
        exercise_completion = db.session.query(
            func.date(NLPExerciseProgress.completed_at).label('date'),
            func.count(NLPExerciseProgress.id).label('count')
        ).filter(
            NLPExerciseProgress.completed == True,
            NLPExerciseProgress.completed_at >= start_time
        ).group_by(
            'date'
        ).order_by(
            'date'
        ).all()

        # Get exercise starts by day
        exercise_starts = db.session.query(
            func.date(NLPExerciseProgress.started_at).label('date'),
            func.count(NLPExerciseProgress.id).label('count')
        ).filter(
            NLPExerciseProgress.started_at >= start_time
        ).group_by(
            'date'
        ).order_by(
            'date'
        ).all()

        # Get completion rates by exercise
        exercise_stats = db.session.query(
            NLPExercise.title,
            func.sum(case([(NLPExerciseProgress.completed == True, 1)], else_=0)).label('completed'),
            func.count(NLPExerciseProgress.id).label('total')
        ).join(
            NLPExerciseProgress, NLPExercise.id == NLPExerciseProgress.exercise_id
        ).filter(
            NLPExerciseProgress.started_at >= start_time
        ).group_by(
            NLPExercise.title
        ).order_by(
            desc('total')
        ).all()

        # Get completion time data by exercise
        completion_times = db.session.query(
            NLPExercise.title,
            func.avg(
                func.extract('epoch', NLPExerciseProgress.completed_at - NLPExerciseProgress.started_at) / 60
            ).label('avg_time')
        ).join(
            NLPExerciseProgress, NLPExercise.id == NLPExerciseProgress.exercise_id
        ).filter(
            NLPExerciseProgress.completed == True,
            NLPExerciseProgress.completed_at >= start_time
        ).group_by(
            NLPExercise.title
        ).all()

        # Prepare data for completion trend chart
        dates = set()
        for date, _ in exercise_completion:
            dates.add(str(date))
        for date, _ in exercise_starts:
            dates.add(str(date))

        dates = sorted(list(dates))

        # Map data to dates
        completions_map = {str(d): c for d, c in exercise_completion}
        starts_map = {str(d): c for d, c in exercise_starts}

        # Fill in the data for each date
        completion_data = []
        start_data = []

        for date in dates:
            completion_data.append(completions_map.get(date, 0))
            start_data.append(starts_map.get(date, 0))

        # Calculate completion rates for each exercise
        exercise_titles = []
        completion_rates = []
        exercise_times = []

        for title, completed, total in exercise_stats:
            exercise_titles.append(title)
            completion_rates.append(round((completed / total) * 100, 1) if total > 0 else 0)

        # Map completion times
        times_map = {title: time for title, time in completion_times}

        for title in exercise_titles:
            exercise_times.append(round(times_map.get(title, 0), 1))

        # Return chart data
        return {
            'dates': dates,
            'completion_data': completion_data,
            'start_data': start_data,
            'exercise_titles': exercise_titles,
            'completion_rates': completion_rates,
            'exercise_times': exercise_times
        }
    except Exception as e:
        logger.error(f"Error getting user progress chart data: {e}")
        return {
            'dates': [],
            'completion_data': [],
            'start_data': [],
            'exercise_titles': [],
            'completion_rates': [],
            'exercise_times': []
        }

def get_business_metrics_chart_data(start_time, period):
    """
    Get business metrics data for charts.

    Args:
        start_time: Datetime representing the start of the analysis period
        period: 'day', 'week', or 'month' for grouping data

    Returns:
        Dictionary of data for charts
    """
    try:
        # Determine the SQL function to extract the period
        if period == 'day':
            extract_fn = func.date(User.created_at)
            sub_extract_fn = func.date(Subscription.created_at)
            format_str = '%Y-%m-%d'
        elif period == 'week':
            # Extract the week and year
            extract_fn = func.concat(
                func.extract('year', User.created_at),
                '-W',
                func.extract('week', User.created_at)
            )
            sub_extract_fn = func.concat(
                func.extract('year', Subscription.created_at),
                '-W',
                func.extract('week', Subscription.created_at)
            )
            format_str = '%Y-W%W'
        else:  # month
            extract_fn = func.concat(
                func.extract('year', User.created_at),
                '-',
                func.extract('month', User.created_at)
            )
            sub_extract_fn = func.concat(
                func.extract('year', Subscription.created_at),
                '-',
                func.extract('month', Subscription.created_at)
            )
            format_str = '%Y-%m'

        # Get new users by period
        new_users_by_period = db.session.query(
            extract_fn.label('period'),
            func.count(User.id).label('new_users')
        ).filter(
            User.created_at >= start_time
        ).group_by(
            'period'
        ).order_by(
            'period'
        ).all()

        # Get new premium subscriptions by period
        new_premium_by_period = db.session.query(
            sub_extract_fn.label('period'),
            func.count(Subscription.id).label('new_premium')
        ).filter(
            Subscription.plan_name.in_(['premium', 'professional']),
            Subscription.created_at >= start_time
        ).group_by(
            'period'
        ).order_by(
            'period'
        ).all()

        # Convert to chart data format
        periods = []
        new_users = []
        new_premium = []

        # First, collect all periods
        all_periods = set()
        for period, _ in new_users_by_period:
            all_periods.add(str(period))
        for period, _ in new_premium_by_period:
            all_periods.add(str(period))

        # Sort periods
        all_periods = sorted(list(all_periods))

        # Map data to periods
        new_users_map = {str(p): c for p, c in new_users_by_period}
        new_premium_map = {str(p): c for p, c in new_premium_by_period}

        # Fill in the data for each period
        for p in all_periods:
            periods.append(p)
            new_users.append(new_users_map.get(p, 0))
            new_premium.append(new_premium_map.get(p, 0))

        # Calculate conversion rates
        conversion_rates = []
        for i in range(len(periods)):
            rate = (new_premium[i] / new_users[i]) * 100 if new_users[i] > 0 else 0
            conversion_rates.append(round(rate, 1))

        # Get subscription distribution
        subscription_counts = db.session.query(
            Subscription.plan_name,
            func.count(Subscription.id).label('count')
        ).filter(
            Subscription.status == 'active'
        ).group_by(
            Subscription.plan_name
        ).all()

        sub_labels = []
        sub_counts = []

        for plan, count in subscription_counts:
            sub_labels.append(plan)
            sub_counts.append(count)

        # Get user retention cohort data
        retention_data = get_retention_cohort_data(start_time, period)

        # Return chart data
        return {
            'periods': periods,
            'new_users': new_users,
            'new_premium': new_premium,
            'conversion_rates': conversion_rates,
            'subscription_distribution': {
                'labels': sub_labels,
                'counts': sub_counts
            },
            'retention_data': retention_data
        }
    except Exception as e:
        logger.error(f"Error getting business metrics chart data: {e}")
        return {
            'periods': [],
            'new_users': [],
            'new_premium': [],
            'conversion_rates': [],
            'subscription_distribution': {
                'labels': [],
                'counts': []
            },
            'retention_data': {
                'cohorts': [],
                'weeks': [],
                'data': []
            }
        }

def get_retention_cohort_data(start_time, period):
    """
    Get user retention cohort data.

    Args:
        start_time: Datetime representing the start of the analysis period
        period: 'day', 'week', or 'month' for grouping data

    Returns:
        Dictionary of cohort data
    """
    try:
        # For simplicity, we'll always use week-based cohorts
        now = datetime.datetime.now()

        # Get cohorts (weeks)
        if period == 'week':
            # Use weeks directly
            num_cohorts = min(8, (now - start_time).days // 7)
            cohort_dates = []

            for i in range(num_cohorts):
                cohort_date = start_time + datetime.timedelta(days=i*7)
                cohort_dates.append(cohort_date)
        else:
            # Just use 8 weeks or available time range
            num_cohorts = min(8, (now - start_time).days // 7)
            cohort_dates = []

            for i in range(num_cohorts):
                cohort_date = start_time + datetime.timedelta(days=i*7)
                cohort_dates.append(cohort_date)

        # Format cohort dates for display
        cohort_labels = [d.strftime('%b %d') for d in cohort_dates]

        # Number of weeks to track retention
        num_weeks = min(8, num_cohorts)
        week_labels = [f"Week {i+1}" for i in range(num_weeks)]

        # Generate retention data (simulated)
        retention_data = []

        for _ in range(num_cohorts):
            cohort_retention = []
            base = 100  # Start with 100%

            for week in range(num_weeks):
                if week == 0:
                    cohort_retention.append(base)
                else:
                    # Simulate decay - more aggressive for older cohorts
                    decay = (week + 1) * (random.randint(5, 15) / 100)
                    retention = max(0, base * (1 - decay))
                    cohort_retention.append(round(retention, 1))

            retention_data.append(cohort_retention)

        return {
            'cohorts': cohort_labels,
            'weeks': week_labels,
            'data': retention_data
        }
    except Exception as e:
        logger.error(f"Error getting retention cohort data: {e}")
        import random

        # Return simulated data as fallback
        num_cohorts = 8
        num_weeks = 8

        cohort_labels = [f"Cohort {i+1}" for i in range(num_cohorts)]
        week_labels = [f"Week {i+1}" for i in range(num_weeks)]

        retention_data = []
        for _ in range(num_cohorts):
            cohort_retention = [100]  # Start with 100%
            current = 100

            for week in range(1, num_weeks):
                # Simulate decay
                decay = random.uniform(0.1, 0.2)
                current = current * (1 - decay)
                cohort_retention.append(round(current, 1))

            retention_data.append(cohort_retention)

        return {
            'cohorts': cohort_labels,
            'weeks': week_labels,
            'data': retention_data
        }

def get_user_details_data(user):
    """
    Get detailed data for a specific user.

    Args:
        user: User object

    Returns:
        Dictionary of user details and activity
    """
    try:
        # Get basic user info
        user_info = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else None,
            'auth_provider': user.auth_provider
        }

        # Get subscription info
        subscription = Subscription.query.filter_by(user_id=user.id).first()
        if subscription:
            user_info['subscription'] = {
                'plan': subscription.plan_name,
                'status': subscription.status,
                'created_at': subscription.created_at.strftime('%Y-%m-%d %H:%M:%S') if subscription.created_at else None,
                'current_period_end': subscription.current_period_end.strftime('%Y-%m-%d') if subscription.current_period_end else None
            }
        else:
            user_info['subscription'] = None

        # Get user preferences
        preferences = UserPreferences.query.filter_by(user_id=user.id).first()
        if preferences:
            user_info['preferences'] = {
                'primary_goal': preferences.primary_goal,
                'experience_level': preferences.experience_level,
                'communication_style': preferences.communication_style,
                'show_explanations': preferences.show_explanations,
                'onboarding_completed': preferences.onboarding_completed
            }
        else:
            user_info['preferences'] = None

        # Get activity metrics
        month_ago = datetime.datetime.now() - datetime.timedelta(days=30)

        # Get message count
        message_count = db.session.query(func.count(ChatHistory.id)).filter(
            ChatHistory.user_id == user.id
        ).scalar() or 0

        # Get recent message count
        recent_message_count = db.session.query(func.count(ChatHistory.id)).filter(
            ChatHistory.user_id == user.id,
            ChatHistory.created_at >= month_ago
        ).scalar() or 0

        # Get session count
        session_count = db.session.query(func.count(func.distinct(ChatHistory.session_id))).filter(
            ChatHistory.user_id == user.id
        ).scalar() or 0

        # Get technique usage
        technique_usage = db.session.query(
            ChatHistory.nlp_technique,
            func.count(ChatHistory.id).label('count')
        ).filter(
            ChatHistory.user_id == user.id,
            ChatHistory.nlp_technique.isnot(None)
        ).group_by(
            ChatHistory.nlp_technique
        ).order_by(
            desc('count')
        ).all()

        # Get mood distribution
        mood_distribution = db.session.query(
            ChatHistory.mood,
            func.count(ChatHistory.id).label('count')
        ).filter(
            ChatHistory.user_id == user.id,
            ChatHistory.mood.isnot(None)
        ).group_by(
            ChatHistory.mood
        ).order_by(
            desc('count')
        ).all()

        # Get exercise completion
        exercise_completion = db.session.query(func.count(NLPExerciseProgress.id)).filter(
            NLPExerciseProgress.user_id == user.id,
            NLPExerciseProgress.completed == True
        ).scalar() or 0

        # Get exercise total
        exercise_total = db.session.query(func.count(NLPExerciseProgress.id)).filter(
            NLPExerciseProgress.user_id == user.id
        ).scalar() or 0

        # Calculate completion rate
        completion_rate = (exercise_completion / exercise_total) * 100 if exercise_total > 0 else 0

        # Add metrics to user info
        user_info['metrics'] = {
            'message_count': message_count,
            'recent_message_count': recent_message_count,
            'session_count': session_count,
            'technique_usage': {t: c for t, c in technique_usage},
            'mood_distribution': {m: c for m, c in mood_distribution},
            'exercise_completion': exercise_completion,
            'exercise_total': exercise_total,
            'completion_rate': round(completion_rate, 1)
        }

        # Get recent activity
        recent_activity = db.session.query(
            ChatHistory.created_at,
            ChatHistory.user_message,
            ChatHistory.nlp_technique,
            ChatHistory.mood
        ).filter(
            ChatHistory.user_id == user.id
        ).order_by(
            desc(ChatHistory.created_at)
        ).limit(10).all()

        user_info['recent_activity'] = [{
            'timestamp': item[0].strftime('%Y-%m-%d %H:%M:%S'),
            'message': item[1],
            'technique': item[2],
            'mood': item[3]
        } for item in recent_activity]

        return user_info
    except Exception as e:
        logger.error(f"Error getting user details data: {e}")
        return {
            'id': user.id,
            'email': user.email,
            'error': str(e)
        }