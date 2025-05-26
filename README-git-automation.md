# Git Automation System

A powerful system for organizing Git commits by feature and enforcing conventional commit standards in your workflow.

## Features

- **Feature-based organization**: Group commits by features and track progress
- **Conventional commit standards**: Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification
- **Interactive commit wizard**: Guided process for creating well-structured commits
- **Push management**: Verify and organize commits before pushing to remote
- **Smart suggestions**: Auto-generate commit messages based on changes
- **Command-line interface**: Easy to use and integrate into workflows

## Installation

1. Ensure you have Python 3.6+ installed
2. Clone this repository or copy the `git_tools` directory to your project
3. Make the script executable:
   ```bash
   chmod +x git_automation.py
   ```

## Usage

### Basic Commands

```bash
# Create a commit (interactive mode)
./git_automation.py commit

# Create a commit (automatic mode)
./git_automation.py commit --auto

# Push to remote (interactive mode)
./git_automation.py push

# Push to remote (automatic mode)
./git_automation.py push --auto

# Force push to remote (use with caution)
./git_automation.py push --force
```

### Feature Management

```bash
# Create a new feature
./git_automation.py feature create "My Feature" --description "Description of my feature" --tags "frontend,ui" --issues "123,456"

# Create a feature and branch
./git_automation.py feature create "My Feature" --create-branch --base-branch main

# List active features
./git_automation.py feature list

# List all features (including completed)
./git_automation.py feature list --all

# Filter features by tag
./git_automation.py feature list --tag frontend

# Show feature details
./git_automation.py feature show "My Feature"

# Mark feature as completed
./git_automation.py feature complete "My Feature"
```

## Conventional Commit Standards

This system enforces the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Supported Types

- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that do not affect the meaning of the code (white-space, formatting, etc)
- **refactor**: A code change that neither fixes a bug nor adds a feature
- **perf**: A code change that improves performance
- **test**: Adding missing tests or correcting existing tests
- **build**: Changes to the build system or external dependencies
- **ci**: Changes to CI configuration files and scripts
- **chore**: Other changes that don't modify src or test files
- **revert**: Reverts a previous commit

## Architecture

The system consists of several modules:

- **conventional_commit.py**: Utilities for creating and validating conventional commits
- **feature_manager.py**: Manages features and their relationship to branches and commits
- **commit_wizard.py**: Interactive tool for creating well-structured commits
- **push_manager.py**: Manages pushes to remote repositories
- **git_automation.py**: Main command-line interface

## Integration with Existing Workflows

### Git Hooks

You can integrate this system with Git hooks for automatic validation. Create a file `.git/hooks/commit-msg` with:

```bash
#!/bin/bash
python /path/to/git_automation.py validate-message "$1"
```

Make it executable:
```bash
chmod +x .git/hooks/commit-msg
```

### CI/CD Integration

You can use this system in CI/CD pipelines to validate commits and organize features:

```yaml
validate_commits:
  script:
    - python /path/to/git_automation.py validate-commits
```

## Best Practices

1. **Create a feature first**: Always start by creating a feature before making changes
2. **One feature per branch**: Keep each feature in its own branch
3. **Small, focused commits**: Make small commits that focus on a single change
4. **Descriptive commit messages**: Write clear, descriptive commit messages
5. **Link to issues**: Reference related issues in commit messages
6. **Complete features**: Mark features as completed when they're done

## Development

To contribute to this system:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python -m unittest discover`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.