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
    
    // ======== NLP Exercise Functionality ========
    
    // Get references to exercise elements
    const findExercisesBtn = document.getElementById('findExercisesBtn');
    const exercisesList = document.getElementById('exercisesList');
    const exerciseModal = new bootstrap.Modal(document.getElementById('exerciseModal'));
    const exerciseContainer = document.getElementById('exerciseContainer');
    const exerciseStepContainer = document.getElementById('exerciseStepContainer');
    const exerciseProgress = document.getElementById('exerciseProgress');
    const currentStepNumber = document.getElementById('currentStepNumber');
    const totalSteps = document.getElementById('totalSteps');
    const estimatedTimeRemaining = document.getElementById('estimatedTimeRemaining');
    const prevStepBtn = document.getElementById('prevStepBtn');
    const nextStepBtn = document.getElementById('nextStepBtn');
    
    // Variables to track exercise state
    let currentExercise = null;
    let currentStep = 0;
    let exerciseSteps = [];
    let progressId = null;
    let userResponses = {};
    
    // Event listener for finding exercises
    findExercisesBtn.addEventListener('click', function() {
        // Get current NLP technique
        const technique = nlpTechniqueSelect.value;
        
        // Show loading state
        findExercisesBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Loading...';
        findExercisesBtn.disabled = true;
        
        // Fetch exercises for the current technique
        fetch(`/exercises/${technique}`)
            .then(response => response.json())
            .then(exercises => {
                // Clear existing list
                exercisesList.innerHTML = '';
                
                if (exercises.length === 0) {
                    // No exercises found
                    exercisesList.innerHTML = `
                        <div class="list-group-item border-0 text-center py-4">
                            <i class="fas fa-search me-1"></i>
                            No exercises found for ${technique.replace('_', ' ')}.
                        </div>
                    `;
                } else {
                    // Populate exercise list
                    exercises.forEach(exercise => {
                        const exerciseItem = document.createElement('a');
                        exerciseItem.href = '#';
                        exerciseItem.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
                        exerciseItem.dataset.exerciseId = exercise.id;
                        
                        // Difficulty badge class
                        let badgeClass = 'bg-success';
                        if (exercise.difficulty === 'intermediate') badgeClass = 'bg-warning';
                        if (exercise.difficulty === 'advanced') badgeClass = 'bg-danger';
                        
                        exerciseItem.innerHTML = `
                            <div>
                                <h6 class="mb-1">${exercise.title}</h6>
                                <small class="text-secondary">${exercise.estimated_time} min</small>
                            </div>
                            <span class="badge ${badgeClass}">${exercise.difficulty}</span>
                        `;
                        
                        // Add click event to load the exercise
                        exerciseItem.addEventListener('click', function(e) {
                            e.preventDefault();
                            loadExercise(exercise.id);
                        });
                        
                        exercisesList.appendChild(exerciseItem);
                    });
                }
                
                // Show the list
                exercisesList.classList.remove('d-none');
                
                // Restore button state
                findExercisesBtn.innerHTML = '<i class="fas fa-search me-1"></i> Find Exercises';
                findExercisesBtn.disabled = false;
            })
            .catch(error => {
                console.error('Error fetching exercises:', error);
                
                // Show error message
                exercisesList.innerHTML = `
                    <div class="list-group-item border-0 text-center py-3">
                        <i class="fas fa-exclamation-circle text-danger me-1"></i>
                        Error loading exercises. Please try again.
                    </div>
                `;
                
                // Show the list
                exercisesList.classList.remove('d-none');
                
                // Restore button state
                findExercisesBtn.innerHTML = '<i class="fas fa-search me-1"></i> Find Exercises';
                findExercisesBtn.disabled = false;
            });
    });
    
    // Function to load an exercise
    function loadExercise(exerciseId) {
        // Reset exercise state
        currentStep = 0;
        exerciseSteps = [];
        userResponses = {};
        
        // Show loading state in modal
        exerciseContainer.innerHTML = `
            <div class="exercise-loading text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-3">Loading exercise...</p>
            </div>
        `;
        
        // Show modal
        exerciseModal.show();
        
        // Fetch exercise details
        fetch(`/exercise/${exerciseId}`)
            .then(response => response.json())
            .then(exercise => {
                // Store exercise data
                currentExercise = exercise;
                exerciseSteps = exercise.steps;
                
                // Update modal title
                document.getElementById('exerciseModalLabel').textContent = exercise.title;
                
                // Start the exercise
                fetch(`/exercise/${exerciseId}/start`, {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(progress => {
                    // Store progress ID
                    progressId = progress.progress_id;
                    
                    // Show exercise overview
                    exerciseContainer.innerHTML = `
                        <div class="text-center mb-4">
                            <span class="badge bg-primary mb-3 px-3 py-2">${exercise.technique.replace('_', ' ')}</span>
                            <h4>${exercise.title}</h4>
                        </div>
                        <p class="lead">${exercise.description}</p>
                        <div class="row mb-4 text-center">
                            <div class="col-6">
                                <div class="border rounded p-3">
                                    <div class="h2 mb-0">
                                        <i class="fas fa-clock text-primary"></i>
                                    </div>
                                    <div class="small text-secondary">Estimated Time</div>
                                    <div class="mt-1">${exercise.estimated_time} minutes</div>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="border rounded p-3">
                                    <div class="h2 mb-0">
                                        <i class="fas fa-signal text-primary"></i>
                                    </div>
                                    <div class="small text-secondary">Difficulty</div>
                                    <div class="mt-1">${exercise.difficulty}</div>
                                </div>
                            </div>
                        </div>
                        <div class="d-grid">
                            <button class="btn btn-primary" id="startExerciseBtn">
                                <i class="fas fa-play me-1"></i> Start Exercise
                            </button>
                        </div>
                    `;
                    
                    // Add event listener to start button
                    document.getElementById('startExerciseBtn').addEventListener('click', function() {
                        startExercise();
                    });
                })
                .catch(error => {
                    console.error('Error starting exercise:', error);
                    exerciseContainer.innerHTML = `
                        <div class="alert alert-danger" role="alert">
                            <i class="fas fa-exclamation-circle me-1"></i>
                            Error starting exercise. Please try again later.
                        </div>
                    `;
                });
            })
            .catch(error => {
                console.error('Error loading exercise:', error);
                exerciseContainer.innerHTML = `
                    <div class="alert alert-danger" role="alert">
                        <i class="fas fa-exclamation-circle me-1"></i>
                        Error loading exercise. Please try again later.
                    </div>
                `;
            });
    }
    
    // Function to start the exercise
    function startExercise() {
        // Hide exercise container
        exerciseContainer.classList.add('d-none');
        
        // Show step container and progress
        exerciseStepContainer.classList.remove('d-none');
        exerciseProgress.classList.remove('d-none');
        
        // Set total steps
        totalSteps.textContent = exerciseSteps.length;
        
        // Set estimated time remaining
        estimatedTimeRemaining.textContent = currentExercise.estimated_time;
        
        // Show first step
        showStep(0);
    }
    
    // Function to show a specific step
    function showStep(stepIndex) {
        // Update current step
        currentStep = stepIndex;
        
        // Update step number display
        currentStepNumber.textContent = stepIndex + 1;
        
        // Update progress bar
        const progressPercent = (stepIndex / (exerciseSteps.length - 1)) * 100;
        document.querySelector('.progress-bar').style.width = `${progressPercent}%`;
        
        // Update estimated time remaining
        const stepsRemaining = exerciseSteps.length - stepIndex - 1;
        const timePerStep = currentExercise.estimated_time / exerciseSteps.length;
        const timeRemaining = Math.max(1, Math.round(stepsRemaining * timePerStep));
        estimatedTimeRemaining.textContent = timeRemaining;
        
        // Get current step data
        const step = exerciseSteps[stepIndex];
        
        // Generate step HTML based on type
        let stepHtml = '';
        
        switch (step.type) {
            case 'instruction':
                stepHtml = `
                    <div class="instruction-step mb-4">
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-1"></i>
                            ${step.content}
                        </div>
                    </div>
                `;
                break;
                
            case 'text_input':
                stepHtml = `
                    <div class="text-input-step mb-4">
                        <label class="form-label">${step.prompt}</label>
                        <textarea 
                            class="form-control mb-2" 
                            rows="3" 
                            placeholder="${step.placeholder || ''}"
                            data-step="${stepIndex}"
                        >${userResponses[`step_${stepIndex}`] || ''}</textarea>
                    </div>
                `;
                break;
                
            case 'multiple_choice':
                stepHtml = `
                    <div class="multiple-choice-step mb-4">
                        <label class="form-label mb-3">${step.prompt}</label>
                        <div class="list-group">
                            ${step.options.map((option, idx) => `
                                <label class="list-group-item list-group-item-action">
                                    <input 
                                        class="form-check-input me-2" 
                                        type="radio" 
                                        name="step_${stepIndex}" 
                                        value="${idx}"
                                        data-step="${stepIndex}"
                                        ${userResponses[`step_${stepIndex}`] == idx ? 'checked' : ''}
                                    >
                                    ${option}
                                </label>
                            `).join('')}
                        </div>
                    </div>
                `;
                break;
                
            case 'checkbox':
                stepHtml = `
                    <div class="checkbox-step mb-4">
                        <div class="form-check">
                            <input 
                                class="form-check-input" 
                                type="checkbox" 
                                id="checkbox_step_${stepIndex}"
                                data-step="${stepIndex}"
                                ${userResponses[`step_${stepIndex}`] === true ? 'checked' : ''}
                            >
                            <label class="form-check-label" for="checkbox_step_${stepIndex}">
                                ${step.prompt}
                            </label>
                        </div>
                    </div>
                `;
                break;
                
            case 'reflection':
                stepHtml = `
                    <div class="reflection-step mb-4">
                        <div class="card bg-light">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="fas fa-lightbulb me-1 text-warning"></i>
                                    Reflection
                                </h5>
                                <p class="card-text">${step.prompt}</p>
                                <textarea 
                                    class="form-control mb-2" 
                                    rows="4" 
                                    placeholder="${step.placeholder || ''}"
                                    data-step="${stepIndex}"
                                >${userResponses[`step_${stepIndex}`] || ''}</textarea>
                            </div>
                        </div>
                    </div>
                `;
                break;
                
            default:
                stepHtml = `
                    <div class="alert alert-warning">
                        Unknown step type: ${step.type}
                    </div>
                `;
        }
        
        // Show the step content
        exerciseStepContainer.innerHTML = stepHtml;
        
        // Add event listeners to save responses
        const inputs = exerciseStepContainer.querySelectorAll('[data-step]');
        inputs.forEach(input => {
            if (input.type === 'radio') {
                input.addEventListener('change', saveResponse);
            } else if (input.type === 'checkbox') {
                input.addEventListener('change', saveResponse);
            } else if (input.tagName === 'TEXTAREA') {
                input.addEventListener('input', saveResponse);
            }
        });
        
        // Update navigation buttons
        prevStepBtn.disabled = stepIndex === 0;
        
        if (stepIndex === exerciseSteps.length - 1) {
            nextStepBtn.textContent = 'Complete';
            nextStepBtn.classList.add('btn-success');
            nextStepBtn.classList.remove('btn-primary');
        } else {
            nextStepBtn.textContent = 'Next';
            nextStepBtn.classList.add('btn-primary');
            nextStepBtn.classList.remove('btn-success');
        }
    }
    
    // Function to save user response
    function saveResponse(e) {
        const stepIndex = parseInt(e.target.dataset.step, 10);
        const stepKey = `step_${stepIndex}`;
        
        if (e.target.type === 'radio') {
            userResponses[stepKey] = e.target.value;
        } else if (e.target.type === 'checkbox') {
            userResponses[stepKey] = e.target.checked;
        } else if (e.target.tagName === 'TEXTAREA') {
            userResponses[stepKey] = e.target.value;
        }
        
        // Update exercise progress in the database
        updateExerciseProgress();
    }
    
    // Function to update exercise progress
    function updateExerciseProgress() {
        if (!progressId) return;
        
        fetch(`/exercise/progress/${progressId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                current_step: currentStep,
                notes: JSON.stringify(userResponses),
                completed: currentStep === exerciseSteps.length - 1
            })
        })
        .then(response => response.json())
        .catch(error => {
            console.error('Error updating progress:', error);
        });
    }
    
    // Event listener for previous step button
    prevStepBtn.addEventListener('click', function() {
        if (currentStep > 0) {
            showStep(currentStep - 1);
        }
    });
    
    // Event listener for next step button
    nextStepBtn.addEventListener('click', function() {
        if (currentStep < exerciseSteps.length - 1) {
            showStep(currentStep + 1);
        } else {
            // Final step - complete the exercise
            completeExercise();
        }
    });
    
    // Function to complete the exercise
    function completeExercise() {
        // Update progress to completed
        fetch(`/exercise/progress/${progressId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                current_step: currentStep,
                notes: JSON.stringify(userResponses),
                completed: true
            })
        })
        .then(response => response.json())
        .then(() => {
            // Hide step container and progress
            exerciseStepContainer.classList.add('d-none');
            exerciseProgress.classList.add('d-none');
            
            // Show completion message
            exerciseContainer.classList.remove('d-none');
            exerciseContainer.innerHTML = `
                <div class="text-center mb-4">
                    <div class="display-1 text-success mb-3">
                        <i class="fas fa-check-circle"></i>
                    </div>
                    <h4>Exercise Completed!</h4>
                    <p class="lead">Great job working through this exercise.</p>
                </div>
                
                <div class="card bg-light mb-4">
                    <div class="card-body">
                        <h5 class="card-title">
                            <i class="fas fa-lightbulb me-1 text-warning"></i>
                            What's Next?
                        </h5>
                        <p class="card-text">
                            Try to apply what you've learned from this exercise in your daily life.
                            The more you practice, the more natural these skills will become.
                        </p>
                    </div>
                </div>
                
                <div class="d-grid gap-2">
                    <button class="btn btn-primary" data-bs-dismiss="modal">
                        <i class="fas fa-check me-1"></i> Close Exercise
                    </button>
                    <button class="btn btn-outline-primary" id="shareWithAIBtn">
                        <i class="fas fa-comment-dots me-1"></i> Discuss This Exercise in Chat
                    </button>
                </div>
            `;
            
            // Add event listener for sharing with AI
            document.getElementById('shareWithAIBtn').addEventListener('click', function() {
                // Close the modal
                exerciseModal.hide();
                
                // Add a message to the chat about the exercise
                const exerciseSummary = `I just completed the "${currentExercise.title}" exercise for ${currentExercise.technique.replace('_', ' ')}. Can you help me reflect on what I learned?`;
                messageInput.value = exerciseSummary;
                
                // Wait for modal to close then send
                setTimeout(() => {
                    sendMessage();
                }, 500);
            });
            
            // Add a system message to the chat about completing the exercise
            const systemMessage = document.createElement('div');
            systemMessage.className = 'chat-message system';
            systemMessage.innerHTML = `
                <div class="message-content system">
                    <p class="mb-0">
                        <i class="fas fa-trophy me-1 text-warning"></i> 
                        You completed the <strong>${currentExercise.title}</strong> exercise!
                    </p>
                </div>
            `;
            chatbox.appendChild(systemMessage);
            chatbox.scrollTop = chatbox.scrollHeight;
        })
        .catch(error => {
            console.error('Error completing exercise:', error);
            // Show error message
            alert('Error completing exercise. Please try again.');
        });
    }
});
