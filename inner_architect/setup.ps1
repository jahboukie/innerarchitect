# Setup script for The Inner Architect (Windows PowerShell)

# Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Green
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Green
pip install -e .

# Create .env file if it doesn't exist
if (-not (Test-Path .\.env)) {
    Write-Host "Creating .env file with sample configuration..." -ForegroundColor Green
    $secretKey = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
    
    @"
# Database connection
DATABASE_URL=postgresql://localhost/inner_architect

# Authentication
SECRET_KEY=$secretKey
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
"@ | Out-File -FilePath .\.env -Encoding utf8
    
    Write-Host "Please edit the .env file to add your API keys." -ForegroundColor Yellow
} else {
    Write-Host ".env file already exists, skipping creation." -ForegroundColor Yellow
}

# Initialize Flask-Migrate
Write-Host "Initializing database migrations..." -ForegroundColor Green
if (-not (Test-Path .\migrations)) {
    flask db init
    flask db migrate -m "Initial migration"
    flask db upgrade
} else {
    Write-Host "Migrations folder already exists, running upgrade..." -ForegroundColor Yellow
    flask db upgrade
}

Write-Host ""
Write-Host "Setup complete! You can now run the application with:" -ForegroundColor Green
Write-Host "flask run" -ForegroundColor Cyan
Write-Host ""
Write-Host "Make sure to update your .env file with your API keys before starting." -ForegroundColor Yellow
Write-Host "Also ensure you have PostgreSQL installed and a database named 'inner_architect' created." -ForegroundColor Yellow