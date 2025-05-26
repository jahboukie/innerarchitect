"""
Commit Wizard for Git Automation

This module provides an interactive command-line tool for creating
conventional commits organized by features.
"""

import os
import sys
import argparse
import subprocess
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path

from git_tools.conventional_commit import (
    CommitType, 
    create_conventional_commit,
    analyze_changes,
    generate_commit_message
)

from git_tools.feature_manager import FeatureManager, Feature


class CommitWizard:
    """
    Interactive tool for creating well-structured git commits.
    """
    
    def __init__(self, repo_path: str = "."):
        """
        Initialize the commit wizard.
        
        Args:
            repo_path: Path to the git repository
        """
        self.repo_path = Path(repo_path).resolve()
        self.feature_manager = FeatureManager(repo_path)
    
    def get_staged_files(self) -> List[str]:
        """Get a list of files staged for commit."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "--cached"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return [line for line in result.stdout.strip().split("\n") if line]
        except subprocess.CalledProcessError:
            return []
    
    def get_diff_for_staged(self) -> str:
        """Get the diff for staged changes."""
        try:
            result = subprocess.run(
                ["git", "diff", "--cached"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError:
            return ""
    
    def create_commit(self, message: str) -> Optional[str]:
        """
        Create a commit with the given message.
        
        Args:
            message: Commit message
            
        Returns:
            Commit hash if successful, None otherwise
        """
        try:
            # Create the commit
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_path,
                check=True
            )
            
            # Get the commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            commit_hash = result.stdout.strip()
            
            # Associate with current feature
            self.feature_manager.add_commit_to_current_feature(commit_hash)
            
            return commit_hash
        except subprocess.CalledProcessError as e:
            print(f"Error creating commit: {e}")
            return None
    
    def get_or_create_feature(self) -> Optional[Feature]:
        """
        Get the current feature or prompt to create a new one.
        
        Returns:
            Feature object if successful, None otherwise
        """
        # Check if we're already on a feature branch
        current_feature = self.feature_manager.get_current_feature()
        if current_feature:
            return current_feature
        
        # Prompt to create a new feature
        print("No feature found for the current branch.")
        create_new = input("Create a new feature? [y/N] ").lower() == 'y'
        
        if not create_new:
            return None
        
        # Get feature details
        name = input("Feature name: ")
        description = input("Description (optional): ")
        tags_input = input("Tags (comma-separated, optional): ")
        tags = [tag.strip() for tag in tags_input.split(",")] if tags_input else []
        issues_input = input("Related issues (comma-separated, optional): ")
        issues = [issue.strip() for issue in issues_input.split(",")] if issues_input else []
        
        # Create the feature
        feature = self.feature_manager.create_feature(
            name=name,
            description=description,
            tags=tags,
            related_issues=issues
        )
        
        # Create the branch
        create_branch = input(f"Create and switch to branch '{feature.branch_name}'? [Y/n] ").lower() != 'n'
        if create_branch:
            base_branch = input("Base branch [main]: ") or "main"
            success = self.feature_manager.create_feature_branch(feature.name, base_branch)
            if not success:
                print(f"Failed to create branch for feature '{feature.name}'")
        
        return feature
    
    def suggest_commit_message(self, feature: Optional[Feature] = None) -> str:
        """
        Suggest a commit message based on staged changes and current feature.
        
        Args:
            feature: Current feature (optional)
            
        Returns:
            Suggested commit message
        """
        # Get staged files and diff
        staged_files = self.get_staged_files()
        diff_content = self.get_diff_for_staged()
        
        # Get branch name for scope
        branch_name = self.feature_manager.get_current_branch() if not feature else feature.branch_name
        
        # Generate commit message
        return generate_commit_message(staged_files, diff_content, branch_name)
    
    def interactive_commit(self) -> Optional[str]:
        """
        Interactive commit creation process.
        
        Returns:
            Commit hash if successful, None otherwise
        """
        # Check if there are staged changes
        staged_files = self.get_staged_files()
        if not staged_files:
            print("No staged changes. Stage changes with 'git add' first.")
            return None
        
        print(f"Files staged for commit ({len(staged_files)}):")
        for file in staged_files:
            print(f"  - {file}")
        print()
        
        # Get or create feature
        feature = self.get_or_create_feature()
        
        # Generate suggested commit message
        suggested_message = self.suggest_commit_message(feature)
        print(f"\nSuggested commit message:\n{suggested_message}\n")
        
        # Prompt for commit type
        print("Commit types:")
        for commit_type in CommitType:
            print(f"  {commit_type.value}: {commit_type.name.lower()}")
        
        commit_type_input = input("\nEnter commit type [Use suggested]: ").lower()
        if commit_type_input:
            try:
                commit_type = CommitType(commit_type_input)
            except ValueError:
                print(f"Invalid commit type '{commit_type_input}'. Using suggested.")
                commit_type = None
        else:
            commit_type = None
        
        # Prompt for scope
        scope_input = input("Enter scope (optional) [Use suggested]: ")
        scope = scope_input if scope_input else None
        
        # Prompt for description
        description_input = input("Enter description [Use suggested]: ")
        description = description_input if description_input else None
        
        # Prompt for breaking change
        breaking_change = input("Is this a breaking change? [y/N] ").lower() == 'y'
        
        # Prompt for body
        body_input = input("Enter commit body (optional) [empty]: ")
        body = body_input if body_input else None
        
        # Prompt for issues
        issues_input = input("Enter related issues (comma-separated, optional) [empty]: ")
        issues = [issue.strip() for issue in issues_input.split(",")] if issues_input else None
        
        # Create commit message
        if commit_type and description:
            # Use provided values
            message = create_conventional_commit(
                commit_type=commit_type,
                description=description,
                scope=scope,
                body=body,
                breaking_change=breaking_change,
                issues=issues
            )
        else:
            # Use suggested message
            message = suggested_message
        
        # Confirm
        print(f"\nFinal commit message:\n{message}\n")
        confirm = input("Create commit? [Y/n] ").lower() != 'n'
        
        if confirm:
            commit_hash = self.create_commit(message)
            if commit_hash:
                print(f"Commit created: {commit_hash}")
                return commit_hash
        
        return None
    
    def auto_commit(self) -> Optional[str]:
        """
        Automatically create a commit with a generated message.
        
        Returns:
            Commit hash if successful, None otherwise
        """
        # Check if there are staged changes
        staged_files = self.get_staged_files()
        if not staged_files:
            print("No staged changes. Stage changes with 'git add' first.")
            return None
        
        # Get feature and generate message
        feature = self.feature_manager.get_current_feature()
        message = self.suggest_commit_message(feature)
        
        # Create the commit
        commit_hash = self.create_commit(message)
        if commit_hash:
            print(f"Commit created: {commit_hash}")
            print(f"Message:\n{message}")
            return commit_hash
        
        return None


def main():
    """Main entry point for the commit wizard."""
    parser = argparse.ArgumentParser(description="Git Commit Wizard")
    parser.add_argument("--auto", action="store_true", help="Create commit automatically without prompts")
    parser.add_argument("--repo", default=".", help="Path to the git repository")
    args = parser.parse_args()
    
    wizard = CommitWizard(args.repo)
    
    if args.auto:
        wizard.auto_commit()
    else:
        wizard.interactive_commit()


if __name__ == "__main__":
    main()