/**
 * Code Splitter for Inner Architect
 *
 * This module implements dynamic imports and code splitting to improve
 * frontend performance by loading code only when needed.
 */

// Module registry to avoid duplicate loads
const moduleRegistry = new Map();

// Promise cache for in-progress module loading
const loadingModules = new Map();

/**
 * Dynamically import a module and cache the result
 * 
 * @param {string} modulePath - Path to the module
 * @param {Object} options - Options for importing
 * @param {boolean} options.force - Force reload even if cached
 * @param {function} options.onProgress - Progress callback
 * @returns {Promise<any>} - The loaded module
 */
function loadModule(modulePath, options = {}) {
    const { force = false, onProgress = null } = options;
    
    // Return cached module if available and not forced reload
    if (!force && moduleRegistry.has(modulePath)) {
        return Promise.resolve(moduleRegistry.get(modulePath));
    }
    
    // Return in-progress loading promise if available
    if (loadingModules.has(modulePath)) {
        return loadingModules.get(modulePath);
    }
    
    // Start loading the module
    console.log(`[Code Splitter] Loading module: ${modulePath}`);
    
    // Create loading promise
    const loadingPromise = new Promise((resolve, reject) => {
        // Add script tag dynamically
        const script = document.createElement('script');
        script.type = 'text/javascript';
        script.src = modulePath;
        script.async = true;
        
        // Set up success handler
        script.onload = () => {
            console.log(`[Code Splitter] Module loaded: ${modulePath}`);
            
            // Get the module from global scope (module should register itself)
            const moduleObj = window[getModuleNameFromPath(modulePath)];
            
            if (!moduleObj) {
                const error = new Error(`Module ${modulePath} did not register properly`);
                loadingModules.delete(modulePath);
                reject(error);
                return;
            }
            
            // Cache the module
            moduleRegistry.set(modulePath, moduleObj);
            loadingModules.delete(modulePath);
            
            // Return the module
            resolve(moduleObj);
        };
        
        // Set up error handler
        script.onerror = (error) => {
            console.error(`[Code Splitter] Failed to load module: ${modulePath}`, error);
            loadingModules.delete(modulePath);
            reject(new Error(`Failed to load module: ${modulePath}`));
        };
        
        // Add script to document
        document.head.appendChild(script);
    });
    
    // Store the loading promise
    loadingModules.set(modulePath, loadingPromise);
    
    return loadingPromise;
}

/**
 * Extract module name from file path
 * 
 * @param {string} path - Module file path
 * @returns {string} - Module name
 */
function getModuleNameFromPath(path) {
    // Extract the filename without extension
    const filename = path.split('/').pop().split('.')[0];
    
    // Convert kebab-case to camelCase
    return filename.replace(/-([a-z])/g, (g) => g[1].toUpperCase());
}

/**
 * Load multiple modules in parallel
 * 
 * @param {string[]} modulePaths - Array of module paths
 * @param {Object} options - Options for importing
 * @returns {Promise<any[]>} - Array of loaded modules
 */
function loadModules(modulePaths, options = {}) {
    return Promise.all(modulePaths.map(path => loadModule(path, options)));
}

/**
 * Register a module for use with code splitting
 * 
 * @param {string} name - Module name
 * @param {Object} moduleObj - Module object
 */
function registerModule(name, moduleObj) {
    window[name] = moduleObj;
    console.log(`[Code Splitter] Registered module: ${name}`);
}

/**
 * Load a module for a specific feature only when needed
 * 
 * @param {string} featureName - Feature name
 * @param {function} initCallback - Callback to run after module is loaded
 */
function loadFeature(featureName, initCallback) {
    // Map feature names to module paths
    const featureModules = {
        'chat': '/static/js/features/chat-feature.js',
        'exercises': '/static/js/features/exercises-feature.js',
        'profile': '/static/js/features/profile-feature.js',
        'techniques': '/static/js/features/techniques-feature.js',
        'dashboard': '/static/js/features/dashboard-feature.js',
        'reminders': '/static/js/features/reminders-feature.js',
        'subscription': '/static/js/features/subscription-feature.js',
        'voice': '/static/js/features/voice-feature.js',
        'journeys': '/static/js/features/journeys-feature.js'
    };
    
    // Check if feature module is defined
    if (!featureModules[featureName]) {
        console.error(`[Code Splitter] Unknown feature: ${featureName}`);
        return Promise.reject(new Error(`Unknown feature: ${featureName}`));
    }
    
    // Load the feature module
    return loadModule(featureModules[featureName])
        .then(module => {
            if (typeof initCallback === 'function') {
                initCallback(module);
            }
            return module;
        });
}

/**
 * Lazy load components for a page
 * 
 * @param {string} pageId - ID of the current page
 */
function lazyLoadPageComponents(pageId) {
    // Map pages to component modules
    const pageComponents = {
        'chat-page': [
            '/static/js/components/chat-message.js',
            '/static/js/components/mood-selector.js',
            '/static/js/components/technique-selector.js'
        ],
        'dashboard-page': [
            '/static/js/components/progress-chart.js',
            '/static/js/components/usage-stats.js',
            '/static/js/components/technique-stats.js'
        ],
        'techniques-page': [
            '/static/js/components/technique-card.js',
            '/static/js/components/technique-details.js'
        ],
        'profile-page': [
            '/static/js/components/profile-form.js',
            '/static/js/components/subscription-details.js'
        ],
        'reminders-page': [
            '/static/js/components/reminder-form.js',
            '/static/js/components/reminder-list.js'
        ]
    };
    
    // Get components for the current page
    const components = pageComponents[pageId] || [];
    
    if (components.length === 0) {
        return Promise.resolve([]);
    }
    
    // Load all components
    return loadModules(components)
        .then(loadedModules => {
            console.log(`[Code Splitter] Loaded ${loadedModules.length} components for ${pageId}`);
            return loadedModules;
        });
}

/**
 * Preload modules that will likely be needed soon
 * 
 * @param {string[]} modulePaths - Array of module paths to preload
 */
function preloadModules(modulePaths) {
    // Use requestIdleCallback if available, otherwise setTimeout
    const schedulePreload = window.requestIdleCallback || 
        (cb => setTimeout(cb, 1000));
    
    schedulePreload(() => {
        console.log('[Code Splitter] Preloading modules in idle time');
        
        modulePaths.forEach(path => {
            const link = document.createElement('link');
            link.rel = 'preload';
            link.as = 'script';
            link.href = path;
            document.head.appendChild(link);
        });
    });
}

/**
 * Initialize lazy loading based on the current page
 */
function initLazyLoading() {
    // Detect current page
    const pageId = document.body.dataset.page;
    
    if (!pageId) {
        return;
    }
    
    // Load page-specific components
    lazyLoadPageComponents(pageId)
        .catch(error => {
            console.error('[Code Splitter] Error loading page components:', error);
        });
    
    // Handle dynamic feature loading
    document.querySelectorAll('[data-load-feature]').forEach(element => {
        const featureName = element.dataset.loadFeature;
        
        // Load feature when element becomes visible or on interaction
        const loadTrigger = element.dataset.loadTrigger || 'visible';
        
        if (loadTrigger === 'visible') {
            // Use Intersection Observer to load when visible
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        loadFeature(featureName, module => {
                            if (typeof module.init === 'function') {
                                module.init(element);
                            }
                        });
                        observer.disconnect();
                    }
                });
            });
            
            observer.observe(element);
        } else if (loadTrigger === 'click') {
            // Load on click
            element.addEventListener('click', (event) => {
                // Show loading indicator
                const originalContent = element.innerHTML;
                element.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
                element.disabled = true;
                
                loadFeature(featureName, module => {
                    // Restore button
                    element.innerHTML = originalContent;
                    element.disabled = false;
                    
                    if (typeof module.init === 'function') {
                        module.init(element);
                    }
                }).catch(error => {
                    console.error(`[Code Splitter] Error loading feature ${featureName}:`, error);
                    element.innerHTML = originalContent;
                    element.disabled = false;
                });
            });
        }
    });
}

// Export public API
window.CodeSplitter = {
    loadModule,
    loadModules,
    registerModule,
    loadFeature,
    lazyLoadPageComponents,
    preloadModules,
    initLazyLoading
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initLazyLoading();
});