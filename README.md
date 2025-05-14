# The Inner Architect

A Flask-based self-help web application providing AI-powered emotional support and cognitive reframing through an intuitive, multilingual chat interface.

## Project Overview

The Inner Architect helps users improve their mental wellbeing by using Neuro-Linguistic Programming (NLP) techniques to modify thought patterns. The application utilizes OpenAI's API to generate responses that are contextually relevant and emotionally supportive, with a clean, professional design inspired by modern web applications.

## Key Features

- Interactive AI-powered chat interface
- Multiple NLP techniques for emotional support
- User progress tracking and insights
- Subscription-based premium features
- Multilingual support
- Progressive Web App (PWA) capabilities
- Authentication via Replit Auth and Email
- Stripe integration for payments

## Documentation

This repository includes comprehensive documentation:

### For Developers

- [Technical Documentation](TECHNICAL_DOCUMENTATION.md): System architecture, components, and implementation details
- [Handover Document](HANDOVER_DOCUMENT.md): Essential information for developers taking over the project
- [Production Setup](PRODUCTION_SETUP.md): Instructions for configuring the app for production

### For Deployment

- [Deployment Guide](DEPLOYMENT_GUIDE.md): Detailed instructions for deploying to production
- [Monitoring Configuration](monitoring_config.py): Application health monitoring setup
- [Production Configuration](production_config.py): Settings specific to production environments

### For Users

- [User Guide](USER_GUIDE.md): End-user documentation for using the application

## Getting Started

### Prerequisites

- Python 3.11
- PostgreSQL database
- APIs: OpenAI, Stripe, SendGrid

### Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables (see [Handover Document](HANDOVER_DOCUMENT.md))
4. Run the application: `python main.py`

## Project Structure

```
├── app.py                  # Main application initialization
├── main.py                 # Entry point
├── models.py               # Database models
├── replit_auth_new.py      # Replit authentication implementation
├── email_auth.py           # Email authentication implementation
├── conversation_context.py # Conversation management
├── subscription_manager.py # Subscription handling
├── nlp_*.py                # NLP technique implementations
├── api_fallback.py         # API error handling and fallbacks
├── monitoring_config.py    # Application monitoring configuration
├── production_config.py    # Production environment settings
├── static/                 # Static assets (CSS, JS, images)
│   ├── css/                # Stylesheets
│   ├── js/                 # JavaScript files
│   ├── icons/              # Application icons
│   ├── manifest.json       # PWA manifest
│   └── service-worker.js   # PWA service worker
├── templates/              # HTML templates
│   ├── base.html           # Base template with common elements
│   ├── landing.html        # Landing page
│   ├── profile.html        # User profile
│   ├── chat.html           # Chat interface
│   └── ...                 # Other templates
└── translations/           # Language translation files
```

## Development

- Run the application in development mode: `python main.py`
- Access the application at: http://localhost:5000

## Deployment

Refer to the [Deployment Guide](DEPLOYMENT_GUIDE.md) for detailed deployment instructions.

## Built With

- [Flask](https://flask.palletsprojects.com/) - Web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM
- [OpenAI API](https://platform.openai.com/) - AI model integration
- [Stripe](https://stripe.com/) - Payment processing
- [SendGrid](https://sendgrid.com/) - Email delivery
- [Bootstrap](https://getbootstrap.com/) - Frontend framework

## License

This project is licensed under the MIT License.

## Contact

For questions about this project, please contact [Your Contact Information].