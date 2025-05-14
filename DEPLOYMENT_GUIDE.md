# The Inner Architect - Deployment Guide

## Deployment Overview

This document provides detailed instructions for deploying The Inner Architect to production environments. The application is designed to be deployed on Replit but can be adapted to other platforms.

## Prerequisites

Before deploying, ensure you have:

1. All required API keys:
   - OpenAI API key
   - Stripe API keys (both test and live)
   - SendGrid API key

2. A PostgreSQL database instance
3. Access to the Replit deployment interface
4. SSL certificate (automatically handled by Replit)

## Environment Configuration

### Required Environment Variables

Set the following environment variables in the Replit Secrets panel:

```
DATABASE_URL=postgresql://username:password@host:port/database
OPENAI_API_KEY=your_openai_api_key
STRIPE_SECRET_KEY=your_stripe_live_key
SENDGRID_API_KEY=your_sendgrid_api_key
SESSION_SECRET=random_secure_string
REPL_ID=your_replit_id (for Replit Auth)
```

### Optional Environment Variables

```
STRIPE_WEBHOOK_SECRET=your_webhook_secret
ISSUER_URL=https://replit.com/oidc (for custom OIDC provider)
LOG_LEVEL=INFO (DEBUG, INFO, WARNING, ERROR, CRITICAL)
```

## Production Build Process

### Preparing for Production

1. Update `requirements.txt` to include all dependencies with pinned versions
2. Set `debug=False` in the Flask application
3. Ensure all static assets are properly referenced with versioning
4. Update service worker to cache appropriate static resources

### Database Setup

1. Ensure the PostgreSQL database is properly configured:
   ```sql
   CREATE DATABASE innerarchitect;
   CREATE USER appuser WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE innerarchitect TO appuser;
   ```

2. When first deploying, the application will create all necessary tables automatically

## Deployment Steps on Replit

1. Push all code changes to the main branch
2. Configure all environment variables in the Secrets panel
3. Set the correct entrypoint in the `.replit` file:
   ```
   run = "gunicorn --bind 0.0.0.0:5000 --workers 2 main:app"
   ```
4. Click the "Deploy" button in the Replit interface
5. Verify the deployment by checking logs and testing key functionality

## Post-Deployment Verification

After deploying, verify these critical functions:

1. **Authentication**:
   - Test both Replit Auth and Email Authentication
   - Verify password reset flow
   - Test account linking if applicable

2. **Database Connections**:
   - Ensure all database queries are working
   - Check for any migration issues
   - Verify transaction handling is working properly

3. **API Integrations**:
   - Test OpenAI API connectivity
   - Verify Stripe checkout and webhooks
   - Test SendGrid email delivery

4. **PWA Functionality**:
   - Test installation on mobile devices
   - Verify offline capabilities
   - Check for service worker errors

## Monitoring and Alerting

### Monitoring Setup

Monitor these critical aspects:

1. **Application Logs**:
   - Set up log monitoring to capture errors and warnings
   - Configure alerts for critical errors

2. **Database Monitoring**:
   - Monitor database connection pool usage
   - Track query performance and slow queries
   - Set up alerts for database connection issues

3. **API Usage**:
   - Monitor OpenAI API usage and costs
   - Track Stripe webhook events and failures
   - Monitor email delivery rates and bounces

### Health Checks

Set up regular health checks for:
- Application uptime
- Database connectivity
- API response times
- SSL certificate validity

## Backup and Recovery

### Database Backups

1. Configure daily PostgreSQL database backups:
   ```bash
   pg_dump -Fc innerarchitect > innerarchitect_$(date +%Y%m%d).dump
   ```

2. Store backups securely in an off-site location

### Recovery Process

In case of data loss:
1. Restore from the latest backup:
   ```bash
   pg_restore -d innerarchitect innerarchitect_backup.dump
   ```

2. Verify data integrity after restoration

## SSL and Security

- Replit Deployments automatically handle SSL certificates
- Ensure all external endpoints are accessed via HTTPS
- Regularly update dependencies to patch security vulnerabilities
- Consider adding rate limiting for authentication endpoints

## Performance Optimization

### Server Configuration

- Configure gunicorn workers based on available memory: `workers = (2 x $num_cores) + 1`
- Set appropriate timeouts for long-running operations

### Caching Strategy

- Implement browser caching for static assets
- Consider adding Redis cache for API responses if needed
- Configure service worker caching for offline access

## Troubleshooting Common Issues

### Database Connection Problems

- Check connection string format in environment variables
- Verify database user permissions
- Check for connection pool exhaustion

### Authentication Failures

- Verify Replit Auth configuration (REPL_ID, etc.)
- Check for email verification issues
- Ensure transaction management is working correctly

### Webhook Processing Issues

- Verify Stripe webhook signature
- Check for webhook endpoint accessibility
- Review webhook processing code for errors

## Production Checklist

Before going live with real users, verify:

- [ ] All API keys are production (not test) keys
- [ ] Debug mode is disabled
- [ ] Error pages are properly configured
- [ ] Monitoring and alerts are set up
- [ ] Database backups are configured
- [ ] User data privacy controls are working
- [ ] Rate limiting is in place for sensitive endpoints
- [ ] All subscription plans are correctly configured in Stripe