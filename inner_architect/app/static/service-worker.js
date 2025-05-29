// Service Worker for The Inner Architect PWA
'use strict';

const CACHE_NAME = 'inner-architect-v2';
const OFFLINE_DB_NAME = 'inner-architect-offline';
const OFFLINE_STORE_NAME = 'user-actions';
const ASSETS_TO_CACHE = [
  '/',
  '/static/style.css',
  '/static/css/premium.css',
  '/static/js/subscription_handler.js',
  '/static/js/offline-sync.js',
  '/static/js/push-notifications.js',
  '/offline',
  '/static/icons/icon-72x72.png',
  '/static/icons/icon-96x96.png',
  '/static/icons/icon-128x128.png',
  '/static/icons/icon-144x144.png',
  '/static/icons/icon-152x152.png',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-384x384.png',
  '/static/icons/icon-512x512.png',
  '/static/icons/chat-shortcut.png',
  '/static/icons/progress-shortcut.png',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
];

// Cache additional resources for offline access
const OFFLINE_RESOURCES = [
  '/techniques',
  '/dashboard',
  '/profile',
  '/static/js/techniques-offline.js',
  '/static/js/exercises-offline.js',
  '/static/data/techniques.json',
  '/static/data/exercises.json'
];

// Install event - cache assets with error handling
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        
        // Cache core assets
        return cache.addAll(ASSETS_TO_CACHE)
          .then(() => {
            // Cache additional offline resources
            return cache.addAll(OFFLINE_RESOURCES);
          })
          .catch(error => {
            console.error('Cache addAll error:', error);
            // Continue installation even if some assets fail to cache
            return Promise.resolve();
          });
      })
      .then(() => {
        // Initialize IndexedDB for offline data
        return initOfflineDatabase();
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    Promise.all([
      caches.keys().then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => {
            if (cacheName !== CACHE_NAME) {
              return caches.delete(cacheName);
            }
          })
        );
      }),
      self.clients.claim()
    ])
  );
});

// Fetch event - network first with offline fallback strategy
self.addEventListener('fetch', event => {
  // Skip non-GET requests and cross-origin requests
  if (event.request.method !== 'GET' || !event.request.url.startsWith(self.location.origin)) {
    return;
  }

  // Handle API requests differently - they need special handling for offline mode
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
            
            // If we get here, we can't serve the request
            console.log('No offline content available for:', event.request.url);
            return new Response('Offline content not available', { 
              status: 503,
              statusText: 'Service Unavailable',
              headers: new Headers({ 'Content-Type': 'text/plain' })
            });
          });
      })
  );
});

// Handle API requests - special handling for offline mode
function handleApiRequest(event) {
  event.respondWith(
    fetch(event.request.clone())
      .then(response => {
        return response;
      })
      .catch(error => {
        console.log('API request failed, saving to offline queue:', event.request.url);
        
        // If it's a POST/PUT/DELETE, save it to IndexedDB for later sync
        if (event.request.method !== 'GET') {
          event.waitUntil(
            saveActionForSync(event.request.clone())
          );
        }
        
        // For GET requests in API, try to serve cached data if available
        if (event.request.method === 'GET') {
          return caches.match(event.request)
            .then(cachedResponse => {
              if (cachedResponse) {
                return cachedResponse;
              }
              
              // Generate fallback response based on the endpoint
              return generateFallbackResponse(event.request.url);
            });
        }
        
        // Return a basic success response for non-GET requests
        // The actual operation will be performed when online
        return new Response(JSON.stringify({
          success: true,
          offline: true,
          message: 'Your request has been saved and will be processed when you are back online.'
        }), {
          headers: { 'Content-Type': 'application/json' }
        });
      })
  );
}

// Initialize IndexedDB for offline storage
function initOfflineDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(OFFLINE_DB_NAME, 1);
    
    request.onerror = event => {
      console.error('IndexedDB error:', event.target.error);
      reject(event.target.error);
    };
    
    request.onupgradeneeded = event => {
      const db = event.target.result;
      
      // Create object store for offline actions
      if (!db.objectStoreNames.contains(OFFLINE_STORE_NAME)) {
        const store = db.createObjectStore(OFFLINE_STORE_NAME, { keyPath: 'id', autoIncrement: true });
        store.createIndex('timestamp', 'timestamp', { unique: false });
        store.createIndex('synced', 'synced', { unique: false });
        console.log('Created offline actions store');
      }
    };
    
    request.onsuccess = event => {
      console.log('IndexedDB initialized successfully');
      resolve(event.target.result);
    };
  });
}

// Save an action for later synchronization
async function saveActionForSync(request) {
  try {
    const db = await openDB();
    const tx = db.transaction(OFFLINE_STORE_NAME, 'readwrite');
    const store = tx.objectStore(OFFLINE_STORE_NAME);
    
    // Clone request data
    const requestData = await request.clone().text();
    
    // Store action
    const action = {
      url: request.url,
      method: request.method,
      headers: Array.from(request.headers.entries()),
      data: requestData,
      timestamp: Date.now(),
      synced: false
    };
    
    await store.add(action);
    await tx.complete;
    
    console.log('Saved action for later sync:', action);
    return true;
  } catch (error) {
    console.error('Error saving action for sync:', error);
    return false;
  }
}

// Open the IndexedDB database
function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(OFFLINE_DB_NAME, 1);
    request.onerror = event => reject(event.target.error);
    request.onsuccess = event => resolve(event.target.result);
  });
}

// Generate fallback response for API endpoints
function generateFallbackResponse(url) {
  const responseData = { offline: true };
  
  // Add specific data based on the endpoint
  if (url.includes('/api/techniques')) {
    responseData.techniques = getTechniquesOfflineData();
  } else if (url.includes('/api/exercises')) {
    responseData.exercises = getExercisesOfflineData();
  } else if (url.includes('/api/user/profile')) {
    responseData.profile = getUserProfileOfflineData();
  } else {
    responseData.message = 'This data is not available offline';
  }
  
  return new Response(JSON.stringify(responseData), {
    headers: { 'Content-Type': 'application/json' }
  });
}

// Offline data for techniques
function getTechniquesOfflineData() {
  return [
    { id: 'reframing', name: 'Reframing', description: 'Change perspective on situations' },
    { id: 'anchoring', name: 'Anchoring', description: 'Link positive states to triggers' },
    { id: 'pattern_interruption', name: 'Pattern Interruption', description: 'Break negative thought patterns' }
  ];
}

// Offline data for exercises
function getExercisesOfflineData() {
  return [
    { id: 'daily_reframe', name: 'Daily Reframing', type: 'reframing' },
    { id: 'confidence_anchor', name: 'Confidence Anchor', type: 'anchoring' }
  ];
}

// Offline user profile data
function getUserProfileOfflineData() {
  return {
    name: 'Offline User',
    exercises_completed: 0,
    streak_days: 0
  };
}

// Background sync for offline actions
self.addEventListener('sync', event => {
  if (event.tag === 'sync-user-data') {
    event.waitUntil(syncUserData());
  } else if (event.tag === 'sync-exercise-progress') {
    event.waitUntil(syncExerciseProgress());
  } else if (event.tag === 'sync-all') {
    event.waitUntil(syncAll());
  }
});

// Sync user data
async function syncUserData() {
  console.log('Syncing user data...');
  return syncOfflineActions(/\/api\/user\//);
}

// Sync exercise progress
async function syncExerciseProgress() {
  console.log('Syncing exercise progress...');
  return syncOfflineActions(/\/api\/exercises\/progress/);
}

// Sync all offline actions
async function syncAll() {
  console.log('Syncing all offline actions...');
  return syncOfflineActions(/.*/);
}

// Sync offline actions based on URL pattern
async function syncOfflineActions(urlPattern) {
  try {
    const db = await openDB();
    const tx = db.transaction(OFFLINE_STORE_NAME, 'readwrite');
    const store = tx.objectStore(OFFLINE_STORE_NAME);
    const index = store.index('synced');
    
    const unsyncedActions = await index.getAll(false);
    
    const syncPromises = unsyncedActions
      .filter(action => urlPattern.test(action.url))
      .map(async action => {
        try {
          // Recreate the request
          const request = new Request(action.url, {
            method: action.method,
            headers: new Headers(action.headers),
            body: action.method !== 'GET' ? action.data : undefined
          });
          
          // Send the request
          const response = await fetch(request);
          
          if (response.ok) {
            // Mark action as synced
            action.synced = true;
            await store.put(action);
            console.log('Synced action:', action.url);
            return true;
          } else {
            console.error('Sync failed for action:', action.url, response.status);
            return false;
          }
        } catch (error) {
          console.error('Error syncing action:', action.url, error);
          return false;
        }
      });
    
    const results = await Promise.all(syncPromises);
    await tx.complete;
    
    // Count successful syncs
    const successCount = results.filter(Boolean).length;
    console.log(`Synced ${successCount} out of ${results.length} actions`);
    
    return successCount;
  } catch (error) {
    console.error('Error syncing offline actions:', error);
    return 0;
  }
}

// Handle push notifications
self.addEventListener('push', event => {
  console.log('Push notification received', event);
  
  const data = event.data.json();
  const options = {
    body: data.body,
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/maskable-icon.png',
    vibrate: [100, 50, 100],
    data: {
      url: data.url || '/'
    },
    actions: data.actions || [
      {
        action: 'open',
        title: 'Open'
      },
      {
        action: 'dismiss',
        title: 'Dismiss'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
  event.notification.close();
  
  if (event.action === 'dismiss') {
    return;
  }
  
  // Default behavior - open the app and navigate to the specified URL
  const url = event.notification.data.url || '/';
  
  event.waitUntil(
    clients.matchAll({ type: 'window' })
      .then(clientsList => {
        // If a window is already open, focus it and navigate
        for (const client of clientsList) {
          if (client.url.includes(self.location.origin) && 'focus' in client) {
            client.focus();
            client.navigate(url);
            return;
          }
        }
        
        // Otherwise open a new window
        if (clients.openWindow) {
          return clients.openWindow(url);
        }
      })
  );
});

// Handle periodic background sync (advanced feature)
self.addEventListener('periodicsync', event => {
  if (event.tag === 'check-reminders') {
    event.waitUntil(checkReminders());
  } else if (event.tag === 'update-content') {
    event.waitUntil(updateOfflineContent());
  }
});

// Check for due reminders
async function checkReminders() {
  console.log('Checking for due reminders...');
  
  try {
    const response = await fetch('/api/reminders/due');
    const reminders = await response.json();
    
    if (reminders.length > 0) {
      // Show notification for the first due reminder
      const reminder = reminders[0];
      
      await self.registration.showNotification('Practice Reminder', {
        body: reminder.title,
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/maskable-icon.png',
        vibrate: [100, 50, 100],
        data: {
          url: `/reminders/${reminder.reminder_id}`
        },
        actions: [
          {
            action: 'complete',
            title: 'Mark Complete'
          },
          {
            action: 'snooze',
            title: 'Snooze'
          }
        ]
      });
    }
    
    return true;
  } catch (error) {
    console.error('Error checking reminders:', error);
    return false;
  }
}

// Update offline content
async function updateOfflineContent() {
  console.log('Updating offline content...');
  
  try {
    const cache = await caches.open(CACHE_NAME);
    
    // Refresh cached resources
    await Promise.all(
      OFFLINE_RESOURCES.map(url => 
        fetch(url).then(response => {
          if (response.ok) {
            return cache.put(url, response);
          }
        }).catch(error => {
          console.error('Error updating cache for:', url, error);
        })
      )
    );
    
    console.log('Offline content updated successfully');
    return true;
  } catch (error) {
    console.error('Error updating offline content:', error);
    return false;
  }
}