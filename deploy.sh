#!/bin/bash
# Deployment script for InnerArchitect

set -e  # Exit immediately if a command exits with non-zero status

# Function for error handling
handle_error() {
    echo "Error: Deployment failed at line $1"
    # Send notification if configured
    if [ -n "$NOTIFICATION_EMAIL" ]; then
        echo "Deployment failed at $(date)" | mail -s "InnerArchitect Deployment Error" $NOTIFICATION_EMAIL
    fi
    exit 1
}

# Set error trap
trap 'handle_error $LINENO' ERR

# Configuration
APP_DIR=$(dirname "$0")
VENV_DIR="$APP_DIR/venv"
LOG_DIR="$APP_DIR/logs"
BACKUP_DIR="$APP_DIR/backups"
ENV_FILE="$APP_DIR/.env"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Ensure directories exist
mkdir -p "$LOG_DIR"
mkdir -p "$BACKUP_DIR"

# Load environment variables if .env file exists
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
fi

# Create backup of the current state
echo "Creating backup..."
tar -czf "$BACKUP_DIR/backup_$TIMESTAMP.tar.gz" -C "$APP_DIR" app static templates migrations

# Setup or update virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

echo "Upgrading pip and installing dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -e "$APP_DIR"

# Run database migrations
echo "Running database migrations..."
cd "$APP_DIR"
"$VENV_DIR/bin/python" -c "
import os
os.environ['FLASK_APP'] = 'inner_architect.wsgi'
from flask_migrate import upgrade
upgrade()
"

# Update static assets
echo "Collecting static assets..."
if [ -d "$APP_DIR/static_build" ]; then
    rm -rf "$APP_DIR/static_build"
fi
mkdir -p "$APP_DIR/static_build"
cp -r "$APP_DIR/static/"* "$APP_DIR/static_build/"

# Run tests
echo "Running tests..."
"$VENV_DIR/bin/pytest" -xvs inner_architect/tests/

# Restart services
echo "Restarting services..."
if [ -f "$APP_DIR/gunicorn.pid" ]; then
    kill -HUP $(cat "$APP_DIR/gunicorn.pid")
else
    "$VENV_DIR/bin/gunicorn" --config "$APP_DIR/gunicorn_config.py" inner_architect.wsgi:app -D
fi

# Cache clear
echo "Clearing application cache..."
"$VENV_DIR/bin/python" -c "
import os
os.environ['FLASK_APP'] = 'inner_architect.wsgi'
from inner_architect.app import create_app
app = create_app()
with app.app_context():
    if hasattr(app, 'cache'):
        app.cache.clear()
"

# Run health check
echo "Running health check..."
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ "$HEALTH_STATUS" -ne 200 ]; then
    echo "Health check failed with status $HEALTH_STATUS. Rolling back..."
    # Rollback logic would go here
    exit 1
fi

# Log deployment
echo "Deployment completed successfully at $(date)" >> "$LOG_DIR/deployment.log"
echo "Deployment completed successfully!"