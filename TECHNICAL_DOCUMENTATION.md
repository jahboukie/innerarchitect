# The Inner Architect - Technical Documentation

## Project Overview

The Inner Architect is a Flask-based self-help web application providing AI-powered emotional support and cognitive reframing through an intuitive, multilingual chat interface. The application leverages OpenAI's API to generate responses that incorporate Neuro-Linguistic Programming (NLP) techniques to help users modify thought patterns and improve mental wellbeing.

## Technology Stack

- **Backend**: Python 3.11, Flask
- **Database**: PostgreSQL
- **Authentication**: Replit Auth (OpenID Connect) and Email Authentication
- **AI Integration**: OpenAI API
- **Payment Processing**: Stripe
- **Email Service**: SendGrid
- **Frontend**: Bootstrap, JavaScript
- **Deployment**: Replit Deployments
- **PWA Support**: Service Worker, Manifest

## System Architecture

The application follows a classic MVC architecture:

- **Models**: SQLAlchemy ORM with PostgreSQL
- **Views**: Jinja2 Templates with Bootstrap CSS
- **Controllers**: Flask Routes and API Endpoints

## Core Components

### Authentication System

The system supports two authentication methods:

1. **Replit Auth** (`replit_auth_new.py`): OpenID Connect authentication through Replit
2. **Email Auth** (`email_auth.py`): Traditional email/password authentication

Authentication features include:
- Account linking between Replit and Email accounts
- Password reset flow
- Email verification
- Session management
- CSRF protection

### AI Conversation Engine

The conversation system (`conversation_context.py`) maintains context between user interactions using:
- Memory management to track important user details
- Context retrieval to ensure continuity
- Sentiment analysis for emotional context
- Topic extraction for theme consistency

### NLP Techniques

The application includes several NLP techniques for cognitive reframing:
- Pattern interruption
- Reframing
- Anchoring
- Swish pattern
- Belief change

### Subscription System

The subscription system (`subscription_manager.py`) handles three tiers:
- Free Tier: Basic cognitive reframing
- Premium Tier ($9.99/month): Enhanced techniques and tracking
- Professional Tier ($19.99/month): All features, including voice interactions

### Internationalization

The application supports multiple languages with:
- UI translation through `language_util.py`
- Dynamic content translation
- RTL language support

### PWA Functionality

The app functions as a Progressive Web App with:
- Offline support via service worker
- Installation capability with manifest.json
- Icon assets for multiple device sizes
- Push notifications for practice reminders
- Background sync for offline actions
- Voice input support for hands-free interaction
- Haptic feedback for improved mobile experience

### Analytics Dashboard

The application includes a comprehensive analytics dashboard:
- User engagement tracking with activity metrics
- Technique effectiveness measurement
- User progress analysis
- Business metrics and subscription insights
- Cohort analysis for user retention
- Data visualization with Chart.js

## Database Schema

Key database models include:

- **User**: Authentication and profile information
- **Subscription**: Plan details and payment status
- **ChatHistory**: Stores user interactions
- **ConversationContext**: Manages conversation state
- **ConversationMemoryItem**: Stores specific memory items
- **NLPExercise**: Technique exercises for users
- **NLPExerciseProgress**: Tracks user progress on exercises
- **TechniqueEffectiveness**: Stores user ratings of techniques
- **TechniqueUsageStats**: Tracks technique usage metrics
- **UserPreferences**: Stores user settings and preferences
- **UsageQuota**: Manages user usage limits and quotas

## API Integrations

The application integrates with several external APIs:

- **OpenAI API**: For AI-powered responses
- **Stripe API**: For subscription management and payments
- **SendGrid API**: For transactional emails

## Error Handling

The application implements comprehensive error handling including:
- API fallback responses (`api_fallback.py`)
- Transaction management for database stability
- Standardized logging across modules
- User-friendly error messages

## Performance Considerations

- Database connection pooling
- Database transaction management
- API timeout handling with retries
- Memory management for conversation context

## Security Features

### HIPAA-Compliant Security Implementation

The application implements military-grade security controls to ensure HIPAA compliance:

- **Encryption**: AES-256-GCM encryption for all PHI at rest and in transit
- **Access Control**: Role-based and attribute-based access control with least privilege
- **Multi-Factor Authentication**: TOTP-based MFA for staff and users
- **Audit Logging**: Immutable, tamper-evident audit trail for all PHI access
- **Break-Glass Protocol**: Emergency access procedures with comprehensive logging
- **Session Security**: Secure cookies, session timeout, and hijacking detection
- **Security Monitoring**: Anomaly detection and proactive threat monitoring

### Additional Security Controls

- CSRF protection
- Secure password handling with PBKDF2
- Token-based authentication
- Environment variable secrets management
- Database constraint enforcement
- Field-level encryption for sensitive data
- Just-In-Time elevated access for sensitive operations

## Filesystem Structure

- `/app.py`: Main application file
- `/models.py`: Database models
- `/conversation_context.py`: Conversation management
- `/subscription_manager.py`: Subscription handling
- `/nlp_*.py`: NLP technique implementation
- `/replit_auth_new.py` & `/email_auth.py`: Authentication systems
- `/templates/`: HTML templates
  - `/templates/security/`: Security-related templates for MFA, etc.
- `/static/`: CSS, JS, and static assets
- `/translations/`: Language files
- `/analytics/`: Analytics dashboard modules
- `/api/`: API endpoints for various features
- `/security/`: HIPAA-compliant security implementation
  - `/security/encryption.py`: Data encryption at rest and in transit
  - `/security/access_control.py`: Role-based access control and MFA
  - `/security/audit.py`: Tamper-evident audit logging
  - `/security/routes.py`: Security-related routes
  - `/security/rbac_config.json`: Role and permission definitions

## Known Issues and Limitations

- Trial subscription functionality is not fully implemented in the database schema
- PWA offline functionality is limited to basic features
- Some advanced NLP techniques require Professional subscription