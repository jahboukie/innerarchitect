import os
import logging
import uuid
import json
from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.DEBUG)

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
from database import db
db.init_app(app)

# Import models
from models import User, ChatHistory, JournalEntry

# Create database tables
with app.app_context():
    db.create_all()
    logging.info("Database tables created")

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Import NLP analyzer
from nlp_analyzer import recommend_technique, get_technique_description

# Home route
@app.route('/')
def index():
    # Generate a session ID if one doesn't exist
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    return render_template('index.html')

# Route to get NLP technique recommendations
@app.route('/recommend_technique', methods=['POST'])
def get_technique_recommendation():
    """
    Endpoint for recommending the most appropriate NLP technique
    based on the user's message and mood.
    """
    # Get the user message and mood from the request
    data = request.json
    message = data.get('message', '')
    mood = data.get('mood', 'neutral')
    
    # Log the received request
    logging.debug(f"Technique recommendation request: Message={message}, Mood={mood}")
    
    # Get technique recommendation
    recommendation = recommend_technique(message, mood)
    
    # Return the recommendation as JSON
    return jsonify(recommendation)

@app.route('/chat', methods=['POST'])
def chat():
    """
    Endpoint for AI interaction.
    Receives user message, processes it through OpenAI,
    and returns the AI response.
    """
    # Get the user message, mood, and NLP technique from the request
    data = request.json
    message = data.get('message', '')
    mood = data.get('mood', 'neutral')
    technique = data.get('technique', 'reframing')
    
    # Get session ID for tracking the conversation
    session_id = session.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    
    # Log the received message for debugging
    logging.debug(f"Received message: {message} (Mood: {mood}, Technique: {technique}, Session: {session_id})")
    
    # Check if OpenAI API key is available
    if not OPENAI_API_KEY:
        logging.error("OpenAI API key is missing")
        return jsonify({
            'response': "I'm sorry, but I'm not fully configured yet. Please provide an OpenAI API key to enable AI responses."
        })
    
    try:
        # Prepare the prompt for OpenAI with NLP techniques
        system_prompt = """You are The Inner Architect, a supportive self-help guide with expertise in Neuro-Linguistic Programming (NLP).
        
        Your goal is to help users reframe negative thoughts and build more positive mental patterns using NLP techniques including:
        
        1. Reframing: Help users see situations from different perspectives.
        2. Pattern interruption: Suggest ways to break negative thought cycles.
        3. Anchoring: Associate positive emotions with specific triggers.
        4. Future pacing: Guide users to visualize positive future outcomes.
        5. Sensory-based language: Use visual, auditory, and kinesthetic language matching the user's communication style.
        6. Meta model questioning: Ask questions that challenge limiting beliefs and generalizations.
        
        Based on the user's mood and message:
        1. Acknowledge their current emotional state with empathy
        2. Identify any limiting beliefs or negative patterns
        3. Apply 1-2 appropriate NLP techniques to help reframe their thinking
        4. Provide a practical, actionable suggestion they can implement immediately
        
        Keep responses concise (2-3 short paragraphs maximum) and conversational. Use the user's name if available.
        """
        
        # Make the API call to OpenAI
        # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"User mood: {mood}\nUser message: {message}\nRequested NLP technique: {technique}"}
            ],
            max_tokens=300  # Limit response length
        )
        
        # Extract the AI response
        ai_response = response.choices[0].message.content.strip()
        logging.debug(f"AI response: {ai_response}")
        
        # Save the chat history to the database
        try:
            chat_entry = ChatHistory(
                session_id=session_id,
                user_message=message,
                ai_response=ai_response,
                mood=mood,
                nlp_technique=technique
            )
            db.session.add(chat_entry)
            db.session.commit()
            logging.info(f"Chat history saved with ID: {chat_entry.id}")
        except Exception as db_error:
            # Log the error but don't interrupt user experience
            logging.error(f"Error saving chat history: {str(db_error)}")
            db.session.rollback()
        
        # Return the AI response to the frontend
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
