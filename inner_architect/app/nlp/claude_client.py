import os
import logging
from typing import Dict, List, Optional, Any
from anthropic import Anthropic
from flask import current_app

logger = logging.getLogger(__name__)

class ClaudeClient:
    """
    Client for interacting with Claude API.
    
    This class handles communication with Anthropic's Claude API,
    including managing the conversation, prompt formatting, and response parsing.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-opus-20240229"):
        """
        Initialize the Claude client.
        
        Args:
            api_key: Anthropic API key (if None, taken from environment)
            model: Claude model to use (default: claude-3-opus-20240229)
        """
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY') or current_app.config.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("Anthropic API key not found. Please set ANTHROPIC_API_KEY environment variable.")
        
        self.client = Anthropic(api_key=self.api_key)
        self.model = model
        self.max_tokens = 4096  # Default max tokens for response
    
    def generate_response(
        self, 
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None, 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate a response from Claude given messages and an optional system prompt.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            system_prompt: Optional system instructions for Claude
            temperature: Controls randomness (0-1)
            max_tokens: Maximum tokens in the response
            
        Returns:
            Claude's response text
        """
        try:
            # Create the completion request
            response = self.client.messages.create(
                model=self.model,
                messages=messages,
                system=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens or self.max_tokens
            )
            
            # Extract and return the response text
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Error generating Claude response: {str(e)}")
            # Return a fallback response
            return "I'm having trouble processing your request right now. Please try again later."
    
    def chat_completion(
        self, 
        user_message: str, 
        conversation_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """
        Generate a chat response from Claude.
        
        Args:
            user_message: The current message from the user
            conversation_history: Previous messages in the conversation
            system_prompt: Optional system instructions for Claude
            temperature: Controls randomness (0-1)
            
        Returns:
            Claude's response text
        """
        # Initialize or use provided conversation history
        messages = conversation_history or []
        
        # Add the current user message to the conversation
        messages.append({"role": "user", "content": user_message})
        
        # Generate and return the response
        return self.generate_response(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature
        )
    
    def analyze_text(
        self, 
        text: str, 
        task_description: str,
        temperature: float = 0.3
    ) -> str:
        """
        Analyze text using Claude for specific NLP tasks.
        
        Args:
            text: The text to analyze
            task_description: Description of the analysis task
            temperature: Controls randomness (0-1)
            
        Returns:
            Claude's analysis result
        """
        system_prompt = f"You are an expert in natural language processing and psychological analysis. {task_description}"
        
        messages = [
            {"role": "user", "content": text}
        ]
        
        return self.generate_response(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature
        )
    
    def extract_insights(
        self, 
        conversation: List[Dict[str, str]], 
        extraction_type: str = "themes"
    ) -> Dict[str, Any]:
        """
        Extract insights from a conversation.
        
        Args:
            conversation: List of conversation messages
            extraction_type: Type of insights to extract ('themes', 'memories', 'summary', etc.)
            
        Returns:
            Dictionary containing the extracted insights
        """
        # Create prompt based on extraction type
        extraction_prompts = {
            "themes": "Identify the main themes, topics, and emotional patterns in this conversation.",
            "memories": "Extract key facts, preferences, goals, and concerns the user has mentioned.",
            "summary": "Provide a concise summary of this conversation, highlighting the main points."
        }
        
        prompt = extraction_prompts.get(
            extraction_type, 
            "Analyze this conversation and extract key insights."
        )
        
        system_prompt = f"""
        You are an AI assistant specializing in conversation analysis and psychological insights.
        {prompt}
        Format your response as a JSON object with appropriate keys and values.
        Be concise but thorough in your analysis.
        """
        
        # Create a simplified version of the conversation
        simplified_conversation = []
        for message in conversation:
            simplified_conversation.append({
                "role": message.get("role", "user"),
                "content": message.get("content", "")
            })
        
        response = self.generate_response(
            messages=simplified_conversation,
            system_prompt=system_prompt,
            temperature=0.3
        )
        
        # Parse response (in a real implementation, handle JSON parsing properly)
        # For now, we'll just return the text response
        return {"result": response}

# Singleton instance
claude_client = None

def get_claude_client() -> ClaudeClient:
    """Get or create a singleton Claude client instance."""
    global claude_client
    if claude_client is None:
        claude_client = ClaudeClient()
    return claude_client