"""
Feature Manager for Git Automation

This module helps organize commits by features and provides tools for
managing feature branches and related commits.
"""

import os
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple, Any
from datetime import datetime


class Feature:
    """
    Represents a development feature with metadata and related commits.
    """
    
    def __init__(self, 
                 name: str, 
                 description: str = "", 
                 branch_name: Optional[str] = None,
                 tags: List[str] = None,
                 created_at: Optional[str] = None,
                 updated_at: Optional[str] = None,
                 completed: bool = False,
                 related_issues: List[str] = None):
        """
        Initialize a new feature.
        
        Args:
            name: Feature name
            description: Feature description
            branch_name: Git branch name for this feature
            tags: List of tags/categories for this feature
            created_at: Creation timestamp (ISO format)
            updated_at: Last update timestamp (ISO format)
            completed: Whether the feature is completed
            related_issues: List of related issue IDs
        """
        self.name = name
        self.description = description
        self.branch_name = branch_name or self._generate_branch_name()
        self.tags = tags or []
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or self.created_at
        self.completed = completed
        self.related_issues = related_issues or []
        self.commits: List[str] = []  # List of commit hashes
    
    def _generate_branch_name(self) -> str:
        """Generate a branch name from the feature name."""
        # Convert to lowercase, replace spaces with hyphens, remove special chars
        branch_name = self.name.lower().replace(" ", "-")
        branch_name = ''.join(c for c in branch_name if c.isalnum() or c == '-')
        return f"feature/{branch_name}"
    
    def add_commit(self, commit_hash: str) -> None:
        """Add a commit hash to this feature."""
        if commit_hash not in self.commits:
            self.commits.append(commit_hash)
            self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert feature to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "branch_name": self.branch_name,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed": self.completed,
            "related_issues": self.related_issues,
            "commits": self.commits
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Feature':
        """Create a Feature object from dictionary data."""
        feature = cls(
            name=data["name"],
            description=data.get("description", ""),
            branch_name=data.get("branch_name"),
            tags=data.get("tags", []),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            completed=data.get("completed", False),
            related_issues=data.get("related_issues", [])
        )
        feature.commits = data.get("commits", [])
        return feature


class FeatureManager:
    """
    Manages features and their relationships to git branches and commits.
    """
    
    def __init__(self, repo_path: str):
        """
        Initialize the feature manager.
        
        Args:
            repo_path: Path to the git repository
        """
        self.repo_path = Path(repo_path)
        self.features_dir = self.repo_path / ".git" / "features"
        self.features_file = self.features_dir / "features.json"
        self.features: Dict[str, Feature] = {}
        self._load_features()
    
    def _load_features(self) -> None:
        """Load features from the features file."""
        if not self.features_dir.exists():
            self.features_dir.mkdir(exist_ok=True)
        
        if self.features_file.exists():
            try:
                with open(self.features_file, 'r') as f:
                    data = json.load(f)
                    for feature_data in data.get("features", []):
                        feature = Feature.from_dict(feature_data)
                        self.features[feature.name] = feature
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading features: {e}")
    
    def _save_features(self) -> None:
        """Save features to the features file."""
        if not self.features_dir.exists():
            self.features_dir.mkdir(exist_ok=True)
        
        try:
            with open(self.features_file, 'w') as f:
                features_data = [feature.to_dict() for feature in self.features.values()]
                json.dump({"features": features_data}, f, indent=2)
        except IOError as e:
            print(f"Error saving features: {e}")
    
    def create_feature(self, name: str, description: str = "", tags: List[str] = None, 
                      related_issues: List[str] = None) -> Feature:
        """
        Create a new feature.
        
        Args:
            name: Feature name
            description: Feature description
            tags: List of tags/categories
            related_issues: List of related issue IDs
            
        Returns:
            The created Feature object
        """
        if name in self.features:
            raise ValueError(f"Feature '{name}' already exists")
        
        feature = Feature(
            name=name,
            description=description,
            tags=tags,
            related_issues=related_issues
        )
        
        self.features[name] = feature
        self._save_features()
        return feature
    
    def get_feature(self, name: str) -> Optional[Feature]:
        """Get a feature by name."""
        return self.features.get(name)
    
    def list_features(self, include_completed: bool = True) -> List[Feature]:
        """
        List all features.
        
        Args:
            include_completed: Whether to include completed features
            
        Returns:
            List of Feature objects
        """
        if include_completed:
            return list(self.features.values())
        else:
            return [f for f in self.features.values() if not f.completed]
    
    def find_features_by_tag(self, tag: str) -> List[Feature]:
        """Find features with a specific tag."""
        return [f for f in self.features.values() if tag in f.tags]
    
    def find_feature_by_branch(self, branch_name: str) -> Optional[Feature]:
        """Find a feature by its branch name."""
        for feature in self.features.values():
            if feature.branch_name == branch_name:
                return feature
        return None
    
    def mark_feature_completed(self, name: str) -> bool:
        """
        Mark a feature as completed.
        
        Args:
            name: Feature name
            
        Returns:
            True if successful, False if feature not found
        """
        feature = self.get_feature(name)
        if not feature:
            return False
        
        feature.completed = True
        feature.updated_at = datetime.now().isoformat()
        self._save_features()
        return True
    
    def get_current_branch(self) -> str:
        """Get the name of the current git branch."""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "main"  # Default to main if there's an error
    
    def get_current_feature(self) -> Optional[Feature]:
        """Get the feature for the current branch."""
        current_branch = self.get_current_branch()
        return self.find_feature_by_branch(current_branch)
    
    def create_feature_branch(self, feature_name: str, base_branch: str = "main") -> bool:
        """
        Create a git branch for a feature.
        
        Args:
            feature_name: Name of the feature
            base_branch: Base branch to create from
            
        Returns:
            True if successful, False otherwise
        """
        feature = self.get_feature(feature_name)
        if not feature:
            return False
        
        try:
            # Check if branch already exists
            result = subprocess.run(
                ["git", "show-ref", "--verify", f"refs/heads/{feature.branch_name}"],
                cwd=self.repo_path,
                capture_output=True,
                check=False
            )
            
            if result.returncode == 0:
                print(f"Branch {feature.branch_name} already exists")
                return True
            
            # Create and checkout the branch
            subprocess.run(
                ["git", "checkout", "-b", feature.branch_name, base_branch],
                cwd=self.repo_path,
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error creating branch: {e}")
            return False
    
    def add_commit_to_current_feature(self, commit_hash: str) -> bool:
        """
        Add a commit to the current feature.
        
        Args:
            commit_hash: Git commit hash
            
        Returns:
            True if successful, False if no current feature
        """
        feature = self.get_current_feature()
        if not feature:
            return False
        
        feature.add_commit(commit_hash)
        self._save_features()
        return True
    
    def get_latest_commit_hash(self) -> Optional[str]:
        """Get the hash of the latest commit."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None