"""
Conventional Commit Standards Helper for Git Automation

This module implements tools to help create and validate conventional commit messages.
Following the Conventional Commits specification (https://www.conventionalcommits.org/)
"""

import re
import enum
from typing import List, Dict, Optional, Tuple, Any, Set


class CommitType(enum.Enum):
    """
    Standard conventional commit types
    """
    FEAT = "feat"       # New feature
    FIX = "fix"         # Bug fix
    DOCS = "docs"       # Documentation changes
    STYLE = "style"     # Code style changes (formatting, missing semicolons, etc)
    REFACTOR = "refactor"  # Code change that neither fixes a bug nor adds a feature
    PERF = "perf"       # Performance improvements
    TEST = "test"       # Adding or correcting tests
    BUILD = "build"     # Changes to build system or external dependencies
    CI = "ci"           # Changes to CI configuration files and scripts
    CHORE = "chore"     # Other changes that don't modify src or test files
    REVERT = "revert"   # Reverts a previous commit


# Regular expression for conventional commits
# format: type(scope?): description
CONVENTIONAL_COMMIT_REGEX = r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9-]+\))?: .+$"


def validate_commit_message(message: str) -> bool:
    """
    Check if a commit message follows the conventional commit format.
    
    Args:
        message: The commit message to validate
        
    Returns:
        True if the message follows the conventional format, False otherwise
    """
    # Skip validation for merge commits
    if message.startswith("Merge "):
        return True
    
    # Extract the first line (subject)
    subject = message.split("\n")[0].strip()
    
    # Check if it matches the conventional commit pattern
    return bool(re.match(CONVENTIONAL_COMMIT_REGEX, subject))


def parse_commit_message(message: str) -> Optional[Dict[str, Any]]:
    """
    Parse a conventional commit message into its components.
    
    Args:
        message: The commit message to parse
        
    Returns:
        Dictionary with type, scope (optional), and description, or None if not valid
    """
    # Skip parsing for merge commits
    if message.startswith("Merge "):
        return {
            "type": "merge",
            "scope": None,
            "description": message
        }
    
    # Extract the first line (subject)
    subject = message.split("\n")[0].strip()
    
    # Parse using regex
    match = re.match(r"^([a-z]+)(?:\(([a-z0-9-]+)\))?: (.+)$", subject)
    
    if not match:
        return None
    
    commit_type, scope, description = match.groups()
    
    # Get the message body (if any)
    body = "\n".join(message.split("\n")[1:]).strip()
    
    return {
        "type": commit_type,
        "scope": scope,
        "description": description,
        "body": body if body else None
    }


def create_conventional_commit(
    commit_type: CommitType, 
    description: str, 
    scope: Optional[str] = None, 
    body: Optional[str] = None,
    breaking_change: bool = False,
    issues: Optional[List[str]] = None
) -> str:
    """
    Create a commit message following the conventional commit format.
    
    Args:
        commit_type: The type of change
        description: A short description of the change
        scope: Optional scope of the change
        body: Optional detailed description
        breaking_change: Whether this is a breaking change
        issues: Optional list of issue references (e.g., "#123")
        
    Returns:
        Formatted commit message
    """
    # Ensure the first letter of the description is lowercase
    if description and len(description) > 0:
        description = description[0].lower() + description[1:]
    
    # Create the subject line
    if scope:
        subject = f"{commit_type.value}({scope}): {description}"
    else:
        subject = f"{commit_type.value}: {description}"
    
    # Add exclamation mark for breaking changes
    if breaking_change and "!" not in subject:
        subject = subject.replace(":", "!:", 1)
    
    # Build the full message
    message_parts = [subject]
    
    # Add body if provided
    if body:
        message_parts.append("")  # Empty line
        message_parts.append(body)
    
    # Add breaking change footer if needed
    if breaking_change:
        message_parts.append("")  # Empty line
        message_parts.append("BREAKING CHANGE: This commit introduces breaking changes.")
    
    # Add issue references if provided
    if issues and len(issues) > 0:
        message_parts.append("")  # Empty line
        
        for issue in issues:
            # Clean up issue reference
            clean_issue = issue.strip()
            if not clean_issue.startswith("#") and not clean_issue.startswith("fixes #"):
                clean_issue = f"#{clean_issue}"
            
            message_parts.append(f"Fixes {clean_issue}")
    
    return "\n".join(message_parts)


def suggest_commit_type(files_changed: List[str]) -> CommitType:
    """
    Suggest a commit type based on the files that were changed.
    
    Args:
        files_changed: List of files modified in the commit
        
    Returns:
        Suggested commit type
    """
    # Check if only documentation files were changed
    doc_extensions = {".md", ".txt", ".rst", ".adoc", ".doc", ".docx"}
    all_docs = all(any(f.endswith(ext) for ext in doc_extensions) for f in files_changed)
    if all_docs:
        return CommitType.DOCS
    
    # Check if only test files were changed
    test_patterns = {"test_", "_test", "spec_", "_spec", "/tests/", "/test/"}
    all_tests = all(any(pattern in f for pattern in test_patterns) for f in files_changed)
    if all_tests:
        return CommitType.TEST
    
    # Check if CI configuration files were changed
    ci_patterns = {".github/", "azure-pipelines", ".gitlab-ci", "jenkins", ".travis"}
    all_ci = all(any(pattern in f for pattern in ci_patterns) for f in files_changed)
    if all_ci:
        return CommitType.CI
    
    # Check if only style files were changed
    style_files = {".prettierrc", ".eslintrc", ".stylelintrc", ".editorconfig"}
    all_style = all(f in style_files for f in files_changed)
    if all_style:
        return CommitType.STYLE
    
    # Default to feature for new files, fix for modified files
    if any(not f.startswith("modified:") for f in files_changed):
        return CommitType.FEAT
    else:
        return CommitType.FIX


def analyze_changes(diff_content: str) -> Dict[str, Any]:
    """
    Analyze git diff output to understand the nature of changes.
    
    Args:
        diff_content: Output from git diff command
        
    Returns:
        Dictionary with analysis results
    """
    added_lines = 0
    removed_lines = 0
    modified_files = set()
    
    # Simple analysis of diff content
    for line in diff_content.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            added_lines += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed_lines += 1
        elif line.startswith("diff --git"):
            # Extract filename from diff header
            parts = line.split(" ")
            if len(parts) >= 3:
                file_path = parts[2].strip()
                if file_path.startswith("a/"):
                    file_path = file_path[2:]
                modified_files.add(file_path)
    
    # Determine change magnitude
    total_changes = added_lines + removed_lines
    if total_changes < 10:
        magnitude = "small"
    elif total_changes < 50:
        magnitude = "medium"
    else:
        magnitude = "large"
    
    return {
        "added_lines": added_lines,
        "removed_lines": removed_lines,
        "modified_files": list(modified_files),
        "file_count": len(modified_files),
        "magnitude": magnitude,
        "net_change": added_lines - removed_lines
    }


def generate_commit_message(
    files_changed: List[str],
    diff_content: str,
    feature_branch: Optional[str] = None
) -> str:
    """
    Generate a conventional commit message based on the changes.
    
    Args:
        files_changed: List of files changed
        diff_content: Content of the git diff
        feature_branch: Optional feature branch name to extract scope
        
    Returns:
        Suggested commit message
    """
    # Analyze the changes
    analysis = analyze_changes(diff_content)
    
    # Determine commit type based on files changed
    commit_type = suggest_commit_type(files_changed)
    
    # Extract scope from feature branch if available
    scope = None
    if feature_branch:
        # Extract scope from branch name (e.g., feature/user-auth → user-auth)
        parts = feature_branch.split("/")
        if len(parts) >= 2:
            scope = parts[1].lower().replace("_", "-")
    
    # Create a descriptive message based on analysis
    if commit_type == CommitType.FEAT:
        description = f"Add new functionality with {analysis['file_count']} files modified"
    elif commit_type == CommitType.FIX:
        description = f"Fix issues in {analysis['file_count']} files"
    elif commit_type == CommitType.REFACTOR:
        description = f"Refactor code in {analysis['file_count']} files"
    elif commit_type == CommitType.DOCS:
        description = f"Update documentation with {analysis['added_lines']} new lines"
    elif commit_type == CommitType.TEST:
        description = f"Add tests with {analysis['added_lines']} new lines"
    else:
        description = f"Update {analysis['file_count']} files with {analysis['added_lines']} additions and {analysis['removed_lines']} deletions"
    
    # Generate a complete commit message
    return create_conventional_commit(
        commit_type=commit_type,
        description=description,
        scope=scope
    )