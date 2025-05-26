"""
Integration module for the InnerArchitect internationalization framework.

This module provides functions to integrate the i18n framework with the
main Flask application.
"""

from flask import Flask, g, request, session, url_for, redirect, flash
from typing import Optional, Dict, Any

# Import the i18n framework
from i18n.flask_integration import InnerArchitectI18n
from i18n.translations import (
    get_languages, 
    get_language_name,
    is_rtl_language,
    detect_language_from_header
)

def init_i18n(app: Flask) -> InnerArchitectI18n:
    """
    Initialize the i18n framework with the Flask application.
    
    Args:
        app: Flask application instance
        
    Returns:
        Initialized i18n extension
    """
    # Create and initialize the extension
    i18n = InnerArchitectI18n(app)
    
    # Register language selection route
    @app.route('/language/<lang_code>')
    def set_language(lang_code: str):
        """
        Set the user's preferred language.
        
        Args:
            lang_code: Language code to set
            
        Returns:
            Redirect to previous page or home
        """
        # Validate language
        if lang_code in get_languages():
            session['language'] = lang_code
            session.modified = True
            
            # Flash message in the new language
            if lang_code != 'en':
                # Get the translated message for the notification
                messages = {
                    'es': 'Idioma cambiado a Español',
                    'fr': 'Langue changée en Français',
                    'de': 'Sprache auf Deutsch geändert',
                    'zh': '语言已更改为中文',
                    'ja': '言語が日本語に変更されました',
                    'ru': 'Язык изменен на русский',
                    'pt': 'Idioma alterado para Português',
                    'ar': 'تم تغيير اللغة إلى العربية',
                    'hi': 'भाषा हिंदी में बदली गई',
                    'ko': '언어가 한국어로 변경되었습니다',
                    'it': 'Lingua cambiata in Italiano'
                }
                
                message = messages.get(
                    lang_code, 
                    f"Language changed to {get_language_name(lang_code)}"
                )
                flash(message, "info")
            else:
                flash("Language changed to English", "info")
        
        # Redirect back to referrer or home
        referrer = request.referrer
        if referrer and referrer.startswith(request.host_url):
            return redirect(referrer)
        
        return redirect(url_for('index'))
    
    return i18n

def register_jinja_extensions(app: Flask):
    """
    Register Jinja2 extensions and filters for i18n.
    
    Args:
        app: Flask application instance
    """
    # Import formatters
    from i18n.formatting import (
        format_date,
        format_time,
        format_datetime, 
        format_number,
        format_currency,
        format_percent
    )
    
    # Add filters
    app.jinja_env.filters['format_date'] = format_date
    app.jinja_env.filters['format_time'] = format_time
    app.jinja_env.filters['format_datetime'] = format_datetime
    app.jinja_env.filters['format_number'] = format_number
    app.jinja_env.filters['format_currency'] = format_currency
    app.jinja_env.filters['format_percent'] = format_percent
    app.jinja_env.filters['is_rtl'] = is_rtl_language
    app.jinja_env.filters['lang_name'] = get_language_name