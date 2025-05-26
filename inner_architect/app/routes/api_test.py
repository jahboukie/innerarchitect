"""
API Test Routes for testing API fallback functionality.

These routes allow testing of the API fallback mechanism without affecting
normal application functionality.
"""
import time
import logging
from flask import Blueprint, request, jsonify, render_template, current_app

from ..services.claude_client import claude_client
from ..services.ai_client_factory import ai_client_factory
from api_fallback import APITimeoutError, APIConnectionError, APIResponseError

# Create a Blueprint for API test routes
api_test = Blueprint('api_test', __name__, url_prefix='/api-test')

# Initialize logger
logger = logging.getLogger(__name__)

@api_test.route('/')
def index():
    """Render the API test interface."""
    return render_template('api_test.html')

@api_test.route('/chat', methods=['POST'])
def chat():
    """
    Test chat completion API with fallback mechanism.
    
    Returns:
        JSON response with chat completion result or error
    """
    data = request.json
    message = data.get('message', '')
    technique = data.get('technique', '')
    simulate_error = data.get('simulate_error', '')
    
    if not message:
        return jsonify({
            'success': False,
            'error': 'Message is required'
        }), 400
    
    try:
        # Simulate specific errors if requested
        if simulate_error:
            if simulate_error == 'timeout':
                logger.info("Simulating API timeout error")
                raise APITimeoutError("Simulated timeout error")
            elif simulate_error == 'connection':
                logger.info("Simulating API connection error")
                raise APIConnectionError("Simulated connection error")
            elif simulate_error == 'response':
                logger.info("Simulating API response error")
                raise APIResponseError("Simulated response error")
        
        # Process the chat message with the Claude client
        response = claude_client.chat_completion(
            messages=[
                {"role": "user", "content": message}
            ],
            technique_id=technique if technique else None,
            auto_select_technique=not technique,
            temperature=0.7,
            max_tokens=500
        )
        
        return jsonify({
            'success': True,
            'message': response.get('message', ''),
            'technique': response.get('technique', {}).get('id', ''),
            'mood': response.get('mood', ''),
            'model': response.get('model', ''),
            'provider': response.get('provider', ''),
            'is_fallback': response.get('is_fallback', False)
        })
        
    except Exception as e:
        logger.error(f"Error in chat API: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_test.route('/provider-status')
def provider_status():
    """
    Get the status of all AI providers.
    
    Returns:
        JSON response with provider status information
    """
    providers = ai_client_factory.providers.copy()
    
    # Remove client objects from the response
    for provider in providers.values():
        if 'client' in provider:
            provider['client'] = 'Client object (removed from response)'
    
    return jsonify({
        'success': True,
        'active_provider': ai_client_factory.active_provider,
        'providers': providers
    })

@api_test.route('/simulate-provider-failure', methods=['POST'])
def simulate_provider_failure():
    """
    Simulate a provider failure to test fallback mechanism.
    
    Returns:
        JSON response with result of the simulation
    """
    data = request.json
    provider = data.get('provider', '')
    error_type = data.get('error_type', 'response')
    
    if not provider or provider not in ai_client_factory.providers:
        return jsonify({
            'success': False,
            'error': 'Valid provider name is required'
        }), 400
    
    # Create appropriate error based on type
    if error_type == 'timeout':
        error = APITimeoutError(f"Simulated timeout error for {provider}")
    elif error_type == 'connection':
        error = APIConnectionError(f"Simulated connection error for {provider}")
    else:
        error = APIResponseError(f"Simulated response error for {provider}")
    
    # Mark the provider as failed
    ai_client_factory._mark_provider_failure(provider, error)
    
    # Check if active provider changed
    active_provider = ai_client_factory._set_active_provider()
    
    return jsonify({
        'success': True,
        'provider': provider,
        'error_type': error_type,
        'active_provider': active_provider,
        'provider_info': {
            'available': ai_client_factory.providers[provider]['available'],
            'failure_count': ai_client_factory.providers[provider]['failure_count']
        }
    })

@api_test.route('/reset-providers')
def reset_providers():
    """
    Reset all providers to available status.
    
    Returns:
        JSON response confirming reset
    """
    for provider in ai_client_factory.providers.values():
        provider['available'] = True
        provider['failure_count'] = 0
        provider['last_failure_time'] = 0
    
    ai_client_factory._set_active_provider()
    
    return jsonify({
        'success': True,
        'message': 'All providers reset to available status',
        'active_provider': ai_client_factory.active_provider
    })