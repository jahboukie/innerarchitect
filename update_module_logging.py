#!/usr/bin/env python3
"""
Script to update modules to use the logging_config system.

This script:
1. Adds the necessary import statements
2. Creates a module-specific logger
3. Updates logging calls to use the new system
"""

import os
import re
import sys

def read_file(filename):
    """Read file content."""
    with open(filename, 'r') as f:
        return f.read()

def write_file(filename, content):
    """Write content to file."""
    with open(filename, 'w') as f:
        f.write(content)

def update_imports(content, module_name):
    """
    Add imports for logging_config and module-specific logger.
    Returns (updated_content, has_logging_import, has_logger_definition)
    """
    # Check if logging imports already exist
    if "from logging_config import" in content:
        return content, True, "logger = get_logger" in content
    
    # Check for traditional logging import
    has_logging_import = "import logging" in content
    
    # For import insertion point, find the last import statement
    import_lines = re.findall(r'^(?:from|import) .*$', content, re.MULTILINE)
    if import_lines:
        last_import = import_lines[-1]
        last_import_index = content.find(last_import) + len(last_import)
        
        # Insert the logging import after the last import
        logging_import = "\n\nfrom logging_config import get_logger, info, error, debug, warning, critical, exception\n\n"
        content = content[:last_import_index] + logging_import + content[last_import_index:]
        
        # Add logger definition after imports
        logger_def = f"# Get module-specific logger\nlogger = get_logger('{module_name}')\n\n"
        
        # Find where to put the logger definition - after imports but before any code
        first_non_import = re.search(r'^\s*[^#\s]', content[last_import_index + len(logging_import):], re.MULTILINE)
        if first_non_import:
            first_non_import_index = last_import_index + len(logging_import) + first_non_import.start()
            content = content[:first_non_import_index] + logger_def + content[first_non_import_index:]
        else:
            content = content + logger_def
        
        return content, True, True
    else:
        # No imports found, add to top of file
        logging_import = "from logging_config import get_logger, info, error, debug, warning, critical, exception\n\n"
        logger_def = f"# Get module-specific logger\nlogger = get_logger('{module_name}')\n\n"
        content = logging_import + logger_def + content
        return content, True, True

def update_logging_calls(content):
    """
    Update logging calls to use our new system.
    Returns (updated_content, updates_made)
    """
    original_content = content
    
    patterns = [
        (r'logging\.info\((.*?)\)', r'info(\1)'),
        (r'logging\.error\((.*?)\)', r'error(\1)'),
        (r'logging\.debug\((.*?)\)', r'debug(\1)'),
        (r'logging\.warning\((.*?)\)', r'warning(\1)'),
        (r'logging\.critical\((.*?)\)', r'critical(\1)'),
        (r'logging\.exception\((.*?)\)', r'exception(\1)'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    # Remove logging.basicConfig calls
    content = re.sub(
        r'logging\.basicConfig\(.*?\)',
        '# Logging is configured in logging_config.py',
        content
    )
    
    return content, content != original_content

def process_module(filename):
    """Process a module to use the new logging system."""
    if not os.path.exists(filename):
        print(f"Error: File {filename} not found")
        return False
    
    if not filename.endswith('.py'):
        print(f"Error: File {filename} is not a Python file")
        return False
    
    # Derive module name from filename
    module_name = os.path.basename(filename)
    if module_name.endswith('.py'):
        module_name = module_name[:-3]
    
    # Read file content
    content = read_file(filename)
    
    # Update imports
    content, has_imports, has_logger = update_imports(content, module_name)
    
    # Update logging calls
    content, made_call_updates = update_logging_calls(content)
    
    # Check if any changes were made
    if not (has_imports or made_call_updates):
        print(f"No changes needed for {filename}")
        return False
    
    # Write updated content back to file
    write_file(filename, content)
    print(f"Updated logging for {filename}")
    return True

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python update_module_logging.py <filename1> [filename2 ...]")
        sys.exit(1)
    
    updated = 0
    for filename in sys.argv[1:]:
        if process_module(filename):
            updated += 1
    
    print(f"Updated {updated} of {len(sys.argv) - 1} modules")

if __name__ == "__main__":
    main()