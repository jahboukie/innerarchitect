"""
Content Delivery Optimization Module

This module provides tools for optimizing content delivery through CDN integration,
static asset optimization, and resource delivery strategies.
"""

import os
import re
import time
import hashlib
import gzip
import logging
from typing import Dict, List, Optional, Union, Set, Tuple, Any
from pathlib import Path
from functools import wraps
from urllib.parse import urlparse, urlunparse

from flask import Flask, request, Response, url_for

# Initialize logging
from logging_config import get_logger
logger = get_logger('performance.content_delivery')


class AssetProcessor:
    """
    Processes and optimizes static assets (CSS, JS, images) for production delivery.
    """
    
    def __init__(self, app_root: str, static_folder: str = 'static',
                output_folder: Optional[str] = None):
        """
        Initialize asset processor.
        
        Args:
            app_root: Application root directory
            static_folder: Static files folder name
            output_folder: Output folder for processed assets (defaults to static_folder/dist)
        """
        self.app_root = Path(app_root)
        self.static_folder = Path(static_folder)
        self.static_path = self.app_root / self.static_folder
        
        if output_folder:
            self.output_path = self.app_root / output_folder
        else:
            self.output_path = self.static_path / 'dist'
        
        # Ensure output directory exists
        self.output_path.mkdir(exist_ok=True, parents=True)
        
        # Track processed assets
        self.processed_assets: Dict[str, str] = {}  # original path -> processed path
        
        # File patterns for different types of assets
        self.js_pattern = re.compile(r'\.js$')
        self.css_pattern = re.compile(r'\.css$')
        self.image_pattern = re.compile(r'\.(jpg|jpeg|png|gif|svg|webp)$')
        
        # Map of file extensions to mime types
        self.mime_types = {
            '.js': 'application/javascript',
            '.css': 'text/css',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.webp': 'image/webp',
            '.woff': 'font/woff',
            '.woff2': 'font/woff2',
            '.ttf': 'font/ttf',
            '.eot': 'application/vnd.ms-fontobject',
            '.otf': 'font/otf',
            '.ico': 'image/x-icon',
        }
        
    def _get_file_hash(self, file_path: Path) -> str:
        """
        Calculate a hash of the file contents for cache busting.
        
        Args:
            file_path: Path to the file
            
        Returns:
            MD5 hash of the file contents
        """
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            buf = f.read(65536)  # Read in 64k chunks
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()[:8]  # Use first 8 chars of hash
    
    def _get_output_path(self, file_path: Path, file_hash: str) -> Path:
        """
        Get the output path for a processed asset with hash.
        
        Args:
            file_path: Original file path
            file_hash: File hash for cache busting
            
        Returns:
            Output path with hash in filename
        """
        # Get relative path from static folder
        rel_path = file_path.relative_to(self.static_path)
        
        # Insert hash before extension
        stem = rel_path.stem
        suffix = rel_path.suffix
        hashed_name = f"{stem}.{file_hash}{suffix}"
        
        # Create output path
        if rel_path.parent == Path('.'):
            # File is in root of static folder
            return self.output_path / hashed_name
        else:
            # File is in subdirectory
            return self.output_path / rel_path.parent / hashed_name
    
    def _minify_js(self, content: str) -> str:
        """
        Minify JavaScript content.
        
        Args:
            content: JavaScript content
            
        Returns:
            Minified JavaScript
        """
        try:
            # Try to use terser if available (better but requires Node.js)
            import subprocess
            
            # Write content to temporary file
            temp_file = self.output_path / "temp.js"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Run terser
            result = subprocess.run(
                ["npx", "terser", str(temp_file), "--compress", "--mangle"],
                capture_output=True,
                text=True
            )
            
            # Clean up temp file
            temp_file.unlink()
            
            if result.returncode == 0:
                return result.stdout
            else:
                logger.warning(f"Terser minification failed: {result.stderr}")
                # Fall back to simple minification
                return self._simple_minify_js(content)
                
        except (ImportError, FileNotFoundError):
            # Fall back to simple minification
            return self._simple_minify_js(content)
    
    def _simple_minify_js(self, content: str) -> str:
        """
        Simple JavaScript minification without external dependencies.
        
        Args:
            content: JavaScript content
            
        Returns:
            Minified JavaScript
        """
        # Remove comments
        content = re.sub(r'//.*?\n', '\n', content)  # Remove // comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)  # Remove /* */ comments
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r';\s+', ';', content)
        content = re.sub(r'{\s+', '{', content)
        content = re.sub(r'}\s+', '}', content)
        content = re.sub(r',\s+', ',', content)
        content = re.sub(r':\s+', ':', content)
        content = re.sub(r'=\s+', '=', content)
        content = re.sub(r'\s+=', '=', content)
        
        return content.strip()
    
    def _minify_css(self, content: str) -> str:
        """
        Minify CSS content.
        
        Args:
            content: CSS content
            
        Returns:
            Minified CSS
        """
        try:
            # Try to use csso if available
            import subprocess
            
            # Write content to temporary file
            temp_file = self.output_path / "temp.css"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Run csso
            result = subprocess.run(
                ["npx", "csso", str(temp_file), "--output", str(temp_file) + ".min"],
                capture_output=True,
                text=True
            )
            
            # Read minified file
            if result.returncode == 0 and os.path.exists(str(temp_file) + ".min"):
                with open(str(temp_file) + ".min", 'r', encoding='utf-8') as f:
                    minified = f.read()
                
                # Clean up temp files
                temp_file.unlink()
                Path(str(temp_file) + ".min").unlink()
                
                return minified
            else:
                logger.warning(f"CSSO minification failed: {result.stderr}")
                # Fall back to simple minification
                return self._simple_minify_css(content)
                
        except (ImportError, FileNotFoundError):
            # Fall back to simple minification
            return self._simple_minify_css(content)
    
    def _simple_minify_css(self, content: str) -> str:
        """
        Simple CSS minification without external dependencies.
        
        Args:
            content: CSS content
            
        Returns:
            Minified CSS
        """
        # Remove comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r';\s+', ';', content)
        content = re.sub(r'{\s+', '{', content)
        content = re.sub(r'}\s+', '}', content)
        content = re.sub(r',\s+', ',', content)
        content = re.sub(r':\s+', ':', content)
        
        return content.strip()
    
    def _optimize_image(self, file_path: Path) -> Optional[bytes]:
        """
        Optimize image file.
        
        Args:
            file_path: Path to image file
            
        Returns:
            Optimized image data or None if optimization failed
        """
        try:
            # Try to use imagemin if available
            import subprocess
            
            # Determine output path
            output_file = self.output_path / "temp_optimized" / file_path.name
            output_file.parent.mkdir(exist_ok=True, parents=True)
            
            # Run appropriate optimizer based on file type
            if file_path.suffix.lower() in ['.jpg', '.jpeg']:
                result = subprocess.run(
                    ["npx", "imagemin", str(file_path), "--plugin=mozjpeg", "-o", str(output_file.parent)],
                    capture_output=True
                )
            elif file_path.suffix.lower() == '.png':
                result = subprocess.run(
                    ["npx", "imagemin", str(file_path), "--plugin=pngquant", "-o", str(output_file.parent)],
                    capture_output=True
                )
            elif file_path.suffix.lower() == '.svg':
                result = subprocess.run(
                    ["npx", "svgo", str(file_path), "-o", str(output_file)],
                    capture_output=True
                )
            else:
                # For other image types, just copy
                result = subprocess.run(
                    ["cp", str(file_path), str(output_file)],
                    capture_output=True
                )
            
            # Read optimized file if successful
            if result.returncode == 0 and output_file.exists():
                with open(output_file, 'rb') as f:
                    optimized_data = f.read()
                
                # Clean up temp file
                output_file.unlink()
                return optimized_data
            else:
                logger.warning(f"Image optimization failed for {file_path}")
                return None
                
        except (ImportError, FileNotFoundError):
            logger.warning(f"Image optimization tools not available")
            return None
    
    def process_file(self, file_path: Union[str, Path]) -> Optional[str]:
        """
        Process a single file for production delivery.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            URL path to the processed file or None if processing failed
        """
        file_path = Path(file_path)
        
        # Check if file exists
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return None
        
        # Check if already processed
        str_path = str(file_path)
        if str_path in self.processed_assets:
            return self.processed_assets[str_path]
        
        # Get file hash for cache busting
        file_hash = self._get_file_hash(file_path)
        
        # Get output path
        output_path = self._get_output_path(file_path, file_hash)
        output_path.parent.mkdir(exist_ok=True, parents=True)
        
        # Process based on file type
        if self.js_pattern.search(str(file_path)):
            # Process JavaScript
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Minify
            minified = self._minify_js(content)
            
            # Write to output file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(minified)
            
            # Create gzipped version
            with open(str(output_path) + '.gz', 'wb') as f:
                f.write(gzip.compress(minified.encode('utf-8')))
            
        elif self.css_pattern.search(str(file_path)):
            # Process CSS
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Minify
            minified = self._minify_css(content)
            
            # Write to output file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(minified)
            
            # Create gzipped version
            with open(str(output_path) + '.gz', 'wb') as f:
                f.write(gzip.compress(minified.encode('utf-8')))
            
        elif self.image_pattern.search(str(file_path)):
            # Process image
            optimized = self._optimize_image(file_path)
            
            if optimized:
                # Write optimized image
                with open(output_path, 'wb') as f:
                    f.write(optimized)
            else:
                # Just copy the original
                with open(file_path, 'rb') as src, open(output_path, 'wb') as dst:
                    dst.write(src.read())
        
        else:
            # For other file types, just copy
            with open(file_path, 'rb') as src, open(output_path, 'wb') as dst:
                dst.write(src.read())
        
        # Get URL path for the processed file
        rel_output = output_path.relative_to(self.app_root)
        url_path = '/' + str(rel_output).replace('\\', '/')
        
        # Store in processed assets cache
        self.processed_assets[str_path] = url_path
        
        logger.info(f"Processed asset: {file_path} -> {url_path}")
        return url_path
    
    def process_directory(self, dir_path: Union[str, Path]) -> Dict[str, str]:
        """
        Process all files in a directory recursively.
        
        Args:
            dir_path: Directory to process
            
        Returns:
            Dictionary mapping original file paths to processed URL paths
        """
        dir_path = Path(dir_path)
        
        # Check if directory exists
        if not dir_path.exists() or not dir_path.is_dir():
            logger.warning(f"Directory not found: {dir_path}")
            return {}
        
        # Process all files recursively
        result = {}
        for root, _, files in os.walk(dir_path):
            root_path = Path(root)
            for file in files:
                file_path = root_path / file
                processed_path = self.process_file(file_path)
                if processed_path:
                    result[str(file_path)] = processed_path
        
        return result
    
    def get_processed_path(self, original_path: Union[str, Path]) -> Optional[str]:
        """
        Get the processed URL path for an original file path.
        
        Args:
            original_path: Original file path
            
        Returns:
            Processed URL path or None if not processed
        """
        str_path = str(original_path)
        return self.processed_assets.get(str_path)
    
    def get_manifest(self) -> Dict[str, str]:
        """
        Get a manifest of all processed assets.
        
        Returns:
            Dictionary mapping original file paths to processed URL paths
        """
        return dict(self.processed_assets)
    
    def save_manifest(self, output_path: Optional[Union[str, Path]] = None) -> bool:
        """
        Save the asset manifest to a JSON file.
        
        Args:
            output_path: Path to save the manifest (defaults to output_path/manifest.json)
            
        Returns:
            True if successful
        """
        import json
        
        if output_path is None:
            output_path = self.output_path / 'manifest.json'
        else:
            output_path = Path(output_path)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.processed_assets, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving manifest: {e}")
            return False
    
    def load_manifest(self, input_path: Optional[Union[str, Path]] = None) -> bool:
        """
        Load an asset manifest from a JSON file.
        
        Args:
            input_path: Path to load the manifest from (defaults to output_path/manifest.json)
            
        Returns:
            True if successful
        """
        import json
        
        if input_path is None:
            input_path = self.output_path / 'manifest.json'
        else:
            input_path = Path(input_path)
        
        try:
            if not input_path.exists():
                logger.warning(f"Manifest file not found: {input_path}")
                return False
            
            with open(input_path, 'r', encoding='utf-8') as f:
                self.processed_assets = json.load(f)
            return True
        except Exception as e:
            logger.error(f"Error loading manifest: {e}")
            return False


class CdnIntegration:
    """
    Integrates with Content Delivery Networks for optimized asset delivery.
    """
    
    def __init__(self, cdn_url: Optional[str] = None, enabled: bool = False):
        """
        Initialize CDN integration.
        
        Args:
            cdn_url: Base URL of the CDN
            enabled: Whether CDN integration is enabled
        """
        self.cdn_url = cdn_url
        self.enabled = enabled
        
        # File extensions to serve from CDN
        self.cdn_extensions = {
            '.js', '.css', '.jpg', '.jpeg', '.png', '.gif', '.svg',
            '.woff', '.woff2', '.ttf', '.eot', '.otf', '.ico', '.webp'
        }
    
    def get_cdn_url(self, path: str) -> str:
        """
        Convert a local path to a CDN URL if enabled.
        
        Args:
            path: Local URL path (e.g., /static/js/app.js)
            
        Returns:
            CDN URL or original path
        """
        if not self.enabled or not self.cdn_url:
            return path
        
        # Check if the path has a CDN extension
        _, ext = os.path.splitext(path)
        if ext.lower() not in self.cdn_extensions:
            return path
        
        # Skip URLs that are already absolute
        if path.startswith(('http://', 'https://', '//')):
            return path
        
        # Ensure the path starts with a slash
        if not path.startswith('/'):
            path = '/' + path
        
        # Combine with CDN URL
        cdn_base = self.cdn_url.rstrip('/')
        return f"{cdn_base}{path}"
    
    def should_use_cdn(self, path: str) -> bool:
        """
        Check if a path should be served from the CDN.
        
        Args:
            path: URL path
            
        Returns:
            True if the path should be served from CDN
        """
        if not self.enabled or not self.cdn_url:
            return False
        
        # Check if the path has a CDN extension
        _, ext = os.path.splitext(path)
        return ext.lower() in self.cdn_extensions


# Flask extension for content delivery optimization
class ContentDelivery:
    """
    Flask extension for content delivery optimization.
    """
    
    def __init__(self, app=None):
        """
        Initialize the extension.
        
        Args:
            app: Flask application (optional)
        """
        self.app = app
        self.asset_processor = None
        self.cdn = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """
        Initialize the extension with a Flask application.
        
        Args:
            app: Flask application
        """
        self.app = app
        
        # Get configuration
        app_root = app.root_path
        static_folder = app.static_folder
        
        # Check if in production mode
        debug = app.config.get('DEBUG', False)
        testing = app.config.get('TESTING', False)
        production = not (debug or testing)
        
        # Initialize asset processor if in production
        if production:
            output_folder = app.config.get('ASSETS_OUTPUT_FOLDER')
            self.asset_processor = AssetProcessor(app_root, static_folder, output_folder)
            
            # Load existing manifest if available
            manifest_path = app.config.get('ASSETS_MANIFEST_PATH')
            if manifest_path:
                self.asset_processor.load_manifest(manifest_path)
        
        # Initialize CDN integration
        cdn_url = app.config.get('CDN_URL')
        cdn_enabled = app.config.get('CDN_ENABLED', False)
        self.cdn = CdnIntegration(cdn_url, cdn_enabled)
        
        # Register Jinja2 extension for asset URLs
        app.jinja_env.globals['asset_url'] = self.asset_url
        
        # Register middleware for compression and cache headers
        if production:
            app.after_request(self._add_cache_headers)
            app.after_request(self._handle_compression)
    
    def process_assets(self):
        """Process static assets for production delivery."""
        if self.asset_processor:
            static_path = self.app.static_folder
            self.asset_processor.process_directory(static_path)
            self.asset_processor.save_manifest()
    
    def asset_url(self, path: str) -> str:
        """
        Get the URL for an asset, with optional CDN and cache busting.
        
        Args:
            path: Asset path relative to static folder
            
        Returns:
            URL for the asset
        """
        # Check if we're in production mode with asset processor
        if self.asset_processor:
            # Add static folder to path if not included
            if not path.startswith(self.app.static_folder):
                full_path = os.path.join(self.app.static_folder, path.lstrip('/'))
            else:
                full_path = path
            
            # Get processed path or process now
            processed_path = self.asset_processor.get_processed_path(full_path)
            if not processed_path:
                processed_path = self.asset_processor.process_file(full_path)
            
            # If processing succeeded, use the processed path
            if processed_path:
                # Check if we should use CDN
                if self.cdn and self.cdn.should_use_cdn(processed_path):
                    return self.cdn.get_cdn_url(processed_path)
                return processed_path
        
        # In development mode or if processing failed, use normal url_for
        static_url = url_for('static', filename=path.lstrip('/'))
        
        # Check if we should use CDN
        if self.cdn and self.cdn.should_use_cdn(static_url):
            return self.cdn.get_cdn_url(static_url)
        
        return static_url
    
    def _add_cache_headers(self, response):
        """
        Add appropriate cache headers to responses.
        
        Args:
            response: Flask response object
            
        Returns:
            Modified response
        """
        # Skip for error responses
        if response.status_code >= 400:
            return response
        
        # Skip for non-GET requests
        if request.method != 'GET':
            return response
        
        # Set Cache-Control header for static assets
        if request.path.startswith('/static/') or request.path.startswith('/dist/'):
            # Check if it's a file that should be cached long-term
            _, ext = os.path.splitext(request.path)
            long_cache_extensions = {
                '.js', '.css', '.jpg', '.jpeg', '.png', '.gif', '.svg',
                '.woff', '.woff2', '.ttf', '.eot', '.otf', '.ico', '.webp'
            }
            
            if ext.lower() in long_cache_extensions:
                # Long cache for static assets with cache busting
                if 'Cache-Control' not in response.headers:
                    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            else:
                # Shorter cache for other static files
                if 'Cache-Control' not in response.headers:
                    response.headers['Cache-Control'] = 'public, max-age=86400'
        else:
            # For other resources, use no-cache to allow revalidation
            if 'Cache-Control' not in response.headers:
                response.headers['Cache-Control'] = 'no-cache'
        
        return response
    
    def _handle_compression(self, response):
        """
        Handle response compression based on Accept-Encoding.
        
        Args:
            response: Flask response object
            
        Returns:
            Modified response
        """
        # Skip for error responses
        if response.status_code >= 400:
            return response
        
        # Skip if Content-Encoding is already set
        if 'Content-Encoding' in response.headers:
            return response
        
        # Skip for non-GET requests
        if request.method != 'GET':
            return response
        
        # Check Accept-Encoding header
        accept_encoding = request.headers.get('Accept-Encoding', '')
        
        # Check if response is compressible
        compressible_types = {
            'text/html', 'text/css', 'text/javascript', 'application/javascript',
            'application/json', 'text/plain', 'text/xml', 'application/xml'
        }
        
        content_type = response.headers.get('Content-Type', '')
        is_compressible = any(ct in content_type for ct in compressible_types)
        
        # Check if we should serve a pre-compressed file
        if is_compressible and 'gzip' in accept_encoding and self.asset_processor:
            path = request.path
            
            # Check if this is a processed asset with a .gz version
            if path.startswith('/dist/') and (path.endswith('.js') or path.endswith('.css')):
                gz_path = os.path.join(self.app.root_path, path.lstrip('/') + '.gz')
                
                if os.path.exists(gz_path):
                    # Serve the pre-compressed file
                    with open(gz_path, 'rb') as f:
                        data = f.read()
                    
                    response.data = data
                    response.headers['Content-Encoding'] = 'gzip'
                    response.headers['Content-Length'] = str(len(data))
                    return response
        
        # For other responses, let the web server handle compression
        return response


# Initialize for Flask app
def init_app(app):
    """
    Initialize content delivery optimization for a Flask app.
    
    Args:
        app: Flask application
        
    Returns:
        ContentDelivery instance
    """
    content_delivery = ContentDelivery(app)
    
    # Process assets if in production mode
    if not app.config.get('DEBUG', False) and not app.config.get('TESTING', False):
        with app.app_context():
            content_delivery.process_assets()
    
    return content_delivery