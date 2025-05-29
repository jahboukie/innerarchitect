#!/usr/bin/env python
"""
Asset Optimizer for Inner Architect

This module provides tools for optimizing and managing static assets including:
- CSS and JS minification
- File bundling
- Content hashing for cache busting
- Critical CSS extraction
- Image optimization
"""

import os
import re
import json
import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

# Default directories
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
DIST_DIR = os.path.join(STATIC_DIR, 'dist')
SOURCE_MAPS_DIR = os.path.join(DIST_DIR, 'maps')
MANIFEST_FILE = os.path.join(DIST_DIR, 'asset-manifest.json')

# File types for processing
CSS_EXTENSIONS = {'.css'}
JS_EXTENSIONS = {'.js'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp'}

class AssetOptimizer:
    """Asset optimization and management for static files."""
    
    def __init__(
        self, 
        static_dir: str = STATIC_DIR,
        dist_dir: str = DIST_DIR,
        create_source_maps: bool = True,
        manifest_file: str = MANIFEST_FILE
    ):
        """
        Initialize the asset optimizer.
        
        Args:
            static_dir: Directory containing static assets
            dist_dir: Directory for optimized output
            create_source_maps: Whether to generate source maps
            manifest_file: Path to the asset manifest file
        """
        self.static_dir = static_dir
        self.dist_dir = dist_dir
        self.create_source_maps = create_source_maps
        self.manifest_file = manifest_file
        self.manifest = {}
        
        # Create output directories if they don't exist
        os.makedirs(self.dist_dir, exist_ok=True)
        if self.create_source_maps:
            os.makedirs(SOURCE_MAPS_DIR, exist_ok=True)
            
        # Load existing manifest if it exists
        if os.path.exists(self.manifest_file):
            try:
                with open(self.manifest_file, 'r') as f:
                    self.manifest = json.load(f)
            except json.JSONDecodeError:
                self.manifest = {}
    
    def optimize_all(self) -> Dict[str, str]:
        """
        Optimize all static assets and return the manifest.
        
        Returns:
            Dict mapping original filenames to optimized filenames
        """
        # Process CSS files
        css_files = self._find_files(self.static_dir, CSS_EXTENSIONS)
        for css_file in css_files:
            self._process_css(css_file)
        
        # Process JS files
        js_files = self._find_files(self.static_dir, JS_EXTENSIONS)
        for js_file in js_files:
            self._process_js(js_file)
        
        # Process images
        image_files = self._find_files(self.static_dir, IMAGE_EXTENSIONS)
        for image_file in image_files:
            self._process_image(image_file)
        
        # Write the manifest file
        self._write_manifest()
        
        return self.manifest
    
    def get_asset_url(self, original_path: str) -> str:
        """
        Get the optimized URL for an asset.
        
        Args:
            original_path: Original path to the asset
            
        Returns:
            Path to the optimized asset
        """
        # Normalize the path to match manifest keys
        norm_path = os.path.normpath(original_path).replace('\\', '/')
        if norm_path.startswith('/'):
            norm_path = norm_path[1:]
            
        # Check if path is in manifest
        if norm_path in self.manifest:
            return self.manifest[norm_path]
        
        # Try with '/static/' prefix removed
        if norm_path.startswith('static/'):
            norm_path = norm_path[7:]
            if norm_path in self.manifest:
                return self.manifest[norm_path]
        
        # Return original path if not found
        return original_path
    
    def extract_critical_css(self, html_file: str, output_file: str) -> str:
        """
        Extract critical CSS for a specific HTML file.
        
        Args:
            html_file: Path to HTML file
            output_file: Path to output CSS file
            
        Returns:
            Path to the critical CSS file
        """
        try:
            # Check if critical-css-cli is installed
            subprocess.run(['npx', '--version'], check=True, capture_output=True)
            
            # Run critical-css-cli to extract critical CSS
            subprocess.run([
                'npx', 'critical', 
                '--base', self.static_dir,
                '--inline', 'false',
                '--extract', 'true',
                '--target', output_file,
                html_file
            ], check=True)
            
            # Add to manifest
            rel_path = os.path.relpath(output_file, self.static_dir)
            hashed_file = self._add_content_hash(output_file)
            self.manifest[rel_path] = os.path.basename(hashed_file)
            
            return hashed_file
        except subprocess.CalledProcessError:
            print("Error: Critical CSS extraction failed. Make sure 'critical' is installed.")
            return ""
    
    def _find_files(self, directory: str, extensions: Set[str]) -> List[str]:
        """
        Find files with specific extensions in a directory.
        
        Args:
            directory: Directory to search
            extensions: Set of file extensions to include
            
        Returns:
            List of file paths
        """
        results = []
        for root, _, files in os.walk(directory):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in extensions:
                    results.append(os.path.join(root, file))
        return results
    
    def _process_css(self, css_file: str) -> str:
        """
        Process a CSS file - minify and add content hash.
        
        Args:
            css_file: Path to the CSS file
            
        Returns:
            Path to the processed file
        """
        try:
            # Read the original file
            with open(css_file, 'r', encoding='utf-8') as f:
                css_content = f.read()
            
            # Basic CSS minification
            minified = self._minify_css(css_content)
            
            # Create a temporary minified file
            temp_file = os.path.join(self.dist_dir, os.path.basename(css_file))
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(minified)
            
            # Add content hash to filename
            hashed_file = self._add_content_hash(temp_file)
            
            # Add to manifest
            rel_path = os.path.relpath(css_file, self.static_dir)
            self.manifest[rel_path] = os.path.basename(hashed_file)
            
            # Remove temporary file if it's different from the hashed file
            if temp_file != hashed_file and os.path.exists(temp_file):
                os.remove(temp_file)
            
            return hashed_file
        except Exception as e:
            print(f"Error processing CSS file {css_file}: {str(e)}")
            return css_file
    
    def _process_js(self, js_file: str) -> str:
        """
        Process a JavaScript file - minify and add content hash.
        
        Args:
            js_file: Path to the JS file
            
        Returns:
            Path to the processed file
        """
        try:
            # Read the original file
            with open(js_file, 'r', encoding='utf-8') as f:
                js_content = f.read()
            
            # Basic JS minification
            minified = self._minify_js(js_content)
            
            # Create a temporary minified file
            temp_file = os.path.join(self.dist_dir, os.path.basename(js_file))
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(minified)
            
            # Add content hash to filename
            hashed_file = self._add_content_hash(temp_file)
            
            # Add to manifest
            rel_path = os.path.relpath(js_file, self.static_dir)
            self.manifest[rel_path] = os.path.basename(hashed_file)
            
            # Remove temporary file if it's different from the hashed file
            if temp_file != hashed_file and os.path.exists(temp_file):
                os.remove(temp_file)
            
            return hashed_file
        except Exception as e:
            print(f"Error processing JS file {js_file}: {str(e)}")
            return js_file
    
    def _process_image(self, image_file: str) -> str:
        """
        Process an image file - optimize and add content hash.
        
        Args:
            image_file: Path to the image file
            
        Returns:
            Path to the processed file
        """
        # Only add content hash for now, optimization requires additional libraries
        dest_file = os.path.join(self.dist_dir, os.path.basename(image_file))
        shutil.copy2(image_file, dest_file)
        
        # Add content hash to filename
        hashed_file = self._add_content_hash(dest_file)
        
        # Add to manifest
        rel_path = os.path.relpath(image_file, self.static_dir)
        self.manifest[rel_path] = os.path.basename(hashed_file)
        
        # Remove temporary file if it's different from the hashed file
        if dest_file != hashed_file and os.path.exists(dest_file):
            os.remove(dest_file)
        
        return hashed_file
    
    def _add_content_hash(self, file_path: str) -> str:
        """
        Add content hash to a filename for cache busting.
        
        Args:
            file_path: Path to the file
            
        Returns:
            New file path with content hash
        """
        # Calculate file hash
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()[:8]
        
        # Create new filename with hash
        filename, ext = os.path.splitext(file_path)
        hashed_filename = f"{filename}.{file_hash}{ext}"
        
        # Rename the file
        os.rename(file_path, hashed_filename)
        
        return hashed_filename
    
    def _minify_css(self, css_content: str) -> str:
        """
        Minify CSS content using basic regex-based minification.
        
        Args:
            css_content: CSS content to minify
            
        Returns:
            Minified CSS content
        """
        # Remove comments
        css_content = re.sub(r'/\*[\s\S]*?\*/', '', css_content)
        
        # Remove whitespace
        css_content = re.sub(r'\s+', ' ', css_content)
        css_content = re.sub(r'\s*{\s*', '{', css_content)
        css_content = re.sub(r'\s*}\s*', '}', css_content)
        css_content = re.sub(r'\s*;\s*', ';', css_content)
        css_content = re.sub(r'\s*:\s*', ':', css_content)
        css_content = re.sub(r'\s*,\s*', ',', css_content)
        
        # Remove last semicolons
        css_content = re.sub(r';}', '}', css_content)
        
        return css_content.strip()
    
    def _minify_js(self, js_content: str) -> str:
        """
        Minify JavaScript content using basic regex-based minification.
        
        Args:
            js_content: JavaScript content to minify
            
        Returns:
            Minified JavaScript content
        """
        # Remove comments (simple cases only)
        js_content = re.sub(r'//.*?\n', '\n', js_content)
        js_content = re.sub(r'/\*[\s\S]*?\*/', '', js_content)
        
        # Remove whitespace (simple cases only)
        js_content = re.sub(r'\s+', ' ', js_content)
        js_content = re.sub(r';\s*', ';', js_content)
        js_content = re.sub(r'{\s*', '{', js_content)
        js_content = re.sub(r'}\s*', '}', js_content)
        js_content = re.sub(r',\s*', ',', js_content)
        js_content = re.sub(r':\s*', ':', js_content)
        js_content = re.sub(r'=\s*', '=', js_content)
        
        return js_content.strip()
    
    def _write_manifest(self) -> None:
        """Write the asset manifest to disk."""
        with open(self.manifest_file, 'w') as f:
            json.dump(self.manifest, f, indent=2)


def register_asset_helper(app) -> None:
    """
    Register asset helper functions with the Flask app.
    
    Args:
        app: Flask application instance
    """
    # Create asset optimizer
    optimizer = AssetOptimizer()
    
    @app.template_filter('asset_url')
    def asset_url_filter(path: str) -> str:
        """
        Template filter to convert asset paths to hashed versions.
        
        Args:
            path: Original asset path
            
        Returns:
            URL to the hashed asset
        """
        return optimizer.get_asset_url(path)
    
    # Add context processor for asset URLs
    @app.context_processor
    def asset_processor() -> Dict:
        """
        Add asset_url function to the template context.
        
        Returns:
            Dictionary with asset_url function
        """
        return {'asset_url': optimizer.get_asset_url}


if __name__ == "__main__":
    # When run directly, optimize all assets
    print("Optimizing static assets...")
    optimizer = AssetOptimizer()
    manifest = optimizer.optimize_all()
    print(f"Optimization complete. {len(manifest)} assets processed.")
    print(f"Asset manifest written to {MANIFEST_FILE}")