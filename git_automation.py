#!/usr/bin/env python3
"""
Git Automation System

This script provides a command-line interface for the git automation tools,
which help organize commits by feature and ensure professional commit messages
following conventional commit standards.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

from git_tools.commit_wizard import CommitWizard
from git_tools.push_manager import PushManager
from git_tools.feature_manager import FeatureManager


def setup_parser() -> argparse.ArgumentParser:
    """Set up command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Git Automation System with Feature Management and Conventional Commits"
    )
    
    # Global options
    parser.add_argument("--repo", default=".", help="Path to the git repository")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Commit command
    commit_parser = subparsers.add_parser("commit", help="Create a conventional commit")
    commit_parser.add_argument("--auto", action="store_true", help="Create commit automatically without prompts")
    
    # Push command
    push_parser = subparsers.add_parser("push", help="Push commits to remote")
    push_parser.add_argument("--auto", action="store_true", help="Push automatically without prompts")
    push_parser.add_argument("--force", action="store_true", help="Force push")
    
    # Feature commands
    feature_parser = subparsers.add_parser("feature", help="Manage features")
    feature_subparsers = feature_parser.add_subparsers(dest="feature_command", help="Feature command")
    
    # Create feature
    create_parser = feature_subparsers.add_parser("create", help="Create a new feature")
    create_parser.add_argument("name", help="Feature name")
    create_parser.add_argument("--description", "-d", help="Feature description")
    create_parser.add_argument("--tags", "-t", help="Tags (comma-separated)")
    create_parser.add_argument("--issues", "-i", help="Related issues (comma-separated)")
    create_parser.add_argument("--create-branch", "-b", action="store_true", help="Create and switch to branch")
    create_parser.add_argument("--base-branch", default="main", help="Base branch for new feature branch")
    
    # List features
    list_parser = feature_subparsers.add_parser("list", help="List features")
    list_parser.add_argument("--all", "-a", action="store_true", help="Include completed features")
    list_parser.add_argument("--tag", "-t", help="Filter by tag")
    
    # Show feature
    show_parser = feature_subparsers.add_parser("show", help="Show feature details")
    show_parser.add_argument("name", help="Feature name")
    
    # Complete feature
    complete_parser = feature_subparsers.add_parser("complete", help="Mark feature as completed")
    complete_parser.add_argument("name", help="Feature name")
    
    return parser


def handle_feature_command(args):
    """Handle feature commands."""
    manager = FeatureManager(args.repo)
    
    if args.feature_command == "create":
        # Parse tags and issues
        tags = [t.strip() for t in args.tags.split(",")] if args.tags else []
        issues = [i.strip() for i in args.issues.split(",")] if args.issues else []
        
        # Create feature
        feature = manager.create_feature(
            name=args.name,
            description=args.description or "",
            tags=tags,
            related_issues=issues
        )
        
        print(f"Created feature: {feature.name}")
        
        # Create branch if requested
        if args.create_branch:
            success = manager.create_feature_branch(feature.name, args.base_branch)
            if success:
                print(f"Created and switched to branch: {feature.branch_name}")
            else:
                print(f"Failed to create branch: {feature.branch_name}")
    
    elif args.feature_command == "list":
        # List features
        if args.tag:
            features = manager.find_features_by_tag(args.tag)
            print(f"Features with tag '{args.tag}':")
        else:
            features = manager.list_features(include_completed=args.all)
            print("All features:" if args.all else "Active features:")
        
        if not features:
            print("  No features found")
        else:
            for feature in features:
                status = "Completed" if feature.completed else "Active"
                print(f"  - {feature.name} ({status})")
                if feature.description:
                    print(f"    Description: {feature.description}")
                if feature.branch_name:
                    print(f"    Branch: {feature.branch_name}")
    
    elif args.feature_command == "show":
        # Show feature details
        feature = manager.get_feature(args.name)
        if not feature:
            print(f"Feature not found: {args.name}")
            return
        
        print(f"Feature: {feature.name}")
        print(f"Status: {'Completed' if feature.completed else 'Active'}")
        print(f"Description: {feature.description}")
        print(f"Branch: {feature.branch_name}")
        print(f"Created: {feature.created_at}")
        print(f"Updated: {feature.updated_at}")
        
        if feature.tags:
            print(f"Tags: {', '.join(feature.tags)}")
        
        if feature.related_issues:
            print(f"Related issues: {', '.join(feature.related_issues)}")
        
        if feature.commits:
            print(f"\nCommits ({len(feature.commits)}):")
            for commit_hash in feature.commits:
                try:
                    # Get commit message
                    result = subprocess.run(
                        ["git", "log", "--format=%s", "-n", "1", commit_hash],
                        cwd=args.repo,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    message = result.stdout.strip()
                    print(f"  {commit_hash[:8]} - {message}")
                except subprocess.CalledProcessError:
                    print(f"  {commit_hash[:8]}")
    
    elif args.feature_command == "complete":
        # Complete feature
        success = manager.mark_feature_completed(args.name)
        if success:
            print(f"Marked feature as completed: {args.name}")
        else:
            print(f"Feature not found: {args.name}")
    
    else:
        print("Unknown feature command")


def main():
    """Main entry point for the git automation system."""
    parser = setup_parser()
    args = parser.parse_args()
    
    if args.command == "commit":
        wizard = CommitWizard(args.repo)
        if args.auto:
            wizard.auto_commit()
        else:
            wizard.interactive_commit()
    
    elif args.command == "push":
        push_manager = PushManager(args.repo)
        if args.auto:
            push_manager.auto_push(force=args.force)
        else:
            push_manager.interactive_push()
    
    elif args.command == "feature":
        handle_feature_command(args)
    
    else:
        print("No command specified. Use --help for usage information.")
        parser.print_help()


if __name__ == "__main__":
    main()