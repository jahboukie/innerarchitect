/**
 * Image Optimizer for Inner Architect
 *
 * This module implements modern image optimization techniques:
 * - Lazy loading
 * - Responsive images
 * - Blur-up loading
 * - Image format detection
 * - WebP/AVIF support detection
 */

// Detect browser support for modern image formats
const supportedFormats = {
    webp: false,
    avif: false
};

// Check WebP support
(function checkWebP() {
    const img = new Image();
    img.onload = function() {
        supportedFormats.webp = (img.width > 0) && (img.height > 0);
    };
    img.onerror = function() {
        supportedFormats.webp = false;
    };
    img.src = 'data:image/webp;base64,UklGRhoAAABXRUJQVlA4TA0AAAAvAAAAEAcQERGIiP4HAA==';
})();

// Check AVIF support
(function checkAVIF() {
    const img = new Image();
    img.onload = function() {
        supportedFormats.avif = (img.width > 0) && (img.height > 0);
    };
    img.onerror = function() {
        supportedFormats.avif = false;
    };
    img.src = 'data:image/avif;base64,AAAAIGZ0eXBhdmlmAAAAAGF2aWZtaWYxbWlhZk1BMUIAAADybWV0YQAAAAAAAAAoaGRscgAAAAAAAAAAcGljdAAAAAAAAAAAAAAAAGxpYmF2aWYAAAAADnBpdG0AAAAAAAEAAAAeaWxvYwAAAABEAAABAAEAAAABAAABGgAAAB0AAAAoaWluZgAAAAAAAQAAABppbmZlAgAAAAABAABhdjAxQ29sb3IAAAAAamlwcnAAAABLaXBjbwAAABRpc3BlAAAAAAAAAAIAAAACAAAAEHBpeGkAAAAAAwgICAAAAAxhdjFDgQ0MAAAAABNjb2xybmNseAACAAIAAYAAAAAXaXBtYQAAAAAAAAABAAEEAQKDBAAAACVtZGF0EgAKCBgANogQEAwgMg8f8D///8WfhwB8+ErK42A=';
})();

/**
 * Optimize image elements with lazy loading and format detection
 * 
 * @param {string} selector - CSS selector for images to optimize
 * @param {Object} options - Options for image optimization
 * @param {boolean} options.lazyLoad - Whether to use lazy loading
 * @param {boolean} options.responsive - Whether to use responsive images
 * @param {boolean} options.blurUp - Whether to use blur-up loading
 * @param {boolean} options.useWebP - Whether to use WebP format when supported
 * @param {boolean} options.useAVIF - Whether to use AVIF format when supported
 */
function optimizeImages(selector = 'img', options = {}) {
    // Default options
    const settings = Object.assign({
        lazyLoad: true,
        responsive: true,
        blurUp: true,
        useWebP: true,
        useAVIF: true
    }, options);
    
    // Get all target images
    const images = document.querySelectorAll(selector);
    
    // Exit if no images found
    if (images.length === 0) {
        return;
    }
    
    console.log(`[Image Optimizer] Optimizing ${images.length} images`);
    console.log(`[Image Optimizer] Format support: WebP=${supportedFormats.webp}, AVIF=${supportedFormats.avif}`);
    
    // Process each image
    images.forEach(img => {
        // Skip images that are already processed
        if (img.dataset.optimized === 'true') {
            return;
        }
        
        // Get image source
        const originalSrc = img.dataset.src || img.src;
        if (!originalSrc) {
            return;
        }
        
        // Get image dimensions
        const width = img.dataset.width || img.width || 0;
        const height = img.dataset.height || img.height || 0;
        
        // Apply lazy loading if enabled
        if (settings.lazyLoad) {
            // Set native lazy loading attribute
            img.loading = 'lazy';
            
            // Set data-src for custom lazy loading
            if (!img.dataset.src) {
                img.dataset.src = originalSrc;
                
                // Clear src for non-native lazy loading (if using IntersectionObserver)
                if ('IntersectionObserver' in window) {
                    img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + width + ' ' + height + '"%3E%3C/svg%3E';
                }
            }
        }
        
        // Apply responsive image loading if enabled
        if (settings.responsive && width && height) {
            // Set sizes attribute if not present
            if (!img.sizes) {
                img.sizes = '(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw';
            }
            
            // Create srcset with different sizes
            if (!img.srcset) {
                // Parse original URL to prepare for responsive variants
                const fileUrl = new URL(originalSrc, window.location.href);
                const filePath = fileUrl.pathname;
                const fileExt = filePath.split('.').pop();
                const basePath = filePath.substring(0, filePath.lastIndexOf('.'));
                
                // Create srcset with different sizes
                const widths = [320, 640, 960, 1280, 1920];
                const srcsetItems = [];
                
                // Filter widths based on image size
                const targetWidths = widths.filter(w => w <= width * 2 || width === 0);
                
                // Generate srcset items
                targetWidths.forEach(w => {
                    // Try to use responsive image naming convention if files exist
                    // Format: image-320w.jpg, image-640w.jpg, etc.
                    const sizeVariant = `${basePath}-${w}w.${fileExt}`;
                    srcsetItems.push(`${fileUrl.origin}${sizeVariant} ${w}w`);
                });
                
                // Set srcset if we have items
                if (srcsetItems.length > 0) {
                    img.srcset = srcsetItems.join(', ');
                }
            }
        }
        
        // Apply modern format options if enabled
        if ((settings.useWebP && supportedFormats.webp) || 
            (settings.useAVIF && supportedFormats.avif)) {
            
            // Parse original URL
            const fileUrl = new URL(originalSrc, window.location.href);
            const filePath = fileUrl.pathname;
            const fileExt = filePath.split('.').pop().toLowerCase();
            
            // Only convert compatible formats (jpg, jpeg, png)
            if (['jpg', 'jpeg', 'png'].includes(fileExt)) {
                const basePath = filePath.substring(0, filePath.lastIndexOf('.'));
                
                // Create picture element for format selection
                if (!img.parentElement.matches('picture')) {
                    // Create picture element
                    const picture = document.createElement('picture');
                    
                    // Insert picture element before img
                    img.parentNode.insertBefore(picture, img);
                    
                    // Move img inside picture
                    picture.appendChild(img);
                    
                    // Add source elements for modern formats
                    if (settings.useAVIF && supportedFormats.avif) {
                        const avifSource = document.createElement('source');
                        avifSource.srcset = `${fileUrl.origin}${basePath}.avif`;
                        avifSource.type = 'image/avif';
                        picture.insertBefore(avifSource, img);
                    }
                    
                    if (settings.useWebP && supportedFormats.webp) {
                        const webpSource = document.createElement('source');
                        webpSource.srcset = `${fileUrl.origin}${basePath}.webp`;
                        webpSource.type = 'image/webp';
                        picture.insertBefore(webpSource, img);
                    }
                }
            }
        }
        
        // Apply blur-up loading if enabled
        if (settings.blurUp && !img.dataset.blurupApplied) {
            // Add tiny thumbnail version for blur-up effect
            if (img.dataset.blurupSrc) {
                const blurupImg = new Image();
                blurupImg.src = img.dataset.blurupSrc;
                
                blurupImg.onload = function() {
                    // Create canvas for blur effect
                    const canvas = document.createElement('canvas');
                    const ctx = canvas.getContext('2d');
                    
                    // Set canvas size (small for performance)
                    canvas.width = 40;
                    canvas.height = Math.round(40 * (blurupImg.height / blurupImg.width));
                    
                    // Draw image to canvas
                    ctx.drawImage(blurupImg, 0, 0, canvas.width, canvas.height);
                    
                    // Apply blur effect
                    ctx.filter = 'blur(8px)';
                    ctx.drawImage(canvas, 0, 0, canvas.width, canvas.height);
                    
                    // Create blurred data URL
                    const blurredDataUrl = canvas.toDataURL('image/jpeg', 0.5);
                    
                    // Create wrapper and apply background
                    const wrapper = document.createElement('div');
                    wrapper.style.position = 'relative';
                    wrapper.style.overflow = 'hidden';
                    wrapper.style.background = `url(${blurredDataUrl}) no-repeat center center/cover`;
                    
                    // Replace image with wrapper
                    img.parentNode.insertBefore(wrapper, img);
                    wrapper.appendChild(img);
                    
                    // Style the image
                    img.style.position = 'relative';
                    img.style.opacity = '0';
                    img.style.transition = 'opacity 0.5s ease-in-out';
                    
                    // Set flag to prevent duplicate application
                    img.dataset.blurupApplied = 'true';
                    
                    // When actual image loads, fade it in
                    img.onload = function() {
                        img.style.opacity = '1';
                    };
                };
            }
        }
        
        // Set flag to prevent duplicate processing
        img.dataset.optimized = 'true';
    });
    
    // Set up IntersectionObserver for custom lazy loading if supported
    if (settings.lazyLoad && 'IntersectionObserver' in window) {
        const lazyImageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    
                    // Load the actual image
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                    }
                    
                    // Load the actual srcset
                    if (img.dataset.srcset) {
                        img.srcset = img.dataset.srcset;
                    }
                    
                    // Stop observing this image
                    observer.unobserve(img);
                }
            });
        });
        
        // Start observing images with data-src
        document.querySelectorAll('img[data-src]').forEach(img => {
            lazyImageObserver.observe(img);
        });
    }
}

/**
 * Preload critical images for faster rendering
 * 
 * @param {string[]} imagePaths - Array of image paths to preload
 */
function preloadCriticalImages(imagePaths) {
    if (!imagePaths || !imagePaths.length) {
        return;
    }
    
    console.log(`[Image Optimizer] Preloading ${imagePaths.length} critical images`);
    
    // Create link elements for preloading
    imagePaths.forEach(path => {
        const link = document.createElement('link');
        link.rel = 'preload';
        link.as = 'image';
        link.href = path;
        
        // Add format hint for WebP if supported
        if (path.endsWith('.webp') && supportedFormats.webp) {
            link.type = 'image/webp';
        }
        
        // Add format hint for AVIF if supported
        if (path.endsWith('.avif') && supportedFormats.avif) {
            link.type = 'image/avif';
        }
        
        document.head.appendChild(link);
    });
}

/**
 * Generate a low-quality placeholder for an image
 * 
 * @param {string} imageSrc - Source of the original image
 * @param {number} size - Size of the placeholder in pixels
 * @returns {Promise<string>} - Data URL of the placeholder
 */
function generatePlaceholder(imageSrc, size = 20) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        
        img.onload = function() {
            try {
                // Create canvas for the placeholder
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                
                // Calculate aspect ratio
                const aspectRatio = img.width / img.height;
                
                // Set canvas size
                canvas.width = size;
                canvas.height = Math.round(size / aspectRatio);
                
                // Draw image to canvas at smaller size
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                
                // Create data URL
                const placeholderUrl = canvas.toDataURL('image/jpeg', 0.1);
                
                resolve(placeholderUrl);
            } catch (err) {
                reject(err);
            }
        };
        
        img.onerror = function() {
            reject(new Error('Failed to load image'));
        };
        
        img.crossOrigin = 'Anonymous';
        img.src = imageSrc;
    });
}

/**
 * Convert an image to WebP format if supported
 * 
 * @param {string} imageSrc - Source of the original image
 * @param {number} quality - Quality of the WebP image (0-1)
 * @returns {Promise<string>} - Data URL of the WebP image
 */
function convertToWebP(imageSrc, quality = 0.8) {
    return new Promise((resolve, reject) => {
        // Check if WebP is supported
        if (!supportedFormats.webp) {
            reject(new Error('WebP not supported'));
            return;
        }
        
        const img = new Image();
        
        img.onload = function() {
            try {
                // Create canvas
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                
                // Set canvas size
                canvas.width = img.width;
                canvas.height = img.height;
                
                // Draw image to canvas
                ctx.drawImage(img, 0, 0);
                
                // Convert to WebP
                const webpUrl = canvas.toDataURL('image/webp', quality);
                
                resolve(webpUrl);
            } catch (err) {
                reject(err);
            }
        };
        
        img.onerror = function() {
            reject(new Error('Failed to load image'));
        };
        
        img.crossOrigin = 'Anonymous';
        img.src = imageSrc;
    });
}

/**
 * Initialize image optimization
 */
function initImageOptimization() {
    // Run on DOMContentLoaded
    document.addEventListener('DOMContentLoaded', () => {
        // Get critical images from page data attribute if available
        const criticalImages = document.body.dataset.criticalImages;
        if (criticalImages) {
            try {
                const imagePaths = JSON.parse(criticalImages);
                preloadCriticalImages(imagePaths);
            } catch (e) {
                console.error('[Image Optimizer] Error parsing critical images:', e);
            }
        }
        
        // Optimize all images on page
        optimizeImages('img');
        
        // Optimize background images
        optimizeBackgroundImages();
        
        // Process dynamically added images
        observeDynamicImages();
    });
}

/**
 * Optimize elements with background images
 */
function optimizeBackgroundImages() {
    // Find elements with data-bg attribute
    const elements = document.querySelectorAll('[data-bg]');
    
    elements.forEach(el => {
        const bgUrl = el.dataset.bg;
        
        // Apply background with lazy loading
        if (bgUrl) {
            // Use IntersectionObserver for lazy loading if available
            if ('IntersectionObserver' in window) {
                const bgObserver = new IntersectionObserver((entries, observer) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            const element = entry.target;
                            
                            // Apply background image
                            element.style.backgroundImage = `url(${bgUrl})`;
                            
                            // Stop observing
                            observer.unobserve(element);
                        }
                    });
                });
                
                bgObserver.observe(el);
            } else {
                // Fallback for browsers without IntersectionObserver
                el.style.backgroundImage = `url(${bgUrl})`;
            }
        }
    });
}

/**
 * Observe DOM for dynamically added images
 */
function observeDynamicImages() {
    // Use MutationObserver to detect new images
    if ('MutationObserver' in window) {
        const observer = new MutationObserver(mutations => {
            let newImages = [];
            
            mutations.forEach(mutation => {
                // Check for new nodes
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach(node => {
                        // If node is an image
                        if (node.nodeName === 'IMG') {
                            newImages.push(node);
                        }
                        // If node has child images
                        else if (node.nodeType === 1) {
                            const childImages = node.querySelectorAll('img');
                            if (childImages.length > 0) {
                                newImages = [...newImages, ...childImages];
                            }
                        }
                    });
                }
            });
            
            // Optimize new images
            if (newImages.length > 0) {
                console.log(`[Image Optimizer] Optimizing ${newImages.length} new images`);
                optimizeImages(newImages);
            }
        });
        
        // Start observing
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
}

/**
 * Apply optimization to specific images
 * 
 * @param {NodeList|HTMLImageElement[]} images - Images to optimize
 * @param {Object} options - Optimization options
 */
function optimizeImages(images, options = {}) {
    // Handle both selector strings and NodeList/Array
    if (typeof images === 'string') {
        // It's a selector
        optimizeImages(document.querySelectorAll(images), options);
        return;
    }
    
    // Process each image
    images.forEach(img => {
        // Skip non-image elements
        if (!(img instanceof HTMLImageElement)) {
            return;
        }
        
        // Skip already optimized images
        if (img.dataset.optimized === 'true') {
            return;
        }
        
        // Default options
        const settings = Object.assign({
            lazyLoad: true,
            responsive: true,
            blurUp: true,
            useWebP: supportedFormats.webp,
            useAVIF: supportedFormats.avif
        }, options);
        
        // Apply lazy loading
        if (settings.lazyLoad) {
            img.loading = 'lazy';
            
            // Use data-src if available
            if (img.dataset.src && !img.src.startsWith('data:')) {
                img.dataset.originalSrc = img.src;
                img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + 
                    (img.width || 1) + ' ' + (img.height || 1) + '"%3E%3C/svg%3E';
            }
        }
        
        // Mark as optimized
        img.dataset.optimized = 'true';
    });
    
    // Set up lazy loading observer
    if ('IntersectionObserver' in window) {
        const lazyImageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    
                    // Load original image
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                    } else if (img.dataset.originalSrc) {
                        img.src = img.dataset.originalSrc;
                    }
                    
                    // Load srcset if available
                    if (img.dataset.srcset) {
                        img.srcset = img.dataset.srcset;
                    }
                    
                    // Stop observing
                    observer.unobserve(img);
                }
            });
        });
        
        // Observe all images
        images.forEach(img => {
            if (img instanceof HTMLImageElement) {
                lazyImageObserver.observe(img);
            }
        });
    }
}

// Export public API
window.ImageOptimizer = {
    optimizeImages,
    preloadCriticalImages,
    generatePlaceholder,
    convertToWebP,
    getSupportedFormats: () => ({ ...supportedFormats }),
    initImageOptimization
};

// Initialize when script is loaded
initImageOptimization();