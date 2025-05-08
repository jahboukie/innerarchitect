import os
import logging
import uuid
from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Define base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize database
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# Import models after defining db to avoid circular imports
from models import User, ChatHistory, JournalEntry

# Create database tables
with app.app_context():
    db.create_all()
    logging.info("Database tables created")

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Home route
@app.route('/')
def index():
    # Generate a session ID if one doesn't exist
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """
    Endpoint for AI interaction.
    Receives user message, processes it through OpenAI,
    and returns the AI response.
    """
    # Get the user message and mood from the request
    data = request.json
    message = data.get('message', '')
    mood = data.get('mood', 'neutral')
    
    # Log the received message for debugging
    logging.debug(f"Received message: {message} (Mood: {mood})")
    
    # Check if OpenAI API key is available
    if not OPENAI_API_KEY:
        logging.error("OpenAI API key is missing")
        return jsonify({
            'response': "I'm sorry, but I'm not fully configured yet. Please provide an OpenAI API key to enable AI responses."
        })
    
    try:
        # Prepare the prompt for OpenAI
        system_prompt = """You are The Inner Architect, a supportive self-help guide.
        Your goal is to help users reframe negative thoughts and build more positive mental patterns.
        Acknowledge the user's mood and message, then respond with empathy and helpful insights.
        Keep responses concise (2-3 short paragraphs maximum) and conversational.
        """
        
        # Make the API call to OpenAI
        # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"User mood: {mood}\nUser message: {message}"}
            ],
            max_tokens=300  # Limit response length
        )
        
        # Extract and return the AI response
        ai_response = response.choices[0].message.content.strip()
        logging.debug(f"AI response: {ai_response}")
        
        return jsonify({
            'response': ai_response
        })
        
    except Exception as e:
        # Log any errors
        logging.error(f"Error calling OpenAI API: {str(e)}")
        return jsonify({
            'response': "I'm sorry, I encountered an error while processing your message. Please try again later."
        })

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
