# The Inner Architect - Handover Document

## Getting Started for Developers

This document provides essential information for developers taking over this project.

### Prerequisites

- Python 3.11
- PostgreSQL database
- Access to the following API keys:
  - OpenAI API key
  - Stripe API keys
  - SendGrid API key

### Local Development Setup

1. **Clone the repository**:
   ```bash
   git clone <repository URL>
   cd the-inner-architect
   ```

2. **Set up environment variables**:
   Create a `.env` file with the following variables:
   ```
   DATABASE_URL=<your_postgres_connection_string>
   OPENAI_API_KEY=<your_openai_api_key>
   STRIPE_SECRET_KEY=<your_stripe_secret_key>
   SENDGRID_API_KEY=<your_sendgrid_api_key>
   SESSION_SECRET=<random_secret_key>
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python main.py
   ```

### Database Management

- Database migrations are handled through SQLAlchemy's schema updates
- Run `python db_init.py` to initialize the database if needed
- Use `python check_db.py` to verify database integrity

### Testing

- Manual testing is currently the primary method
- Test the authentication flow with both Replit Auth and Email authentication
- Test the subscription flow with test Stripe credentials
- Test the AI conversation capabilities with various user scenarios

### Common Issues and Solutions

#### Authentication Issues

- If users have trouble logging in with Replit Auth, check for transaction issues with `python db_cleanup.py`
- Email verification problems are usually related to SendGrid API key issues
- Account linking requires user records to have matching email addresses

#### Database Errors

- "Current transaction is aborted" errors are addressed with the fix in `auth_repair.py`
- Connection pooling issues can be resolved by adjusting the settings in `app.py`

#### AI Response Problems

- If AI responses are not contextually appropriate, check `conversation_context.py` settings
- Adjust `MAX_CONTEXT_MESSAGES` and memory retrieval settings for better continuity
- API failures should be handled by `api_fallback.py` with graceful degradation

### Deployment Process

1. Ensure all dependencies are correctly listed in `requirements.txt`
2. Configure environment variables in the Replit Secrets panel
3. Use the "Deploy" button in Replit to start the deployment process
4. Verify the deployment by checking all key functionality

### Monitoring and Maintenance

- Check application logs for errors and warnings
- Monitor database performance, especially during high traffic
- Keep API keys updated and check usage limits
- Watch for Stripe webhook failures that might impact subscription status updates

### Future Development Roadmap

1. **High Priority**:
   - Add database migrations for trial subscription fields
   - Enhance error reporting for better debugging
   - Add unit tests for critical components

2. **Medium Priority**:
   - Implement additional NLP techniques
   - Add more language options
   - Improve PWA offline capabilities

3. **Low Priority**:
   - Add admin dashboard for user management
   - Implement A/B testing for UI improvements
   - Add analytics for usage patterns

### Contact Information

For questions about the codebase or deployment, contact:
- Project Manager: [Name & Contact Details]
- Lead Developer: [Name & Contact Details]
- DevOps: [Name & Contact Details]

### Documentation Resources

- `TECHNICAL_DOCUMENTATION.md`: Detailed system design
- `USER_GUIDE.md`: End-user documentation
- Code comments for specific implementation details
- API documentation for external services:
  - [OpenAI API](https://platform.openai.com/docs/api-reference)
  - [Stripe API](https://stripe.com/docs/api)
  - [SendGrid API](https://docs.sendgrid.com/api-reference)
  - [Flask Documentation](https://flask.palletsprojects.com/)