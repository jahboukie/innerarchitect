"""
Locale-aware formatting module for The Inner Architect's i18n framework.

This module provides formatting functions for dates, times, numbers, and currencies
based on the user's locale preferences.
"""

import datetime
from typing import Dict, Any, Optional, Union, Tuple, List
from decimal import Decimal
import re

from .translations import get_current_language

# Locale configuration
# Format: 'locale': {
#    'date_format': str,      # Format for date (strftime format)
#    'time_format': str,      # Format for time (strftime format)
#    'datetime_format': str,  # Format for datetime (strftime format)
#    'decimal_separator': str,  # Character used to separate decimal part
#    'thousand_separator': str, # Character used to separate thousands
#    'currency_symbol': str,  # Currency symbol
#    'currency_format': str,  # Format for currency (using {symbol} and {value})
#    'percent_format': str,   # Format for percentages
# }
LOCALE_FORMATS = {
    # English (US)
    'en': {
        'date_format': '%m/%d/%Y',
        'time_format': '%I:%M %p',
        'datetime_format': '%m/%d/%Y %I:%M %p',
        'decimal_separator': '.',
        'thousand_separator': ',',
        'currency_symbol': '$',
        'currency_format': '{symbol}{value}',
        'percent_format': '{value}%'
    },
    # English (UK)
    'en-GB': {
        'date_format': '%d/%m/%Y',
        'time_format': '%H:%M',
        'datetime_format': '%d/%m/%Y %H:%M',
        'decimal_separator': '.',
        'thousand_separator': ',',
        'currency_symbol': '£',
        'currency_format': '{symbol}{value}',
        'percent_format': '{value}%'
    },
    # Spanish
    'es': {
        'date_format': '%d/%m/%Y',
        'time_format': '%H:%M',
        'datetime_format': '%d/%m/%Y %H:%M',
        'decimal_separator': ',',
        'thousand_separator': '.',
        'currency_symbol': '€',
        'currency_format': '{value} {symbol}',
        'percent_format': '{value}%'
    },
    # Spanish (Mexico)
    'es-MX': {
        'date_format': '%d/%m/%Y',
        'time_format': '%H:%M',
        'datetime_format': '%d/%m/%Y %H:%M',
        'decimal_separator': '.',
        'thousand_separator': ',',
        'currency_symbol': '$',
        'currency_format': '{symbol}{value}',
        'percent_format': '{value}%'
    },
    # French
    'fr': {
        'date_format': '%d/%m/%Y',
        'time_format': '%H:%M',
        'datetime_format': '%d/%m/%Y %H:%M',
        'decimal_separator': ',',
        'thousand_separator': ' ',
        'currency_symbol': '€',
        'currency_format': '{value} {symbol}',
        'percent_format': '{value} %'
    },
    # German
    'de': {
        'date_format': '%d.%m.%Y',
        'time_format': '%H:%M',
        'datetime_format': '%d.%m.%Y %H:%M',
        'decimal_separator': ',',
        'thousand_separator': '.',
        'currency_symbol': '€',
        'currency_format': '{value} {symbol}',
        'percent_format': '{value} %'
    },
    # Chinese
    'zh': {
        'date_format': '%Y-%m-%d',
        'time_format': '%H:%M',
        'datetime_format': '%Y-%m-%d %H:%M',
        'decimal_separator': '.',
        'thousand_separator': ',',
        'currency_symbol': '¥',
        'currency_format': '{symbol}{value}',
        'percent_format': '{value}%'
    },
    # Japanese
    'ja': {
        'date_format': '%Y/%m/%d',
        'time_format': '%H:%M',
        'datetime_format': '%Y/%m/%d %H:%M',
        'decimal_separator': '.',
        'thousand_separator': ',',
        'currency_symbol': '¥',
        'currency_format': '{symbol}{value}',
        'percent_format': '{value}%'
    },
    # Russian
    'ru': {
        'date_format': '%d.%m.%Y',
        'time_format': '%H:%M',
        'datetime_format': '%d.%m.%Y %H:%M',
        'decimal_separator': ',',
        'thousand_separator': ' ',
        'currency_symbol': '₽',
        'currency_format': '{value} {symbol}',
        'percent_format': '{value}%'
    },
    # Portuguese
    'pt': {
        'date_format': '%d/%m/%Y',
        'time_format': '%H:%M',
        'datetime_format': '%d/%m/%Y %H:%M',
        'decimal_separator': ',',
        'thousand_separator': '.',
        'currency_symbol': '€',
        'currency_format': '{value} {symbol}',
        'percent_format': '{value}%'
    },
    # Portuguese (Brazil)
    'pt-BR': {
        'date_format': '%d/%m/%Y',
        'time_format': '%H:%M',
        'datetime_format': '%d/%m/%Y %H:%M',
        'decimal_separator': ',',
        'thousand_separator': '.',
        'currency_symbol': 'R$',
        'currency_format': '{symbol} {value}',
        'percent_format': '{value}%'
    },
    # Arabic
    'ar': {
        'date_format': '%d/%m/%Y',
        'time_format': '%H:%M',
        'datetime_format': '%d/%m/%Y %H:%M',
        'decimal_separator': '٫',
        'thousand_separator': '٬',
        'currency_symbol': 'د.إ',
        'currency_format': '{value} {symbol}',
        'percent_format': '{value}٪'
    }
}

def get_locale_info(locale: Optional[str] = None) -> Dict[str, Any]:
    """
    Get formatting information for a locale.
    
    Args:
        locale: Locale code (if None, uses current language)
        
    Returns:
        Dict with formatting information
    """
    if locale is None:
        locale = get_current_language()
    
    # If locale exists, return it
    if locale in LOCALE_FORMATS:
        return LOCALE_FORMATS[locale]
    
    # For region codes, try to find the base language
    base_lang = locale.split('-')[0] if '-' in locale else locale
    if base_lang in LOCALE_FORMATS:
        return LOCALE_FORMATS[base_lang]
    
    # Default to English if not found
    return LOCALE_FORMATS['en']

def format_date(
    date: Union[datetime.date, datetime.datetime, str], 
    format_str: Optional[str] = None,
    locale: Optional[str] = None
) -> str:
    """
    Format a date according to locale conventions.
    
    Args:
        date: Date to format (date, datetime or ISO format string)
        format_str: Optional custom format string (strftime format)
        locale: Locale to use (if None, uses current language)
        
    Returns:
        Formatted date string
    """
    # Convert string to datetime if needed
    if isinstance(date, str):
        try:
            date = datetime.datetime.fromisoformat(date)
        except ValueError:
            # If it's not a valid ISO format, return the string as is
            return date
    
    # Get locale info
    locale_info = get_locale_info(locale)
    
    # Use provided format or locale default
    date_format = format_str or locale_info['date_format']
    
    # Format the date
    return date.strftime(date_format)

def format_time(
    time: Union[datetime.time, datetime.datetime, str], 
    format_str: Optional[str] = None,
    locale: Optional[str] = None
) -> str:
    """
    Format a time according to locale conventions.
    
    Args:
        time: Time to format (time, datetime or ISO format string)
        format_str: Optional custom format string (strftime format)
        locale: Locale to use (if None, uses current language)
        
    Returns:
        Formatted time string
    """
    # Convert string to datetime if needed
    if isinstance(time, str):
        try:
            # Try parsing as time only first
            try:
                time = datetime.time.fromisoformat(time)
            except ValueError:
                # If that fails, try as datetime
                time = datetime.datetime.fromisoformat(time)
        except ValueError:
            # If it's not a valid ISO format, return the string as is
            return time
    
    # Get locale info
    locale_info = get_locale_info(locale)
    
    # Use provided format or locale default
    time_format = format_str or locale_info['time_format']
    
    # Format the time
    return time.strftime(time_format)

def format_datetime(
    dt: Union[datetime.datetime, str], 
    format_str: Optional[str] = None,
    locale: Optional[str] = None
) -> str:
    """
    Format a datetime according to locale conventions.
    
    Args:
        dt: Datetime to format (datetime or ISO format string)
        format_str: Optional custom format string (strftime format)
        locale: Locale to use (if None, uses current language)
        
    Returns:
        Formatted datetime string
    """
    # Convert string to datetime if needed
    if isinstance(dt, str):
        try:
            dt = datetime.datetime.fromisoformat(dt)
        except ValueError:
            # If it's not a valid ISO format, return the string as is
            return dt
    
    # Get locale info
    locale_info = get_locale_info(locale)
    
    # Use provided format or locale default
    datetime_format = format_str or locale_info['datetime_format']
    
    # Format the datetime
    return dt.strftime(datetime_format)

def format_number(
    number: Union[int, float, Decimal, str], 
    decimal_places: Optional[int] = None,
    locale: Optional[str] = None
) -> str:
    """
    Format a number according to locale conventions.
    
    Args:
        number: Number to format
        decimal_places: Number of decimal places to show (if None, uses all available)
        locale: Locale to use (if None, uses current language)
        
    Returns:
        Formatted number string
    """
    # Convert string to number if needed
    if isinstance(number, str):
        try:
            # Try as int first, then as float
            try:
                number = int(number)
            except ValueError:
                number = float(number)
        except ValueError:
            # If it's not a valid number, return the string as is
            return number
    
    # Get locale info
    locale_info = get_locale_info(locale)
    decimal_separator = locale_info['decimal_separator']
    thousand_separator = locale_info['thousand_separator']
    
    # Convert to string with specified decimal places
    if decimal_places is not None:
        # Use specified decimal places
        if isinstance(number, (int, float)):
            number_str = f"{number:.{decimal_places}f}"
        else:  # Decimal
            number_str = format(number, f".{decimal_places}f")
    else:
        # Use all available decimal places
        number_str = str(number)
    
    # Split into integer and decimal parts
    if '.' in number_str:
        int_part, dec_part = number_str.split('.')
    else:
        int_part, dec_part = number_str, ''
    
    # Add thousand separators to integer part
    int_part_with_separators = ''
    for i, digit in enumerate(reversed(int_part)):
        if i > 0 and i % 3 == 0:
            int_part_with_separators = thousand_separator + int_part_with_separators
        int_part_with_separators = digit + int_part_with_separators
    
    # Combine parts using locale's decimal separator
    if dec_part:
        return f"{int_part_with_separators}{decimal_separator}{dec_part}"
    else:
        return int_part_with_separators

def format_currency(
    amount: Union[int, float, Decimal, str],
    currency: Optional[str] = None,
    locale: Optional[str] = None
) -> str:
    """
    Format a currency amount according to locale conventions.
    
    Args:
        amount: Amount to format
        currency: Currency code (if None, uses locale default)
        locale: Locale to use (if None, uses current language)
        
    Returns:
        Formatted currency string
    """
    # Get locale info
    locale_info = get_locale_info(locale)
    
    # Format the number part with 2 decimal places
    value = format_number(amount, decimal_places=2, locale=locale)
    
    # Get currency symbol based on provided currency code or locale default
    if currency:
        # Map of currency codes to symbols
        currency_symbols = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'JPY': '¥',
            'CNY': '¥',
            'RUB': '₽',
            'BRL': 'R$',
            'INR': '₹',
            'AED': 'د.إ',
            'AUD': 'A$',
            'CAD': 'C$',
            'CHF': 'Fr',
            'MXN': 'Mex$'
        }
        symbol = currency_symbols.get(currency, currency)
    else:
        symbol = locale_info['currency_symbol']
    
    # Apply the currency format template
    return locale_info['currency_format'].format(symbol=symbol, value=value)

def format_percent(
    value: Union[float, Decimal, str],
    decimal_places: int = 1,
    locale: Optional[str] = None
) -> str:
    """
    Format a percentage according to locale conventions.
    
    Args:
        value: Value to format (0.01 = 1%)
        decimal_places: Number of decimal places to show
        locale: Locale to use (if None, uses current language)
        
    Returns:
        Formatted percentage string
    """
    # Convert string to float if needed
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            # If it's not a valid number, return the string as is
            return value
    
    # Convert to percentage (multiply by 100)
    percent_value = value * 100
    
    # Format the number
    formatted_value = format_number(percent_value, decimal_places=decimal_places, locale=locale)
    
    # Get locale info
    locale_info = get_locale_info(locale)
    
    # Apply the percentage format template
    return locale_info['percent_format'].format(value=formatted_value)