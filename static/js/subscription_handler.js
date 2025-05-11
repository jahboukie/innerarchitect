/**
 * Subscription Handler
 * 
 * This module handles subscription-related interactions on the frontend,
 * including displaying quota limitations and upgrade prompts.
 */

const SubscriptionHandler = {
    /**
     * Handle API response that includes a quota_exceeded flag
     * @param {Object} response - API response object
     * @param {Function} callback - Callback function to execute if quota is not exceeded
     */
    handleQuotaResponse: function(response, callback) {
        if (response && response.quota_exceeded) {
            this.showQuotaExceededModal(response.error || 'You have reached your subscription limit.');
            return false;
        }
        
        if (typeof callback === 'function') {
            callback(response);
        }
        
        return true;
    },
    
    /**
     * Show a modal when user has exceeded their subscription quota
     * @param {string} message - The error message to display
     */
    showQuotaExceededModal: function(message) {
        // Check if modal already exists
        let modal = document.getElementById('quotaExceededModal');
        
        if (!modal) {
            // Create modal element
            modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.id = 'quotaExceededModal';
            modal.setAttribute('tabindex', '-1');
            modal.setAttribute('aria-labelledby', 'quotaExceededModalLabel');
            modal.setAttribute('aria-hidden', 'true');
            
            modal.innerHTML = `
                <div class="modal-dialog">
                    <div class="modal-content bg-dark text-light">
                        <div class="modal-header border-bottom border-secondary">
                            <h5 class="modal-title" id="quotaExceededModalLabel">Subscription Limit Reached</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body" id="quotaExceededMessage">
                            ${message}
                        </div>
                        <div class="modal-footer border-top border-secondary">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <a href="/landing" class="btn btn-primary">Upgrade Subscription</a>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
        } else {
            // Update existing modal message
            document.getElementById('quotaExceededMessage').textContent = message;
        }
        
        // Initialize and show modal
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    },
    
    /**
     * Handle errors from API requests and check if they're quota-related
     * @param {Object} error - Error object from API request
     */
    handleApiError: function(error) {
        if (error && error.responseJSON && error.responseJSON.quota_exceeded) {
            this.showQuotaExceededModal(error.responseJSON.error || 'Subscription limit reached');
            return true;
        }
        return false;
    },
    
    /**
     * Initialize event handlers for subscription-related elements
     */
    init: function() {
        // Add event listeners for upgrade buttons
        document.querySelectorAll('.upgrade-subscription-btn').forEach(button => {
            button.addEventListener('click', function(e) {
                window.location.href = '/landing';
            });
        });
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    SubscriptionHandler.init();
});