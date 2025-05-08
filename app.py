import os
import logging
from flask import Flask, render_template, request, jsonify

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

# Home route
@app.route('/')
def index():
    return render_template('index.html')

# Placeholder for future chat route
@app.route('/chat', methods=['POST'])
def chat():
    """
    Future endpoint for AI interaction.
    This is a placeholder that currently echoes the message back.
    Will be modified to integrate with external AI model.
    """
    message = request.json.get('message', '')
    # Placeholder response (will be replaced with AI integration)
    response = f"Echo: {message}"
    
    return jsonify({
        'response': response
    })

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
