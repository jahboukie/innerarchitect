"""
Flask integration for The Inner Architect's i18n framework.

This module provides a Flask extension that integrates the i18n framework
with Flask applications.
"""

from typing import Dict, Any, Optional, List, Callable
from flask import Flask, g, request, session, current_app
import logging

from .translations import (
    get_translation, 
    get_languages, 
    set_language, 
    get_current_language,
    is_rtl_language,
    get_language_name,
    detect_language_from_header
)

from .formatting import (
    format_date,
    format_time,
    format_datetime, 
    format_number,
    format_currency,
    format_percent,
    get_locale_info
)

# Initialize logging
logger = logging.getLogger('i18n.flask_integration')

class InnerArchitectI18n:
    """
    Flask extension for The Inner Architect's i18n framework.
    
    This extension integrates the i18n framework with Flask applications,
    providing translations and locale-aware formatting in templates.
    """
    
    def __init__(self, app=None):
        """
        Initialize the extension.
        
        Args:
            app: Flask application instance (or None to use init_app)
        """
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """
        Initialize the extension with a Flask application.
        
        Args:
            app: Flask application instance
        """
        # Store extension on app
        app.i18n = self
        
        # Set up before_request handler to initialize language
        app.before_request(self._before_request)
        
        # Add template helpers
        self._register_template_helpers(app)
        
        # Add the extension to extensions list
        app.extensions['inner_architect_i18n'] = self
    
    def _before_request(self):
        """
        Before request handler that sets up language and locale information.
        
        This is automatically registered with the Flask app.
        """
        # Set default language if not in session
        if 'language' not in session:
            # Try to detect from Accept-Language header
            session['language'] = detect_language_from_header(
                request.headers.get('Accept-Language')
            )
        
        # Store language in g for templates
        g.language = session.get('language', 'en')
        g.languages = get_languages()
        g.is_rtl = is_rtl_language(g.language)
        
        # Store locale info in g
        g.locale_info = get_locale_info(g.language)
    
    def _register_template_helpers(self, app: Flask):
        """
        Register template helper functions.
        
        Args:
            app: Flask application instance
        """
        # Translation function for templates
        @app.context_processor
        def add_translation_helpers():
            """Add translation helpers to template context."""
            def translate(key, default=None):
                """Translate a key to the current language."""
                return get_translation(key, default, g.language)
            
            # Add various helpers to template context
            return {
                'translate': translate,
                't': translate,  # Shorthand alias
                'format_date': format_date,
                'format_time': format_time,
                'format_datetime': format_datetime,
                'format_number': format_number,
                'format_currency': format_currency,
                'format_percent': format_percent,
                'is_rtl': is_rtl_language,
                'get_language_name': get_language_name
            }
        
        # For compatibility with the existing g.translate
        app.before_request(self._setup_g_translate)
    
    def _setup_g_translate(self):
        """Set up g.translate for compatibility with existing code."""
        def translate(text_key, default=None):
            """Translate a key to the current language."""
            return get_translation(text_key, default, g.language)
        
        g.translate = translate
    
    def get_translation(self, key: str, default: Optional[str] = None, lang_code: Optional[str] = None) -> str:
        """
        Get a translation for a key.
        
        Args:
            key: Translation key
            default: Default text if translation is not found
            lang_code: Language code (if None, uses current language)
            
        Returns:
            Translated text
        """
        if lang_code is None:
            lang_code = get_current_language()
        
        return get_translation(key, default, lang_code)
    
    def set_language(self, lang_code: str) -> bool:
        """
        Set the current language.
        
        Args:
            lang_code: Language code
            
        Returns:
            True if successful, False otherwise
        """
        return set_language(lang_code)