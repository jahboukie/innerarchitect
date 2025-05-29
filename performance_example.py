#!/usr/bin/env python
"""
Performance Optimization Suite Example for Inner Architect

This script demonstrates how to use the Performance Optimization Suite
in the Inner Architect application with examples for each component.
"""

# Import Flask and create a minimal application
from flask import Flask, jsonify, request, render_template_string
from flask_sqlalchemy import SQLAlchemy
import os
import time

# Create a minimal Flask application
app = Flask(__name__)
app.config.update(
    SECRET_KEY='development-key',
    SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    TEMPLATES_AUTO_RELOAD=True,
    DEBUG=True
)

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Define a simple model for demonstration
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    
    def __repr__(self):
        return f'<User {self.username}>'

# Create tables
with app.app_context():
    db.create_all()
    
    # Add some sample data
    if not User.query.first():
        users = [
            User(username=f'user{i}', email=f'user{i}@example.com')
            for i in range(1, 101)
        ]
        db.session.add_all(users)
        db.session.commit()

# Import the Performance Optimization Suite
from performance.integration import init_performance

# Initialize the Performance Optimization Suite
performance_suite = init_performance(app)

# Import decorators for optimization
from performance import (
    optimize_query,
    profile_performance,
    profile_memory
)

# Example of query caching
@app.route('/api/users')
@optimize_query(expire=60)  # Cache for 60 seconds
def get_users():
    """Get all users with caching."""
    # This query will be cached
    users = User.query.all()
    
    return jsonify({
        'users': [
            {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
            for user in users
        ]
    })

# Example of performance profiling
@app.route('/api/users/<int:user_id>')
@profile_performance(name='get_user_by_id')
def get_user(user_id):
    """Get a user by ID with performance profiling."""
    # This function's performance will be tracked
    user = User.query.get_or_404(user_id)
    
    # Simulate some processing time
    time.sleep(0.01)
    
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email
    })

# Example of memory profiling
@app.route('/api/process-data')
@profile_memory
def process_data():
    """Process data with memory profiling."""
    # This function's memory usage will be tracked
    
    # Simulate a memory-intensive operation
    data = [{'index': i, 'value': f'data_{i}'} for i in range(10000)]
    
    # Process the data
    result = []
    for item in data:
        result.append({
            'processed_index': item['index'] * 2,
            'processed_value': item['value'].upper()
        })
    
    return jsonify({
        'result_size': len(result),
        'first_items': result[:5]
    })

# Example of frontend optimization with a simple page
@app.route('/')
def index():
    """Render a simple page that uses frontend optimization."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Performance Optimization Example</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
        <style>
            .card { margin-bottom: 20px; }
        </style>
        
        <!-- Include optimization scripts from the suite -->
        {{ optimization_scripts|safe }}
    </head>
    <body data-page="demo-page">
        <div class="container py-4">
            <h1 class="mb-4">Performance Optimization Demo</h1>
            
            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">Query Caching Example</h5>
                        </div>
                        <div class="card-body">
                            <p>This example demonstrates query caching.</p>
                            <button id="loadUsersBtn" class="btn btn-primary">
                                Load Users
                            </button>
                            <div id="usersResult" class="mt-3"></div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">Performance Profiling Example</h5>
                        </div>
                        <div class="card-body">
                            <p>This example demonstrates performance profiling.</p>
                            <div class="input-group mb-3">
                                <input type="number" id="userIdInput" class="form-control" placeholder="User ID" value="1" min="1" max="100">
                                <button id="loadUserBtn" class="btn btn-primary">
                                    Load User
                                </button>
                            </div>
                            <div id="userResult" class="mt-3"></div>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">Memory Profiling Example</h5>
                        </div>
                        <div class="card-body">
                            <p>This example demonstrates memory profiling.</p>
                            <button id="processDataBtn" class="btn btn-primary">
                                Process Data
                            </button>
                            <div id="processResult" class="mt-3"></div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">Image Optimization Example</h5>
                        </div>
                        <div class="card-body">
                            <p>This example demonstrates image optimization with lazy loading.</p>
                            <div class="row" id="imageContainer">
                                <!-- Images will be loaded here -->
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Set up button handlers
            document.getElementById('loadUsersBtn').addEventListener('click', loadUsers);
            document.getElementById('loadUserBtn').addEventListener('click', loadUser);
            document.getElementById('processDataBtn').addEventListener('click', processData);
            
            // Load example images with optimization
            loadExampleImages();
        });
        
        function loadUsers() {
            const btn = document.getElementById('loadUsersBtn');
            const result = document.getElementById('usersResult');
            
            // Show loading state
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
            result.innerHTML = '';
            
            // Record start time
            const startTime = performance.now();
            
            // Fetch users
            fetch('/api/users')
                .then(response => response.json())
                .then(data => {
                    // Calculate time
                    const endTime = performance.now();
                    const duration = endTime - startTime;
                    
                    // Show result
                    result.innerHTML = `
                        <div class="alert alert-info">
                            <p>Loaded ${data.users.length} users in ${duration.toFixed(2)}ms</p>
                            <p><small>Check the Network tab to see if the request was cached</small></p>
                        </div>
                    `;
                })
                .catch(error => {
                    result.innerHTML = `
                        <div class="alert alert-danger">
                            Error: ${error.message}
                        </div>
                    `;
                })
                .finally(() => {
                    // Restore button state
                    btn.disabled = false;
                    btn.innerHTML = 'Load Users';
                });
        }
        
        function loadUser() {
            const btn = document.getElementById('loadUserBtn');
            const result = document.getElementById('userResult');
            const userId = document.getElementById('userIdInput').value;
            
            // Validate input
            if (!userId) {
                result.innerHTML = `
                    <div class="alert alert-warning">
                        Please enter a user ID
                    </div>
                `;
                return;
            }
            
            // Show loading state
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
            result.innerHTML = '';
            
            // Record start time
            const startTime = performance.now();
            
            // Fetch user
            fetch(`/api/users/${userId}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error ${response.status}`);
                    }
                    return response.json();
                })
                .then(user => {
                    // Calculate time
                    const endTime = performance.now();
                    const duration = endTime - startTime;
                    
                    // Show result
                    result.innerHTML = `
                        <div class="alert alert-info">
                            <p>Loaded user in ${duration.toFixed(2)}ms</p>
                            <p>Username: ${user.username}</p>
                            <p>Email: ${user.email}</p>
                        </div>
                    `;
                })
                .catch(error => {
                    result.innerHTML = `
                        <div class="alert alert-danger">
                            Error: ${error.message}
                        </div>
                    `;
                })
                .finally(() => {
                    // Restore button state
                    btn.disabled = false;
                    btn.innerHTML = 'Load User';
                });
        }
        
        function processData() {
            const btn = document.getElementById('processDataBtn');
            const result = document.getElementById('processResult');
            
            // Show loading state
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
            result.innerHTML = '';
            
            // Record start time
            const startTime = performance.now();
            
            // Fetch process result
            fetch('/api/process-data')
                .then(response => response.json())
                .then(data => {
                    // Calculate time
                    const endTime = performance.now();
                    const duration = endTime - startTime;
                    
                    // Show result
                    result.innerHTML = `
                        <div class="alert alert-info">
                            <p>Processed ${data.result_size} items in ${duration.toFixed(2)}ms</p>
                            <p>Check the server logs for memory usage information</p>
                        </div>
                    `;
                })
                .catch(error => {
                    result.innerHTML = `
                        <div class="alert alert-danger">
                            Error: ${error.message}
                        </div>
                    `;
                })
                .finally(() => {
                    // Restore button state
                    btn.disabled = false;
                    btn.innerHTML = 'Process Data';
                });
        }
        
        function loadExampleImages() {
            const container = document.getElementById('imageContainer');
            
            // Create some example images
            const colors = ['ff5252', '4caf50', '2196f3', 'ffc107', '9c27b0'];
            const imageSize = 300;
            
            for (let i = 0; i < 10; i++) {
                const color = colors[i % colors.length];
                const imageUrl = `https://via.placeholder.com/${imageSize}/${color}/ffffff?text=Image+${i+1}`;
                
                const col = document.createElement('div');
                col.className = 'col-6 mb-3';
                
                const img = document.createElement('img');
                img.className = 'img-fluid rounded';
                img.alt = `Example Image ${i+1}`;
                img.dataset.src = imageUrl;  // Use data-src for lazy loading
                img.dataset.width = imageSize;
                img.dataset.height = imageSize;
                
                col.appendChild(img);
                container.appendChild(col);
            }
            
            // Optimize images with lazy loading
            if (window.ImageOptimizer) {
                window.ImageOptimizer.optimizeImages('img');
            }
        }
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

# Run the application
if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')