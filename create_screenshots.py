#!/usr/bin/env python3
"""
Generate placeholder screenshots for the PWA
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_screenshot(filename, text, width=1280, height=720, bg_color=(255, 255, 255), text_color=(70, 140, 250), is_mobile=False):
    """Create a simple placeholder screenshot with text"""
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Draw gradient background
    gradient_start = (110, 142, 251)  # #6e8efb
    gradient_end = (167, 119, 227)    # #a777e3
    
    for y in range(height):
        r = int(gradient_start[0] + (gradient_end[0] - gradient_start[0]) * y / height)
        g = int(gradient_start[1] + (gradient_end[1] - gradient_start[1]) * y / height)
        b = int(gradient_start[2] + (gradient_end[2] - gradient_start[2]) * y / height)
        for x in range(width):
            alpha = 50  # Semi-transparent
            draw.point((x, y), fill=(r, g, b, alpha))
    
    # Add app name
    app_name = "The Inner Architect"
    
    # Font sizes depend on device type
    title_size = 40 if is_mobile else 60
    desc_size = 20 if is_mobile else 30
    
    # Use default font with adjusted sizes
    font = ImageFont.load_default()
    
    # Draw app name
    title_y = height // 5
    desc_y = height // 2
    
    # Draw device frame if mobile
    if is_mobile:
        # Draw phone frame
        frame_color = (40, 40, 40)
        frame_width = 20
        corner_radius = 30
        
        # Draw rounded rectangle for phone frame
        draw.rounded_rectangle(
            [(frame_width, frame_width), (width - frame_width, height - frame_width)],
            corner_radius,
            fill=None,
            outline=frame_color,
            width=frame_width
        )
        
        # Draw status bar
        status_bar_height = 40
        draw.rectangle(
            [(frame_width*2, frame_width*2), (width - frame_width*2, frame_width*2 + status_bar_height)],
            fill=(30, 30, 30, 180)
        )
        
        # Adjust text positions for mobile
        title_y = height // 4
    
    # Draw app name (centered)
    text_width = len(app_name) * title_size // 2
    draw.text(
        (width // 2 - text_width // 2, title_y), 
        app_name, 
        font=font, 
        fill=(255, 255, 255)
    )
    
    # Draw screen description (centered)
    lines = text.split('\n')
    line_height = desc_size + 5
    start_y = desc_y - (len(lines) * line_height) // 2
    
    for i, line in enumerate(lines):
        text_width = len(line) * desc_size // 3
        draw.text(
            (width // 2 - text_width // 2, start_y + i * line_height), 
            line, 
            font=font, 
            fill=(255, 255, 255)
        )
    
    # Save the image
    img.save(filename)
    print(f"Created {filename}")

if __name__ == "__main__":
    # Create output directory if it doesn't exist
    screenshots_dir = "static/screenshots"
    if not os.path.exists(screenshots_dir):
        os.makedirs(screenshots_dir)
    
    # Create desktop screenshots (16:9 ratio)
    create_screenshot(
        os.path.join(screenshots_dir, "screenshot1.png"),
        "Home Screen\nStart your transformation journey"
    )
    
    create_screenshot(
        os.path.join(screenshots_dir, "screenshot2.png"),
        "Premium Features\nUnlock advanced techniques and tools"
    )
    
    create_screenshot(
        os.path.join(screenshots_dir, "screenshot3.png"),
        "Progress Dashboard\nTrack your personal growth"
    )
    
    # Create mobile screenshots (9:19.5 ratio - like iPhone)
    create_screenshot(
        os.path.join(screenshots_dir, "mobile1.png"),
        "Chat Interface\nAI-powered cognitive reframing",
        width=390,
        height=844,
        is_mobile=True
    )
    
    create_screenshot(
        os.path.join(screenshots_dir, "mobile2.png"),
        "Techniques Explorer\nLearn powerful NLP methods",
        width=390,
        height=844,
        is_mobile=True
    )