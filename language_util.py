"""
Language Utility module for The Inner Architect

This module provides multilingual support through translation capabilities
and language detection.
"""

import logging
import json
import os
import time
from functools import lru_cache
from typing import Optional, Dict, Any, List, Union, Callable, TypeVar, Iterable

# External OpenAI API for translations and language detection
from openai import OpenAI
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam

from logging_config import get_logger, info, error, debug, warning, critical, exception

# Initialize OpenAI client
# Get module-specific logger
logger = get_logger('language_util')

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Default parameters for OpenAI API calls
DEFAULT_MODEL = "gpt-4o"  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

def safe_openai_call(
    func: Callable, 
    *args, 
    retry_count: int = MAX_RETRIES, 
    fallback_value: Any = None,
    **kwargs
) -> Any:
    """
    Safely execute an OpenAI API call with error handling and retries.
    
    Args:
        func: The OpenAI function to call
        *args: Positional arguments to pass to the function
        retry_count: Number of retries on temporary errors
        fallback_value: Value to return if all retries fail
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the API call or fallback_value if it fails
    """
    if not openai_client:
        warning("OpenAI client not initialized - API key may be missing")
        return fallback_value
        
    attempts = 0
    last_error = None
    
    while attempts < retry_count:
        try:
            result = func(*args, **kwargs)
            if attempts > 0:
                info(f"OpenAI API call succeeded after {attempts+1} attempts")
            return result
            
        except Exception as e:
            error_type = type(e).__name__
            attempts += 1
            
            # Determine if the error is retryable
            retryable = "Timeout" in error_type or \
                        "RateLimitError" in error_type or \
                        "ServiceUnavailableError" in error_type or \
                        "APIConnectionError" in error_type
                        
            if retryable and attempts < retry_count:
                retry_delay = RETRY_DELAY * attempts  # Exponential backoff
                warning(f"Retryable error on OpenAI API call ({error_type}): {str(e)}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                # Non-retryable error or max retries reached
                error_message = f"Error calling OpenAI API ({error_type}): {str(e)}"
                if attempts == retry_count:
                    error_message += f" after {attempts} retries"
                error(error_message)
                last_error = e
                break
                
    # If we got here, all retries failed
    if "AuthenticationError" in type(last_error).__name__:
        critical("Authentication error with OpenAI API. Check your API key.")
    
    return fallback_value

def safe_chat_completion(
    messages: List[Dict[str, str]], 
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1000, 
    temperature: float = 0.7,
    fallback_response: str = ""
) -> str:
    """
    Safely execute a chat completion with the OpenAI API.
    
    Args:
        messages: List of message dictionaries (role, content)
        model: The model to use
        max_tokens: Maximum number of tokens to generate
        temperature: Sampling temperature
        fallback_response: Response to return if the API call fails
        
    Returns:
        The generated text or fallback_response if the call fails
    """
    if not openai_client:
        warning("OpenAI client not initialized - API key may be missing")
        return fallback_response
    
    # Convert messages to properly typed message objects
    typed_messages: List[ChatCompletionMessageParam] = []
    
    for msg in messages:
        if 'role' in msg and 'content' in msg:
            role = msg['role']
            content = msg['content']
            
            if role == 'system':
                typed_messages.append({"role": "system", "content": content})
            elif role == 'user':
                typed_messages.append({"role": "user", "content": content})
            elif role == 'assistant':
                typed_messages.append({"role": "assistant", "content": content})
    
    # Define the closure function to be called by safe_openai_call
    def execute_chat_completion():
        # Check if we have a valid client and messages
        if not openai_client:
            return fallback_response
            
        if not typed_messages:
            warning("No valid messages for chat completion")
            return fallback_response
            
        # Make the API call
        completion = openai_client.chat.completions.create(
            model=model,
            messages=typed_messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # Extract and return the response
        if completion and completion.choices:
            result = completion.choices[0].message.content
            return result.strip() if result else fallback_response
        return fallback_response
    
    result = safe_openai_call(
        execute_chat_completion,
        fallback_value=fallback_response
    )
    
    return result if result is not None else fallback_response

# Supported languages
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'zh': 'Chinese',
    'ja': 'Japanese',
    'ru': 'Russian',
    'pt': 'Portuguese'
}

# Language direction for CSS
RTL_LANGUAGES = {'ar', 'he', 'fa', 'ur'}

# Default language
DEFAULT_LANGUAGE = 'en'

# Translations cache
_translations_cache = {}


def detect_language(text):
    """
    Detect the language of a given text.
    
    Args:
        text (str): The text to analyze.
        
    Returns:
        str: The language code (ISO 639-1) or 'en' if detection fails.
    """
    if not text or len(text.strip()) < 3:
        return DEFAULT_LANGUAGE
    
    if not openai_client:
        # Simple fallback - check for specific characters
        # This is a very basic approach and not very accurate
        text = text.lower()
        
        # Check for Chinese characters
        if any('\u4e00' <= char <= '\u9fff' for char in text):
            return 'zh'
            
        # Check for Japanese characters (Hiragana or Katakana)
        if any('\u3040' <= char <= '\u30ff' for char in text):
            return 'ja'
            
        # Check for Cyrillic (Russian)
        if any('\u0400' <= char <= '\u04FF' for char in text):
            return 'ru'
            
        # For other languages, a more sophisticated approach would be needed
        # Default to English for now in this fallback
        return DEFAULT_LANGUAGE
    
    # Use the safe chat completion helper
    prompt = f"""Detect the language of the following text. Respond with only the ISO 639-1 language code (e.g., 'en' for English, 'es' for Spanish, etc.).

Text: "{text}"

Language code:"""

    messages = [
        {"role": "system", "content": "You are a language detection specialist. Respond with only the ISO 639-1 language code."},
        {"role": "user", "content": prompt}
    ]
    
    # Use our safe chat completion function with appropriate parameters
    lang_code = safe_chat_completion(
        messages=messages,
        model=DEFAULT_MODEL,
        max_tokens=10,
        temperature=0.3,  # Lower temperature for more deterministic output
        fallback_response=DEFAULT_LANGUAGE
    ).lower()
    
    # Extract the language code if it's wrapped in quotes or other characters
    if "'" in lang_code or '"' in lang_code:
        lang_code = ''.join(c for c in lang_code if c.isalpha())
    
    # Verify it's a supported language code, default to English if not
    if lang_code in SUPPORTED_LANGUAGES:
        return lang_code
    
    return DEFAULT_LANGUAGE


def translate_text(text, target_lang='en', source_lang=None):
    """
    Translate text to the target language.
    
    Args:
        text (str): The text to translate.
        target_lang (str): The target language code.
        source_lang (str, optional): The source language code. If not provided, it will be detected.
        
    Returns:
        str: The translated text or original text if translation fails.
    """
    if not text or len(text.strip()) < 3:
        return text
    
    # If target is already the source language, no need to translate
    if source_lang and source_lang == target_lang:
        return text
    
    if target_lang == DEFAULT_LANGUAGE and not source_lang:
        # Assume it's already in English if we're translating to English and 
        # don't know the source language
        return text
    
    if not openai_client:
        # Cannot translate without OpenAI API
        return text
    
    # Detect source language if not provided
    if not source_lang:
        source_lang = detect_language(text)
        
        # If source is already the target language, no need to translate
        if source_lang == target_lang:
            return text
    
    # Use safe chat completion for translation
    prompt = f"""Translate the following text from {SUPPORTED_LANGUAGES.get(source_lang, source_lang)} to {SUPPORTED_LANGUAGES.get(target_lang, target_lang)}.
Only provide the translated text with no additional explanations or notes.

Text: "{text}"

Translation:"""
    
    messages = [
        {"role": "system", "content": "You are a professional translator. Provide only the translated text with no additional comments."},
        {"role": "user", "content": prompt}
    ]
    
    # Use our safe chat completion function with appropriate parameters
    translated_text = safe_chat_completion(
        messages=messages,
        model=DEFAULT_MODEL,
        max_tokens=1000,
        temperature=0.3,  # Lower temperature for more accurate translation
        fallback_response=text  # Return original text if translation fails
    )
    
    # If we got a valid response, clean it up
    if translated_text and translated_text != text:
        # Remove quotes if they were added by the AI
        if (translated_text.startswith('"') and translated_text.endswith('"')) or \
           (translated_text.startswith("'") and translated_text.endswith("'")):
            translated_text = translated_text[1:-1]
    
    return translated_text


@lru_cache(maxsize=8)
def load_translations(lang_code):
    """
    Load translations for a specific language.
    
    Args:
        lang_code (str): The language code.
        
    Returns:
        dict: A dictionary of translations.
    """
    if lang_code == DEFAULT_LANGUAGE:
        return {}
    
    if lang_code in _translations_cache:
        return _translations_cache[lang_code]
    
    try:
        # Try to load from file first
        translation_file = f"translations/{lang_code}.json"
        
        if os.path.exists(translation_file):
            with open(translation_file, 'r', encoding='utf-8') as f:
                translations = json.load(f)
                _translations_cache[lang_code] = translations
                return translations
        
        # If no file exists, return empty dict
        _translations_cache[lang_code] = {}
        return {}
        
    except Exception as e:
        error(f"Error loading translations for {lang_code}: {e}")
        _translations_cache[lang_code] = {}
        return {}


def translate_ui_text(text_key, target_lang='en', default=None):
    """
    Get the translated UI text for a specific key.
    
    Args:
        text_key (str): The text key in the translations dictionary.
        target_lang (str): The target language code.
        default (str, optional): Default text if translation is not found.
        
    Returns:
        str: The translated text or default/key if not found.
    """
    if target_lang == DEFAULT_LANGUAGE:
        return default or text_key
    
    translations = load_translations(target_lang)
    
    # If key exists in translations, return it
    if text_key in translations:
        return translations[text_key]
    
    # If default is provided, return that
    if default:
        # Optionally translate the default text if it's not a key
        return translate_text(default, target_lang, DEFAULT_LANGUAGE)
    
    # Otherwise return the key itself
    return text_key


def is_rtl(lang_code):
    """
    Check if a language is right-to-left.
    
    Args:
        lang_code (str): The language code.
        
    Returns:
        bool: True if the language is RTL, False otherwise.
    """
    return lang_code in RTL_LANGUAGES


def get_language_name(lang_code):
    """
    Get the display name of a language.
    
    Args:
        lang_code (str): The language code.
        
    Returns:
        str: The language name.
    """
    return SUPPORTED_LANGUAGES.get(lang_code, lang_code)


def get_supported_languages():
    """
    Get a list of supported languages.
    
    Returns:
        dict: A dictionary of supported language codes and their names.
    """
    return SUPPORTED_LANGUAGES


def translate_content(content, target_lang='en'):
    """
    Translate a content object (dictionary with text fields).
    
    Args:
        content (dict): The content dictionary.
        target_lang (str): The target language code.
        
    Returns:
        dict: The translated content dictionary.
    """
    if target_lang == DEFAULT_LANGUAGE:
        return content
    
    if not isinstance(content, dict):
        if isinstance(content, str):
            return translate_text(content, target_lang)
        return content
    
    # Create a new dictionary to hold the translations
    translated_content = {}
    
    # Translate each field, recursively handling nested dictionaries and lists
    for key, value in content.items():
        if isinstance(value, str):
            translated_content[key] = translate_text(value, target_lang)
        elif isinstance(value, dict):
            translated_content[key] = translate_content(value, target_lang)
        elif isinstance(value, list):
            # Handle lists of strings or dictionaries
            translated_list = []
            for item in value:
                if isinstance(item, str):
                    translated_list.append(translate_text(item, target_lang))
                elif isinstance(item, dict):
                    translated_list.append(translate_content(item, target_lang))
                else:
                    translated_list.append(item)
            translated_content[key] = translated_list
        else:
            # For non-string values (like numbers, booleans), keep as is
            translated_content[key] = value
    
    return translated_content