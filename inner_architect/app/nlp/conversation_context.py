import json
import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from app import db
from app.models.chat import ConversationContext, ConversationMemoryItem, ChatHistory
from app.nlp.claude_client import get_claude_client

logger = logging.getLogger(__name__)

def get_or_create_context(user_id: Optional[str], session_id: str) -> ConversationContext:
    """
    Get the active conversation context or create a new one if none exists.
    
    Args:
        user_id: The user ID (None for anonymous users)
        session_id: The session ID
        
    Returns:
        Active ConversationContext object
    """
    try:
        # Look for an active context
        context = None
        if user_id:
            context = ConversationContext.query.filter_by(
                user_id=user_id, 
                session_id=session_id,
                is_active=True
            ).first()
        else:
            context = ConversationContext.query.filter_by(
                session_id=session_id,
                is_active=True,
                user_id=None
            ).first()
        
        # If no active context exists, create a new one
        if not context:
            context = ConversationContext(
                user_id=user_id,
                session_id=session_id,
                is_active=True,
                title="New Conversation",
                summary=None,
                themes=None
            )
            db.session.add(context)
            db.session.commit()
            logger.info(f"Created new conversation context: {context.id}")
            
        return context
        
    except Exception as e:
        logger.error(f"Error getting or creating context: {str(e)}")
        db.session.rollback()
        
        # Create a new context if an error occurred
        context = ConversationContext(
            user_id=user_id,
            session_id=session_id,
            is_active=True,
            title="New Conversation",
            summary=None,
            themes=None
        )
        db.session.add(context)
        db.session.commit()
        return context

def create_new_context(user_id: Optional[str], session_id: str) -> ConversationContext:
    """
    Create a new conversation context and deactivate any existing active context.
    
    Args:
        user_id: The user ID (None for anonymous users)
        session_id: The session ID
        
    Returns:
        New ConversationContext object
    """
    try:
        # Deactivate any existing active context
        if user_id:
            existing_contexts = ConversationContext.query.filter_by(
                user_id=user_id, 
                session_id=session_id,
                is_active=True
            ).all()
        else:
            existing_contexts = ConversationContext.query.filter_by(
                session_id=session_id,
                is_active=True,
                user_id=None
            ).all()
        
        for context in existing_contexts:
            context.is_active = False
        
        # Create a new active context
        new_context = ConversationContext(
            user_id=user_id,
            session_id=session_id,
            is_active=True,
            title="New Conversation",
            summary=None,
            themes=None
        )
        db.session.add(new_context)
        db.session.commit()
        
        logger.info(f"Created new conversation context: {new_context.id}")
        return new_context
        
    except Exception as e:
        logger.error(f"Error creating new context: {str(e)}")
        db.session.rollback()
        
        # Create a new context if an error occurred
        context = ConversationContext(
            user_id=user_id,
            session_id=session_id,
            is_active=True,
            title="New Conversation",
            summary=None,
            themes=None
        )
        db.session.add(context)
        db.session.commit()
        return context

def add_message_to_context(
    context_id: int, 
    user_message: str, 
    ai_response: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    mood: Optional[str] = None,
    nlp_technique: Optional[str] = None
) -> ChatHistory:
    """
    Add a message exchange to the conversation context.
    
    Args:
        context_id: The conversation context ID
        user_message: The user's message
        ai_response: The AI's response
        user_id: The user ID (optional)
        session_id: The session ID (optional)
        mood: The detected user mood (optional)
        nlp_technique: The applied NLP technique (optional)
        
    Returns:
        The created ChatHistory object
    """
    try:
        # Create a new chat history entry
        chat_entry = ChatHistory(
            user_id=user_id,
            session_id=session_id or str(uuid.uuid4()),
            context_id=context_id,
            user_message=user_message,
            ai_response=ai_response,
            mood=mood,
            nlp_technique=nlp_technique
        )
        
        db.session.add(chat_entry)
        db.session.commit()
        
        logger.info(f"Added message to context {context_id}: {chat_entry.id}")
        return chat_entry
        
    except Exception as e:
        logger.error(f"Error adding message to context: {str(e)}")
        db.session.rollback()
        raise

def enhance_prompt_with_context(
    context_id: int, 
    user_message: str,
    max_history: int = 5,
    include_memories: bool = True
) -> Tuple[str, List[Dict[str, str]]]:
    """
    Enhance a user prompt with relevant context from conversation history and memories.
    
    Args:
        context_id: The conversation context ID
        user_message: The current user message
        max_history: Maximum number of past exchanges to include
        include_memories: Whether to include memory items
        
    Returns:
        Tuple of (enhanced prompt, conversation history)
    """
    try:
        # Get the conversation context
        context = ConversationContext.query.get(context_id)
        if not context:
            logger.warning(f"Context not found: {context_id}")
            return user_message, []
        
        # Get recent conversation history
        history = ChatHistory.query.filter_by(context_id=context_id) \
            .order_by(ChatHistory.created_at.desc()) \
            .limit(max_history) \
            .all()
        
        # Format history as a list of messages for Claude
        conversation_history = []
        for entry in reversed(history):  # Oldest first
            conversation_history.append({
                "role": "user",
                "content": entry.user_message
            })
            conversation_history.append({
                "role": "assistant",
                "content": entry.ai_response
            })
        
        # Get relevant memories if requested
        if include_memories and context.memory_items.count() > 0:
            # Get memory items ordered by relevance
            memories = ConversationMemoryItem.query.filter_by(context_id=context_id) \
                .order_by(ConversationMemoryItem.relevance.desc()) \
                .limit(5) \
                .all()
            
            # Update last_used_at for these memories
            for memory in memories:
                memory.last_used_at = datetime.utcnow()
            
            db.session.commit()
        
        return user_message, conversation_history
        
    except Exception as e:
        logger.error(f"Error enhancing prompt with context: {str(e)}")
        return user_message, []

def update_context_summary(context_id: int) -> bool:
    """
    Update the context summary and themes based on recent conversation.
    
    Args:
        context_id: The conversation context ID
        
    Returns:
        Success flag
    """
    try:
        # Get the conversation context
        context = ConversationContext.query.get(context_id)
        if not context:
            logger.warning(f"Context not found: {context_id}")
            return False
        
        # Get recent conversation history (up to 10 exchanges)
        history = ChatHistory.query.filter_by(context_id=context_id) \
            .order_by(ChatHistory.created_at.desc()) \
            .limit(10) \
            .all()
        
        if not history:
            logger.info(f"No history found for context {context_id}")
            return False
        
        # Format history for Claude
        formatted_history = []
        for entry in reversed(history):  # Oldest first
            formatted_history.append({
                "role": "user",
                "content": entry.user_message
            })
            formatted_history.append({
                "role": "assistant",
                "content": entry.ai_response
            })
        
        # Get the Claude client
        claude = get_claude_client()
        
        # Extract themes and summary
        system_prompt = """
        You are an expert in conversation analysis. Analyze this conversation and provide:
        1. A concise, 1-2 sentence summary of the conversation
        2. A list of 3-5 key themes or topics discussed
        
        Format your response as JSON with two keys: "summary" and "themes" (as an array of strings).
        """
        
        response = claude.generate_response(
            messages=formatted_history,
            system_prompt=system_prompt,
            temperature=0.3
        )
        
        # Parse the JSON response (with error handling)
        try:
            # Extract JSON from the response
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            
            result = json.loads(json_str)
            
            # Update the context
            context.summary = result.get("summary")
            context.themes = json.dumps(result.get("themes", []))
            
            # Update title if it's still the default
            if context.title == "New Conversation" and result.get("summary"):
                # Generate a shorter title from the summary
                title_prompt = f"Based on this summary: '{result.get('summary')}', generate a very short (3-6 words) title for the conversation. Response should contain ONLY the title text, nothing else."
                title = claude.analyze_text(title_prompt, "Generate a concise title.").strip()
                context.title = title[:100]  # Limit to 100 chars
            
            db.session.commit()
            logger.info(f"Updated context {context_id} summary and themes")
            return True
            
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            logger.warning(f"Failed to parse JSON response for context {context_id}")
            
            # Try to extract summary and themes manually
            lines = response.split("\n")
            summary = ""
            themes = []
            
            for line in lines:
                if "summary" in line.lower() and ":" in line:
                    summary = line.split(":", 1)[1].strip()
                elif any(theme_marker in line.lower() for theme_marker in ["theme", "topic"]) and ":" in line:
                    theme = line.split(":", 1)[1].strip()
                    themes.append(theme)
            
            if summary:
                context.summary = summary
                if context.title == "New Conversation":
                    context.title = summary[:50] + "..."
            
            if themes:
                context.themes = json.dumps(themes)
                
            db.session.commit()
            logger.info(f"Updated context {context_id} with manually extracted data")
            return True
            
    except Exception as e:
        logger.error(f"Error updating context summary: {str(e)}")
        db.session.rollback()
        return False

def consolidate_memories(context_id: int) -> bool:
    """
    Extract and consolidate memories from conversation history.
    
    Args:
        context_id: The conversation context ID
        
    Returns:
        Success flag
    """
    try:
        # Get the conversation context
        context = ConversationContext.query.get(context_id)
        if not context:
            logger.warning(f"Context not found: {context_id}")
            return False
        
        # Get unprocessed conversation history
        # This would typically be chat history since the last memory extraction
        last_memory = ConversationMemoryItem.query.filter_by(context_id=context_id) \
            .order_by(ConversationMemoryItem.created_at.desc()) \
            .first()
        
        last_processed_time = last_memory.created_at if last_memory else datetime.min
        
        history = ChatHistory.query.filter_by(context_id=context_id) \
            .filter(ChatHistory.created_at > last_processed_time) \
            .order_by(ChatHistory.created_at.asc()) \
            .all()
        
        if not history:
            logger.info(f"No new history to process for context {context_id}")
            return False
        
        # Format history for Claude
        formatted_history = []
        for entry in history:
            formatted_history.append({
                "role": "user",
                "content": entry.user_message
            })
            formatted_history.append({
                "role": "assistant",
                "content": entry.ai_response
            })
        
        # Get the Claude client
        claude = get_claude_client()
        
        # Extract memories
        system_prompt = """
        You are an expert in conversation analysis and memory extraction. Review this conversation and extract:
        1. Facts - specific information the user has shared about themselves
        2. Preferences - likes, dislikes, and preferences the user has expressed
        3. Goals - aspirations, objectives, or intentions the user has mentioned
        4. Concerns - worries, anxieties, or challenges the user has discussed
        
        Format your response as JSON with an array of memory items, each with these properties:
        - "type": one of "fact", "preference", "goal", or "concern"
        - "content": the specific memory content
        - "confidence": a number from 0.0 to 1.0 indicating how confident you are about this memory
        - "source_index": the index of the user message this came from (0 for the first user message)
        
        Only include clear, specific memories with confidence > 0.7. Avoid repetition of existing memories.
        """
        
        response = claude.generate_response(
            messages=formatted_history,
            system_prompt=system_prompt,
            temperature=0.3
        )
        
        # Parse the JSON response (with error handling)
        try:
            # Extract JSON from the response
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            
            memories = json.loads(json_str)
            
            # Check if memories is a dict with a 'memories' key
            if isinstance(memories, dict) and 'memories' in memories:
                memories = memories['memories']
            
            # Add memories to the database
            for memory in memories:
                memory_type = memory.get('type')
                content = memory.get('content')
                confidence = memory.get('confidence', 0.8)
                source_index = memory.get('source_index', 0)
                
                if memory_type and content:
                    # Check if a similar memory already exists
                    similar_memory = ConversationMemoryItem.query.filter_by(
                        context_id=context_id,
                        memory_type=memory_type
                    ).filter(
                        ConversationMemoryItem.content.like(f"%{content[:50]}%")
                    ).first()
                    
                    if not similar_memory:
                        # Get corresponding message ID if possible
                        source_message_id = None
                        if 0 <= source_index < len(history):
                            source_message_id = history[source_index].id
                        
                        # Create new memory item
                        memory_item = ConversationMemoryItem(
                            context_id=context_id,
                            memory_type=memory_type,
                            content=content,
                            confidence=confidence,
                            relevance=1.0,  # New memories start with high relevance
                            source_message_id=source_message_id
                        )
                        db.session.add(memory_item)
            
            db.session.commit()
            logger.info(f"Added memories to context {context_id}")
            return True
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response for context {context_id}: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Error consolidating memories: {str(e)}")
        db.session.rollback()
        return False

def get_context_messages(context_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get messages for a specific conversation context.
    
    Args:
        context_id: The conversation context ID
        limit: Maximum number of messages to retrieve
        
    Returns:
        List of message dictionaries
    """
    try:
        # Get the conversation context
        context = ConversationContext.query.get(context_id)
        if not context:
            logger.warning(f"Context not found: {context_id}")
            return []
        
        # Get chat history
        history = ChatHistory.query.filter_by(context_id=context_id) \
            .order_by(ChatHistory.created_at.desc()) \
            .limit(limit) \
            .all()
        
        # Format as list of dictionaries
        messages = []
        for entry in reversed(history):  # Oldest first
            messages.append({
                "id": entry.id,
                "user_message": entry.user_message,
                "ai_response": entry.ai_response,
                "mood": entry.mood,
                "nlp_technique": entry.nlp_technique,
                "timestamp": entry.created_at.isoformat()
            })
        
        return messages
        
    except Exception as e:
        logger.error(f"Error getting context messages: {str(e)}")
        return []