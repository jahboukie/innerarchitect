/**
 * Haptic Feedback Module for The Inner Architect
 * 
 * This module provides haptic feedback functionality for mobile devices,
 * enhancing the user experience with touch feedback.
 */

class HapticFeedback {
  constructor() {
    // Check if vibration is supported
    this.isSupported = 'vibrate' in navigator;
    
    // Default patterns
    this.patterns = {
      success: [50],
      error: [100, 50, 100],
      warning: [50, 50, 50],
      notification: [50, 100, 50],
      selection: [20],
      longPress: [50],
      heavyImpact: [70],
      mediumImpact: [40],
      lightImpact: [20],
      doubleImpact: [20, 50, 20]
    };
    
    this.isEnabled = this._loadPreference();
    
    // Initialize when DOM is loaded
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.init());
    } else {
      this.init();
    }
  }
  
  /**
   * Initialize haptic feedback
   */
  init() {
    // Add haptic toggle to settings if available
    const hapticToggle = document.getElementById('haptic-feedback-toggle');
    if (hapticToggle) {
      hapticToggle.checked = this.isEnabled;
      hapticToggle.addEventListener('change', (e) => {
        this.isEnabled = e.target.checked;
        this._savePreference();
        
        // Provide feedback when enabled
        if (this.isEnabled) {
          this.trigger('success');
        }
      });
    }
    
    // Set up haptic elements - anything with data-haptic attribute
    this._setupHapticElements();
    
    console.log(`Haptic feedback initialized. Supported: ${this.isSupported}, Enabled: ${this.isEnabled}`);
  }
  
  /**
   * Load user preference for haptic feedback
   */
  _loadPreference() {
    try {
      const saved = localStorage.getItem('hapticFeedbackEnabled');
      return saved !== null ? JSON.parse(saved) : true; // Default to enabled
    } catch (error) {
      console.error('Error loading haptic feedback preference:', error);
      return true;
    }
  }
  
  /**
   * Save user preference for haptic feedback
   */
  _savePreference() {
    try {
      localStorage.setItem('hapticFeedbackEnabled', JSON.stringify(this.isEnabled));
    } catch (error) {
      console.error('Error saving haptic feedback preference:', error);
    }
  }
  
  /**
   * Set up elements with haptic feedback
   */
  _setupHapticElements() {
    // Find all elements with data-haptic attribute
    document.querySelectorAll('[data-haptic]').forEach(element => {
      const pattern = element.dataset.haptic || 'selection';
      
      element.addEventListener('click', () => {
        this.trigger(pattern);
      });
      
      // For elements with long-press functionality
      if (element.dataset.hapticLongpress) {
        let pressTimer;
        
        element.addEventListener('touchstart', () => {
          pressTimer = setTimeout(() => {
            this.trigger('longPress');
          }, 500);
        });
        
        element.addEventListener('touchend', () => {
          clearTimeout(pressTimer);
        });
        
        element.addEventListener('touchmove', () => {
          clearTimeout(pressTimer);
        });
      }
    });
    
    // Set up form elements
    this._setupFormElements();
  }
  
  /**
   * Set up haptic feedback for form elements
   */
  _setupFormElements() {
    // Buttons
    document.querySelectorAll('button:not([data-haptic])').forEach(button => {
      button.addEventListener('click', () => {
        if (button.classList.contains('btn-primary')) {
          this.trigger('mediumImpact');
        } else if (button.classList.contains('btn-danger')) {
          this.trigger('error');
        } else {
          this.trigger('selection');
        }
      });
    });
    
    // Checkboxes and radio buttons
    document.querySelectorAll('input[type="checkbox"], input[type="radio"]').forEach(input => {
      input.addEventListener('change', () => {
        this.trigger('selection');
      });
    });
    
    // Toggle switches
    document.querySelectorAll('.form-switch input[type="checkbox"]').forEach(toggle => {
      toggle.addEventListener('change', () => {
        this.trigger('mediumImpact');
      });
    });
    
    // Select dropdowns
    document.querySelectorAll('select').forEach(select => {
      select.addEventListener('change', () => {
        this.trigger('selection');
      });
    });
  }
  
  /**
   * Trigger haptic feedback with the specified pattern
   * @param {string|number[]} pattern - The name of a predefined pattern or a custom vibration pattern
   */
  trigger(pattern) {
    if (!this.isSupported || !this.isEnabled) {
      return false;
    }
    
    try {
      let vibrationPattern;
      
      if (typeof pattern === 'string') {
        vibrationPattern = this.patterns[pattern] || this.patterns.selection;
      } else if (Array.isArray(pattern)) {
        vibrationPattern = pattern;
      } else {
        vibrationPattern = this.patterns.selection;
      }
      
      navigator.vibrate(vibrationPattern);
      return true;
    } catch (error) {
      console.error('Error triggering haptic feedback:', error);
      return false;
    }
  }
  
  /**
   * Check if haptic feedback is supported
   */
  isHapticSupported() {
    return this.isSupported;
  }
  
  /**
   * Enable haptic feedback
   */
  enable() {
    this.isEnabled = true;
    this._savePreference();
    
    // Update toggle if it exists
    const hapticToggle = document.getElementById('haptic-feedback-toggle');
    if (hapticToggle) {
      hapticToggle.checked = true;
    }
    
    // Provide feedback that it was enabled
    this.trigger('success');
  }
  
  /**
   * Disable haptic feedback
   */
  disable() {
    this.isEnabled = false;
    this._savePreference();
    
    // Update toggle if it exists
    const hapticToggle = document.getElementById('haptic-feedback-toggle');
    if (hapticToggle) {
      hapticToggle.checked = false;
    }
  }
  
  /**
   * Add a custom pattern
   * @param {string} name - The name of the pattern
   * @param {number[]} pattern - The vibration pattern (array of durations in ms)
   */
  addPattern(name, pattern) {
    if (!Array.isArray(pattern)) {
      console.error('Pattern must be an array of durations');
      return false;
    }
    
    this.patterns[name] = pattern;
    return true;
  }
}

// Initialize haptic feedback and make it globally accessible
const hapticFeedback = new HapticFeedback();
window.hapticFeedback = hapticFeedback;