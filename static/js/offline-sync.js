/**
 * Offline Synchronization Module for The Inner Architect
 * 
 * This module handles synchronization of data between online and offline modes,
 * ensuring that user data is preserved and synchronized when connectivity is restored.
 */

class OfflineSyncManager {
  constructor() {
    this.dbName = 'inner-architect-offline';
    this.dbVersion = 1;
    this.userActionsStore = 'user-actions';
    this.db = null;
    this.isOnline = navigator.onLine;
    this.syncInProgress = false;
    this.lastSyncTime = null;
    this.pendingChanges = 0;
    
    // Initialize when the DOM is loaded
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.init());
    } else {
      this.init();
    }
  }
  
  /**
   * Initialize the offline sync manager
   */
  async init() {
    try {
      // Open database
      await this.openDatabase();
      
      // Set up event listeners for online/offline
      window.addEventListener('online', () => this.handleOnlineStatusChange(true));
      window.addEventListener('offline', () => this.handleOnlineStatusChange(false));
      
      // Check pending changes
      await this.checkPendingChanges();
      
      // Set up UI elements
      this.setupUI();
      
      // Try to sync if online
      if (this.isOnline) {
        this.syncChanges();
      }
      
      console.log('Offline sync manager initialized');
    } catch (error) {
      console.error('Error initializing offline sync manager:', error);
    }
  }
  
  /**
   * Open the IndexedDB database
   */
  async openDatabase() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);
      
      request.onerror = event => {
        console.error('IndexedDB error:', event.target.error);
        reject(event.target.error);
      };
      
      request.onupgradeneeded = event => {
        const db = event.target.result;
        
        // Create object store for user actions if it doesn't exist
        if (!db.objectStoreNames.contains(this.userActionsStore)) {
          const store = db.createObjectStore(this.userActionsStore, { keyPath: 'id', autoIncrement: true });
          store.createIndex('timestamp', 'timestamp', { unique: false });
          store.createIndex('synced', 'synced', { unique: false });
          store.createIndex('type', 'type', { unique: false });
          console.log('Created user actions store');
        }
      };
      
      request.onsuccess = event => {
        this.db = event.target.result;
        console.log('IndexedDB opened successfully');
        resolve(this.db);
      };
    });
  }
  
  /**
   * Set up UI elements for offline status and sync
   */
  setupUI() {
    // Update offline status indicator
    this.updateOfflineStatusUI();
    
    // Set up manual sync button
    const syncBtn = document.getElementById('manual-sync-btn');
    if (syncBtn) {
      syncBtn.addEventListener('click', () => this.syncChanges());
    }
  }
  
  /**
   * Update UI to reflect offline status
   */
  updateOfflineStatusUI() {
    // Update offline indicator
    const offlineIndicator = document.getElementById('offline-indicator');
    const pendingChangesIndicator = document.getElementById('pending-changes-indicator');
    const lastSyncIndicator = document.getElementById('last-sync-indicator');
    
    if (offlineIndicator) {
      if (this.isOnline) {
        offlineIndicator.classList.add('d-none');
      } else {
        offlineIndicator.classList.remove('d-none');
      }
    }
    
    // Update pending changes indicator
    if (pendingChangesIndicator) {
      if (this.pendingChanges > 0) {
        pendingChangesIndicator.textContent = `${this.pendingChanges} pending change${this.pendingChanges > 1 ? 's' : ''}`;
        pendingChangesIndicator.classList.remove('d-none');
      } else {
        pendingChangesIndicator.classList.add('d-none');
      }
    }
    
    // Update last sync time
    if (lastSyncIndicator && this.lastSyncTime) {
      const formattedTime = new Date(this.lastSyncTime).toLocaleTimeString();
      lastSyncIndicator.textContent = `Last synced: ${formattedTime}`;
      lastSyncIndicator.classList.remove('d-none');
    } else if (lastSyncIndicator) {
      lastSyncIndicator.classList.add('d-none');
    }
  }
  
  /**
   * Handle online/offline status changes
   */
  handleOnlineStatusChange(isOnline) {
    this.isOnline = isOnline;
    console.log(`App is now ${isOnline ? 'online' : 'offline'}`);
    
    // Update UI
    this.updateOfflineStatusUI();
    
    // Try to sync if we just came online
    if (isOnline) {
      this.syncChanges();
    }
    
    // Dispatch custom event
    const event = new CustomEvent('connectivityChange', { detail: { isOnline } });
    window.dispatchEvent(event);
  }
  
  /**
   * Check for pending changes in the database
   */
  async checkPendingChanges() {
    if (!this.db) {
      return 0;
    }
    
    try {
      const tx = this.db.transaction(this.userActionsStore, 'readonly');
      const store = tx.objectStore(this.userActionsStore);
      const index = store.index('synced');
      
      const request = index.count(false);
      
      return new Promise((resolve, reject) => {
        request.onsuccess = () => {
          this.pendingChanges = request.result;
          this.updateOfflineStatusUI();
          resolve(this.pendingChanges);
        };
        
        request.onerror = event => {
          console.error('Error counting pending changes:', event.target.error);
          reject(event.target.error);
        };
      });
    } catch (error) {
      console.error('Error checking pending changes:', error);
      return 0;
    }
  }
  
  /**
   * Record a user action for later synchronization
   */
  async recordAction(type, data) {
    if (!this.db) {
      console.error('Database not initialized');
      return false;
    }
    
    try {
      const tx = this.db.transaction(this.userActionsStore, 'readwrite');
      const store = tx.objectStore(this.userActionsStore);
      
      const action = {
        type,
        data,
        timestamp: Date.now(),
        synced: this.isOnline, // If online, mark as synced
        retryCount: 0
      };
      
      const request = store.add(action);
      
      return new Promise((resolve, reject) => {
        request.onsuccess = () => {
          console.log('Recorded action:', type);
          
          // If online, try to sync immediately
          if (this.isOnline) {
            // Sync is handled by the service worker
            navigator.serviceWorker.ready.then(registration => {
              registration.sync.register('sync-all');
            }).catch(error => {
              console.error('Error registering sync:', error);
            });
          } else {
            // Update pending changes count
            this.pendingChanges++;
            this.updateOfflineStatusUI();
          }
          
          resolve(true);
        };
        
        request.onerror = event => {
          console.error('Error recording action:', event.target.error);
          reject(event.target.error);
        };
      });
    } catch (error) {
      console.error('Error recording action:', error);
      return false;
    }
  }
  
  /**
   * Synchronize all pending changes with the server
   */
  async syncChanges() {
    if (!this.isOnline || this.syncInProgress) {
      return false;
    }
    
    this.syncInProgress = true;
    console.log('Starting sync...');
    
    try {
      // Use Background Sync API if available
      if ('serviceWorker' in navigator && 'SyncManager' in window) {
        await navigator.serviceWorker.ready;
        await navigator.serviceWorker.ready.then(registration => {
          return registration.sync.register('sync-all');
        });
        
        // Update pending changes count after sync
        setTimeout(() => {
          this.checkPendingChanges();
          this.lastSyncTime = Date.now();
          this.updateOfflineStatusUI();
          this.syncInProgress = false;
        }, 1000);
        
        return true;
      } else {
        // Fall back to manual sync if Background Sync is not supported
        const result = await this.manualSync();
        this.lastSyncTime = Date.now();
        this.updateOfflineStatusUI();
        this.syncInProgress = false;
        return result;
      }
    } catch (error) {
      console.error('Error syncing changes:', error);
      this.syncInProgress = false;
      return false;
    }
  }
  
  /**
   * Manually sync pending changes with the server
   */
  async manualSync() {
    if (!this.db || !this.isOnline) {
      return false;
    }
    
    try {
      const tx = this.db.transaction(this.userActionsStore, 'readwrite');
      const store = tx.objectStore(this.userActionsStore);
      const index = store.index('synced');
      
      const unsyncedActions = await new Promise((resolve, reject) => {
        const request = index.getAll(false);
        
        request.onsuccess = () => {
          resolve(request.result);
        };
        
        request.onerror = event => {
          reject(event.target.error);
        };
      });
      
      // No unsynced actions
      if (unsyncedActions.length === 0) {
        console.log('No pending changes to sync');
        return true;
      }
      
      console.log(`Syncing ${unsyncedActions.length} actions...`);
      
      // Process each action
      const results = await Promise.all(
        unsyncedActions.map(async action => {
          try {
            // Send action to server
            const response = await fetch(`/api/${action.type}`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify(action.data)
            });
            
            if (response.ok) {
              // Mark as synced
              action.synced = true;
              await new Promise((resolve, reject) => {
                const updateRequest = store.put(action);
                updateRequest.onsuccess = () => resolve();
                updateRequest.onerror = event => reject(event.target.error);
              });
              
              console.log(`Synced action: ${action.type}`);
              return true;
            } else {
              console.error(`Error syncing action: ${action.type}`, response.status);
              // Increment retry count
              action.retryCount = (action.retryCount || 0) + 1;
              await new Promise((resolve, reject) => {
                const updateRequest = store.put(action);
                updateRequest.onsuccess = () => resolve();
                updateRequest.onerror = event => reject(event.target.error);
              });
              
              return false;
            }
          } catch (error) {
            console.error(`Error syncing action: ${action.type}`, error);
            // Increment retry count
            action.retryCount = (action.retryCount || 0) + 1;
            await new Promise((resolve, reject) => {
              const updateRequest = store.put(action);
              updateRequest.onsuccess = () => resolve();
              updateRequest.onerror = event => reject(event.target.error);
            });
            
            return false;
          }
        })
      );
      
      // Update pending changes count
      await this.checkPendingChanges();
      
      // Return true if all actions were synced
      const successCount = results.filter(Boolean).length;
      console.log(`Synced ${successCount} out of ${results.length} actions`);
      
      return successCount === results.length;
    } catch (error) {
      console.error('Error during manual sync:', error);
      return false;
    }
  }
  
  /**
   * Get exercise progress data (cached or from server)
   */
  async getExerciseProgress() {
    try {
      // Try to get from server first if online
      if (this.isOnline) {
        try {
          const response = await fetch('/api/exercises/progress');
          if (response.ok) {
            const data = await response.json();
            
            // Cache the data
            await this.cacheData('exerciseProgress', data);
            
            return data;
          }
        } catch (error) {
          console.error('Error fetching exercise progress from server:', error);
        }
      }
      
      // Fall back to cached data
      return await this.getCachedData('exerciseProgress');
    } catch (error) {
      console.error('Error getting exercise progress:', error);
      return null;
    }
  }
  
  /**
   * Update exercise progress (synced when online)
   */
  async updateExerciseProgress(exerciseId, progress) {
    // Record the action
    await this.recordAction('exercises/progress', {
      exerciseId,
      progress
    });
    
    // Update local cache
    const cachedProgress = await this.getCachedData('exerciseProgress') || {};
    cachedProgress[exerciseId] = progress;
    await this.cacheData('exerciseProgress', cachedProgress);
    
    return true;
  }
  
  /**
   * Cache data in IndexedDB
   */
  async cacheData(key, data) {
    if (!this.db) {
      return false;
    }
    
    try {
      const tx = this.db.transaction('cachedData', 'readwrite');
      const store = tx.objectStore('cachedData');
      
      await new Promise((resolve, reject) => {
        const request = store.put({
          key,
          data,
          timestamp: Date.now()
        });
        
        request.onsuccess = () => resolve();
        request.onerror = event => reject(event.target.error);
      });
      
      return true;
    } catch (error) {
      console.error('Error caching data:', error);
      return false;
    }
  }
  
  /**
   * Get cached data from IndexedDB
   */
  async getCachedData(key) {
    if (!this.db) {
      return null;
    }
    
    try {
      const tx = this.db.transaction('cachedData', 'readonly');
      const store = tx.objectStore('cachedData');
      
      const result = await new Promise((resolve, reject) => {
        const request = store.get(key);
        
        request.onsuccess = () => {
          if (request.result) {
            resolve(request.result.data);
          } else {
            resolve(null);
          }
        };
        
        request.onerror = event => reject(event.target.error);
      });
      
      return result;
    } catch (error) {
      console.error('Error getting cached data:', error);
      return null;
    }
  }
}

// Initialize the offline sync manager
const offlineSyncManager = new OfflineSyncManager();

// Expose for global access
window.offlineSyncManager = offlineSyncManager;