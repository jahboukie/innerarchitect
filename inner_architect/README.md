# The Inner Architect

A web application for cognitive reframing and emotional well-being powered by NLP techniques using Claude AI.

## Overview

The Inner Architect is a tool that helps users improve their communication skills, emotional intelligence, and overall well-being through the application of Neuro-Linguistic Programming (NLP) techniques. It leverages the Claude AI from Anthropic to provide personalized guidance and exercises based on established NLP methodologies.

## Features

- **Chat Interface**: Interact with an AI coach that applies appropriate NLP techniques based on your input
- **Multiple NLP Techniques**: 
  - Cognitive Reframing
  - Pattern Interruption
  - Emotional Anchoring
  - Future Pacing
  - Sensory Language
  - Meta Model Questioning
- **Progress Tracking**: Monitor your growth and see which techniques work best for you
- **Personalized Exercises**: Practice specific NLP techniques with guided exercises
- **Conversation Memory**: AI remembers previous interactions to provide contextual guidance
- **Multi-language Support**: Available in English, Spanish, French, and German
- **PWA Support**: Install as a Progressive Web App for offline access

## Technology Stack

- **Backend**: Python, Flask
- **Database**: PostgreSQL, SQLAlchemy
- **AI**: Claude API (Anthropic)
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **Authentication**: Email-based auth, JWT
- **Payments**: Stripe integration
- **Email**: SendGrid

## Local Development Setup

### Prerequisites

- Python 3.11 or later
- PostgreSQL
- Anthropic API key
- SendGrid API key (for email features)
- Stripe API keys (for subscription features)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/inner-architect.git
   cd inner-architect
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -e .
   ```

4. Create a `.env` file with your configuration:
   ```
   # Database connection
   DATABASE_URL=postgresql://localhost/inner_architect
   
   # Authentication
   SECRET_KEY=your_secure_secret_key_here
   
   # Claude API
   ANTHROPIC_API_KEY=your_anthropic_api_key
   
   # Stripe (optional, for payments)
   STRIPE_SECRET_KEY=your_stripe_test_key
   STRIPE_PUBLISHABLE_KEY=your_stripe_test_publishable_key
   
   # SendGrid (optional, for emails)
   SENDGRID_API_KEY=your_sendgrid_api_key
   DEFAULT_FROM_EMAIL=your-email@example.com
   ```

5. Initialize the database:
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

6. Run the development server:
   ```bash
   flask run
   ```

### Using Docker

Alternatively, you can use Docker to run the application:

```bash
docker-compose up
```

## Deployment

The application can be deployed to various platforms:

### Heroku

```bash
heroku create
heroku addons:create heroku-postgresql:hobby-dev
heroku config:set $(cat .env | grep -v DATABASE_URL)
git push heroku main
heroku run flask db upgrade
```

### AWS, GCP, Azure

Deployment instructions for cloud platforms are available in the `DEPLOYMENT_GUIDE.md` file.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature/my-new-feature`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Anthropic for providing the Claude API
- The NLP community for the techniques and methodologies
- All contributors and users of the application