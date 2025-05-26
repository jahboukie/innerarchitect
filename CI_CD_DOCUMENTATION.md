# CI/CD Pipeline Documentation

This document describes the Continuous Integration and Continuous Deployment (CI/CD) pipeline for The Inner Architect project.

## Overview

The CI/CD pipeline automates the testing, building, and deployment processes, ensuring code quality and streamlining the release workflow. The pipeline is implemented using GitHub Actions and consists of the following stages:

1. **Testing**: Run automated tests and code quality checks
2. **Building**: Create distributable packages
3. **Deployment**: Deploy the application to staging and production environments

## Pipeline Workflow

### Trigger Events

The pipeline is triggered by the following events:
- Push to `main` or `development` branches
- Pull requests targeting `main` or `development` branches

### Jobs

#### 1. Test

This job runs on every push and pull request:

- Sets up Python environment
- Installs dependencies
- Runs linters (flake8, black, isort, mypy)
- Executes tests with coverage reporting
- Uploads coverage reports to Codecov

#### 2. Build

This job runs only on pushes to `main` or `development` branches:

- Sets up Python environment
- Builds distributable packages
- Uploads build artifacts

#### 3. Deploy to Staging

This job runs only on pushes to the `development` branch:

- Downloads build artifacts
- Sets up SSH connection to staging server
- Deploys the application to the staging environment

#### 4. Deploy to Production

This job runs only on pushes to the `main` branch:

- Downloads build artifacts
- Sets up SSH connection to production server
- Deploys the application to the production environment

## Environment Configuration

The pipeline uses the following environment secrets:

- `ANTHROPIC_API_KEY`: API key for Claude
- `STRIPE_SECRET_KEY`: Secret key for Stripe integration
- `STRIPE_PUBLISHABLE_KEY`: Publishable key for Stripe integration
- `SENDGRID_API_KEY`: API key for SendGrid email service
- `SSH_PRIVATE_KEY`: SSH private key for server access
- `STAGING_SERVER_IP`: IP address of the staging server
- `PRODUCTION_SERVER_IP`: IP address of the production server
- `SERVER_USER`: Username for SSH access to servers

## Deployment Process

The deployment process involves the following steps:

1. Transfer built artifacts to the target server
2. Execute the deployment script (`deploy.sh`)
3. The deployment script:
   - Creates a backup of the current state
   - Updates the virtual environment
   - Runs database migrations
   - Updates static assets
   - Restarts services
   - Performs a health check
   - Logs the deployment status

## Docker Deployment

The application can also be deployed using Docker and Docker Compose:

1. Build and run the containers:
   ```
   docker-compose up -d
   ```

2. The Docker setup includes:
   - Web application container
   - PostgreSQL database container
   - Nginx web server container
   - Redis cache container
   - Celery worker container
   - Flower monitoring container

## Rollback Procedure

In case of deployment failure:

1. The deployment script detects failures through its health check
2. If a failure is detected, the script will automatically roll back to the previous backup
3. For manual rollback, use:
   ```
   cd /var/www/innerarchitect/{environment}
   ./deploy.sh rollback
   ```

## Best Practices for Development

1. **Branch Strategy**:
   - `main`: Production-ready code
   - `development`: Integration branch for feature development
   - Feature branches: Created from `development` for individual features

2. **Pull Requests**:
   - Create pull requests from feature branches to `development`
   - Ensure all tests pass before merging
   - Get code review approval before merging

3. **Version Control**:
   - Make atomic commits with clear messages
   - Reference issue numbers in commit messages
   - Keep features small and focused

4. **Testing**:
   - Write tests for all new features and bug fixes
   - Aim for high test coverage
   - Run tests locally before pushing

## Monitoring and Alerts

The CI/CD pipeline includes monitoring and alerting:

1. GitHub Actions notifications for pipeline failures
2. Health check monitoring for deployed applications
3. Error notification emails for failed deployments
4. Integration with monitoring dashboards

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Documentation](https://docs.docker.com/)
- [Flask Deployment Guide](https://flask.palletsprojects.com/en/2.0.x/deploying/)
- [Gunicorn Documentation](https://docs.gunicorn.org/en/stable/)