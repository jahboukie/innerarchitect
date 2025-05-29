# Mobile App Integration Documentation

This document outlines the mobile app integration features that have been added to InnerArchitect, enhancing the existing Progressive Web App (PWA) capabilities with native-like features.

## Overview

The mobile app integration adds the following key features:

1. **Enhanced Offline Support**: Robust offline functionality with background sync capabilities
2. **Push Notifications**: Implementation of web push notifications for reminders and updates
3. **Voice Input**: Speech recognition for hands-free interaction
4. **Haptic Feedback**: Tactile feedback for improved user experience on mobile devices

## Components

### 1. Enhanced Service Worker

The enhanced service worker (`service-worker.js`) provides:

- Improved caching strategy with network-first approach
- IndexedDB integration for offline data storage
- Background sync API integration for syncing offline actions
- Push notification handling
- Periodic background sync for content updates
- Custom API response generation for offline use

Key improvements:
- Added robust error handling for failed API requests
- Implemented queueing system for offline actions
- Added periodic background sync for checking reminders
- Expanded caching strategy to include more resources

### 2. Push Notification System

The push notification system includes:

- API endpoints for managing push subscriptions
- Client-side push notification management
- VAPID key generation and management
- User preference controls for notification types
- Specialized notifications for practice reminders

Implementation files:
- `/api/push_notifications.py`: Server-side API endpoints
- `/static/js/push-notifications.js`: Client-side notification management
- `/templates/practice_reminders.html`: User interface for notification settings

### 3. Offline Sync Manager

The offline sync manager provides:

- Client-side tracking of offline actions
- Background synchronization when connectivity is restored
- Conflict resolution for offline changes
- Local data caching for offline use
- Visual indicators for offline status and pending sync actions

Implementation files:
- `/api/offline_sync.py`: Server-side API endpoints for sync
- `/static/js/offline-sync.js`: Client-side offline management
- Templates updated with offline status indicators

### 4. Voice Input

The voice input system enables:

- Speech recognition for text input
- Voice command support
- Visual feedback during speech recognition
- Support for multiple languages
- Integration with existing form elements

Implementation file:
- `/static/js/voice-input.js`: Voice input management

### 5. Haptic Feedback

The haptic feedback system provides:

- Tactile feedback for user interactions
- Customizable vibration patterns for different actions
- User preference controls for enabling/disabling
- Integration with buttons, form elements, and gestures

Implementation file:
- `/static/js/haptic-feedback.js`: Haptic feedback management

## Implementation Details

### Service Worker Enhancements

The service worker has been completely redesigned to support better offline functionality:

```javascript
// Previous approach - Simple caching
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});

// New approach - Network first with offline fallback and API handling
self.addEventListener('fetch', event => {
  // Skip non-GET requests and cross-origin requests
  if (event.request.method !== 'GET' || !event.request.url.startsWith(self.location.origin)) {
    return;
  }

  // Handle API requests differently
  if (event.request.url.includes('/api/')) {
    handleApiRequest(event);
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Cache successful responses
        if (response && response.status === 200) {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME)
            .then(cache => {
              cache.put(event.request, responseToCache);
            });
        }
        return response;
      })
      .catch(() => {
        // Fallback to cache or offline page
        return caches.match(event.request)
          .then(response => {
            if (response) {
              return response;
            }
            
            // If the request is for a page, serve the offline page
            if (event.request.headers.get('accept').includes('text/html')) {
              return caches.match('/offline');
            }
            
            return new Response('Offline content not available', { 
              status: 503,
              statusText: 'Service Unavailable'
            });
          });
      })
  );
});
```

### Push Notifications Implementation

The push notification system uses the Web Push API with VAPID authentication:

```javascript
// Client-side subscription
async subscribeToPush() {
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
```

### Voice Input Integration

The voice input system uses the Web Speech API:

```javascript
// Start voice recognition for an input element
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
```

## Usage Guidelines

### Offline Mode

The application will automatically detect when the device is offline and:

1. Show an offline indicator to the user
2. Store any user actions for later synchronization
3. Provide access to cached content
4. Automatically sync when connectivity is restored

### Push Notifications

To enable push notifications:

1. Users need to grant notification permission
2. Configure notification preferences in the Settings or Practice Reminders page
3. Notifications will be sent for:
   - Practice reminders
   - Journey updates
   - Exercise recommendations
   - System announcements

### Voice Input

Voice input is available on:

1. Text input fields with the `data-voice-input` attribute
2. The chat interface for hands-free interaction
3. Exercise instructions for accessibility

Voice commands include:
- "Clear text"
- "Submit form"
- "New line"
- "Cancel"

### Haptic Feedback

Haptic feedback is provided for:

1. Button clicks
2. Toggle switches
3. Form submissions
4. Notifications
5. Error states

Users can enable/disable haptic feedback in the Settings page.

## Testing

Testing the mobile app integration features:

1. **Offline Mode**:
   - Enable Chrome DevTools > Network > Offline
   - Interact with the application and observe behavior
   - Re-enable network and observe synchronization

2. **Push Notifications**:
   - Grant notification permission
   - Create a practice reminder
   - Test using the "Check Due Reminders" button

3. **Voice Input**:
   - Click the microphone icon on supported input fields
   - Test voice commands in the chat interface
   - Verify different languages if supported

4. **Haptic Feedback**:
   - Test on a mobile device with vibration support
   - Enable/disable in settings to verify preference is saved

## Browser Compatibility

- **Full Support**: Chrome for Android, Samsung Internet, Edge for Android
- **Partial Support**: iOS Safari (limited push notification and background sync support)
- **Limited Support**: Firefox for Android (no background sync)

## Future Enhancements

Planned future enhancements:

1. **Native App Wrappers**: 
   - Cordova/Capacitor wrapper for publishing to app stores
   - Enhanced access to native device features

2. **Enhanced Biometrics**:
   - Integration with fingerprint/face recognition for secure login

3. **File System Access**:
   - Support for saving and loading local files when supported

4. **Bluetooth Integration**:
   - Support for wearable devices to track stress levels

5. **AR Features**:
   - Augmented reality visualizations for anchoring techniques