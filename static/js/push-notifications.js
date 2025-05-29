/**
 * Push Notifications Management for The Inner Architect
 * 
 * This module manages push notification registration, permissions,
 * and user preferences for notifications.
 */

class PushNotificationManager {
  constructor() {
    this.pushSupported = ('serviceWorker' in navigator) && ('PushManager' in window);
    this.notificationPermission = Notification.permission;
    this.swRegistration = null;
    this.userPreferences = {
      practiceReminders: true,
      journeyUpdates: true,
      exerciseRecommendations: true,
      systemAnnouncements: true
    };
    
    // Initialize when the DOM is loaded
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.init());
    } else {
      this.init();
    }
  }
  
  /**
   * Initialize the push notification manager
   */
  async init() {
    if (!this.pushSupported) {
      console.log('Push notifications not supported in this browser');
      this.updateUI();
      return;
    }
    
    try {
      // Get service worker registration
      this.swRegistration = await navigator.serviceWorker.ready;
      
      // Load user preferences from localStorage
      this.loadUserPreferences();
      
      // Set up UI elements
      this.setupUI();
      
      // Check subscription status
      await this.updateSubscriptionStatus();
      
      console.log('Push notification manager initialized');
    } catch (error) {
      console.error('Error initializing push notification manager:', error);
    }
  }
  
  /**
   * Load user preferences from local storage
   */
  loadUserPreferences() {
    try {
      const savedPrefs = localStorage.getItem('pushNotificationPreferences');
      if (savedPrefs) {
        this.userPreferences = JSON.parse(savedPrefs);
      }
    } catch (error) {
      console.error('Error loading push notification preferences:', error);
    }
  }
  
  /**
   * Save user preferences to local storage
   */
  saveUserPreferences() {
    try {
      localStorage.setItem('pushNotificationPreferences', JSON.stringify(this.userPreferences));
      
      // Send preferences to server if user is subscribed
      this.sendPreferencesToServer();
    } catch (error) {
      console.error('Error saving push notification preferences:', error);
    }
  }
  
  /**
   * Set up UI elements for notification preferences
   */
  setupUI() {
    // Set up permission request button
    const permissionBtn = document.getElementById('push-permission-btn');
    if (permissionBtn) {
      permissionBtn.addEventListener('click', () => this.requestPermission());
    }
    
    // Set up preference toggles
    this.setupPreferenceToggles();
    
    // Update UI based on current state
    this.updateUI();
  }
  
  /**
   * Set up preference toggle switches
   */
  setupPreferenceToggles() {
    // Practice reminders toggle
    const practiceToggle = document.getElementById('push-practice-toggle');
    if (practiceToggle) {
      practiceToggle.checked = this.userPreferences.practiceReminders;
      practiceToggle.addEventListener('change', (e) => {
        this.userPreferences.practiceReminders = e.target.checked;
        this.saveUserPreferences();
      });
    }
    
    // Journey updates toggle
    const journeyToggle = document.getElementById('push-journey-toggle');
    if (journeyToggle) {
      journeyToggle.checked = this.userPreferences.journeyUpdates;
      journeyToggle.addEventListener('change', (e) => {
        this.userPreferences.journeyUpdates = e.target.checked;
        this.saveUserPreferences();
      });
    }
    
    // Exercise recommendations toggle
    const exerciseToggle = document.getElementById('push-exercise-toggle');
    if (exerciseToggle) {
      exerciseToggle.checked = this.userPreferences.exerciseRecommendations;
      exerciseToggle.addEventListener('change', (e) => {
        this.userPreferences.exerciseRecommendations = e.target.checked;
        this.saveUserPreferences();
      });
    }
    
    // System announcements toggle
    const systemToggle = document.getElementById('push-system-toggle');
    if (systemToggle) {
      systemToggle.checked = this.userPreferences.systemAnnouncements;
      systemToggle.addEventListener('change', (e) => {
        this.userPreferences.systemAnnouncements = e.target.checked;
        this.saveUserPreferences();
      });
    }
  }
  
  /**
   * Update UI based on current notification permission
   */
  updateUI() {
    const permissionStatus = document.getElementById('notification-permission-status');
    const preferencesSection = document.getElementById('notification-preferences-section');
    const permissionBtn = document.getElementById('push-permission-btn');
    
    if (!this.pushSupported) {
      // Push not supported
      if (permissionStatus) {
        permissionStatus.textContent = 'Push notifications are not supported in this browser.';
        permissionStatus.className = 'text-secondary';
      }
      
      if (permissionBtn) {
        permissionBtn.disabled = true;
      }
      
      if (preferencesSection) {
        preferencesSection.classList.add('d-none');
      }
      
      return;
    }
    
    // Update based on permission state
    if (permissionStatus) {
      if (this.notificationPermission === 'granted') {
        permissionStatus.textContent = 'Push notifications are enabled.';
        permissionStatus.className = 'text-success';
      } else if (this.notificationPermission === 'denied') {
        permissionStatus.textContent = 'Push notifications are blocked. Please update your browser settings to enable notifications.';
        permissionStatus.className = 'text-danger';
      } else {
        permissionStatus.textContent = 'Push notification permission has not been requested yet.';
        permissionStatus.className = 'text-warning';
      }
    }
    
    // Update button state
    if (permissionBtn) {
      if (this.notificationPermission === 'granted') {
        permissionBtn.textContent = 'Notifications Enabled';
        permissionBtn.disabled = true;
      } else if (this.notificationPermission === 'denied') {
        permissionBtn.textContent = 'Notifications Blocked';
        permissionBtn.disabled = true;
      } else {
        permissionBtn.textContent = 'Enable Notifications';
        permissionBtn.disabled = false;
      }
    }
    
    // Show/hide preferences section
    if (preferencesSection) {
      if (this.notificationPermission === 'granted') {
        preferencesSection.classList.remove('d-none');
      } else {
        preferencesSection.classList.add('d-none');
      }
    }
  }
  
  /**
   * Request permission for push notifications
   */
  async requestPermission() {
    if (!this.pushSupported) {
      console.log('Push notifications not supported');
      return;
    }
    
    try {
      const permission = await Notification.requestPermission();
      this.notificationPermission = permission;
      
      if (permission === 'granted') {
        await this.subscribeToPush();
      }
      
      this.updateUI();
    } catch (error) {
      console.error('Error requesting notification permission:', error);
    }
  }
  
  /**
   * Check current push subscription status
   */
  async updateSubscriptionStatus() {
    if (!this.pushSupported || !this.swRegistration) {
      return;
    }
    
    try {
      const subscription = await this.swRegistration.pushManager.getSubscription();
      
      // If permission is granted but not subscribed, subscribe
      if (this.notificationPermission === 'granted' && !subscription) {
        await this.subscribeToPush();
      }
    } catch (error) {
      console.error('Error checking subscription status:', error);
    }
  }
  
  /**
   * Subscribe to push notifications
   */
  async subscribeToPush() {
    if (!this.pushSupported || !this.swRegistration) {
      return false;
    }
    
    try {
      // Get public key from server
      const response = await fetch('/api/push/vapid-public-key');
      const vapidPublicKeyJson = await response.json();
      const vapidPublicKey = vapidPublicKeyJson.key;
      
      // Convert public key to Uint8Array
      const convertedVapidKey = this.urlBase64ToUint8Array(vapidPublicKey);
      
      // Subscribe
      const subscription = await this.swRegistration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: convertedVapidKey
      });
      
      // Send subscription to server
      await this.sendSubscriptionToServer(subscription);
      
      console.log('User subscribed to push notifications');
      return true;
    } catch (error) {
      console.error('Error subscribing to push notifications:', error);
      return false;
    }
  }
  
  /**
   * Unsubscribe from push notifications
   */
  async unsubscribeFromPush() {
    if (!this.pushSupported || !this.swRegistration) {
      return false;
    }
    
    try {
      const subscription = await this.swRegistration.pushManager.getSubscription();
      
      if (subscription) {
        // Send unsubscribe request to server
        await this.sendUnsubscribeToServer(subscription);
        
        // Unsubscribe on client
        await subscription.unsubscribe();
        
        console.log('User unsubscribed from push notifications');
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('Error unsubscribing from push notifications:', error);
      return false;
    }
  }
  
  /**
   * Send subscription information to server
   */
  async sendSubscriptionToServer(subscription) {
    try {
      await fetch('/api/push/subscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          subscription: subscription.toJSON(),
          preferences: this.userPreferences
        })
      });
      
      console.log('Subscription sent to server');
    } catch (error) {
      console.error('Error sending subscription to server:', error);
    }
  }
  
  /**
   * Send unsubscribe request to server
   */
  async sendUnsubscribeToServer(subscription) {
    try {
      await fetch('/api/push/unsubscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          subscription: subscription.toJSON()
        })
      });
      
      console.log('Unsubscribe request sent to server');
    } catch (error) {
      console.error('Error sending unsubscribe request to server:', error);
    }
  }
  
  /**
   * Send user preferences to server
   */
  async sendPreferencesToServer() {
    try {
      // Only send if we have a subscription
      if (!this.swRegistration) return;
      
      const subscription = await this.swRegistration.pushManager.getSubscription();
      if (!subscription) return;
      
      await fetch('/api/push/preferences', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          subscription: subscription.toJSON(),
          preferences: this.userPreferences
        })
      });
      
      console.log('Preferences sent to server');
    } catch (error) {
      console.error('Error sending preferences to server:', error);
    }
  }
  
  /**
   * Test sending a notification (for debugging)
   */
  async testNotification(title, body, tag) {
    if (this.notificationPermission !== 'granted') {
      console.log('Notification permission not granted');
      return;
    }
    
    const options = {
      body: body || 'This is a test notification',
      icon: '/static/icons/icon-192x192.png',
      badge: '/static/icons/maskable-icon.png',
      tag: tag || 'test-notification',
      vibrate: [100, 50, 100],
      data: {
        url: '/'
      }
    };
    
    await this.swRegistration.showNotification(title || 'Test Notification', options);
  }
  
  /**
   * Convert base64 to Uint8Array for push subscription
   */
  urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/\-/g, '+')
      .replace(/_/g, '/');
    
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    
    return outputArray;
  }
}

// Initialize the push notification manager
const pushManager = new PushNotificationManager();

// Expose for debugging
window.pushManager = pushManager;