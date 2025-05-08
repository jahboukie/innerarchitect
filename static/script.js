// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Get references to DOM elements
    const chatbox = document.getElementById('chatbox');
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');

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
        
        // Add content to message container
        messageDiv.appendChild(contentDiv);
        
        // Add message to chatbox
        chatbox.appendChild(messageDiv);
        
        // Scroll to the bottom of the chatbox
        chatbox.scrollTop = chatbox.scrollHeight;
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
        typingIndicator.className = 'chat-message assistant';
        typingIndicator.innerHTML = '<div class="message-content"><p class="mb-0"><em>Thinking...</em></p></div>';
        chatbox.appendChild(typingIndicator);
        chatbox.scrollTop = chatbox.scrollHeight;
        
        // For now, use a placeholder for mood (will be implemented later)
        const mood = "neutral";
        
        // Make API call to the backend
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                message: message,
                mood: mood
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
});
