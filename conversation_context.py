"""
Conversation Context Module for The Inner Architect

This module manages conversation context across multiple messages,
enabling the AI to maintain memory of previous interactions and provide
more personalized and coherent responses.
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union, Set

from sqlalchemy.exc import SQLAlchemyError
from database import db, safe_commit, create_model, update_model, safe_query
from models import ConversationContext, ConversationMemoryItem, ChatHistory, User
from logging_config import get_logger, error, debug, warning, info

# Initialize OpenAI for memory extraction and context summarization
from openai import OpenAI
import os
from language_util import safe_chat_completion

# Emotional sentiment keywords for better context matching
SENTIMENT_KEYWORDS = {
    'happy': ['happy', 'joy', 'excited', 'pleased', 'delighted', 'content', 'satisfied', 'glad'],
    'sad': ['sad', 'unhappy', 'depressed', 'upset', 'disappointed', 'down', 'gloomy', 'miserable'],
    'angry': ['angry', 'frustrated', 'annoyed', 'irritated', 'mad', 'outraged', 'furious'],
    'anxious': ['anxious', 'worried', 'nervous', 'concerned', 'afraid', 'scared', 'fearful', 'stressed'],
    'confused': ['confused', 'unsure', 'uncertain', 'lost', 'puzzled', 'perplexed', 'disoriented'],
    'hopeful': ['hopeful', 'optimistic', 'positive', 'encouraged', 'confident', 'expectant']
}

# Get module-specific logger
logger = get_logger('conversation_context')

def analyze_message_semantic(message: str) -> Tuple[Optional[str], List[str]]:
    """
    Analyze a message to detect sentiment and extract key topics.
    
    Args:
        message: The message to analyze
        
    Returns:
        Tuple of (detected sentiment or None, list of key topics)
    """
    # Quick keyword-based sentiment detection for faster processing
    message_lower = message.lower()
    
    # Check for emotional keywords in the message
    detected_sentiment = None
    for sentiment, keywords in SENTIMENT_KEYWORDS.items():
        if any(keyword in message_lower for keyword in keywords):
            detected_sentiment = sentiment
            break
    
    # Extract simple topics using keyword frequency (basic approach)
    # Remove common stop words
    stop_words = {'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 
                 "you're", "you've", "you'll", "you'd", 'your', 'yours', 'yourself', 
                 'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her', 
                 'hers', 'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 
                 'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 
                 'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was',
                 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 
                 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 
                 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 
                 'about', 'against', 'between', 'into', 'through', 'during', 'before', 
                 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 
                 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 
                 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 
                 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 
                 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 
                 'will', 'just', 'don', "don't", 'should', "should've", 'now', 'd', 'll',
                 'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't", 'couldn', "couldn't", 
                 'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 
                 'haven', "haven't", 'isn', "isn't", 'ma', 'mightn', "mightn't", 'mustn', 
                 "mustn't", 'needn', "needn't", 'shan', "shan't", 'shouldn', "shouldn't", 
                 'wasn', "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't"}
    
    # Tokenize and extract potential topics
    words = re.findall(r'\b\w+\b', message_lower)
    word_counts = {}
    
    for word in words:
        if word not in stop_words and len(word) > 3:  # Skip stop words and very short words
            word_counts[word] = word_counts.get(word, 0) + 1
    
    # Get the top topics by frequency
    topics = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    top_topics = [word for word, count in topics[:5]]
    
    return detected_sentiment, top_topics


def sentiment_in_text(text: str) -> str:
    """
    Detect sentiment keywords in a text.
    
    Args:
        text: The text to analyze
        
    Returns:
        Comma-separated string of detected sentiments or 'neutral'
    """
    text_lower = text.lower()
    detected = []
    
    for sentiment, keywords in SENTIMENT_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            detected.append(sentiment)
    
    if detected:
        return ', '.join(detected)
    else:
        return 'neutral'

# Maximum number of messages to include in context
MAX_CONTEXT_MESSAGES = 15  # Increased from 10 for better conversation flow

# Maximum number of memory items to include in a prompt
MAX_MEMORY_ITEMS = 8  # Increased from 5 for more comprehensive memory

# Memory relevance decay factor (per day)
MEMORY_DECAY_FACTOR = 0.95  # Increased from 0.9 for slower memory decay

# User preference weight multiplier (increases priority of preference memories)
USER_PREFERENCE_WEIGHT = 1.5


def get_or_create_context(user_id: Optional[str], session_id: str) -> Optional[ConversationContext]:
    """
    Get the active conversation context for a user or session, or create one if none exists.
    
    Args:
        user_id: The user ID if authenticated, None for anonymous users
        session_id: The browser session ID for anonymous users
        
    Returns:
        The active ConversationContext object or None if creation failed
    """
    try:
        # Try to find an active context
        query = ConversationContext.query.filter_by(
            session_id=session_id,
            is_active=True
        )
        
        if user_id:
            query = query.filter_by(user_id=user_id)
            
        context = query.first()
        
        # If no active context, create one
        if not context:
            context_data = {
                'user_id': user_id,
                'session_id': session_id,
                'is_active': True,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            context = create_model(ConversationContext, context_data)
            info(f"Created new conversation context for {'user '+user_id if user_id else 'session '+session_id}")
            
        return context
        
    except Exception as e:
        error_type = type(e).__name__
        error(f"Error ({error_type}) retrieving conversation context: {str(e)}")
        return None


def create_new_context(user_id: Optional[str], session_id: str, transition_message: Optional[str] = None) -> Optional[ConversationContext]:
    """
    Create a new conversation context and deactivate previous ones.
    This helps manage context switching in conversations.
    
    Args:
        user_id: The user ID if authenticated, None for anonymous users
        session_id: The browser session ID for anonymous users
        transition_message: Optional message explaining the context transition
        
    Returns:
        The new ConversationContext object or None if creation failed
    """
    try:
        # Deactivate all existing contexts for this user/session
        query = ConversationContext.query.filter_by(session_id=session_id, is_active=True)
        if user_id:
            query = query.filter_by(user_id=user_id)
            
        old_contexts = query.all()
        
        # Get the most recent active context
        old_context = None
        if old_contexts:
            # Sort by updated_at in descending order
            old_contexts.sort(key=lambda x: x.updated_at, reverse=True)
            old_context = old_contexts[0]
            
            # Deactivate all old contexts
            for context in old_contexts:
                update_data = {'is_active': False}
                update_model(context, update_data)
                
            info(f"Deactivated {len(old_contexts)} old contexts for {'user '+user_id if user_id else 'session '+session_id}")
        
        # Create new context
        context_data = {
            'user_id': user_id,
            'session_id': session_id,
            'is_active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        new_context = create_model(ConversationContext, context_data)
        if not new_context:
            error("Failed to create new context")
            return None
            
        info(f"Created new conversation context for {'user '+user_id if user_id else 'session '+session_id}")
        
        # If there was a previous context and a transition message is provided,
        # transfer some key memories to ensure continuity
        if old_context and transition_message:
            transfer_key_memories(old_context.id, new_context.id, transition_message)
            
        return new_context
        
    except Exception as e:
        error_type = type(e).__name__
        error(f"Error ({error_type}) creating new conversation context: {str(e)}")
        return None


def transfer_key_memories(old_context_id: int, new_context_id: int, transition_message: str) -> int:
    """
    Transfer important memories from old context to new context.
    This ensures conversation continuity during context switching.
    
    Args:
        old_context_id: The ID of the old context
        new_context_id: The ID of the new context
        transition_message: Message describing the transition
        
    Returns:
        Number of memories transferred
    """
    try:
        # Get key memories from the old context
        memories = get_relevant_memories(old_context_id, transition_message, limit=3)
        
        if not memories:
            return 0
            
        # Transfer these memories to the new context
        transferred_count = 0
        for memory in memories:
            # Create a copy of the memory in the new context
            memory_data = {
                'context_id': new_context_id,
                'memory_type': memory['memory_type'],
                'content': memory['content'],
                'confidence': memory['confidence'],
                'relevance': memory['relevance'],
                'created_at': datetime.utcnow()
            }
            
            new_memory = create_model(ConversationMemoryItem, memory_data)
            if new_memory:
                transferred_count += 1
                
        if transferred_count > 0:
            info(f"Transferred {transferred_count} memories from context {old_context_id} to {new_context_id}")
            
        return transferred_count
        
    except Exception as e:
        error_type = type(e).__name__
        error(f"Error ({error_type}) transferring memories: {str(e)}")
        return 0


def detect_context_switch(current_message: str, recent_messages: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """
    Detect whether a conversation has switched to a new topic or context.
    
    Args:
        current_message: The current user message
        recent_messages: List of recent message dictionaries
        
    Returns:
        Tuple of (should_switch_context, transition_message or None)
    """
    if not recent_messages:
        return False, None
        
    # Need at least a few messages to detect a topic change
    if len(recent_messages) < 2:
        return False, None
        
    # Combine recent messages for context
    recent_user_messages = "\n".join([
        f"User: {msg['user_message']}" 
        for msg in recent_messages[-3:] if 'user_message' in msg
    ])
    
    prompt = f"""Analyze the following conversation and determine if the latest message represents a significant shift in topic that warrants starting a new conversation context.

Previous messages:
{recent_user_messages}

Current message:
{current_message}

A new context should be created if the current message:
1. Starts a completely new topic unrelated to previous messages
2. Explicitly indicates the user wants to talk about something new
3. Shows a major shift in the conversation's direction or purpose

Respond with JSON:
{{
  "should_create_new_context": true/false,
  "reason": "Brief explanation of your decision",
  "transition_message": "If creating new context, a message describing what key information should be carried forward"
}}"""

    messages = [
        {"role": "system", "content": "You analyze conversations to detect topic and context changes."},
        {"role": "user", "content": prompt}
    ]
    
    response = safe_chat_completion(
        messages=messages,
        max_tokens=300,
        temperature=0.3,
        fallback_response=""
    )
    
    # Parse and extract decision
    try:
        result = json.loads(response)
        should_switch = result.get('should_create_new_context', False)
        transition_message = result.get('transition_message', None)
        reason = result.get('reason', 'No reason provided')
        
        if should_switch:
            info(f"Context switch detected: {reason}")
            return True, transition_message
        else:
            return False, None
            
    except json.JSONDecodeError:
        warning("Failed to parse context switch response")
        return False, None
    except Exception as e:
        warning(f"Error detecting context switch: {str(e)}")
        return False, None


def add_message_to_context(
    context_id: int, 
    message_id: int,
    extract_memories: bool = True
) -> bool:
    """
    Add a chat message to a conversation context and extract memories.
    
    Args:
        context_id: The context ID
        message_id: The chat message ID
        extract_memories: Whether to extract memory items from the message
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get the message
        message = ChatHistory.query.get(message_id)
        if not message:
            warning(f"Message {message_id} not found")
            return False
            
        # Update the message with the context ID
        update_data = {'context_id': context_id}
        success = update_model(message, update_data)
        
        if not success:
            warning(f"Failed to update message {message_id} with context {context_id}")
            return False
        
        # Extract memories if requested
        if extract_memories:
            # Don't wait for memory extraction to complete
            extract_memories_from_message(context_id, message_id)
            
        return True
        
    except Exception as e:
        error_type = type(e).__name__
        error(f"Error ({error_type}) adding message to context: {str(e)}")
        return False


def get_context_messages(context_id: int, limit: int = MAX_CONTEXT_MESSAGES) -> List[Dict[str, Any]]:
    """
    Get recent messages for a conversation context.
    
    Args:
        context_id: The context ID
        limit: Maximum number of messages to retrieve
        
    Returns:
        List of message dictionaries with user_message, ai_response, and created_at
    """
    try:
        messages = ChatHistory.query.filter_by(context_id=context_id) \
            .order_by(ChatHistory.created_at.desc()) \
            .limit(limit) \
            .all()
            
        # Convert to dictionaries and reverse to chronological order
        message_dicts = [{
            'id': msg.id,
            'user_message': msg.user_message,
            'ai_response': msg.ai_response,
            'mood': msg.mood,
            'nlp_technique': msg.nlp_technique,
            'created_at': msg.created_at.isoformat()
        } for msg in messages]
        
        return list(reversed(message_dicts))
        
    except Exception as e:
        error_type = type(e).__name__
        error(f"Error ({error_type}) retrieving context messages: {str(e)}")
        return []


def extract_memories_from_message(context_id: int, message_id: int) -> List[ConversationMemoryItem]:
    """
    Extract memory items from a chat message using OpenAI.
    
    Args:
        context_id: The context ID
        message_id: The chat message ID
        
    Returns:
        List of created ConversationMemoryItem objects or empty list on failure
    """
    try:
        message = ChatHistory.query.get(message_id)
        if not message:
            warning(f"Message {message_id} not found for memory extraction")
            return []
        
        # Prepare the prompt for memory extraction
        prompt = f"""Extract key information from this conversation that would be useful to remember for future interactions. 
Focus on facts, preferences, goals, concerns, and important life details.

User message: {message.user_message}

AI response: {message.ai_response}

Extract 1-3 memory items formatted as JSON array with these fields:
- memory_type: "fact" (objective information), "preference" (likes/dislikes), "concern" (worries), "goal" (aspirations), or "belief" (perspective)  
- content: The specific memory in a concise statement
- confidence: Number from 0.0-1.0 indicating confidence in this extraction (be conservative)

JSON:"""

        messages = [
            {"role": "system", "content": "You extract key information from conversations to help build memory for an AI assistant."},
            {"role": "user", "content": prompt}
        ]
        
        response = safe_chat_completion(
            messages=messages,
            max_tokens=500,
            temperature=0.3,
            fallback_response="[]"
        )
        
        # Parse response as JSON array
        try:
            memories = json.loads(response)
            if not isinstance(memories, list):
                warning(f"Invalid memory extraction format, expected list but got {type(memories).__name__}")
                return []
        except json.JSONDecodeError as e:
            warning(f"Failed to parse memory extraction response: {str(e)}")
            return []
        
        # Create memory items
        created_items = []
        for memory in memories:
            try:
                memory_data = {
                    'context_id': context_id,
                    'memory_type': memory.get('memory_type', 'fact'),
                    'content': memory.get('content', ''),
                    'source_message_id': message_id,
                    'confidence': float(memory.get('confidence', 0.8)),
                    'relevance': 1.0,  # Start with full relevance
                    'created_at': datetime.utcnow()
                }
                
                memory_item = create_model(ConversationMemoryItem, memory_data)
                if memory_item:
                    created_items.append(memory_item)
                
            except (ValueError, TypeError) as e:
                warning(f"Invalid memory item format: {str(e)}")
                continue
        
        info(f"Extracted {len(created_items)} memory items from message {message_id}")
        return created_items
        
    except Exception as e:
        error_type = type(e).__name__
        error(f"Error ({error_type}) extracting memories from message: {str(e)}")
        return []


def get_relevant_memories(
    context_id: int, 
    current_message: str, 
    limit: int = MAX_MEMORY_ITEMS
) -> List[Dict[str, Any]]:
    """
    Get memory items relevant to the current message.
    
    Args:
        context_id: The context ID
        current_message: The current user message
        limit: Maximum number of items to retrieve
        
    Returns:
        List of memory dictionaries with memory_type, content, and relevance
    """
    try:
        # Analyze user message for sentiment and key topics
        message_sentiment, message_topics = analyze_message_semantic(current_message)
        
        # Get memory items sorted by relevance * confidence
        # If we found sentiment, prioritize memories matching that sentiment
        query = ConversationMemoryItem.query.filter_by(context_id=context_id)
        
        # Apply special weighting for preferences
        memory_items = query.all()
        
        # If no memory items found, return empty list
        if not memory_items:
            return []
            
        # Apply custom weighting and scoring
        weighted_items = []
        for item in memory_items:
            # Base score is relevance * confidence
            base_score = item.relevance * item.confidence
            
            # Apply preference boosting for preference type memories
            if item.memory_type == 'preference':
                base_score *= USER_PREFERENCE_WEIGHT
                
            # Apply recency boost (newer memories get priority)
            days_old = (datetime.utcnow() - item.created_at).days
            recency_factor = max(0.5, 1.0 - (days_old * 0.01))  # Gentle decay
            
            # Apply sentiment matching bonus if we have detected sentiment
            sentiment_match = 1.0
            if message_sentiment and message_sentiment in item.content.lower():
                sentiment_match = 1.25  # 25% boost for emotion-matching memories
                
            # Combine all factors
            final_score = base_score * recency_factor * sentiment_match
            
            weighted_items.append((item, final_score))
        
        # Sort by final score descending
        weighted_items.sort(key=lambda x: x[1], reverse=True)
        
        # If we have fewer items than limit, return all of them
        if len(weighted_items) <= limit:
            return [{
                'memory_type': item.memory_type,
                'content': item.content,
                'confidence': item.confidence,
                'relevance': item.relevance,
                'created_at': item.created_at.isoformat() if item.created_at else None
            } for item, _ in weighted_items]
        
        # Pre-select items based on our weighting system
        selected_items = weighted_items[:limit]
        return [{
            'memory_type': item.memory_type,
            'content': item.content, 
            'confidence': item.confidence,
            'relevance': item.relevance,
            'created_at': item.created_at.isoformat() if item.created_at else None
        } for item, _ in selected_items]
        # Parse response as a list of indices
        try:
            # Extract indices from response
            response_text = response.strip()
            indices = []
            
            # Enhanced parsing that handles different formats
            patterns = [r'\d+']  # Look for numbers
            for pattern in patterns:
                for match in re.finditer(pattern, response_text):
                    try:
                        idx = int(match.group()) - 1  # Convert to 0-based index
                        if 0 <= idx < len(memory_items) and idx not in indices:
                            indices.append(idx)
                    except ValueError:
                        continue
            
            # If we found indices and have enough, use them
            if indices and len(indices) >= min(3, limit):
                # Update the last_used_at timestamp for these memory items
                for idx in indices[:limit]:
                    memory_item = memory_items[idx]
                    update_data = {'last_used_at': datetime.utcnow()}
                    success = update_model(memory_item, update_data)
                    if not success:
                        warning(f"Failed to update last_used_at for memory item {memory_item.id}")
                
                # Return the selected items
                return [{
                    'memory_type': memory_items[idx].memory_type,
                    'content': memory_items[idx].content,
                    'confidence': memory_items[idx].confidence,
                    'relevance': memory_items[idx].relevance,
                    'created_at': memory_items[idx].created_at.isoformat() if memory_items[idx].created_at else None
                } for idx in indices[:limit]]
            
            # Fallback to simpler approach - prioritize memory types based on message
            prioritized_items = []
            
            # Check if message contains questions or concerns
            if any(q in current_message.lower() for q in ['?', 'how', 'what', 'why', 'when', 'where', 'who', 'which', 'can you', 'could you']):
                # Prioritize facts for questions
                for item in memory_items:
                    if item.memory_type == 'fact':
                        prioritized_items.append(item)
            
            # Check if message expresses emotional content
            emotion_keywords = ['feel', 'feeling', 'felt', 'sad', 'happy', 'angry', 'upset', 'excited', 'worried', 'anxious']
            if any(emotion in current_message.lower() for emotion in emotion_keywords):
                # Prioritize preferences and concerns for emotional context
                for item in memory_items:
                    if item.memory_type in ['preference', 'concern']:
                        prioritized_items.append(item)
            
            # Add goals for forward-looking messages  
            future_keywords = ['want', 'hope', 'plan', 'future', 'will', 'going to', 'intend', 'aim']
            if any(future in current_message.lower() for future in future_keywords):
                for item in memory_items:
                    if item.memory_type == 'goal':
                        prioritized_items.append(item)
            
            # Add remaining items to fill up to the limit
            remaining_items = [item for item in memory_items if item not in prioritized_items]
            combined_items = prioritized_items + remaining_items
            
            # Return the combined and deduplicated items up to the limit
            selected_items = []
            seen_ids = set()
            for item in combined_items:
                if item.id not in seen_ids and len(selected_items) < limit:
                    selected_items.append(item)
                    seen_ids.add(item.id)
                    
                    # Update last used timestamp
                    update_data = {'last_used_at': datetime.utcnow()}
                    update_model(item, update_data)
            
            return [{
                'memory_type': item.memory_type,
                'content': item.content,
                'confidence': item.confidence,
                'relevance': item.relevance,
                'created_at': item.created_at.isoformat() if item.created_at else None
            } for item in selected_items]
            
        except Exception as e:
            # Fall back to the first 'limit' items
            warning(f"Error parsing memory relevance results: {str(e)}")
            return [{
                'memory_type': item.memory_type,
                'content': item.content,
                'confidence': item.confidence,
                'relevance': item.relevance,
                'created_at': item.created_at.isoformat() if item.created_at else None
            } for item in memory_items[:limit]]
            
    except Exception as e:
        error_type = type(e).__name__
        error(f"Error ({error_type}) retrieving relevant memories: {str(e)}")
        return []


def update_context_summary(context_id: int) -> bool:
    """
    Update the summary and title of a conversation context.
    
    Args:
        context_id: The context ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get the context
        context = ConversationContext.query.get(context_id)
        if not context:
            warning(f"Context {context_id} not found for summary update")
            return False
            
        # Get recent messages
        messages = get_context_messages(context_id, limit=5)
        if not messages:
            warning(f"No messages found for context {context_id}")
            return False
            
        # Prepare prompt for summary and title generation
        messages_text = "\n\n".join([
            f"User: {msg['user_message']}\nAI: {msg['ai_response']}"
            for msg in messages
        ])
        
        prompt = f"""Summarize the main themes of this conversation and provide a brief title.

Conversation:
{messages_text}

Provide your response in JSON format with these fields:
- title: A brief, descriptive title for the conversation (5 words or less)
- summary: A concise summary of the main themes and topics (2-3 sentences)
- themes: An array of key themes or topics discussed (3-5 items)

JSON:"""

        messages = [
            {"role": "system", "content": "You analyze conversations and extract key themes and summaries."},
            {"role": "user", "content": prompt}
        ]
        
        response = safe_chat_completion(
            messages=messages,
            max_tokens=500,
            temperature=0.3,
            fallback_response=""
        )
        
        # Parse response
        try:
            result = json.loads(response)
            update_data = {
                'title': result.get('title', 'Conversation'),
                'summary': result.get('summary', ''),
                'themes': json.dumps(result.get('themes', [])),
                'updated_at': datetime.utcnow()
            }
            
            success = update_model(context, update_data)
            if success:
                info(f"Updated context {context_id} summary: {update_data['title']}")
            else:
                warning(f"Failed to update context {context_id} summary")
                
            return success
            
        except json.JSONDecodeError as e:
            warning(f"Failed to parse context summary response: {str(e)}")
            return False
            
    except Exception as e:
        error_type = type(e).__name__
        error(f"Error ({error_type}) updating context summary: {str(e)}")
        return False


def decay_memory_relevance() -> int:
    """
    Decay the relevance of memory items over time.
    This should be run periodically via a scheduled task.
    
    Returns:
        The number of memory items updated
    """
    try:
        # Calculate decay factor based on days since last update
        # For simplicity, we'll use a fixed daily decay
        
        # Get items not updated in the past day
        cutoff_date = datetime.utcnow() - timedelta(days=1)
        items = ConversationMemoryItem.query.filter(
            (ConversationMemoryItem.last_used_at == None) | 
            (ConversationMemoryItem.last_used_at < cutoff_date)
        ).all()
        
        update_count = 0
        for item in items:
            # Apply decay factor
            new_relevance = max(0.1, item.relevance * MEMORY_DECAY_FACTOR)
            
            # If relevance changed, update the item
            if new_relevance != item.relevance:
                update_data = {'relevance': new_relevance}
                success = update_model(item, update_data)
                if success:
                    update_count += 1
                    
        if update_count > 0:
            info(f"Decayed relevance for {update_count} memory items")
            
        return update_count
        
    except Exception as e:
        error_type = type(e).__name__
        error(f"Error ({error_type}) decaying memory relevance: {str(e)}")
        return 0


def consolidate_memories(context_id: int, threshold: float = 0.7) -> int:
    """
    Consolidate similar memory items to reduce redundancy.
    This combines similar memories into more comprehensive ones.
    
    Args:
        context_id: The context ID 
        threshold: Similarity threshold for consolidation (0.0-1.0)
        
    Returns:
        Number of memory items consolidated
    """
    try:
        # Get all memory items for the context
        memory_items = ConversationMemoryItem.query.filter_by(context_id=context_id).all()
        
        if len(memory_items) < 3:  # Not enough memories to consolidate
            return 0
            
        # Group memories by type
        memories_by_type = {}
        for item in memory_items:
            if item.memory_type not in memories_by_type:
                memories_by_type[item.memory_type] = []
            memories_by_type[item.memory_type].append(item)
        
        consolidated_count = 0
        
        # Process each memory type group
        for memory_type, items in memories_by_type.items():
            if len(items) < 2:  # Need at least 2 items to consolidate
                continue
                
            # Prepare memory content strings for comparison
            memory_texts = [item.content for item in items]
            
            # If there are many items, use AI to consolidate them
            if len(memory_texts) >= 3:
                consolidated_items = consolidate_memories_with_ai(memory_type, memory_texts, context_id)
                if consolidated_items:
                    consolidated_count += len(memory_texts) - len(consolidated_items)
            else:
                # For just a few items, use simple string similarity
                # This is a basic approach - could be enhanced with embeddings
                clusters = []
                for i, item1 in enumerate(items):
                    added = False
                    for cluster in clusters:
                        if any(string_similarity(item1.content, item2.content) > threshold 
                               for item2 in cluster):
                            cluster.append(item1)
                            added = True
                            break
                    if not added:
                        clusters.append([item1])
                
                # Merge clusters with multiple items
                for cluster in clusters:
                    if len(cluster) > 1:
                        merge_memory_cluster(cluster)
                        consolidated_count += len(cluster) - 1
        
        if consolidated_count > 0:
            info(f"Consolidated {consolidated_count} memory items for context {context_id}")
            
        return consolidated_count
        
    except Exception as e:
        error_type = type(e).__name__
        error(f"Error ({error_type}) consolidating memories: {str(e)}")
        return 0


def consolidate_memories_with_ai(memory_type: str, memory_texts: List[str], context_id: int) -> List[ConversationMemoryItem]:
    """
    Use AI to consolidate similar memories into more coherent items.
    
    Args:
        memory_type: Type of memories being consolidated
        memory_texts: List of memory content strings
        context_id: The context ID
        
    Returns:
        List of newly created memory items
    """
    if not memory_texts:
        return []
        
    # Format the memories for the prompt
    memories_formatted = "\n".join([f"- {txt}" for txt in memory_texts])
    
    prompt = f"""Analyze these memory items of type '{memory_type}' and consolidate similar ones:

{memories_formatted}

Instructions:
1. Identify related or overlapping memories
2. Combine them into more comprehensive memory statements
3. Preserve all important details from the original memories
4. Create 1-3 consolidated memory items

Return a JSON array with these fields:
- content: The consolidated memory statement
- confidence: Number from 0.0-1.0 indicating confidence (usually higher than individual memories)

JSON:"""

    messages = [
        {"role": "system", "content": "You are an AI that consolidates similar memory items from conversations."},
        {"role": "user", "content": prompt}
    ]
    
    response = safe_chat_completion(
        messages=messages,
        max_tokens=800,
        temperature=0.3,
        fallback_response="[]"
    )
    
    # Parse and create new memory items
    try:
        consolidated = json.loads(response)
        if not isinstance(consolidated, list):
            return []
            
        created_items = []
        for memory in consolidated:
            if not isinstance(memory, dict) or 'content' not in memory:
                continue
                
            memory_data = {
                'context_id': context_id,
                'memory_type': memory_type,
                'content': memory.get('content', ''),
                'confidence': float(memory.get('confidence', 0.9)),
                'relevance': 1.0,  # Start with full relevance for new consolidated items
                'created_at': datetime.utcnow()
            }
            
            memory_item = create_model(ConversationMemoryItem, memory_data)
            if memory_item:
                created_items.append(memory_item)
        
        # If consolidation worked, delete the original items
        if created_items:
            # Get all memory items with the same content
            original_items = ConversationMemoryItem.query.filter(
                ConversationMemoryItem.context_id == context_id,
                ConversationMemoryItem.memory_type == memory_type
            ).all()
            
            # Collect IDs of items to delete
            item_ids_to_delete = []
            for item in original_items:
                if item.content in memory_texts:
                    item_ids_to_delete.append(item.id)
            
            # Delete the original items if we found any
            if item_ids_to_delete:
                ConversationMemoryItem.query.filter(
                    ConversationMemoryItem.id.in_(item_ids_to_delete)
                ).delete(synchronize_session=False)
                db.session.commit()
            
        return created_items
            
    except json.JSONDecodeError:
        warning(f"Failed to parse consolidated memories response")
        return []
    except Exception as e:
        error_type = type(e).__name__
        error(f"Error ({error_type}) creating consolidated memories: {str(e)}")
        return []


def string_similarity(s1: str, s2: str) -> float:
    """
    Calculate similarity between two strings.
    This is a simple Jaccard similarity on word sets.
    
    Args:
        s1: First string
        s2: Second string
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not s1 or not s2:
        return 0.0
        
    # Convert to lowercase and split into words
    words1 = set(s1.lower().split())
    words2 = set(s2.lower().split())
    
    # Calculate Jaccard similarity
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    if union == 0:
        return 0.0
        
    return intersection / union


def merge_memory_cluster(cluster: List[ConversationMemoryItem]) -> Optional[ConversationMemoryItem]:
    """
    Merge a cluster of similar memory items into a single, more comprehensive item.
    
    Args:
        cluster: List of similar memory items
        
    Returns:
        The merged memory item or None if merge failed
    """
    if not cluster or len(cluster) < 2:
        return None
        
    try:
        # Sort by confidence, descending
        sorted_items = sorted(cluster, key=lambda x: x.confidence, reverse=True)
        
        # Use the highest confidence item as the base
        base_item = sorted_items[0]
        
        # Create a merged content string that combines unique information
        content_set = set()
        for item in sorted_items:
            content_set.update(item.content.lower().split())
            
        # Keep the original structure of the highest confidence item
        # but augment with additional information from other items
        additional_info = []
        for item in sorted_items[1:]:
            # Find words unique to this item
            item_words = set(item.content.lower().split())
            unique_words = item_words - set(base_item.content.lower().split())
            if len(unique_words) > 3:  # If meaningful unique content exists
                additional_info.append(item.content)
        
        # Create new content
        new_content = base_item.content
        if additional_info:
            new_content += " " + " ".join(additional_info)
        
        # Update the base item with the merged content
        # Use the maximum confidence of all items
        max_confidence = max(item.confidence for item in cluster)
        update_data = {
            'content': new_content,
            'confidence': max_confidence,
            'relevance': 1.0,  # Reset relevance for the merged item
            'updated_at': datetime.utcnow()
        }
        
        success = update_model(base_item, update_data)
        
        if success:
            # Delete the other items that were merged
            for item in sorted_items[1:]:
                db.session.delete(item)
            db.session.commit()
            return base_item
            
        return None
        
    except Exception as e:
        error_type = type(e).__name__
        error(f"Error ({error_type}) merging memory cluster: {str(e)}")
        return None


def enhance_prompt_with_context(
    user_id: Optional[str], 
    session_id: str, 
    user_message: str, 
    system_prompt: str
) -> Tuple[str, Optional[int]]:
    """
    Enhance a system prompt with conversation context and relevant memories.
    
    Args:
        user_id: The user ID if authenticated, None for anonymous users
        session_id: The browser session ID 
        user_message: The current user message
        system_prompt: The original system prompt
        
    Returns:
        Tuple of (enhanced system prompt, context_id or None)
    """
    # Get active context
    context = get_or_create_context(user_id, session_id)
    if not context:
        return system_prompt, None
        
    # Get recent messages
    recent_messages = get_context_messages(context.id, limit=5)
    
    # Check if this is a new topic that should trigger a context switch
    if recent_messages and len(recent_messages) >= 2:
        should_switch, transition_message = detect_context_switch(user_message, recent_messages)
        if should_switch:
            # Create a new context with a smooth transition
            new_context = create_new_context(user_id, session_id, transition_message)
            if new_context:
                info(f"Switched to new conversation context {new_context.id}")
                context = new_context
                
                # Update recent messages with the new context
                recent_messages = []  # No messages in the new context yet
    
    # Get relevant memories for the current message
    memories = get_relevant_memories(context.id, user_message)
    
    # If we have more than 10 memories in this context, try consolidating them
    memory_count = ConversationMemoryItem.query.filter_by(context_id=context.id).count()
    if memory_count > 10:
        try:
            consolidated = consolidate_memories(context.id)
            if consolidated > 0:
                info(f"Consolidated {consolidated} memories in context {context.id}")
        except Exception as e:
            warning(f"Memory consolidation failed: {str(e)}")
    
    # Build context section of the prompt
    context_parts = []
    
    # Add conversation summary if available
    if context.summary:
        context_parts.append(f"CONVERSATION SUMMARY: {context.summary}")
    
    # Add recent conversation history if available
    if recent_messages:
        context_parts.append("RECENT CONVERSATION:")
        for msg in recent_messages:
            context_parts.append(f"User: {msg['user_message']}")
            context_parts.append(f"You: {msg['ai_response']}")
    
    # Add relevant memories if available
    if memories:
        context_parts.append("IMPORTANT CONTEXT ABOUT THE USER:")
        for memory in memories:
            memory_type = memory['memory_type'].upper()
            content = memory['content']
            context_parts.append(f"- {memory_type}: {content}")
            
    # Add user preferences if available (focus on preferences memory type)
    user_preferences = [m for m in memories if m['memory_type'] == 'preference']
    if user_preferences:
        context_parts.append("USER PREFERENCES (Be sure to respect these in your response):")
        for pref in user_preferences:
            context_parts.append(f"- {pref['content']}")
    
    # Add guidance for empathetic response based on conversation history
    if recent_messages and any('mood' in msg and msg['mood'] in ['sad', 'anxious', 'angry', 'frustrated'] for msg in recent_messages):
        context_parts.append("COMMUNICATION GUIDANCE: The user appears to be experiencing challenging emotions. Respond with extra empathy and support. Acknowledge their feelings before offering perspectives or suggestions.")
    
    # If we have context, add it to the system prompt
    if context_parts:
        context_text = "\n\n".join(context_parts)
        enhanced_prompt = f"{system_prompt}\n\n===\nCONVERSATION CONTEXT:\n{context_text}\n===\n\nUse this context to inform your response while maintaining a natural conversational tone. Reference relevant past information without explicitly stating 'based on our previous conversation' or similar phrases that break immersion."
        return enhanced_prompt, context.id
    
    # Otherwise, return the original prompt
    return system_prompt, context.id