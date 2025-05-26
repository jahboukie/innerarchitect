import json
import uuid
import logging
from flask import (
    Blueprint, render_template, request, jsonify, session, flash,
    redirect, url_for, current_app, g
)
from flask_login import current_user, login_required

from app import db
from app.models import User, ChatHistory, ConversationContext, ConversationMemoryItem
from app.nlp.techniques import (
    apply_technique, suggest_technique, detect_user_mood, 
    get_technique_details, get_all_techniques
)
from app.nlp.conversation_context import (
    get_or_create_context, create_new_context, add_message_to_context,
    enhance_prompt_with_context, update_context_summary, consolidate_memories
)
from app.utils.subscription import (
    check_quota_available, increment_usage_quota, check_feature_access
)

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
chat = Blueprint('chat', __name__)

@chat.route('/')
def index():
    """Chat interface main page."""
    # Ensure there's a session ID
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    # Get or create a conversation context
    user_id = current_user.id if current_user.is_authenticated else None
    context = get_or_create_context(user_id, session['session_id'])
    
    # Get all available techniques
    techniques = get_all_techniques()
    
    # Check if user has premium access
    has_premium = False
    if current_user.is_authenticated:
        has_premium = check_feature_access(current_user.id, 'advanced_nlp')
    
    return render_template(
        'chat.html',
        context=context,
        techniques=techniques,
        has_premium=has_premium
    )

@chat.route('/new-conversation', methods=['POST'])
def new_conversation():
    """Start a new conversation."""
    # Ensure there's a session ID
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    # Create a new conversation context
    user_id = current_user.id if current_user.is_authenticated else None
    context = create_new_context(user_id, session['session_id'])
    
    return jsonify({
        'success': True,
        'context_id': context.id,
        'title': context.title
    })

@chat.route('/message', methods=['POST'])
def send_message():
    """Process a user message and generate a response."""
    try:
        # Get request data
        data = request.json
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({
                'success': False,
                'error': 'Message cannot be empty'
            }), 400
        
        # Get session ID or create one
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        
        # Get user ID if authenticated
        user_id = current_user.id if current_user.is_authenticated else None
        
        # Check if user has available quota
        quota_available, quota_message = check_quota_available(
            user_id=user_id,
            browser_session_id=session.get('browser_session_id'),
            quota_type='daily_messages'
        )
        
        if not quota_available:
            return jsonify({
                'success': False,
                'error': 'Message quota exceeded',
                'message': quota_message
            }), 403
        
        # Get or create conversation context
        context = get_or_create_context(user_id, session['session_id'])
        
        # Detect user's mood
        mood = detect_user_mood(user_message)
        
        # Get specified technique or suggest one based on the message
        technique_id = data.get('technique')
        if not technique_id:
            # Get user history for better technique suggestion
            user_history = None
            if user_id:
                # In a real implementation, fetch user's technique ratings
                user_history = []
            
            technique_id = suggest_technique(user_message, user_history)
        
        # Get user preferences if available
        user_preferences = None
        if user_id:
            # In a real implementation, fetch from database
            user_preferences = {
                'experience_level': 'beginner',
                'show_explanations': True,
                'communication_style': 'supportive'
            }
        
        # Check if the technique is premium and if the user has access
        premium_techniques = ['pattern_interruption', 'anchoring', 'future_pacing', 'sensory_language', 'meta_model']
        if technique_id in premium_techniques:
            has_access = False
            if user_id:
                has_access = check_feature_access(user_id, 'advanced_nlp')
            
            if not has_access:
                # Fallback to a non-premium technique
                technique_id = 'reframing'
                logger.info(f"User does not have access to premium technique {technique_id}, falling back to reframing")
        
        # Enhance the prompt with conversation context
        enhanced_message, conversation_history = enhance_prompt_with_context(
            context.id, 
            user_message,
            max_history=5,
            include_memories=True
        )
        
        # Apply the NLP technique to generate a response
        ai_response, metadata = apply_technique(
            technique_id,
            enhanced_message,
            conversation_history,
            user_preferences
        )
        
        # Add message to conversation context
        chat_entry = add_message_to_context(
            context.id,
            user_message,
            ai_response,
            user_id,
            session['session_id'],
            mood,
            technique_id
        )
        
        # Increment usage quota
        increment_usage_quota(
            user_id=user_id,
            browser_session_id=session.get('browser_session_id'),
            quota_type='daily_messages'
        )
        
        # Update context summary and memories asynchronously
        # In a real implementation, this would be done in a background task
        try:
            update_context_summary(context.id)
            consolidate_memories(context.id)
        except Exception as e:
            logger.error(f"Error updating context: {str(e)}")
        
        # Get technique details for response
        technique_details = get_technique_details(technique_id)
        
        return jsonify({
            'success': True,
            'message': ai_response,
            'message_id': chat_entry.id,
            'technique': {
                'id': technique_id,
                'name': technique_details.get('name', 'Unknown Technique'),
                'description': technique_details.get('description', '')
            },
            'mood': mood,
            'timestamp': chat_entry.created_at.isoformat()
        })
        
    except Exception as e:
        logger.exception(f"Error processing message: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing your message'
        }), 500

@chat.route('/history')
def get_history():
    """Get chat history for the current session."""
    # Ensure there's a session ID
    if 'session_id' not in session:
        return jsonify({
            'success': False,
            'error': 'No active session'
        }), 400
    
    # Get user ID if authenticated
    user_id = current_user.id if current_user.is_authenticated else None
    
    try:
        # Get active context
        context = get_or_create_context(user_id, session['session_id'])
        
        # Get chat history for this context
        history = ChatHistory.query.filter_by(context_id=context.id) \
            .order_by(ChatHistory.created_at.asc()) \
            .all()
        
        # Format history for response
        formatted_history = []
        for entry in history:
            formatted_history.append({
                'id': entry.id,
                'user_message': entry.user_message,
                'ai_response': entry.ai_response,
                'mood': entry.mood,
                'technique': entry.nlp_technique,
                'timestamp': entry.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'history': formatted_history,
            'context': {
                'id': context.id,
                'title': context.title,
                'summary': context.summary
            }
        })
        
    except Exception as e:
        logger.exception(f"Error fetching chat history: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while fetching chat history'
        }), 500

@chat.route('/contexts')
def get_contexts():
    """Get all conversation contexts for the current user."""
    # Get user ID if authenticated
    if not current_user.is_authenticated:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    try:
        # Get all contexts for this user
        contexts = ConversationContext.query.filter_by(user_id=current_user.id) \
            .order_by(ConversationContext.updated_at.desc()) \
            .all()
        
        # Format contexts for response
        formatted_contexts = []
        for context in contexts:
            # Get message count
            message_count = ChatHistory.query.filter_by(context_id=context.id).count()
            
            formatted_contexts.append({
                'id': context.id,
                'title': context.title,
                'summary': context.summary,
                'is_active': context.is_active,
                'message_count': message_count,
                'created_at': context.created_at.isoformat(),
                'updated_at': context.updated_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'contexts': formatted_contexts
        })
        
    except Exception as e:
        logger.exception(f"Error fetching contexts: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while fetching contexts'
        }), 500

@chat.route('/switch-context/<int:context_id>', methods=['POST'])
def switch_context(context_id):
    """Switch to a different conversation context."""
    # Get user ID if authenticated
    if not current_user.is_authenticated:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    try:
        # Check if context exists and belongs to user
        context = ConversationContext.query.filter_by(
            id=context_id,
            user_id=current_user.id
        ).first()
        
        if not context:
            return jsonify({
                'success': False,
                'error': 'Context not found'
            }), 404
        
        # Deactivate all other contexts
        ConversationContext.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).update({'is_active': False})
        
        # Activate this context
        context.is_active = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'context': {
                'id': context.id,
                'title': context.title,
                'summary': context.summary
            }
        })
        
    except Exception as e:
        logger.exception(f"Error switching context: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'An error occurred while switching context'
        }), 500

@chat.route('/delete-context/<int:context_id>', methods=['POST'])
def delete_context(context_id):
    """Delete a conversation context."""
    # Get user ID if authenticated
    if not current_user.is_authenticated:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    try:
        # Check if context exists and belongs to user
        context = ConversationContext.query.filter_by(
            id=context_id,
            user_id=current_user.id
        ).first()
        
        if not context:
            return jsonify({
                'success': False,
                'error': 'Context not found'
            }), 404
        
        # If this is the active context, create a new one
        is_active = context.is_active
        
        # Delete related memories
        ConversationMemoryItem.query.filter_by(context_id=context_id).delete()
        
        # Delete related chat history
        ChatHistory.query.filter_by(context_id=context_id).delete()
        
        # Delete the context
        db.session.delete(context)
        db.session.commit()
        
        # If we deleted the active context, create a new one
        if is_active:
            new_context = create_new_context(current_user.id, session['session_id'])
            
            return jsonify({
                'success': True,
                'new_context': {
                    'id': new_context.id,
                    'title': new_context.title
                }
            })
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.exception(f"Error deleting context: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'An error occurred while deleting context'
        }), 500

@chat.route('/rename-context/<int:context_id>', methods=['POST'])
def rename_context(context_id):
    """Rename a conversation context."""
    # Get request data
    data = request.json
    new_title = data.get('title', '').strip()
    
    if not new_title:
        return jsonify({
            'success': False,
            'error': 'Title cannot be empty'
        }), 400
    
    # Get user ID if authenticated
    if not current_user.is_authenticated:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    try:
        # Check if context exists and belongs to user
        context = ConversationContext.query.filter_by(
            id=context_id,
            user_id=current_user.id
        ).first()
        
        if not context:
            return jsonify({
                'success': False,
                'error': 'Context not found'
            }), 404
        
        # Update title
        context.title = new_title
        db.session.commit()
        
        return jsonify({
            'success': True,
            'title': new_title
        })
        
    except Exception as e:
        logger.exception(f"Error renaming context: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'An error occurred while renaming context'
        }), 500