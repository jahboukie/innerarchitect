// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Get references to DOM elements
    const chatbox = document.getElementById('chatbox');
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    const moodButtons = document.querySelectorAll('.mood-btn');
    const selectedMoodDisplay = document.getElementById('selectedMood');
    
    // Track the current selected mood
    let currentMood = "neutral"; // Default mood
    
    // Function to format time for message timestamps
    function formatTime() {
        const now = new Date();
        return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    
    // Function to add a new message to the chat display
    function addMessageToChat(message, sender) {
        // Create message container
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${sender}`;
        
        // Create message content container
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Process message text (handle paragraphs)
        const paragraphs = message.split('\n').filter(p => p.trim() !== '');
        paragraphs.forEach((paragraph, index) => {
            const p = document.createElement('p');
            p.textContent = paragraph;
            
            // Add appropriate class to last paragraph
            if (index === paragraphs.length - 1) {
                p.className = 'mb-0';
            }
            
            contentDiv.appendChild(p);
        });
        
        // Add timestamp for assistant messages
        if (sender === 'assistant') {
            const timeStamp = document.createElement('div');
            timeStamp.className = 'message-timestamp';
            timeStamp.textContent = formatTime();
            contentDiv.appendChild(timeStamp);
        }
        
        // Add content to message container
        messageDiv.appendChild(contentDiv);
        
        // Add message to chatbox with a staggered animation
        setTimeout(() => {
            chatbox.appendChild(messageDiv);
            // Scroll to the bottom of the chatbox
            chatbox.scrollTop = chatbox.scrollHeight;
        }, sender === 'assistant' ? 150 : 0); // Slight delay for assistant messages for a more natural feel
    }

    // Function to send a message and get AI response
    function sendMessage() {
        const message = messageInput.value.trim();
        
        // Don't send empty messages
        if (message === '') return;
        
        // Add user message to chat
        addMessageToChat(message, 'user');
        
        // Clear input field
        messageInput.value = '';
        
        // Show a "typing" indicator
        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'chat-message assistant typing';
        typingIndicator.innerHTML = '<div class="message-content"><div class="typing-indicator"><span></span><span></span><span></span></div></div>';
        chatbox.appendChild(typingIndicator);
        chatbox.scrollTop = chatbox.scrollHeight;
        
        // Make API call to the backend
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                message: message,
                mood: currentMood
            })
        })
        .then(response => response.json())
        .then(data => {
            // Remove typing indicator
            chatbox.removeChild(typingIndicator);
            
            // Log the response to console for debugging
            console.log("AI Response:", data);
            
            // Add the AI's response to chat
            addMessageToChat(data.response, 'assistant');
            
            // Scroll to the bottom of the chatbox
            chatbox.scrollTop = chatbox.scrollHeight;
        })
        .catch(error => {
            // Remove typing indicator
            chatbox.removeChild(typingIndicator);
            
            console.error('Error:', error);
            // Show error message in chat
            addMessageToChat("I'm sorry, I couldn't process your message. Please try again later.", 'assistant');
        });
    }
    
    // Function to update the current mood
    function updateMood(mood, buttonEl) {
        // Update the current mood
        currentMood = mood;
        
        // Update the UI
        moodButtons.forEach(btn => {
            btn.classList.remove('active');
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-outline-secondary');
        });
        
        // Highlight the selected button
        buttonEl.classList.add('active');
        buttonEl.classList.add('btn-primary');
        buttonEl.classList.remove('btn-outline-secondary');
        
        // Update the mood display in the chat header
        const moodIcon = getMoodIcon(mood);
        selectedMoodDisplay.innerHTML = `<i class="${moodIcon} me-1"></i> ${mood.charAt(0).toUpperCase() + mood.slice(1)}`;
        selectedMoodDisplay.classList.remove('d-none');
        
        // Add a system message about the mood change
        const systemMessage = document.createElement('div');
        systemMessage.className = 'chat-message system';
        systemMessage.innerHTML = `<div class="message-content system"><p class="mb-0"><i class="${moodIcon} me-1"></i> You're feeling <strong>${mood}</strong> today.</p></div>`;
        chatbox.appendChild(systemMessage);
        chatbox.scrollTop = chatbox.scrollHeight;
    }
    
    // Helper function to get appropriate icon for a mood
    function getMoodIcon(mood) {
        switch(mood) {
            case 'happy': return 'fas fa-smile';
            case 'sad': return 'fas fa-frown';
            case 'frustrated': return 'fas fa-angry';
            case 'exhausted': return 'fas fa-tired';
            case 'neutral':
            default: return 'fas fa-meh';
        }
    }

    // Add event listeners to mood buttons
    moodButtons.forEach(button => {
        button.addEventListener('click', function() {
            const mood = this.getAttribute('data-mood');
            updateMood(mood, this);
        });
    });

    // Event listener for send button click
    sendButton.addEventListener('click', sendMessage);
    
    // Event listener for Enter key in input field
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    // Auto-focus the input field when the page loads
    messageInput.focus();
    
    // Add smooth scroll behavior to the chatbox
    chatbox.addEventListener('wheel', function(e) {
        // Only smooth scroll when not at the top
        if (chatbox.scrollTop > 0) {
            e.preventDefault();
            chatbox.scrollTop += e.deltaY;
        }
    });
});
