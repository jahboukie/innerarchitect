#!/bin/bash
#
# Deployment notification script for InnerArchitect
# This script sends notifications about deployments to Slack and/or email
# It includes deployment status and relevant details
#

set -e

# Get input parameters with defaults
ENVIRONMENT=${DEPLOYMENT_ENV:-"production"}
STATUS=${DEPLOYMENT_STATUS:-"success"}
COMMIT_SHA=${GITHUB_SHA:-$(git rev-parse HEAD)}
COMMIT_MSG=${COMMIT_MESSAGE:-$(git log -1 --pretty=format:%s)}
BRANCH=${GITHUB_REF_NAME:-$(git rev-parse --abbrev-ref HEAD)}
DEPLOYER=${GITHUB_ACTOR:-$(git config user.name)}
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

# Load sensitive variables from environment if available
SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL:-""}
NOTIFICATION_EMAIL=${NOTIFICATION_EMAIL:-""}

# Set colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;36m'
NC='\033[0m' # No Color

# Create log file
LOG_FILE="/tmp/deployment_notification_$(date +%Y%m%d_%H%M%S).log"
echo "Deployment notification started at $(date)" > "$LOG_FILE"
echo "Environment: $ENVIRONMENT" >> "$LOG_FILE"
echo "Status: $STATUS" >> "$LOG_FILE"
echo "Commit: $COMMIT_SHA" >> "$LOG_FILE"
echo "Message: $COMMIT_MSG" >> "$LOG_FILE"
echo "Branch: $BRANCH" >> "$LOG_FILE"
echo "Deployer: $DEPLOYER" >> "$LOG_FILE"
echo "-------------------------------------------" >> "$LOG_FILE"

# Format status for display
if [ "$STATUS" == "success" ]; then
    STATUS_EMOJI="✅"
    STATUS_COLOR="good"
    STATUS_TEXT="Succeeded"
else
    STATUS_EMOJI="❌"
    STATUS_COLOR="danger"
    STATUS_TEXT="Failed"
fi

# Function to send Slack notification
send_slack_notification() {
    if [ -z "$SLACK_WEBHOOK_URL" ]; then
        echo -e "${YELLOW}⚠ Slack webhook URL not configured, skipping Slack notification${NC}"
        echo "⚠ Slack webhook URL not configured, skipping Slack notification" >> "$LOG_FILE"
        return 0
    fi
    
    echo -e "${BLUE}Sending Slack notification...${NC}"
    
    # Create the JSON payload for Slack
    PAYLOAD=$(cat <<EOF
{
    "attachments": [
        {
            "color": "$STATUS_COLOR",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "$STATUS_EMOJI InnerArchitect Deployment $STATUS_TEXT",
                        "emoji": true
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": "*Environment:*\n$ENVIRONMENT"
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Deployed by:*\n$DEPLOYER"
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Branch:*\n$BRANCH"
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Time:*\n$TIMESTAMP"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Commit:* \`$COMMIT_SHA\`\n*Message:* $COMMIT_MSG"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "View application: https://${ENVIRONMENT}.innerarchitect.app"
                        }
                    ]
                }
            ]
        }
    ]
}
EOF
)

    # Send to Slack
    HTTP_RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/slack_response.txt -X POST -H "Content-type: application/json" -d "$PAYLOAD" "$SLACK_WEBHOOK_URL")
    
    if [ "$HTTP_RESPONSE" == "200" ]; then
        echo -e "${GREEN}✓ Slack notification sent successfully${NC}"
        echo "✓ Slack notification sent successfully" >> "$LOG_FILE"
    else
        echo -e "${RED}✗ Failed to send Slack notification. HTTP status: $HTTP_RESPONSE${NC}"
        echo "✗ Failed to send Slack notification. HTTP status: $HTTP_RESPONSE" >> "$LOG_FILE"
        cat /tmp/slack_response.txt >> "$LOG_FILE"
    fi
}

# Function to send email notification
send_email_notification() {
    if [ -z "$NOTIFICATION_EMAIL" ]; then
        echo -e "${YELLOW}⚠ Notification email not configured, skipping email notification${NC}"
        echo "⚠ Notification email not configured, skipping email notification" >> "$LOG_FILE"
        return 0
    fi
    
    echo -e "${BLUE}Sending email notification to $NOTIFICATION_EMAIL...${NC}"
    
    # Create email subject
    SUBJECT="InnerArchitect $ENVIRONMENT Deployment $STATUS_TEXT"
    
    # Create email body
    EMAIL_BODY=$(cat <<EOF
InnerArchitect Deployment Notification

Status: $STATUS_TEXT
Environment: $ENVIRONMENT
Branch: $BRANCH
Commit: $COMMIT_SHA
Commit Message: $COMMIT_MSG
Deployed by: $DEPLOYER
Timestamp: $TIMESTAMP

View the application: https://${ENVIRONMENT}.innerarchitect.app

This is an automated message from the InnerArchitect CI/CD pipeline.
EOF
)

    # Send email
    if echo "$EMAIL_BODY" | mail -s "$SUBJECT" "$NOTIFICATION_EMAIL"; then
        echo -e "${GREEN}✓ Email notification sent successfully${NC}"
        echo "✓ Email notification sent successfully" >> "$LOG_FILE"
    else
        echo -e "${RED}✗ Failed to send email notification${NC}"
        echo "✗ Failed to send email notification" >> "$LOG_FILE"
    fi
}

# Main execution
echo -e "${BLUE}Starting deployment notification for $ENVIRONMENT environment${NC}"

# Send notifications
send_slack_notification
send_email_notification

echo -e "${GREEN}✓ Deployment notifications completed${NC}"
echo "✓ Deployment notifications completed" >> "$LOG_FILE"