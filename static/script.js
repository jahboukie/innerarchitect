// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Get references to DOM elements
    const chatbox = document.getElementById('chatbox');
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    const moodButtons = document.querySelectorAll('.mood-btn');
    const selectedMoodDisplay = document.getElementById('selectedMood');
    const nlpTechniqueSelect = document.getElementById('nlpTechniqueSelect');
    const techniqueDescription = document.getElementById('techniqueDescription');
    
    // Track the current selected mood and NLP technique
    let currentMood = "neutral"; // Default mood
    let currentTechnique = "reframing"; // Default technique
    
    // NLP technique descriptions
    const nlpDescriptions = {
        'reframing': '<strong>Reframing</strong>: See situations from new perspectives and find positive aspects in challenges.',
        'pattern_interruption': '<strong>Pattern Interruption</strong>: Break negative thought cycles and establish new, healthier patterns.',
        'anchoring': '<strong>Anchoring</strong>: Associate positive emotions with specific physical or mental triggers.',
        'future_pacing': '<strong>Future Pacing</strong>: Visualize positive future outcomes and mentally rehearse success.',
        'sensory_language': '<strong>Sensory Language</strong>: Use visual, auditory, and kinesthetic language to enhance communication.',
        'meta_model': '<strong>Meta Model Questions</strong>: Challenge limiting beliefs and generalizations through targeted questions.'
    };
    
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
                mood: currentMood,
                technique: currentTechnique
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
    
    // Event listener for NLP technique select
    nlpTechniqueSelect.addEventListener('change', function() {
        currentTechnique = this.value;
        techniqueDescription.innerHTML = `<p class="mb-0">${nlpDescriptions[currentTechnique]}</p>`;
        
        // Add a system message about the technique change
        const systemMessage = document.createElement('div');
        systemMessage.className = 'chat-message system';
        systemMessage.innerHTML = `<div class="message-content system"><p class="mb-0"><i class="fas fa-lightbulb me-1"></i> Now focusing on <strong>${currentTechnique.replace('_', ' ')}</strong> technique.</p></div>`;
        chatbox.appendChild(systemMessage);
        chatbox.scrollTop = chatbox.scrollHeight;
        
        // Hide recommendation explanation when manually changing technique
        document.getElementById('recommendationExplanation').classList.add('d-none');
    });
    
    // Get the most recent user message from the chat
    function getLastUserMessage() {
        const userMessages = document.querySelectorAll('.chat-message.user .message-content');
        if (userMessages.length === 0) {
            return "";
        }
        // Return the text content of the last user message
        const lastMessage = userMessages[userMessages.length - 1];
        let messageText = "";
        // Combine text from all paragraph elements
        lastMessage.querySelectorAll('p').forEach(p => {
            messageText += p.textContent + " ";
        });
        return messageText.trim();
    }
    
    // Event listener for recommend button click
    document.getElementById('recommendButton').addEventListener('click', function() {
        const lastUserMessage = getLastUserMessage();
        
        // If no message has been sent yet, show a system message explaining that
        if (!lastUserMessage) {
            const systemMessage = document.createElement('div');
            systemMessage.className = 'chat-message system';
            systemMessage.innerHTML = `<div class="message-content system"><p class="mb-0"><i class="fas fa-info-circle me-1"></i> Please send a message first so I can recommend an appropriate technique.</p></div>`;
            chatbox.appendChild(systemMessage);
            chatbox.scrollTop = chatbox.scrollHeight;
            return;
        }
        
        // Show loading state for the recommendation button
        const originalButtonText = this.innerHTML;
        this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Analyzing...';
        this.disabled = true;
        
        // Make API call to the backend to get the recommendation
        fetch('/recommend_technique', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                message: lastUserMessage,
                mood: currentMood
            })
        })
        .then(response => response.json())
        .then(data => {
            console.log("Technique recommendation:", data);
            
            // Update the select dropdown with the recommended technique
            nlpTechniqueSelect.value = data.technique;
            
            // Trigger the change event on the select to update the description
            const changeEvent = new Event('change');
            nlpTechniqueSelect.dispatchEvent(changeEvent);
            
            // Update currentTechnique value
            currentTechnique = data.technique;
            
            // Show the recommendation explanation
            const recommendExplanation = document.getElementById('recommendationExplanation');
            recommendExplanation.classList.remove('d-none');
            recommendExplanation.querySelector('.recommendation-text').textContent = data.explanation;
            
            // Add a system message about the recommendation
            const systemMessage = document.createElement('div');
            systemMessage.className = 'chat-message system';
            systemMessage.innerHTML = `
                <div class="message-content system">
                    <p class="mb-0">
                        <i class="fas fa-magic me-1"></i> 
                        Recommended technique: <strong>${data.technique.replace('_', ' ')}</strong>
                        <span class="badge bg-info ms-1">Confidence: ${Math.round(data.confidence * 100)}%</span>
                    </p>
                </div>`;
            chatbox.appendChild(systemMessage);
            chatbox.scrollTop = chatbox.scrollHeight;
        })
        .catch(error => {
            console.error('Error getting technique recommendation:', error);
            
            // Show error message in chat
            const systemMessage = document.createElement('div');
            systemMessage.className = 'chat-message system';
            systemMessage.innerHTML = `<div class="message-content system"><p class="mb-0"><i class="fas fa-exclamation-circle me-1"></i> Sorry, I couldn't generate a technique recommendation. Please try again later.</p></div>`;
            chatbox.appendChild(systemMessage);
            chatbox.scrollTop = chatbox.scrollHeight;
        })
        .finally(() => {
            // Restore the button to its original state
            this.innerHTML = originalButtonText;
            this.disabled = false;
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
