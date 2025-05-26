"""
AI Client Factory for creating and managing AI provider clients.

This module implements a factory pattern for creating AI clients
and provides fallback mechanisms to switch between different providers
when one becomes unavailable.
"""
import os
import logging
import time
from typing import Dict, Any, List, Optional, Callable, Tuple
from functools import wraps

# Import API fallback utilities
from api_fallback import APIError, APITimeoutError, APIConnectionError, APIResponseError
from api_fallback import with_retry_and_timeout, get_fallback_response

# Import monitoring utilities
try:
    from ..utils.monitoring import track_api_call
    from ..utils.logging_setup import log_api_call
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    # Create dummy decorator if monitoring is not available
    def track_api_call(f):
        return f
    # Create dummy function if logging setup is not available
    def log_api_call(*args, **kwargs):
        pass

# Initialize logger
logger = logging.getLogger('inner_architect.ai_client_factory')

class AIClientFactory:
    """
    Factory for creating and managing AI provider clients.
    Handles automatic fallback between providers when one fails.
    """
    
    def __init__(self):
        # Available providers and their priorities (lower number = higher priority)
        self.providers = {
            'claude': {
                'priority': 1,
                'client': None,
                'available': True,
                'last_failure_time': 0,
                'failure_count': 0,
                'cooldown_period': 300,  # 5 minutes
                'max_failures': 3,
                'api_key_env': 'ANTHROPIC_API_KEY'
            },
            'openai': {
                'priority': 2,
                'client': None,
                'available': True,
                'last_failure_time': 0,
                'failure_count': 0,
                'cooldown_period': 300,  # 5 minutes
                'max_failures': 3,
                'api_key_env': 'OPENAI_API_KEY'
            }
        }
        
        # Current active provider
        self.active_provider = 'claude'
        
        # Initialize clients
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize AI clients for all providers."""
        # Initialize Claude client if API key is available
        if os.environ.get(self.providers['claude']['api_key_env']):
            try:
                from anthropic import Anthropic
                self.providers['claude']['client'] = Anthropic(
                    api_key=os.environ.get(self.providers['claude']['api_key_env'])
                )
                logger.info("Claude client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Claude client: {e}")
                self.providers['claude']['available'] = False
        else:
            logger.warning(f"Claude API key not found in environment ({self.providers['claude']['api_key_env']})")
            self.providers['claude']['available'] = False
        
        # Initialize OpenAI client if API key is available
        if os.environ.get(self.providers['openai']['api_key_env']):
            try:
                from openai import OpenAI
                self.providers['openai']['client'] = OpenAI(
                    api_key=os.environ.get(self.providers['openai']['api_key_env'])
                )
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.providers['openai']['available'] = False
        else:
            logger.warning(f"OpenAI API key not found in environment ({self.providers['openai']['api_key_env']})")
            self.providers['openai']['available'] = False
        
        # Set initial active provider to the highest priority available one
        self._set_active_provider()
    
    def _set_active_provider(self) -> str:
        """
        Set the active provider to the highest priority available provider.
        
        Returns:
            Name of the active provider
        """
        available_providers = {
            name: info for name, info in self.providers.items() 
            if info['available'] and self._is_provider_cooled_down(name)
        }
        
        if not available_providers:
            logger.error("No available AI providers found")
            # Reset all providers if all are unavailable
            self._reset_unavailable_providers()
            # Try again with reset providers
            available_providers = {
                name: info for name, info in self.providers.items() if info['available']
            }
            
            if not available_providers:
                # If still no available providers, use a dummy provider
                logger.critical("All AI providers are unavailable")
                self.active_provider = 'fallback'
                return self.active_provider
        
        # Sort by priority and get the highest priority provider
        sorted_providers = sorted(
            available_providers.items(), 
            key=lambda x: x[1]['priority']
        )
        
        self.active_provider = sorted_providers[0][0]
        logger.info(f"Active provider set to: {self.active_provider}")
        
        return self.active_provider
    
    def _is_provider_cooled_down(self, provider_name: str) -> bool:
        """
        Check if a provider has cooled down after failures.
        
        Args:
            provider_name: Name of the provider to check
        
        Returns:
            True if the provider has cooled down, False otherwise
        """
        provider = self.providers.get(provider_name)
        if not provider:
            return False
            
        current_time = time.time()
        cooldown_time = provider['last_failure_time'] + provider['cooldown_period']
        
        # If the cooldown period has passed, reset the failure count
        if current_time > cooldown_time and provider['failure_count'] > 0:
            provider['failure_count'] = 0
            logger.info(f"Provider {provider_name} cooldown period passed, resetting failure count")
            
        return provider['failure_count'] < provider['max_failures']
    
    def _reset_unavailable_providers(self):
        """Reset all providers that are marked as unavailable."""
        for name, info in self.providers.items():
            if not info['available']:
                # Only reset if the cooldown period has passed
                current_time = time.time()
                cooldown_time = info['last_failure_time'] + info['cooldown_period']
                
                if current_time > cooldown_time:
                    logger.info(f"Resetting provider {name} availability")
                    info['available'] = True
                    info['failure_count'] = 0
    
    def _mark_provider_failure(self, provider_name: str, error: Exception):
        """
        Mark a provider as having failed and potentially make it unavailable.
        
        Args:
            provider_name: Name of the provider that failed
            error: The exception that caused the failure
        """
        if provider_name not in self.providers:
            return
            
        provider = self.providers[provider_name]
        provider['failure_count'] += 1
        provider['last_failure_time'] = time.time()
        
        logger.warning(
            f"Provider {provider_name} failed (count: {provider['failure_count']}): {str(error)}"
        )
        
        # If max failures reached, mark as unavailable
        if provider['failure_count'] >= provider['max_failures']:
            provider['available'] = False
            logger.error(
                f"Provider {provider_name} marked as unavailable after {provider['failure_count']} failures"
            )
            
            # If this was the active provider, switch to a new one
            if self.active_provider == provider_name:
                self._set_active_provider()
    
    def with_fallback(self, func: Callable) -> Callable:
        """
        Decorator to add provider fallback logic to API functions.
        
        Args:
            func: Function to decorate
            
        Returns:
            Decorated function with fallback capability
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            context = kwargs.get('context', {})
            
            # Try each available provider
            for provider_name, info in sorted(
                self.providers.items(), 
                key=lambda x: x[1]['priority']
            ):
                if not info['available'] or not self._is_provider_cooled_down(provider_name):
                    continue
                
                # Set the client for this attempt
                kwargs['provider'] = provider_name
                kwargs['client'] = info['client']
                
                try:
                    result = func(*args, **kwargs)
                    # If successful, update active provider if it changed
                    if provider_name != self.active_provider:
                        logger.info(f"Switching active provider from {self.active_provider} to {provider_name}")
                        self.active_provider = provider_name
                    return result
                except Exception as e:
                    logger.warning(f"Provider {provider_name} call failed: {str(e)}")
                    last_error = e
                    self._mark_provider_failure(provider_name, e)
            
            # All providers failed, return fallback response
            logger.error("All providers failed, returning fallback response")
            
            # Determine error type
            if isinstance(last_error, APITimeoutError):
                error_type = "timeout"
            elif isinstance(last_error, APIConnectionError):
                error_type = "connection"
            else:
                error_type = "response"
                
            return get_fallback_response(error_type, context)
            
        return wrapper
    
    def get_active_client(self):
        """
        Get the client for the currently active provider.
        
        Returns:
            The active client or None if no client is available
        """
        if self.active_provider == 'fallback':
            return None
            
        return self.providers.get(self.active_provider, {}).get('client')
    
    @track_api_call
    def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to the active provider with fallback.
        
        Args:
            messages: List of message dictionaries with role and content
            model: Model identifier (optional, uses provider default if not specified)
            temperature: Sampling temperature
            max_tokens: Maximum number of tokens to generate
            context: Optional context dictionary for fallback responses
            
        Returns:
            Dictionary with the model's response
        """
        @self.with_fallback
        @with_retry_and_timeout()
        def _chat_completion(
            messages: List[Dict[str, str]], 
            model: Optional[str],
            temperature: float,
            max_tokens: int,
            provider: str,
            client: Any,
            context: Optional[Dict[str, Any]],
            **kwargs
        ) -> Dict[str, Any]:
            if provider == 'claude':
                # Claude-specific implementation
                # Default to Claude 3 Sonnet if no model is specified
                claude_model = model or "claude-3-sonnet-20240229"
                
                # Convert message format if needed
                claude_messages = []
                system_prompt = None
                
                for msg in messages:
                    if msg['role'] == 'system':
                        # Claude uses a system parameter instead of a system message
                        system_prompt = msg['content']
                    else:
                        claude_messages.append({
                            'role': msg['role'],
                            'content': msg['content']
                        })
                
                response = client.messages.create(
                    model=claude_model,
                    messages=claude_messages,
                    system=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
                return {
                    'message': response.content[0].text,
                    'model': response.model,
                    'provider': 'claude',
                    'is_fallback': False
                }
                
            elif provider == 'openai':
                # OpenAI-specific implementation
                # Default to GPT-4 if no model is specified
                openai_model = model or "gpt-4"
                
                response = client.chat.completions.create(
                    model=openai_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
                return {
                    'message': response.choices[0].message.content,
                    'model': response.model,
                    'provider': 'openai',
                    'is_fallback': False
                }
            else:
                raise ValueError(f"Unsupported provider: {provider}")
        
        # Set up context for better fallback responses
        context = context or {}
        context.setdefault('endpoint', 'chat')
        
        # Get request ID for tracking
        request_id = context.get('request_id', f"req_{int(time.time() * 1000)}")
        
        # Track message characteristics for monitoring
        message_count = len(messages)
        user_message = next((msg['content'] for msg in reversed(messages) if msg['role'] == 'user'), '')
        user_message_length = len(user_message)
        
        # Log the request
        logger.info(
            f"Chat completion request: provider={self.active_provider}, model={model}, "
            f"messages={message_count}, request_id={request_id}"
        )
        
        # Execute the chat completion
        result = _chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            context=context,
            request_id=request_id
        )
        
        # Add request metadata to the result
        result['request_id'] = request_id
        result['timestamp'] = time.time()
        
        # Track response characteristics
        if 'message' in result:
            result['response_length'] = len(result['message'])
        
        return result

# Create a singleton instance of the factory
ai_client_factory = AIClientFactory()