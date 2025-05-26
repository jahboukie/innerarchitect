// Main JavaScript file for The Inner Architect

// DOM content loaded event
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Add smooth scrolling to all links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // Handle PWA installation
    let deferredPrompt;
    
    window.addEventListener('beforeinstallprompt', (e) => {
        // Prevent Chrome 76+ from automatically showing the prompt
        e.preventDefault();
        // Stash the event so it can be triggered later
        deferredPrompt = e;
        
        // Show install button if available
        const installButton = document.querySelector('.pwa-install-button');
        if (installButton) {
            installButton.style.display = 'block';
            
            installButton.addEventListener('click', () => {
                // Show the install prompt
                deferredPrompt.prompt();
                
                // Wait for the user to respond to the prompt
                deferredPrompt.userChoice.then((choiceResult) => {
                    if (choiceResult.outcome === 'accepted') {
                        console.log('User accepted the install prompt');
                        // Hide the button after installation
                        installButton.style.display = 'none';
                    } else {
                        console.log('User dismissed the install prompt');
                    }
                    deferredPrompt = null;
                });
            });
        }
    });
    
    // Handle chat interface if present
    const chatForm = document.getElementById('chat-form');
    if (chatForm) {
        chatForm.addEventListener('submit', handleChatSubmit);
    }
    
    // Handle technique selection if present
    const techniqueSelect = document.getElementById('technique-select');
    if (techniqueSelect) {
        techniqueSelect.addEventListener('change', function() {
            const selectedTechniqueInfo = document.getElementById('selected-technique-info');
            const selectedOption = this.options[this.selectedIndex];
            const techniqueId = selectedOption.value;
            
            // Display technique info if available
            if (techniqueId && selectedTechniqueInfo) {
                const techniqueName = selectedOption.textContent;
                const techniqueDescription = selectedOption.getAttribute('data-description');
                
                selectedTechniqueInfo.innerHTML = `
                    <h5>${techniqueName}</h5>
                    <p>${techniqueDescription}</p>
                `;
                selectedTechniqueInfo.style.display = 'block';
            }
        });
    }
});

// Handle chat submission
function handleChatSubmit(event) {
    event.preventDefault();
    
    const messageInput = document.getElementById('message-input');
    const message = messageInput.value.trim();
    
    if (!message) return;
    
    // Clear input
    messageInput.value = '';
    
    // Get selected technique if available
    const techniqueSelect = document.getElementById('technique-select');
    const technique = techniqueSelect ? techniqueSelect.value : null;
    
    // Add user message to chat
    addMessageToChat('user', message);
    
    // Show typing indicator
    showTypingIndicator();
    
    // Send message to server
    fetch('/chat/message', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message: message,
            technique: technique
        })
    })
    .then(response => response.json())
    .then(data => {
        // Hide typing indicator
        hideTypingIndicator();
        
        if (data.success) {
            // Add AI response to chat
            addMessageToChat('ai', data.message, {
                technique: data.technique,
                mood: data.mood
            });
            
            // Update technique info if needed
            updateTechniqueInfo(data.technique);
        } else {
            // Show error message
            addErrorMessage(data.error || 'An error occurred. Please try again.');
        }
    })
    .catch(error => {
        // Hide typing indicator
        hideTypingIndicator();
        
        // Show error message
        addErrorMessage('Connection error. Please check your internet connection and try again.');
        console.error('Error:', error);
    });
}

// Add message to chat
function addMessageToChat(role, content, metadata = {}) {
    const chatMessages = document.querySelector('.chat-messages');
    if (!chatMessages) return;
    
    const messageElement = document.createElement('div');
    messageElement.className = `message message-${role}`;
    
    // Create message content
    let messageHTML = `<div class="message-content">${escapeHTML(content)}</div>`;
    
    // Add metadata for AI messages
    if (role === 'ai' && metadata.technique) {
        messageHTML += `
            <div class="message-metadata">
                <span class="badge bg-primary">
                    <i class="fas fa-brain me-1"></i> ${metadata.technique.name}
                </span>
                ${metadata.mood ? `
                <span class="badge bg-secondary ms-1">
                    <i class="fas fa-heart me-1"></i> ${metadata.mood}
                </span>
                ` : ''}
            </div>
        `;
    }
    
    messageElement.innerHTML = messageHTML;
    
    // Add to chat and scroll to bottom
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Show typing indicator
function showTypingIndicator() {
    const chatMessages = document.querySelector('.chat-messages');
    if (!chatMessages) return;
    
    const typingElement = document.createElement('div');
    typingElement.className = 'message message-ai typing-indicator';
    typingElement.innerHTML = `
        <div class="typing-dots">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    
    // Add ID for easy removal
    typingElement.id = 'typing-indicator';
    
    chatMessages.appendChild(typingElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Hide typing indicator
function hideTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Add error message
function addErrorMessage(message) {
    const chatMessages = document.querySelector('.chat-messages');
    if (!chatMessages) return;
    
    const errorElement = document.createElement('div');
    errorElement.className = 'message message-error';
    errorElement.innerHTML = `
        <div class="message-content">
            <i class="fas fa-exclamation-circle me-2"></i>
            ${escapeHTML(message)}
        </div>
    `;
    
    chatMessages.appendChild(errorElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Update technique info display
function updateTechniqueInfo(technique) {
    const techniqueInfo = document.getElementById('current-technique-info');
    if (!techniqueInfo || !technique) return;
    
    techniqueInfo.innerHTML = `
        <h5>${technique.name}</h5>
        <p>${technique.description}</p>
    `;
    techniqueInfo.style.display = 'block';
}

// Helper function to escape HTML
function escapeHTML(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}