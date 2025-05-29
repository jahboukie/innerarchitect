# InnerArchitect CI/CD Pipeline Documentation

This document provides detailed information about the enhanced CI/CD pipeline for InnerArchitect, including each job, workflow step, security scanning, and quality checks.

## Pipeline Overview

The InnerArchitect CI/CD pipeline is implemented using GitHub Actions and follows industry best practices for continuous integration and deployment. It automates building, testing, and deploying the application while ensuring code quality and security.

The pipeline is triggered on:
- Pushes to `main` and `development` branches
- Pull requests to `main` and `development` branches
- Weekly scheduled security scans (Mondays at 2 AM)

## Workflow Stages

### 1. Security Scan

This job performs comprehensive security scanning of the codebase:

- **Static Application Security Testing (SAST)**: Using Bandit to scan Python code for security vulnerabilities
- **Software Composition Analysis (SCA)**: Using Safety and pip-audit to scan dependencies for known vulnerabilities
- **HIPAA Security Tests**: Running custom security tests to verify HIPAA compliance

Artifacts produced:
- `bandit-results.json`: Results of Bandit SAST scan
- `safety-results.json`: Results of Safety dependency scan
- `pip-audit-results.json`: Results of pip-audit scan
- `security_test.log`: Results of HIPAA security tests

### 2. Lint

This job performs code quality checks:

- **Code Formatting**: Using Black to verify code formatting
- **Import Sorting**: Using isort to verify import order
- **Linting**: Using flake8 to check for syntax errors and style issues
- **Type Checking**: Using mypy for static type checking
- **Code Quality**: Using pylint for comprehensive code quality analysis

Artifacts produced:
- `pylint-report.txt`: Human-readable pylint report
- `pylint-report.json`: Machine-readable pylint report

### 3. Test

This job runs comprehensive tests with coverage reporting:

- Sets up test dependencies including PostgreSQL and Redis
- Runs the test suite with pytest
- Generates coverage reports in XML and HTML formats
- Uploads coverage data to Codecov

Artifacts produced:
- `htmlcov/`: HTML coverage report
- `coverage.xml`: XML coverage report for Codecov

### 4. Docker Build

This job builds and scans the Docker image:

- Sets up Docker Buildx for efficient builds
- Builds the Docker image with appropriate tags
- Scans the built image for security vulnerabilities using Trivy
- Caches Docker layers for faster subsequent builds

Artifacts produced:
- `trivy-results.json`: Container security scan results

### 5. Package

This job creates deployment packages:

- Builds Python packages using the build tool
- Builds and pushes Docker images to GitHub Container Registry (if on main or development branch)
- Tags images appropriately based on branch and commit

Artifacts produced:
- `dist/`: Python package distribution files

### 6. Deploy to Staging

This job deploys to the staging environment (only for development branch):

- Downloads build artifacts
- Creates a deployment package including scripts
- Sets up SSH for secure deployment
- Transfers the package to the staging server
- Executes deployment scripts on the server
- Runs post-deployment health checks
- Sends notifications about deployment status

### 7. Deploy to Production

This job deploys to the production environment (only for main branch):

- Similar to staging deployment but targets production servers
- Includes additional verification steps

## Key Scripts

### Health Check Script

Located at `.github/workflows/scripts/health_check.sh`, this script:

- Verifies application services are running
- Checks key HTTP endpoints for expected responses
- Validates database connectivity
- Creates detailed logs of all checks
- Sends notifications on failure

### Notification Script

Located at `.github/workflows/scripts/notify.sh`, this script:

- Sends deployment notifications via Slack and/or email
- Includes detailed information about the deployment
- Formats messages appropriately for each channel
- Creates logs of notification activity

## Setting Up the Pipeline

### Required Secrets

To use this pipeline, set up the following GitHub repository secrets:

**Authentication:**
- `SSH_PRIVATE_KEY`: SSH key for deploying to servers

**Server Information:**
- `STAGING_SERVER_IP`: IP address of the staging server
- `PRODUCTION_SERVER_IP`: IP address of the production server
- `SERVER_USER`: Username for SSH access to servers

**API Keys:**
- `ANTHROPIC_API_KEY`: API key for Anthropic services
- `STRIPE_SECRET_KEY`: Secret key for Stripe integration
- `STRIPE_PUBLISHABLE_KEY`: Publishable key for Stripe integration
- `SENDGRID_API_KEY`: API key for SendGrid email service
- `SLACK_WEBHOOK_URL`: Webhook URL for Slack notifications

**Notification:**
- `NOTIFICATION_EMAIL`: Email address for deployment notifications

### Required Environments

Set up the following environments in GitHub repository settings:

1. **staging**
   - URL: https://staging.innerarchitect.app
   - Protection rules as needed (e.g., required reviewers)

2. **production**
   - URL: https://innerarchitect.app
   - Protection rules (e.g., required reviewers, wait timer)

## Best Practices

When working with this pipeline:

1. **Branch Strategy**:
   - Use feature branches for development (`feature/*`)
   - Merge to `development` branch for staging deployment
   - Merge to `main` branch for production deployment

2. **Pull Requests**:
   - Create PRs for all changes to `development` and `main`
   - Wait for all checks to pass before merging
   - Require code reviews before merging

3. **Security**:
   - Review security scan results regularly
   - Address critical and high vulnerabilities promptly
   - Update dependencies regularly

4. **Testing**:
   - Maintain high test coverage
   - Add tests for all new features and bug fixes
   - Run tests locally before pushing

## Troubleshooting

Common issues and solutions:

### Failed Deployments

If a deployment fails:

1. Check the GitHub Actions logs for error messages
2. Review the health check logs on the server
3. Verify server connectivity and SSH key access
4. Check application logs on the server
5. Try rolling back to a previous version if needed

### Security Scan Failures

If security scans fail:

1. Review the detailed scan reports in artifacts
2. Address critical vulnerabilities first
3. Create a plan for fixing remaining issues
4. Use `git blame` to identify when vulnerabilities were introduced
5. Consider dependency updates or patches

## Conclusion

This enhanced CI/CD pipeline provides comprehensive automation for building, testing, and deploying InnerArchitect with strong security and quality assurance. Following the guidelines in this document will help maintain a smooth and reliable deployment process.