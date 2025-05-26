#!/bin/bash

# Setup script for The Inner Architect

# Create virtual environment
echo "Creating virtual environment..."
python -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -e .

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file with sample configuration..."
    cat > .env << EOF
# Database connection
DATABASE_URL=postgresql://localhost/inner_architect

# Authentication
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(16))')
FLASK_APP=wsgi.py
FLASK_ENV=development

# Claude API (for NLP features)
ANTHROPIC_API_KEY=your_anthropic_api_key

# Stripe integration (for payments)
STRIPE_SECRET_KEY=your_stripe_test_key
STRIPE_PUBLISHABLE_KEY=your_stripe_test_publishable_key

# Email service (SendGrid)
SENDGRID_API_KEY=your_sendgrid_api_key
DEFAULT_FROM_EMAIL=your-email@example.com
EOF
    echo "Please edit the .env file to add your API keys."
else
    echo ".env file already exists, skipping creation."
fi

# Check if PostgreSQL is installed
if command -v psql &> /dev/null; then
    echo "PostgreSQL is installed."
    
    # Create database if it doesn't exist
    if ! psql -lqt | cut -d \| -f 1 | grep -qw inner_architect; then
        echo "Creating PostgreSQL database 'inner_architect'..."
        createdb inner_architect
    else
        echo "Database 'inner_architect' already exists."
    fi
else
    echo "PostgreSQL is not installed or not in PATH."
    echo "Please install PostgreSQL and create a database named 'inner_architect'."
fi

# Initialize Flask-Migrate
echo "Initializing database migrations..."
if [ ! -d migrations ]; then
    flask db init
    flask db migrate -m "Initial migration"
    flask db upgrade
else
    echo "Migrations folder already exists, running upgrade..."
    flask db upgrade
fi

echo ""
echo "Setup complete! You can now run the application with:"
echo "flask run"
echo ""
echo "Make sure to update your .env file with your API keys before starting."