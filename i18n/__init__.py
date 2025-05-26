"""
Internationalization and Localization Framework for The Inner Architect.

This module provides a comprehensive i18n/l10n framework for the application, 
building on the existing translation functionality.

Features:
- Enhanced language detection
- Locale-aware formatting for dates, numbers, and currencies
- Message extraction and management
- Pluralization support
- Translation caching
- Fallback mechanisms
- Region-specific localization
"""

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

from .message_catalog import (
    load_messages,
    extract_messages,
    save_messages,
    merge_messages
)

# Default exports
__all__ = [
    'get_translation',
    'get_languages',
    'set_language',
    'get_current_language',
    'is_rtl_language',
    'get_language_name',
    'detect_language_from_header',
    'format_date',
    'format_time',
    'format_datetime',
    'format_number',
    'format_currency',
    'format_percent',
    'get_locale_info',
    'load_messages',
    'extract_messages',
    'save_messages',
    'merge_messages'
]