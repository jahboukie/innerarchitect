# Analytics Dashboard Documentation

## Overview

The Inner Architect Analytics Dashboard provides comprehensive insights into user behavior, technique effectiveness, user progress, and business metrics. It is designed for administrators to monitor platform performance, understand user patterns, and make data-driven decisions.

## Features

- **Real-time data visualization** with interactive charts and graphs
- **Time-based filtering** (7 days, 30 days, 90 days, 1 year)
- **Multiple analytics views** for different aspects of the platform
- **User segmentation** to identify key user groups
- **Business insights** for subscription and conversion tracking
- **Cohort analysis** for user retention tracking

## Dashboard Views

The analytics dashboard is organized into several specialized views:

### 1. Overview

The main dashboard that provides a high-level summary of key metrics including:

- Active users
- Message counts
- Technique effectiveness ratings
- Premium conversion rates
- User activity trends
- Technique distribution
- User segments
- Latest insights

### 2. User Engagement

Focuses on how users interact with the platform:

- Active user counts and rates
- Average sessions per user
- Average session duration
- User engagement trends over time
- New user acquisition
- Message distribution by hour
- User retention metrics

### 3. Technique Effectiveness

Analyzes the performance and usage of NLP techniques:

- Most used techniques
- Highest rated techniques
- Overall technique ratings
- Technique usage and effectiveness charts
- Rating distribution across techniques
- Technique effectiveness by mood
- Detailed technique comparison

### 4. User Progress

Tracks user advancement through exercises and techniques:

- Completed exercises
- Completion rates
- Average completion time
- Most popular exercises
- Exercise completion trends
- Completion rates by exercise
- Completion time by exercise
- User progress distribution
- Exercise insights (fastest, lowest completion, most abandoned)

### 5. Business Metrics

Provides insights into growth and subscription metrics:

- Total users
- New user acquisition
- Premium subscription counts
- Premium conversion rates
- Growth trends (users, subscriptions, conversion)
- Subscription distribution
- User retention cohort analysis
- Key business metrics
- Subscription forecasting

### 6. User Insights

Offers detailed user segmentation and analytics:

- User segments by engagement
- User segments by subscription
- User segments by onboarding status
- Conversion opportunities (high engagement free users)
- Churn risk (premium users with decreasing engagement)
- Most improved users
- Users by primary goal
- Users by experience level

## Data Sources

The analytics dashboard draws data from multiple sources:

- **User database**: User profiles, subscription status, preferences
- **Chat history**: User messages, techniques used, timestamps
- **Exercise progress**: Started/completed exercises, completion time
- **Technique ratings**: User ratings of technique effectiveness
- **Subscription data**: Plan types, subscription dates, conversion rates

## API Endpoints

The dashboard relies on several API endpoints to fetch data:

- `/analytics/data/user-engagement`: Provides user engagement metrics and chart data
- `/analytics/data/technique-effectiveness`: Returns technique usage and effectiveness data
- `/analytics/data/user-progress`: Supplies exercise completion and progress data
- `/analytics/data/business-metrics`: Delivers subscription and growth metrics
- `/analytics/data/user-details/<user_id>`: Returns detailed information about a specific user

## Usage Guide

### Accessing the Dashboard

The analytics dashboard is only accessible to administrators. To access it:

1. Log in with an administrator account
2. Navigate to `/analytics/` in the browser

### Time Range Selection

To change the time range for displayed data:

1. Click the time range dropdown at the top right of any view
2. Select from available options (7 days, 30 days, 90 days, 1 year)
3. The dashboard will automatically update with data for the selected period

### Navigating Between Views

To switch between different analytics views:

1. Use the navigation tabs at the top of the dashboard
2. Each tab provides access to a specialized set of metrics and visualizations

### Interacting with Charts

Most charts offer interactive features:

- **Hover over data points** to see detailed values
- **Click on legend items** to toggle visibility of data series
- **Use buttons above charts** to switch between different metrics where available

### Viewing User Details

To view detailed information about specific users:

1. Navigate to the User Insights view
2. Find a user of interest in one of the insight cards
3. Click "View All" to see the complete list of users in that segment
4. Click "Details" next to a specific user to view their complete profile

## Technical Implementation

The analytics dashboard is built using:

- **Backend**: Flask with SQLAlchemy for data processing
- **Frontend**: HTML, CSS, JavaScript with Chart.js for visualizations
- **Data processing**: Python with pandas for data manipulation
- **Database queries**: SQLAlchemy for efficient data retrieval

### Performance Considerations

- Data is aggregated and processed on the server to minimize client-side processing
- Charts are rendered client-side for interactivity
- Time-based filtering is applied at the database level for efficiency
- Large datasets are paginated or summarized to maintain performance

## Troubleshooting

### Common Issues

- **No data appears in charts**: Check that the selected time range contains data
- **Slow loading times**: Consider selecting a smaller time range for faster loading
- **Missing user segments**: Ensure user data is properly categorized in the database

### Support

For technical assistance with the analytics dashboard, contact the development team at:
- Email: dev@innerarchitect.com
- Internal ticket system: Tag as "Analytics Dashboard"