"""
Message catalog management for The Inner Architect's i18n framework.

This module provides utilities for extracting, loading, and managing translation
messages across the application.
"""

import os
import json
import re
import glob
from typing import Dict, Any, List, Set, Optional, Tuple, Iterator
import logging

# Initialize logging
logger = logging.getLogger('i18n.message_catalog')

def load_messages(lang_code: str) -> Dict[str, str]:
    """
    Load messages for a specific language.
    
    Args:
        lang_code: Language code
        
    Returns:
        Dictionary of message translations
    """
    translation_path = f"translations/{lang_code}.json"
    
    if not os.path.exists(translation_path):
        return {}
    
    try:
        with open(translation_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing {translation_path}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error loading {translation_path}: {e}")
        return {}

def save_messages(lang_code: str, messages: Dict[str, str]) -> bool:
    """
    Save messages for a specific language.
    
    Args:
        lang_code: Language code
        messages: Dictionary of message translations
        
    Returns:
        True if successful, False otherwise
    """
    translation_path = f"translations/{lang_code}.json"
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(translation_path), exist_ok=True)
    
    try:
        with open(translation_path, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving {translation_path}: {e}")
        return False

def extract_flask_template_messages(template_dir: str = "templates") -> Set[Tuple[str, Optional[str]]]:
    """
    Extract translation keys from Flask templates.
    
    This function looks for patterns like:
    - {{ g.translate('key', 'default') }}
    - {{ g.translate('key') }}
    
    Args:
        template_dir: Directory containing templates
        
    Returns:
        Set of tuples (key, default_text) for each extracted message
    """
    messages = set()
    
    # Regular expression to match g.translate calls
    translate_pattern = re.compile(r"g\.translate\('([^']+)'(?:\s*,\s*'([^']+)')?", re.DOTALL)
    
    # Find all template files
    template_files = glob.glob(f"{template_dir}/**/*.html", recursive=True)
    
    for file_path in template_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Find all translate calls
                for match in translate_pattern.finditer(content):
                    key = match.group(1)
                    default = match.group(2) if match.group(2) else None
                    messages.add((key, default))
        
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
    
    return messages

def extract_python_messages(source_dir: str = ".") -> Set[Tuple[str, Optional[str]]]:
    """
    Extract translation keys from Python source files.
    
    This function looks for patterns like:
    - g.translate('key', 'default')
    - g.translate('key')
    - translate_ui_text('key', lang, 'default')
    - translate_ui_text('key', lang)
    
    Args:
        source_dir: Directory containing Python source files
        
    Returns:
        Set of tuples (key, default_text) for each extracted message
    """
    messages = set()
    
    # Regular expressions to match different translation call patterns
    patterns = [
        # g.translate('key', 'default')
        re.compile(r"g\.translate\('([^']+)'(?:\s*,\s*'([^']+)')?", re.DOTALL),
        
        # translate_ui_text('key', lang, 'default')
        re.compile(r"translate_ui_text\('([^']+)'(?:\s*,[^,]+)?(?:\s*,\s*'([^']+)')?", re.DOTALL),
        
        # get_translation('key', 'default')
        re.compile(r"get_translation\('([^']+)'(?:\s*,\s*'([^']+)')?", re.DOTALL)
    ]
    
    # Find all Python files
    python_files = glob.glob(f"{source_dir}/**/*.py", recursive=True)
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Apply each pattern
                for pattern in patterns:
                    for match in pattern.finditer(content):
                        key = match.group(1)
                        default = match.group(2) if len(match.groups()) > 1 and match.group(2) else None
                        messages.add((key, default))
        
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
    
    return messages

def extract_messages() -> Dict[str, Optional[str]]:
    """
    Extract all translation messages from templates and Python files.
    
    Returns:
        Dictionary mapping keys to default texts
    """
    # Extract messages from templates and Python files
    template_messages = extract_flask_template_messages()
    python_messages = extract_python_messages()
    
    # Combine messages
    all_messages = template_messages.union(python_messages)
    
    # Convert to dictionary (prioritizing non-None defaults)
    message_dict = {}
    for key, default in all_messages:
        if key in message_dict:
            # Keep existing default if it's not None
            if message_dict[key] is None:
                message_dict[key] = default
        else:
            message_dict[key] = default
    
    return message_dict

def merge_messages(extracted_messages: Dict[str, Optional[str]], lang_code: str) -> Dict[str, str]:
    """
    Merge extracted messages with existing translations.
    
    This preserves existing translations while adding new keys.
    
    Args:
        extracted_messages: Dictionary of extracted messages (key -> default)
        lang_code: Language code to merge with
        
    Returns:
        Updated messages dictionary
    """
    # Load existing messages
    existing = load_messages(lang_code)
    
    # Create a new dictionary with all keys
    merged = {}
    
    # Add all extracted messages
    for key, default in extracted_messages.items():
        if key in existing:
            # Keep existing translation
            merged[key] = existing[key]
        else:
            # Add new key with default as the value to translate
            # For languages other than English, we'll just use the default for now
            # (Translators will need to update these values)
            merged[key] = default if default is not None else key
    
    # Also include any keys in the existing translations that weren't extracted
    # (This preserves translations for legacy keys)
    for key, value in existing.items():
        if key not in merged:
            merged[key] = value
    
    return merged