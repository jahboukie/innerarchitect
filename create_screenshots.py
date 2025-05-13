#!/usr/bin/env python3
"""
Generate placeholder screenshots for the PWA
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_screenshot(filename, text, width=1280, height=720, bg_color=(255, 255, 255), text_color=(70, 140, 250)):
    """Create a simple placeholder screenshot with text"""
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Draw gradient background
    for y in range(height):
        r = int(70 + (180 - 70) * y / height)
        g = int(140 + (160 - 140) * y / height)
        b = int(250 + (230 - 250) * y / height)
        for x in range(width):
            draw.point((x, y), fill=(r, g, b, 50))
    
    # Add app name
    app_name = "The Inner Architect"
    try:
        # Try to use a nicer font if available
        font = ImageFont.truetype("Arial", 60)
        small_font = ImageFont.truetype("Arial", 30)
    except IOError:
        # Fallback to default font
        font = ImageFont.load_default().font_variant(size=60)
        small_font = ImageFont.load_default().font_variant(size=30)
    
    # Draw app name
    draw.text((width//2, height//4), app_name, font=font, fill=(70, 80, 100), anchor="mm")
    
    # Draw screen description
    draw.text((width//2, height//2), text, font=small_font, fill=text_color, anchor="mm")
    
    # Save the image
    img.save(filename)
    print(f"Created {filename}")

if __name__ == "__main__":
    # Create output directory if it doesn't exist
    screenshots_dir = "static/screenshots"
    if not os.path.exists(screenshots_dir):
        os.makedirs(screenshots_dir)
    
    # Create screenshots
    create_screenshot(
        os.path.join(screenshots_dir, "screen1.png"),
        "Home Screen - Start your transformation journey"
    )
    
    create_screenshot(
        os.path.join(screenshots_dir, "screen2.png"),
        "Premium Features - Unlock advanced techniques and tools"
    )