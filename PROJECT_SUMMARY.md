# InnerArchitect Project Reimplementation

## Overview

This project is a reimplementation of the InnerArchitect application originally built on Replit. The new version incorporates several improvements and enhancements, providing a secure, compliant platform for mental health support:

1. **Claude API Integration**: Replaced OpenAI with Claude API for all NLP features for better consistency with other projects.
2. **Proper Local Development Structure**: Organized codebase following best practices for Flask applications.
3. **Enhanced Architecture**: Improved code organization, error handling, and modularity.
4. **Docker Support**: Added Docker configuration for easier development and deployment.
5. **Database Migrations**: Incorporated Flask-Migrate for better database versioning.
6. **CLI Tools**: Added command-line tools for common operations.

## Directory Structure

```
inner_architect/
├── app/
│   ├── __init__.py        # App initialization with application factory
│   ├── auth/              # Authentication-related code
│   ├── models/            # Database models
│   │   ├── __init__.py
│   │   ├── chat.py        # Chat history and conversation models
│   │   ├── nlp.py         # NLP exercise and technique models
│   │   ├── subscription.py # Subscription and quota models
│   │   └── user.py        # User and preferences models
│   ├── nlp/               # NLP techniques and utils
│   │   ├── __init__.py
│   │   ├── claude_client.py         # Claude API integration
│   │   ├── conversation_context.py  # Conversation management
│   │   ├── nlp_exercises.py         # NLP exercises
│   │   └── techniques.py            # NLP techniques implementation
│   ├── routes/            # Route handlers
│   │   ├── __init__.py
│   │   ├── auth.py        # Authentication routes
│   │   ├── chat.py        # Chat interface routes
│   │   └── main.py        # Main page routes
│   ├── static/            # Static assets
│   ├── templates/         # HTML templates
│   └── utils/             # Utility functions
│       ├── __init__.py
│       ├── email.py       # Email utilities
│       └── subscription.py # Subscription management
├── migrations/            # Database migrations
├── tests/                 # Test suite
├── docker-compose.yml     # Docker configuration
├── Dockerfile             # Docker image definition
├── pyproject.toml         # Project dependencies
├── README.md              # Project documentation
├── setup.py               # Installation script
├── setup.sh               # Setup script for Unix systems
├── setup.ps1              # Setup script for Windows
└── wsgi.py                # WSGI entry point
```

## Key Improvements

### Claude API Integration

The NLP features now use Anthropic's Claude API instead of OpenAI. This provides:

- Consistent experience with other Claude-based projects
- Better context handling for conversations with Claude's larger context window
- More nuanced understanding of NLP techniques
- Strong privacy controls and ethical AI guardrails

The `ClaudeClient` class in `app/nlp/claude_client.py` provides a clean interface for:
- Generating responses
- Chat completion
- Text analysis
- Insight extraction

### Architecture Improvements

- **Flask Application Factory**: The application is now built using Flask's application factory pattern, making it more modular and easier to test.
- **Blueprints**: Routes are organized into blueprints for better code organization and scalability.
- **Dependency Injection**: Used proper initialization techniques to avoid circular imports.
- **Type Annotations**: Added type hints for better IDE support and code quality.
- **Error Handling**: Comprehensive error handling throughout the application.
- **Logging**: Improved logging for easier debugging and monitoring.

### Database Enhancements

- **Improved Schema**: Database schema is now more normalized and properly structured.
- **Migrations**: Added Flask-Migrate for database schema management.
- **Relationships**: Properly defined database relationships with appropriate cascade behaviors.
- **Model Methods**: Added helper methods to models for common operations.
- **Query Optimization**: Improved database queries for better performance.

### NLP Techniques Implementation

The project implements six core NLP techniques:

1. **Reframing**: Helps identify and challenge negative thought patterns
2. **Pattern Interruption**: Breaks habitual thought patterns
3. **Anchoring**: Creates associations between triggers and positive emotional states
4. **Future Pacing**: Visualizes successful future outcomes
5. **Sensory Language**: Uses rich sensory words for effective communication
6. **Meta Model Questioning**: Identifies and challenges limiting beliefs

Each technique uses Claude API with specialized prompts to deliver personalized guidance.

### Conversation Context and Memory

The system now includes a sophisticated conversation context and memory system:

- **Context Management**: Conversations are organized into contexts with titles and summaries.
- **Memory Extraction**: The system automatically extracts key facts, preferences, goals, and concerns.
- **Context-Aware Responses**: Responses are enhanced with relevant memories and context.
- **Theme Identification**: Conversation themes are identified and tracked.

### User Experience Improvements

- **Progressive Web App (PWA)**: The application is configured as a PWA with:
  - Advanced offline support with IndexedDB
  - Background sync for offline actions
  - Push notifications for practice reminders
  - Voice input for hands-free interaction
  - Haptic feedback for improved mobile experience
- **Multiple Authentication Methods**: Support for email-based auth and OAuth.
- **Multi-language Support**: Internationalization support for English, Spanish, French, and German.
- **Responsive Design**: Mobile-friendly interface with Bootstrap 5.
- **Technique Discovery**: Users can explore and learn about different NLP techniques.
- **Analytics Dashboard**: Administrators can access comprehensive analytics on user behavior, technique effectiveness, and business metrics.

### DevOps Enhancements

- **Docker Support**: Containerization for consistent development and deployment.
- **CI/CD Ready**: Structure supports continuous integration and deployment.
- **Environment Setup Scripts**: Easy setup for different platforms.
- **Production Configuration**: Gunicorn configuration for production deployment.

## Getting Started

1. Clone the repository and navigate to the project directory
2. Run the setup script for your platform:
   - Unix/Mac: `./setup.sh`
   - Windows: `.\setup.ps1`
3. Configure environment variables in `.env`
4. Start the application:
   - Directly: `flask run`
   - With Docker: `docker-compose up`

## API Keys Required

- **Anthropic API Key**: For Claude API access
- **Stripe API Keys** (optional): For subscription management
- **SendGrid API Key** (optional): For email functionality

## Key Features

1. **Chat Interface**: AI coach that applies NLP techniques based on user input
2. **Multiple NLP Techniques**: Reframing, pattern interruption, anchoring, future pacing, sensory language, and meta model
3. **Progress Tracking**: Monitor effectiveness of different techniques
4. **Personalized Exercises**: Guided practice for NLP techniques
5. **Conversation Memory**: AI remembers previous interactions and extracts key insights
6. **Subscription Management**: Free, Premium, and Professional tiers with different feature access

## Next Steps

1. Complete test coverage to ensure reliability
2. Add CI/CD pipeline configuration for automated testing and deployment
3. Enhance frontend with reactive components for a better user experience
4. Implement additional NLP techniques and exercises
5. ✅ Add analytics for usage patterns and effectiveness
   - Implemented comprehensive analytics dashboard
   - Added user engagement metrics and visualization
   - Created technique effectiveness measurement
   - Built user progress tracking and analysis
   - Developed business metrics and subscription insights
   - Implemented cohort analysis for user retention
   - Added interactive charts with Chart.js
6. Optimize Claude API prompts for even better NLP technique application