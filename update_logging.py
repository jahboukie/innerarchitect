#!/usr/bin/env python3
"""
Script to update logging calls in files to use the new logging_config module.

This script scans Python files and replaces traditional logging calls with our
standardized logging functions from logging_config.
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

def update_logging_calls(content):
    """
    Update logging calls to use the new logging_config module.
    
    Example transforms:
    - logging.info("message") -> info("message")
    - logging.error("error") -> error("error")
    - logging.debug("debug") -> debug("debug")
    - logging.warning("warning") -> warning("warning")
    - logging.critical("critical") -> critical("critical")
    - logging.exception("exception") -> exception("exception")
    """
    patterns = [
        (r'logging\.info\((.*?)\)', r'info(\1)'),
        (r'logging\.error\((.*?)\)', r'error(\1)'),
        (r'logging\.debug\((.*?)\)', r'debug(\1)'),
        (r'logging\.warning\((.*?)\)', r'warning(\1)'),
        (r'logging\.critical\((.*?)\)', r'critical(\1)'),
        (r'logging\.exception\((.*?)\)', r'exception(\1)'),
    ]
    
    updated_content = content
    for pattern, replacement in patterns:
        # Using a non-greedy match to handle multi-line logging statements
        updated_content = re.sub(pattern, replacement, updated_content)
    
    # Replace logging.basicConfig calls
    updated_content = re.sub(
        r'logging\.basicConfig\(.*?\)',
        '# Logging is configured in logging_config.py',
        updated_content
    )
    
    return updated_content

def main():
    if len(sys.argv) < 2:
        print("Usage: python update_logging.py <filename>")
        sys.exit(1)
    
    filename = sys.argv[1]
    if not os.path.exists(filename):
        print(f"Error: File {filename} not found")
        sys.exit(1)
    
    if not filename.endswith('.py'):
        print(f"Error: File {filename} is not a Python file")
        sys.exit(1)
    
    # Read file content
    content = read_file(filename)
    
    # Update logging calls
    updated_content = update_logging_calls(content)
    
    # Check if any changes were made
    if content == updated_content:
        print(f"No changes needed for {filename}")
        sys.exit(0)
    
    # Write updated content back to file
    write_file(filename, updated_content)
    print(f"Updated logging calls in {filename}")

if __name__ == "__main__":
    main()