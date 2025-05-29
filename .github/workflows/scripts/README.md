# CI/CD Workflow Scripts

This directory contains scripts used by the InnerArchitect CI/CD pipeline. These scripts handle deployment verification, notifications, and other automation tasks.

## Available Scripts

### Health Check Script (`health_check.sh`)

This script verifies that the application is running properly after deployment by:

- Checking if required services are running
- Testing key HTTP endpoints for expected responses
- Validating database connectivity
- Creating detailed logs of all checks
- Sending notifications on failure

Usage:
```bash
DEPLOYMENT_ENV=staging bash health_check.sh
```

Environment variables:
- `DEPLOYMENT_ENV`: The environment being checked (staging or production)
- `NOTIFICATION_EMAIL`: Email address to notify on failures

### Notification Script (`notify.sh`)

This script sends deployment notifications to Slack and/or email with:

- Deployment status (success/failure)
- Environment information
- Commit details
- Deployment timestamp
- Links to the deployed application

Usage:
```bash
DEPLOYMENT_ENV=production \
DEPLOYMENT_STATUS=success \
GITHUB_SHA=abc123 \
GITHUB_REF_NAME=main \
GITHUB_ACTOR=username \
COMMIT_MESSAGE="Add new feature" \
SLACK_WEBHOOK_URL=https://hooks.slack.com/... \
NOTIFICATION_EMAIL=team@example.com \
bash notify.sh
```

Environment variables:
- `DEPLOYMENT_ENV`: The environment being deployed (staging or production)
- `DEPLOYMENT_STATUS`: Status of the deployment (success or failure)
- `GITHUB_SHA`: The commit SHA being deployed
- `GITHUB_REF_NAME`: The branch name being deployed
- `GITHUB_ACTOR`: The GitHub username of the person who triggered the deployment
- `COMMIT_MESSAGE`: The commit message
- `SLACK_WEBHOOK_URL`: Webhook URL for Slack notifications
- `NOTIFICATION_EMAIL`: Email address for deployment notifications

## Adding New Scripts

When adding new scripts to this directory:

1. Make the script executable with `chmod +x script_name.sh`
2. Document the script in this README
3. Reference the script in the workflow YAML file
4. Update the CI_CD_DOCUMENTATION.md file with details about the script

## Best Practices

- Include proper error handling in all scripts
- Add detailed logging for troubleshooting
- Make scripts idempotent when possible
- Use environment variables for configuration
- Include meaningful exit codes
- Add comments explaining complex logic