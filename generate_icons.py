#!/usr/bin/env python3
"""
Generate PNG icons from SVG for PWA
"""
import os
import cairosvg
import sys

# List of icon sizes needed for PWA
ICON_SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

def generate_icons(svg_path, output_dir):
    """Generate PNG icons of various sizes from an SVG file"""
    print(f"Generating icons from {svg_path}...")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")
    
    for size in ICON_SIZES:
        output_path = os.path.join(output_dir, f"icon-{size}x{size}.png")
        try:
            cairosvg.svg2png(url=svg_path, write_to=output_path, output_width=size, output_height=size)
            print(f"Generated {output_path}")
        except Exception as e:
            print(f"Error generating {output_path}: {e}")
    
    # Create a maskable icon (centered with padding)
    try:
        output_path = os.path.join(output_dir, "maskable-icon.png")
        cairosvg.svg2png(url=svg_path, write_to=output_path, output_width=192, output_height=192)
        print(f"Generated {output_path}")
    except Exception as e:
        print(f"Error generating maskable icon: {e}")
    
    print("Icon generation complete!")

if __name__ == "__main__":
    svg_path = "static/icons/app-icon.svg"
    output_dir = "static/icons"
    
    generate_icons(svg_path, output_dir)