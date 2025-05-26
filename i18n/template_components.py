"""
Template components for internationalized UI elements.

This module provides Jinja2 macros and functions for rendering common 
internationalized UI components.
"""

from typing import Dict, Any, Optional, List, Union
from datetime import datetime, date, time
from flask import g

from .translations import get_translation, get_language_name, is_rtl_language
from .formatting import format_date, format_number, format_currency

def render_language_selector(
    current_lang: str,
    languages: Dict[str, Any],
    class_name: str = "dropdown",
    button_class: str = "btn btn-sm btn-outline-primary dropdown-toggle rounded-pill",
    dropdown_class: str = "dropdown-menu dropdown-menu-end shadow-sm border-light",
    item_class: str = "dropdown-item",
    active_class: str = "active",
    icon_class: str = "fas fa-globe me-1",
    change_url: str = None
) -> str:
    """
    Render a language selector dropdown.
    
    Args:
        current_lang: Current language code
        languages: Dictionary of language codes to names
        class_name: CSS class for the dropdown container
        button_class: CSS class for the dropdown button
        dropdown_class: CSS class for the dropdown menu
        item_class: CSS class for dropdown items
        active_class: CSS class for the active language
        icon_class: CSS class for the globe icon
        change_url: URL pattern for language change (e.g., "/language/{lang}")
                   The {lang} placeholder will be replaced with the language code
    
    Returns:
        HTML for the language selector
    """
    if change_url is None:
        change_url = "/language/{lang}"
    
    html = f'<div class="{class_name}">\n'
    html += f'  <button class="{button_class}" type="button" id="languageDropdown" '
    html += f'data-bs-toggle="dropdown" aria-expanded="false">\n'
    html += f'    <i class="{icon_class}"></i> {current_lang.upper()}\n'
    html += f'  </button>\n'
    html += f'  <ul class="{dropdown_class}" aria-labelledby="languageDropdown">\n'
    
    for code, name_tuple in languages.items():
        name = name_tuple[1]  # Use native name
        active = ' class="active"' if code == current_lang else ''
        url = change_url.replace('{lang}', code)
        
        html += f'    <li>\n'
        html += f'      <a class="{item_class} {active_class if code == current_lang else ""}" href="{url}">\n'
        html += f'        {name}\n'
        html += f'      </a>\n'
        html += f'    </li>\n'
    
    html += f'  </ul>\n'
    html += f'</div>'
    
    return html

def render_date(
    date_value: Union[datetime, date, str],
    format_str: Optional[str] = None,
    locale: Optional[str] = None
) -> str:
    """
    Render a date according to locale conventions.
    
    Args:
        date_value: Date to format
        format_str: Optional custom format string
        locale: Locale to use (if None, uses current language)
        
    Returns:
        Formatted date HTML
    """
    formatted = format_date(date_value, format_str, locale)
    
    # If it's a datetime or date object, add a title with ISO format for precision
    title = ""
    if isinstance(date_value, (datetime, date)):
        if isinstance(date_value, datetime):
            iso_date = date_value.date().isoformat()
        else:
            iso_date = date_value.isoformat()
        title = f' title="{iso_date}"'
    
    return f'<time{title}>{formatted}</time>'

def render_currency(
    amount: Union[int, float, str],
    currency: Optional[str] = None,
    locale: Optional[str] = None
) -> str:
    """
    Render a currency amount according to locale conventions.
    
    Args:
        amount: Amount to format
        currency: Currency code
        locale: Locale to use (if None, uses current language)
        
    Returns:
        Formatted currency HTML
    """
    formatted = format_currency(amount, currency, locale)
    
    # Use numeric value as title for clarity
    if isinstance(amount, (int, float)):
        title = f' title="{amount}"'
    else:
        title = ""
    
    return f'<span class="currency"{title}>{formatted}</span>'

def render_number(
    number: Union[int, float, str],
    decimal_places: Optional[int] = None,
    locale: Optional[str] = None
) -> str:
    """
    Render a number according to locale conventions.
    
    Args:
        number: Number to format
        decimal_places: Number of decimal places
        locale: Locale to use (if None, uses current language)
        
    Returns:
        Formatted number HTML
    """
    formatted = format_number(number, decimal_places, locale)
    
    # Use numeric value as title for clarity
    if isinstance(number, (int, float)):
        title = f' title="{number}"'
    else:
        title = ""
    
    return f'<span class="number"{title}>{formatted}</span>'

def get_direction_attrs(lang_code: Optional[str] = None) -> str:
    """
    Get HTML attributes for text direction.
    
    Args:
        lang_code: Language code (if None, uses current language)
        
    Returns:
        HTML attributes for text direction
    """
    if lang_code is None:
        # Use g.language if available, otherwise get from session
        lang_code = getattr(g, 'language', None)
    
    # Check if language is RTL
    if is_rtl_language(lang_code):
        return 'dir="rtl"'
    else:
        return 'dir="ltr"'

def render_multilingual_text(
    translations: Dict[str, str],
    default_lang: str = 'en',
    class_name: str = 'multilingual-text'
) -> str:
    """
    Render text in multiple languages with appropriate language tags.
    
    Args:
        translations: Dictionary mapping language codes to translations
        default_lang: Default language to show
        class_name: CSS class for the container
        
    Returns:
        HTML with all translations (visible according to user's language)
    """
    html = f'<span class="{class_name}">\n'
    
    # Get current language from g if available
    current_lang = getattr(g, 'language', default_lang)
    
    # Add spans for each language
    for lang, text in translations.items():
        is_current = lang == current_lang
        direction = get_direction_attrs(lang)
        display = 'inline' if is_current else 'none'
        
        html += f'  <span lang="{lang}" {direction} class="lang-{lang}" style="display: {display};">{text}</span>\n'
    
    html += '</span>'
    return html