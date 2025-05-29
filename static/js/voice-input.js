/**
 * Voice Input Module for The Inner Architect
 * 
 * This module provides speech recognition functionality for text input,
 * allowing users to use voice commands and dictation.
 */

class VoiceInputManager {
  constructor() {
    // Check if speech recognition is supported
    this.SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.isSupported = !!this.SpeechRecognition;
    
    this.recognition = null;
    this.isListening = false;
    this.targetElement = null;
    this.language = 'en-US';
    this.continuous = false;
    this.interimResults = true;
    this.maxAlternatives = 1;
    
    this.onStartCallback = null;
    this.onResultCallback = null;
    this.onEndCallback = null;
    this.onErrorCallback = null;
    
    // Voice commands mapping
    this.commands = {
      'clear text': this._clearText.bind(this),
      'submit form': this._submitForm.bind(this),
      'cancel': this._stopListening.bind(this),
      'new line': this._insertNewLine.bind(this)
    };
    
    // Initialize when the DOM is loaded
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.init());
    } else {
      this.init();
    }
  }
  
  /**
   * Initialize voice input functionality
   */
  init() {
    if (!this.isSupported) {
      console.log('Speech recognition is not supported in this browser');
      return;
    }
    
    // Initialize speech recognition
    this.recognition = new this.SpeechRecognition();
    this.recognition.continuous = this.continuous;
    this.recognition.interimResults = this.interimResults;
    this.recognition.maxAlternatives = this.maxAlternatives;
    this.recognition.lang = this.language;
    
    // Set up event listeners
    this.recognition.onstart = this._handleStart.bind(this);
    this.recognition.onresult = this._handleResult.bind(this);
    this.recognition.onend = this._handleEnd.bind(this);
    this.recognition.onerror = this._handleError.bind(this);
    
    // Add voice buttons to input fields
    this._setupVoiceButtons();
    
    console.log('Voice input manager initialized');
  }
  
  /**
   * Set up voice buttons for input fields
   */
  _setupVoiceButtons() {
    // Find all elements with data-voice-input attribute
    document.querySelectorAll('[data-voice-input]').forEach(input => {
      // Create voice button
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn btn-sm btn-outline-secondary voice-input-button';
      button.innerHTML = '<i class="fas fa-microphone"></i>';
      button.title = 'Click to speak';
      
      // Position button appropriately
      if (input.parentNode.classList.contains('input-group')) {
        // If input is already in an input group, add button as an append
        const appendDiv = document.createElement('div');
        appendDiv.className = 'input-group-append';
        appendDiv.appendChild(button);
        input.parentNode.appendChild(appendDiv);
      } else {
        // Otherwise, create an input group
        const inputGroup = document.createElement('div');
        inputGroup.className = 'input-group';
        
        // Replace the input with the input group
        input.parentNode.insertBefore(inputGroup, input);
        inputGroup.appendChild(input);
        
        // Add the button
        const appendDiv = document.createElement('div');
        appendDiv.className = 'input-group-append';
        appendDiv.appendChild(button);
        inputGroup.appendChild(appendDiv);
      }
      
      // Add click event to button
      button.addEventListener('click', () => {
        if (this.isListening && this.targetElement === input) {
          this.stop();
        } else {
          this.start(input);
        }
      });
    });
    
    // Find all elements with data-voice-command attribute
    document.querySelectorAll('[data-voice-command]').forEach(element => {
      element.addEventListener('click', () => {
        const command = element.dataset.voiceCommand;
        if (command) {
          this.startCommandRecognition([command]);
        }
      });
    });
  }
  
  /**
   * Start voice recognition for an input element
   * @param {HTMLElement} element - The target input element
   * @param {Object} options - Optional settings
   */
  start(element, options = {}) {
    if (!this.isSupported || this.isListening) {
      return false;
    }
    
    try {
      // Set target element
      this.targetElement = element;
      
      // Apply options
      this.recognition.continuous = options.continuous !== undefined ? options.continuous : this.continuous;
      this.recognition.interimResults = options.interimResults !== undefined ? options.interimResults : this.interimResults;
      this.recognition.maxAlternatives = options.maxAlternatives || this.maxAlternatives;
      this.recognition.lang = options.language || this.language;
      
      // Save callbacks
      this.onStartCallback = options.onStart;
      this.onResultCallback = options.onResult;
      this.onEndCallback = options.onEnd;
      this.onErrorCallback = options.onError;
      
      // Start recognition
      this.recognition.start();
      
      // Update UI
      this._updateButtonState(true);
      
      return true;
    } catch (error) {
      console.error('Error starting speech recognition:', error);
      return false;
    }
  }
  
  /**
   * Stop voice recognition
   */
  stop() {
    if (!this.isSupported || !this.isListening) {
      return false;
    }
    
    try {
      this.recognition.stop();
      return true;
    } catch (error) {
      console.error('Error stopping speech recognition:', error);
      return false;
    }
  }
  
  /**
   * Start voice recognition for specific commands
   * @param {string[]} allowedCommands - List of allowed commands
   * @param {function} callback - Callback function when a command is recognized
   */
  startCommandRecognition(allowedCommands, callback) {
    if (!this.isSupported || this.isListening) {
      return false;
    }
    
    try {
      // Create a temporary command dictionary with only allowed commands
      const tempCommands = {};
      
      if (allowedCommands && allowedCommands.length > 0) {
        allowedCommands.forEach(cmd => {
          if (this.commands[cmd]) {
            tempCommands[cmd] = this.commands[cmd];
          }
        });
      } else {
        // If no specific commands are specified, use all commands
        Object.assign(tempCommands, this.commands);
      }
      
      // Start recognition
      this.recognition.continuous = false;
      this.recognition.interimResults = false;
      this.recognition.start();
      
      // Set up one-time event handler for results
      const originalHandler = this.recognition.onresult;
      this.recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript.trim().toLowerCase();
        
        // Check if transcript matches any command
        let commandExecuted = false;
        
        for (const [command, handler] of Object.entries(tempCommands)) {
          if (transcript === command.toLowerCase() || transcript.includes(command.toLowerCase())) {
            handler();
            commandExecuted = true;
            
            if (callback) {
              callback(command, transcript);
            }
            
            break;
          }
        }
        
        if (!commandExecuted && callback) {
          callback(null, transcript);
        }
        
        // Restore original handler
        this.recognition.onresult = originalHandler;
      };
      
      return true;
    } catch (error) {
      console.error('Error starting command recognition:', error);
      return false;
    }
  }
  
  /**
   * Add a custom voice command
   * @param {string} command - The command phrase
   * @param {function} handler - The function to execute when the command is recognized
   */
  addCommand(command, handler) {
    if (typeof command !== 'string' || typeof handler !== 'function') {
      console.error('Command must be a string and handler must be a function');
      return false;
    }
    
    this.commands[command] = handler;
    return true;
  }
  
  /**
   * Set the recognition language
   * @param {string} language - Language code (e.g., 'en-US', 'es-ES')
   */
  setLanguage(language) {
    this.language = language;
    if (this.recognition) {
      this.recognition.lang = language;
    }
  }
  
  /**
   * Handle recognition start event
   */
  _handleStart() {
    this.isListening = true;
    
    // Show visual indicator
    if (this.targetElement) {
      this.targetElement.classList.add('voice-input-active');
    }
    
    // Update button states
    this._updateButtonState(true);
    
    // Call custom callback if provided
    if (this.onStartCallback) {
      this.onStartCallback();
    }
    
    // Trigger haptic feedback if available
    if (window.hapticFeedback) {
      window.hapticFeedback.trigger('notification');
    }
    
    console.log('Speech recognition started');
  }
  
  /**
   * Handle recognition result event
   * @param {SpeechRecognitionEvent} event - The recognition result event
   */
  _handleResult(event) {
    if (!this.targetElement) return;
    
    const results = event.results;
    const currentResult = results[results.length - 1];
    const transcript = currentResult[0].transcript;
    
    // Check if this is a final result
    if (currentResult.isFinal) {
      // Check for commands
      const lowerTranscript = transcript.trim().toLowerCase();
      let isCommand = false;
      
      for (const [command, handler] of Object.entries(this.commands)) {
        if (lowerTranscript === command.toLowerCase() || lowerTranscript.includes(command.toLowerCase())) {
          handler();
          isCommand = true;
          break;
        }
      }
      
      // If not a command, update the input value
      if (!isCommand) {
        if (this.targetElement.tagName === 'TEXTAREA' || this.targetElement.tagName === 'INPUT') {
          const cursorPos = this.targetElement.selectionStart;
          const currentValue = this.targetElement.value;
          const beforeCursor = currentValue.substring(0, cursorPos);
          const afterCursor = currentValue.substring(cursorPos);
          
          this.targetElement.value = beforeCursor + transcript + afterCursor;
          
          // Set cursor position after the inserted text
          this.targetElement.selectionStart = this.targetElement.selectionEnd = cursorPos + transcript.length;
        } else if (this.targetElement.isContentEditable) {
          // Handle contentEditable elements
          const selection = window.getSelection();
          const range = selection.getRangeAt(0);
          const textNode = document.createTextNode(transcript);
          
          range.deleteContents();
          range.insertNode(textNode);
          
          // Move cursor after inserted text
          range.setStartAfter(textNode);
          range.setEndAfter(textNode);
          selection.removeAllRanges();
          selection.addRange(range);
        }
      }
    } else {
      // Show interim results
      if (this.targetElement.dataset.showInterim !== 'false') {
        // Create or update interim results element
        let interimElement = document.getElementById('voice-interim-results');
        if (!interimElement) {
          interimElement = document.createElement('div');
          interimElement.id = 'voice-interim-results';
          interimElement.className = 'voice-interim-results';
          document.body.appendChild(interimElement);
        }
        
        // Position near the target element
        const rect = this.targetElement.getBoundingClientRect();
        interimElement.style.top = `${rect.bottom + window.scrollY + 5}px`;
        interimElement.style.left = `${rect.left + window.scrollX}px`;
        interimElement.style.maxWidth = `${rect.width}px`;
        
        // Update content
        interimElement.textContent = transcript;
        interimElement.style.display = 'block';
      }
    }
    
    // Call custom callback if provided
    if (this.onResultCallback) {
      this.onResultCallback(event, transcript, currentResult.isFinal);
    }
  }
  
  /**
   * Handle recognition end event
   */
  _handleEnd() {
    this.isListening = false;
    
    // Remove visual indicator
    if (this.targetElement) {
      this.targetElement.classList.remove('voice-input-active');
    }
    
    // Update button states
    this._updateButtonState(false);
    
    // Remove interim results element
    const interimElement = document.getElementById('voice-interim-results');
    if (interimElement) {
      interimElement.style.display = 'none';
    }
    
    // Call custom callback if provided
    if (this.onEndCallback) {
      this.onEndCallback();
    }
    
    console.log('Speech recognition ended');
  }
  
  /**
   * Handle recognition error event
   * @param {SpeechRecognitionError} event - The recognition error event
   */
  _handleError(event) {
    console.error('Speech recognition error:', event.error);
    
    // Call custom callback if provided
    if (this.onErrorCallback) {
      this.onErrorCallback(event);
    }
    
    // Update states
    this.isListening = false;
    this._updateButtonState(false);
    
    // Trigger haptic feedback if available
    if (window.hapticFeedback) {
      window.hapticFeedback.trigger('error');
    }
  }
  
  /**
   * Update voice button state
   * @param {boolean} isListening - Whether recognition is active
   */
  _updateButtonState(isListening) {
    // Find all voice buttons
    document.querySelectorAll('.voice-input-button').forEach(button => {
      // Check if this button is associated with the current target element
      const input = button.closest('.input-group').querySelector('input, textarea');
      
      if (input === this.targetElement) {
        // This is the active button
        if (isListening) {
          button.classList.add('btn-danger');
          button.classList.remove('btn-outline-secondary');
          button.innerHTML = '<i class="fas fa-microphone-slash"></i>';
          button.title = 'Click to stop';
        } else {
          button.classList.remove('btn-danger');
          button.classList.add('btn-outline-secondary');
          button.innerHTML = '<i class="fas fa-microphone"></i>';
          button.title = 'Click to speak';
        }
      } else {
        // Reset other buttons
        button.classList.remove('btn-danger');
        button.classList.add('btn-outline-secondary');
        button.innerHTML = '<i class="fas fa-microphone"></i>';
        button.title = 'Click to speak';
      }
    });
  }
  
  /**
   * Clear text in the target element (voice command)
   */
  _clearText() {
    if (this.targetElement) {
      if (this.targetElement.tagName === 'TEXTAREA' || this.targetElement.tagName === 'INPUT') {
        this.targetElement.value = '';
      } else if (this.targetElement.isContentEditable) {
        this.targetElement.innerHTML = '';
      }
    }
    
    // Trigger haptic feedback if available
    if (window.hapticFeedback) {
      window.hapticFeedback.trigger('mediumImpact');
    }
  }
  
  /**
   * Submit the form containing the target element (voice command)
   */
  _submitForm() {
    if (this.targetElement) {
      const form = this.targetElement.closest('form');
      if (form) {
        form.submit();
      }
    }
    
    // Trigger haptic feedback if available
    if (window.hapticFeedback) {
      window.hapticFeedback.trigger('success');
    }
  }
  
  /**
   * Stop listening (voice command)
   */
  _stopListening() {
    this.stop();
    
    // Trigger haptic feedback if available
    if (window.hapticFeedback) {
      window.hapticFeedback.trigger('selection');
    }
  }
  
  /**
   * Insert a new line in the target element (voice command)
   */
  _insertNewLine() {
    if (this.targetElement) {
      if (this.targetElement.tagName === 'TEXTAREA') {
        const cursorPos = this.targetElement.selectionStart;
        const currentValue = this.targetElement.value;
        const beforeCursor = currentValue.substring(0, cursorPos);
        const afterCursor = currentValue.substring(cursorPos);
        
        this.targetElement.value = beforeCursor + '\n' + afterCursor;
        
        // Set cursor position after the new line
        this.targetElement.selectionStart = this.targetElement.selectionEnd = cursorPos + 1;
      } else if (this.targetElement.isContentEditable) {
        // Insert line break in contentEditable element
        document.execCommand('insertLineBreak');
      }
    }
  }
}

// Initialize voice input manager and make it globally accessible
const voiceInput = new VoiceInputManager();
window.voiceInput = voiceInput;