"""
Conversation Context Module for The Inner Architect

This module manages conversation context across multiple messages,
enabling the AI to maintain memory of previous interactions and provide
more personalized and coherent responses.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union

from sqlalchemy.exc import SQLAlchemyError
from database import db, safe_commit, create_model, update_model, safe_query
from models import ConversationContext, ConversationMemoryItem, ChatHistory, User
from logging_config import get_logger, error, debug, warning, info

# Initialize OpenAI for memory extraction and context summarization
from openai import OpenAI
import os
from language_util import safe_chat_completion

# Get module-specific logger
logger = get_logger('conversation_context')

# Maximum number of messages to include in context
MAX_CONTEXT_MESSAGES = 10  

# Maximum number of memory items to include in a prompt
MAX_MEMORY_ITEMS = 5

# Memory relevance decay factor (per day)
MEMORY_DECAY_FACTOR = 0.9


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
        # Get memory items sorted by relevance * confidence
        memory_items = ConversationMemoryItem.query.filter_by(context_id=context_id) \
            .order_by((ConversationMemoryItem.relevance * ConversationMemoryItem.confidence).desc()) \
            .limit(limit * 2) \
            .all()
            
        if not memory_items:
            return []
            
        # If we have only a few items, return them all
        if len(memory_items) <= limit:
            return [{
                'memory_type': item.memory_type,
                'content': item.content,
                'confidence': item.confidence,
                'relevance': item.relevance
            } for item in memory_items]
            
        # For more items, use semantic search to find the most relevant ones
        # This would ideally use embeddings, but for now we'll use a simple prompt
        memories_text = "\n".join([
            f"{i+1}. {item.memory_type.upper()}: {item.content}" 
            for i, item in enumerate(memory_items)
        ])
        
        prompt = f"""Below are memory items from previous conversations with a user. Rank the top {limit} items that are most relevant to the user's current message.

Memory items:
{memories_text}

User's current message:
{current_message}

Return ONLY the numbers of the {limit} most relevant items in order of relevance (most relevant first), as a comma-separated list:"""

        messages = [
            {"role": "system", "content": "You are helping to retrieve relevant contextual information for a conversation."},
            {"role": "user", "content": prompt}
        ]
        
        response = safe_chat_completion(
            messages=messages,
            max_tokens=50,
            temperature=0.3,
            fallback_response=""
        )
        
        # Parse response as a list of indices
        try:
            # Extract indices from response
            indices = []
            for part in response.replace(' ', '').split(','):
                try:
                    idx = int(part) - 1  # Convert to 0-based index
                    if 0 <= idx < len(memory_items):
                        indices.append(idx)
                except ValueError:
                    continue
                    
            # If we couldn't parse anything, just use the first 'limit' items
            if not indices:
                indices = list(range(min(limit, len(memory_items))))
                
            # Return the selected items
            return [{
                'memory_type': memory_items[idx].memory_type,
                'content': memory_items[idx].content,
                'confidence': memory_items[idx].confidence,
                'relevance': memory_items[idx].relevance
            } for idx in indices[:limit]]
            
        except Exception as e:
            # Fall back to the first 'limit' items
            warning(f"Error parsing memory relevance results: {str(e)}")
            return [{
                'memory_type': item.memory_type,
                'content': item.content,
                'confidence': item.confidence,
                'relevance': item.relevance
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
    
    # Get relevant memories
    memories = get_relevant_memories(context.id, user_message)
    
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
    
    # If we have context, add it to the system prompt
    if context_parts:
        context_text = "\n\n".join(context_parts)
        enhanced_prompt = f"{system_prompt}\n\n===\nCONVERSATION CONTEXT:\n{context_text}\n===\n\nUse this context to inform your response while maintaining a natural conversational tone."
        return enhanced_prompt, context.id
    
    # Otherwise, return the original prompt
    return system_prompt, context.id