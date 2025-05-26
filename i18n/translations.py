"""
Translation management module for The Inner Architect's i18n framework.

This module builds on the existing language_util.py functionality, providing
enhanced translation management with better fallback, caching, and context
handling capabilities.
"""

import os
import json
import logging
from functools import lru_cache
from typing import Dict, Optional, List, Tuple, Any
from flask import g, request, session

# Import the existing language utilities for compatibility
import language_util

# Initialize logging
logger = logging.getLogger('i18n.translations')

# Constants
DEFAULT_LANGUAGE = language_util.DEFAULT_LANGUAGE
RTL_LANGUAGES = language_util.RTL_LANGUAGES

# Extended language support
# The format is: 'language_code': ('Language Name', 'Native Name')
SUPPORTED_LANGUAGES = {
    'en': ('English', 'English'),
    'es': ('Spanish', 'Español'),
    'fr': ('French', 'Français'),
    'de': ('German', 'Deutsch'),
    'zh': ('Chinese', '中文'),
    'ja': ('Japanese', '日本語'),
    'ru': ('Russian', 'Русский'),
    'pt': ('Portuguese', 'Português'),
    'ar': ('Arabic', 'العربية'),
    'hi': ('Hindi', 'हिन्दी'),
    'ko': ('Korean', '한국어'),
    'it': ('Italian', 'Italiano')
}

# Language regions for more specific localization
# These define country/region-specific variants of languages
# Format: 'language_region': ('base_language', 'Region Name', 'Native Region Name')
LANGUAGE_REGIONS = {
    'en-US': ('en', 'United States', 'United States'),
    'en-GB': ('en', 'United Kingdom', 'United Kingdom'),
    'en-CA': ('en', 'Canada', 'Canada'),
    'en-AU': ('en', 'Australia', 'Australia'),
    'es-ES': ('es', 'Spain', 'España'),
    'es-MX': ('es', 'Mexico', 'México'),
    'es-AR': ('es', 'Argentina', 'Argentina'),
    'fr-FR': ('fr', 'France', 'France'),
    'fr-CA': ('fr', 'Canada', 'Canada'),
    'pt-BR': ('pt', 'Brazil', 'Brasil'),
    'pt-PT': ('pt', 'Portugal', 'Portugal'),
    'zh-CN': ('zh', 'China', '中国'),
    'zh-TW': ('zh', 'Taiwan', '台湾')
}

# Translation cache
_translation_cache = {}

def get_languages() -> Dict[str, Tuple[str, str]]:
    """
    Get a dictionary of supported languages.
    
    Returns:
        Dict mapping language codes to tuples of (Language Name, Native Name)
    """
    return SUPPORTED_LANGUAGES

def get_regions() -> Dict[str, Tuple[str, str, str]]:
    """
    Get a dictionary of supported language regions.
    
    Returns:
        Dict mapping region codes to tuples of (base language, Region Name, Native Region Name)
    """
    return LANGUAGE_REGIONS

def get_language_name(lang_code: str, native: bool = False) -> str:
    """
    Get the display name of a language.
    
    Args:
        lang_code: The language code
        native: If True, return the native name (e.g. "Español" for Spanish)
              If False, return the English name (e.g. "Spanish")
              
    Returns:
        The language name
    """
    if lang_code in SUPPORTED_LANGUAGES:
        return SUPPORTED_LANGUAGES[lang_code][1 if native else 0]
    elif lang_code in LANGUAGE_REGIONS:
        # For regions, return the base language name with region in parentheses
        base_lang, region_name, native_region = LANGUAGE_REGIONS[lang_code]
        base_name = get_language_name(base_lang, native)
        region = native_region if native else region_name
        return f"{base_name} ({region})"
    
    # Fallback: return the code itself
    return lang_code

def is_rtl_language(lang_code: str) -> bool:
    """
    Check if a language is right-to-left.
    
    Args:
        lang_code: The language code
        
    Returns:
        True if the language is RTL, False otherwise
    """
    # If it's a region code, extract the base language
    if lang_code in LANGUAGE_REGIONS:
        lang_code = LANGUAGE_REGIONS[lang_code][0]
        
    return lang_code in RTL_LANGUAGES

def detect_language_from_header(accept_language_header: Optional[str] = None) -> str:
    """
    Detect language from Accept-Language HTTP header.
    
    Args:
        accept_language_header: The Accept-Language header value
                                If None, uses request.accept_languages
    
    Returns:
        The detected language code or default language
    """
    if accept_language_header is None and request:
        accept_languages = request.accept_languages
    else:
        # No header or no request context, return default
        if accept_language_header is None:
            return DEFAULT_LANGUAGE
        
        # Parse the Accept-Language header manually
        # Format is usually: en-US,en;q=0.9,fr;q=0.8
        languages = []
        for part in accept_language_header.split(','):
            if ';q=' in part:
                lang, weight = part.split(';q=')
                weight = float(weight)
            else:
                lang = part
                weight = 1.0
            languages.append((lang.strip(), weight))
        
        # Sort by weight
        accept_languages = sorted(languages, key=lambda x: x[1], reverse=True)
    
    # First check for exact region matches
    if accept_languages:
        for lang_code, _ in accept_languages:
            if lang_code in LANGUAGE_REGIONS:
                return lang_code
            
    # Then check for base language matches
    if accept_languages:
        for lang_code, _ in accept_languages:
            # Check for exact match
            if lang_code in SUPPORTED_LANGUAGES:
                return lang_code
            
            # Check if it's a region code we don't explicitly support
            base_lang = lang_code.split('-')[0]
            if base_lang in SUPPORTED_LANGUAGES:
                return base_lang
    
    # Fallback to default
    return DEFAULT_LANGUAGE

def get_current_language() -> str:
    """
    Get the current language from Flask's g object or session.
    
    Returns:
        The current language code
    """
    # First check g
    if hasattr(g, 'language'):
        return g.language
    
    # Then check session
    if 'language' in session:
        return session['language']
    
    # Fallback to default
    return DEFAULT_LANGUAGE

def set_language(lang_code: str) -> bool:
    """
    Set the current language in session.
    
    Args:
        lang_code: The language code to set
        
    Returns:
        True if successful, False otherwise
    """
    # Validate language code
    is_valid = (lang_code in SUPPORTED_LANGUAGES or lang_code in LANGUAGE_REGIONS)
    
    if is_valid:
        session['language'] = lang_code
        session.modified = True
        return True
    
    return False

@lru_cache(maxsize=16)
def load_translation_file(lang_code: str) -> Dict[str, str]:
    """
    Load translations for a language from file.
    
    Args:
        lang_code: The language code
        
    Returns:
        Dictionary of translations
    """
    # Default English has no translations file
    if lang_code == DEFAULT_LANGUAGE:
        return {}
    
    # Check cache first
    if lang_code in _translation_cache:
        return _translation_cache[lang_code]
    
    # Determine file path - handle both base languages and regions
    base_lang = lang_code
    if lang_code in LANGUAGE_REGIONS:
        base_lang = LANGUAGE_REGIONS[lang_code][0]
    
    base_translation_file = f"translations/{base_lang}.json"
    region_translation_file = f"translations/{lang_code}.json"
    
    translations = {}
    
    # Load base language first (if it's a region)
    if lang_code in LANGUAGE_REGIONS and os.path.exists(base_translation_file):
        try:
            with open(base_translation_file, 'r', encoding='utf-8') as f:
                translations.update(json.load(f))
        except Exception as e:
            logger.error(f"Error loading base translations for {base_lang}: {e}")
    
    # Then load region-specific translations (which override base ones)
    translation_file = region_translation_file if lang_code in LANGUAGE_REGIONS else base_translation_file
    
    if os.path.exists(translation_file):
        try:
            with open(translation_file, 'r', encoding='utf-8') as f:
                translations.update(json.load(f))
        except Exception as e:
            logger.error(f"Error loading translations for {lang_code}: {e}")
    
    # Cache the result
    _translation_cache[lang_code] = translations
    return translations

def get_translation(key: str, default: Optional[str] = None, lang_code: Optional[str] = None) -> str:
    """
    Get translated text for a key.
    
    Args:
        key: The translation key
        default: Default text if translation is not found
        lang_code: Language code to use (if None, uses current language)
        
    Returns:
        Translated text or default/key if not found
    """
    if lang_code is None:
        lang_code = get_current_language()
        
    # Default language returns default text
    if lang_code == DEFAULT_LANGUAGE:
        return default or key
    
    # Load translations
    translations = load_translation_file(lang_code)
    
    # Check if key exists in translations
    if key in translations:
        return translations[key]
    
    # If it's a region code and translation not found, try the base language
    if lang_code in LANGUAGE_REGIONS:
        base_lang = LANGUAGE_REGIONS[lang_code][0]
        base_translations = load_translation_file(base_lang)
        if key in base_translations:
            return base_translations[key]
    
    # Fallback to dynamic translation if we have claude_client
    if default and lang_code != DEFAULT_LANGUAGE and hasattr(language_util, 'claude_client') and language_util.claude_client:
        try:
            return language_util.translate_text(default, lang_code, DEFAULT_LANGUAGE)
        except Exception as e:
            logger.error(f"Error translating '{key}' dynamically: {e}")
    
    # Return default or key as last resort
    return default or key