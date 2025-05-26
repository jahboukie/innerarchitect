"""
Push Manager for Git Automation

This module helps manage git pushes, ensuring that commits are properly organized
and pushed with appropriate commit messages.
"""

import os
import sys
import argparse
import subprocess
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime

from git_tools.feature_manager import FeatureManager


class PushManager:
    """
    Manages git pushes, including verifying commits and push readiness.
    """
    
    def __init__(self, repo_path: str = "."):
        """
        Initialize the push manager.
        
        Args:
            repo_path: Path to the git repository
        """
        self.repo_path = Path(repo_path).resolve()
        self.feature_manager = FeatureManager(repo_path)
    
    def get_unpushed_commits(self) -> List[Dict[str, Any]]:
        """
        Get a list of commits that haven't been pushed to the remote.
        
        Returns:
            List of dictionaries with commit information
        """
        try:
            # Get the current branch
            current_branch = self.feature_manager.get_current_branch()
            
            # Get the remote branch name
            remote_branch = f"origin/{current_branch}"
            
            # Check if the remote branch exists
            remote_exists = subprocess.run(
                ["git", "show-ref", "--verify", f"refs/remotes/{remote_branch}"],
                cwd=self.repo_path,
                capture_output=True,
                check=False
            ).returncode == 0
            
            if not remote_exists:
                # If the remote branch doesn't exist, get all commits in the branch
                result = subprocess.run(
                    ["git", "log", "--pretty=format:%H|%s|%an|%at", current_branch],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
            else:
                # Get commits that exist in the local branch but not in the remote
                result = subprocess.run(
                    ["git", "log", "--pretty=format:%H|%s|%an|%at", f"{remote_branch}..{current_branch}"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
            
            # Parse the output
            commits = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                
                parts = line.split("|")
                if len(parts) >= 4:
                    commit_hash, subject, author, timestamp = parts[0], parts[1], parts[2], parts[3]
                    try:
                        date = datetime.fromtimestamp(int(timestamp))
                        date_str = date.strftime("%Y-%m-%d %H:%M:%S")
                    except (ValueError, OverflowError):
                        date_str = "Unknown"
                    
                    commits.append({
                        "hash": commit_hash,
                        "subject": subject,
                        "author": author,
                        "date": date_str
                    })
            
            return commits
        except subprocess.CalledProcessError as e:
            print(f"Error getting unpushed commits: {e}")
            return []
    
    def push_to_remote(self, force: bool = False) -> bool:
        """
        Push the current branch to the remote.
        
        Args:
            force: Whether to force push
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the current branch
            current_branch = self.feature_manager.get_current_branch()
            
            # Push to remote
            cmd = ["git", "push", "origin", current_branch]
            if force:
                cmd.append("--force")
            
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                print(f"Successfully pushed to origin/{current_branch}")
                return True
            else:
                print(f"Error pushing to remote: {result.stderr}")
                return False
        except subprocess.CalledProcessError as e:
            print(f"Error pushing to remote: {e}")
            return False
    
    def display_push_summary(self) -> None:
        """Display a summary of commits ready to be pushed."""
        # Get the current feature
        feature = self.feature_manager.get_current_feature()
        
        # Get unpushed commits
        unpushed_commits = self.get_unpushed_commits()
        
        print("=== Push Summary ===")
        print(f"Current branch: {self.feature_manager.get_current_branch()}")
        
        if feature:
            print(f"Feature: {feature.name}")
            print(f"Description: {feature.description}")
            if feature.tags:
                print(f"Tags: {', '.join(feature.tags)}")
            if feature.related_issues:
                print(f"Related issues: {', '.join(feature.related_issues)}")
        else:
            print("No feature associated with this branch")
        
        print(f"\nUnpushed commits ({len(unpushed_commits)}):")
        for commit in unpushed_commits:
            print(f"  {commit['hash'][:8]} - {commit['subject']} ({commit['date']})")
    
    def interactive_push(self) -> bool:
        """
        Interactive push process.
        
        Returns:
            True if successful, False otherwise
        """
        # Display summary
        self.display_push_summary()
        
        # Confirm push
        print("\nReady to push?")
        choice = input("[Y]es / [N]o / [F]orce push: ").lower()
        
        if choice == 'y':
            return self.push_to_remote(force=False)
        elif choice == 'f':
            print("WARNING: Force push will overwrite remote branch history.")
            confirm = input("Are you sure? [y/N] ").lower() == 'y'
            if confirm:
                return self.push_to_remote(force=True)
        
        print("Push canceled")
        return False
    
    def auto_push(self, force: bool = False) -> bool:
        """
        Automatically push to remote.
        
        Args:
            force: Whether to force push
            
        Returns:
            True if successful, False otherwise
        """
        # Display summary
        self.display_push_summary()
        
        # Push to remote
        return self.push_to_remote(force=force)


def main():
    """Main entry point for the push manager."""
    parser = argparse.ArgumentParser(description="Git Push Manager")
    parser.add_argument("--auto", action="store_true", help="Push automatically without prompts")
    parser.add_argument("--force", action="store_true", help="Force push")
    parser.add_argument("--repo", default=".", help="Path to the git repository")
    args = parser.parse_args()
    
    push_manager = PushManager(args.repo)
    
    if args.auto:
        push_manager.auto_push(force=args.force)
    else:
        push_manager.interactive_push()


if __name__ == "__main__":
    main()