#!/bin/bash
#
# Post-deployment health check script for InnerArchitect
# This script verifies that the application is running properly after deployment
# It checks key endpoints, database connectivity, and reports status
#

set -e

# Get the environment (staging or production)
ENVIRONMENT=${DEPLOYMENT_ENV:-"production"}
BASE_URL="https://${ENVIRONMENT}.innerarchitect.app"
[ "$ENVIRONMENT" == "production" ] && BASE_URL="https://innerarchitect.app"

# Set colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;36m'
NC='\033[0m' # No Color

# Create a log file
LOG_FILE="/tmp/health_check_$(date +%Y%m%d_%H%M%S).log"
echo "Health check started at $(date)" > "$LOG_FILE"
echo "Environment: $ENVIRONMENT" >> "$LOG_FILE"
echo "Base URL: $BASE_URL" >> "$LOG_FILE"
echo "-------------------------------------------" >> "$LOG_FILE"

# Function to check if a service is running
check_service() {
    local service_name="$1"
    echo -e "${BLUE}Checking service: $service_name${NC}"
    
    if systemctl is-active --quiet "$service_name"; then
        echo -e "${GREEN}✓ Service $service_name is running${NC}"
        echo "✓ Service $service_name is running" >> "$LOG_FILE"
        return 0
    else
        echo -e "${RED}✗ Service $service_name is not running${NC}"
        echo "✗ Service $service_name is not running" >> "$LOG_FILE"
        return 1
    fi
}

# Function to check HTTP endpoint
check_endpoint() {
    local endpoint="$1"
    local expected_status="${2:-200}"
    local description="${3:-Endpoint check}"
    
    echo -e "${BLUE}Checking endpoint: $endpoint (Expected status: $expected_status)${NC}"
    
    # Use curl to check the endpoint
    local status_code=$(curl -s -o /dev/null -w "%{http_code}" "$endpoint")
    
    if [ "$status_code" -eq "$expected_status" ]; then
        echo -e "${GREEN}✓ $description: $endpoint returned $status_code${NC}"
        echo "✓ $description: $endpoint returned $status_code" >> "$LOG_FILE"
        return 0
    else
        echo -e "${RED}✗ $description: $endpoint returned $status_code (expected $expected_status)${NC}"
        echo "✗ $description: $endpoint returned $status_code (expected $expected_status)" >> "$LOG_FILE"
        return 1
    fi
}

# Function to check database connectivity
check_database() {
    echo -e "${BLUE}Checking database connectivity${NC}"
    
    # Run a simple database check using the application's check_db.py script
    if python /var/www/innerarchitect/$ENVIRONMENT/check_db.py; then
        echo -e "${GREEN}✓ Database connectivity check passed${NC}"
        echo "✓ Database connectivity check passed" >> "$LOG_FILE"
        return 0
    else
        echo -e "${RED}✗ Database connectivity check failed${NC}"
        echo "✗ Database connectivity check failed" >> "$LOG_FILE"
        return 1
    fi
}

# Start health checks
echo -e "${BLUE}Starting health checks for $ENVIRONMENT environment${NC}"
echo -e "${BLUE}Base URL: $BASE_URL${NC}"

# Initialize failure count
FAILURES=0

# Check if services are running
check_service "innerarchitect_$ENVIRONMENT" || FAILURES=$((FAILURES+1))
check_service "nginx" || FAILURES=$((FAILURES+1))
check_service "redis" || FAILURES=$((FAILURES+1))

# Check database connectivity
check_database || FAILURES=$((FAILURES+1))

# Check key endpoints
check_endpoint "$BASE_URL" 200 "Landing page" || FAILURES=$((FAILURES+1))
check_endpoint "$BASE_URL/login" 200 "Login page" || FAILURES=$((FAILURES+1))
check_endpoint "$BASE_URL/api/health" 200 "Health API" || FAILURES=$((FAILURES+1))
check_endpoint "$BASE_URL/api/metrics" 200 "Metrics API" || FAILURES=$((FAILURES+1))

# Check static resources
check_endpoint "$BASE_URL/static/css/style.css" 200 "CSS resource" || FAILURES=$((FAILURES+1))
check_endpoint "$BASE_URL/static/js/script.js" 200 "JS resource" || FAILURES=$((FAILURES+1))
check_endpoint "$BASE_URL/manifest.json" 200 "PWA manifest" || FAILURES=$((FAILURES+1))

# Check if Redis is functioning by accessing a page that depends on it
check_endpoint "$BASE_URL/api/session-check" 200 "Redis session check" || FAILURES=$((FAILURES+1))

# Summarize results
echo "-------------------------------------------" >> "$LOG_FILE"
if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}✓ All health checks passed!${NC}"
    echo "✓ All health checks passed!" >> "$LOG_FILE"
    exit 0
else
    echo -e "${RED}✗ $FAILURES health checks failed!${NC}"
    echo "✗ $FAILURES health checks failed!" >> "$LOG_FILE"
    
    # Send notification about failed health checks
    if [ -n "$NOTIFICATION_EMAIL" ]; then
        echo "Sending email notification to $NOTIFICATION_EMAIL"
        mail -s "Health Check Failed for InnerArchitect $ENVIRONMENT" "$NOTIFICATION_EMAIL" < "$LOG_FILE"
    fi
    
    exit 1
fi