#!/usr/bin/env python
"""
Command-line tools for managing InnerArchitect translations.

This script provides utilities for extracting, updating, and managing translations.
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, List, Optional

from message_catalog import extract_messages, load_messages, save_messages, merge_messages
from translations import SUPPORTED_LANGUAGES, LANGUAGE_REGIONS

def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="InnerArchitect Internationalization CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Extract command
    extract_parser = subparsers.add_parser(
        "extract", 
        help="Extract translation strings from templates and Python files"
    )
    extract_parser.add_argument(
        "--output", "-o",
        help="Output file for extracted messages (default: messages.json)",
        default="messages.json"
    )
    
    # Update command
    update_parser = subparsers.add_parser(
        "update", 
        help="Update translation files with new strings"
    )
    update_parser.add_argument(
        "--lang", "-l",
        help="Language code to update (use 'all' for all languages)",
        default="all"
    )
    
    # Create command
    create_parser = subparsers.add_parser(
        "create", 
        help="Create a new translation file"
    )
    create_parser.add_argument(
        "lang",
        help="Language code to create"
    )
    
    # Status command
    status_parser = subparsers.add_parser(
        "status", 
        help="Show translation status for all languages"
    )
    
    # Init command
    init_parser = subparsers.add_parser(
        "init", 
        help="Initialize translations directory and config"
    )
    
    return parser

def extract_command(args: argparse.Namespace) -> int:
    """
    Extract translation strings and save to a file.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code (0 for success)
    """
    print(f"Extracting translation strings...")
    
    # Extract messages
    messages = extract_messages()
    
    # Save to file
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2, sort_keys=True)
    
    print(f"Extracted {len(messages)} strings to {args.output}")
    return 0

def update_command(args: argparse.Namespace) -> int:
    """
    Update translation files with new strings.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code (0 for success)
    """
    # Extract messages
    print(f"Extracting translation strings...")
    messages = extract_messages()
    print(f"Found {len(messages)} strings")
    
    # Determine languages to update
    languages = []
    if args.lang == "all":
        # Get all existing translation files
        translations_dir = "translations"
        if os.path.exists(translations_dir):
            for filename in os.listdir(translations_dir):
                if filename.endswith(".json"):
                    lang_code = filename[:-5]  # Remove .json extension
                    languages.append(lang_code)
        
        # Also include all supported languages
        for lang_code in SUPPORTED_LANGUAGES:
            if lang_code != "en" and lang_code not in languages:
                languages.append(lang_code)
    else:
        languages = [args.lang]
    
    # Update each language
    for lang_code in languages:
        print(f"Updating translations for {lang_code}...")
        
        # Merge messages with existing translations
        merged = merge_messages(messages, lang_code)
        
        # Save updated translations
        if save_messages(lang_code, merged):
            print(f"Updated {lang_code}.json with {len(merged)} strings")
        else:
            print(f"Error updating {lang_code}.json")
    
    return 0

def create_command(args: argparse.Namespace) -> int:
    """
    Create a new translation file.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code (0 for success)
    """
    lang_code = args.lang
    
    # Check if language is supported
    is_supported = (lang_code in SUPPORTED_LANGUAGES or lang_code in LANGUAGE_REGIONS)
    if not is_supported:
        print(f"Warning: {lang_code} is not in the list of supported languages")
        confirm = input("Continue anyway? (y/n): ")
        if confirm.lower() != 'y':
            return 1
    
    # Check if translation file already exists
    translation_path = f"translations/{lang_code}.json"
    if os.path.exists(translation_path):
        print(f"Error: {translation_path} already exists")
        return 1
    
    # Extract messages
    print(f"Extracting translation strings...")
    messages = extract_messages()
    
    # Create a new translation file with empty values
    new_translations = {}
    for key, default in messages.items():
        # Use default text as initial translation if available
        new_translations[key] = default if default is not None else key
    
    # Save the new translation file
    if save_messages(lang_code, new_translations):
        print(f"Created {lang_code}.json with {len(new_translations)} strings")
        return 0
    else:
        print(f"Error creating {lang_code}.json")
        return 1

def status_command(args: argparse.Namespace) -> int:
    """
    Show translation status for all languages.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code (0 for success)
    """
    # Extract messages to get total count
    print(f"Extracting translation strings...")
    messages = extract_messages()
    total_strings = len(messages)
    
    print(f"Found {total_strings} strings in source files")
    print("\nTranslation Status:")
    print("-------------------")
    
    # Check translations directory
    translations_dir = "translations"
    if not os.path.exists(translations_dir):
        print("No translations directory found")
        return 0
    
    # Get statistics for each translation file
    for filename in sorted(os.listdir(translations_dir)):
        if filename.endswith(".json"):
            lang_code = filename[:-5]  # Remove .json extension
            
            # Get language name
            language_name = None
            if lang_code in SUPPORTED_LANGUAGES:
                language_name = SUPPORTED_LANGUAGES[lang_code][0]
            elif lang_code in LANGUAGE_REGIONS:
                base_lang, region = LANGUAGE_REGIONS[lang_code][0:2]
                if base_lang in SUPPORTED_LANGUAGES:
                    language_name = f"{SUPPORTED_LANGUAGES[base_lang][0]} ({region})"
            
            if not language_name:
                language_name = lang_code
            
            # Load translations
            translations = load_messages(lang_code)
            translated_count = len(translations)
            
            # Calculate percentage
            if total_strings > 0:
                percentage = (translated_count / total_strings) * 100
            else:
                percentage = 100
            
            # Print status
            print(f"{lang_code.ljust(8)} {language_name.ljust(20)} {translated_count}/{total_strings} strings ({percentage:.1f}%)")
    
    return 0

def init_command(args: argparse.Namespace) -> int:
    """
    Initialize translations directory and configuration.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code (0 for success)
    """
    # Create translations directory if it doesn't exist
    translations_dir = "translations"
    if not os.path.exists(translations_dir):
        os.makedirs(translations_dir)
        print(f"Created {translations_dir} directory")
    
    # Create a sample configuration file
    config = {
        "default_language": "en",
        "supported_languages": {
            lang: SUPPORTED_LANGUAGES[lang][0]
            for lang in SUPPORTED_LANGUAGES
        }
    }
    
    config_path = "translations/config.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"Created {config_path}")
    
    # Extract messages
    print(f"Extracting translation strings...")
    messages = extract_messages()
    
    # Create translation files for all supported languages
    for lang_code in SUPPORTED_LANGUAGES:
        if lang_code == "en":
            continue  # Skip English (the default language)
        
        translation_path = f"translations/{lang_code}.json"
        if not os.path.exists(translation_path):
            # Create a new translation file
            new_translations = {}
            for key, default in messages.items():
                new_translations[key] = default if default is not None else key
            
            if save_messages(lang_code, new_translations):
                print(f"Created {lang_code}.json with {len(new_translations)} strings")
            else:
                print(f"Error creating {lang_code}.json")
    
    print("\nInitialization complete!")
    print("You can now edit the translation files in the translations/ directory.")
    
    return 0

def main() -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Execute the appropriate command
    if args.command == "extract":
        return extract_command(args)
    elif args.command == "update":
        return update_command(args)
    elif args.command == "create":
        return create_command(args)
    elif args.command == "status":
        return status_command(args)
    elif args.command == "init":
        return init_command(args)
    else:
        parser.print_help()
        return 0

if __name__ == "__main__":
    sys.exit(main())