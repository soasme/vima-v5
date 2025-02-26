import os
import numpy as np
import random
from PIL import Image

def distribute_images(bg_width, bg_height, num_images, min_scale=0.1, max_scale=0.3, max_attempts=1000):
    """
    Generate coordinates and scales for placing multiple images on a background
    without overlap.
    
    Args:
        bg_width (int): Width of the background image
        bg_height (int): Height of the background image
        num_images (int): Number of images to place
        min_scale (float): Minimum scale factor for images (0.1 = 10% of original size)
        max_scale (float): Maximum scale factor for images (0.3 = 30% of original size)
        max_attempts (int): Maximum number of placement attempts before giving up
        
    Returns:
        list: List of tuples (x, y, scale) for each image
    """
    # Create a mask to track occupied areas
    mask = np.zeros((bg_height, bg_width), dtype=bool)
    
    # List to store coordinates and scales
    placements = []
    
    # Helper function to check if a new placement overlaps with existing ones
    def check_overlap(x, y, width, height):
        # Check if the placement is within bounds
        if x < 0 or y < 0 or x + width > bg_width or y + height > bg_height:
            return True
        
        # Check if the placement overlaps with any existing placement
        if np.any(mask[y:y+height, x:x+width]):
            return True
        
        return False
    
    # Try to place each image
    for _ in range(num_images):
        placed = False
        attempts = 0
        
        # Keep trying until we find a valid placement or exceed max attempts
        while not placed and attempts < max_attempts:
            # Generate a random scale for this image
            scale = random.uniform(min_scale, max_scale)
            
            # Assuming the original image size is equivalent to background dimensions
            # Adjust this if your transparent images have different aspect ratios
            temp_width = int(bg_width * scale)
            temp_height = int(bg_height * scale)
            
            # Generate random coordinates
            x = random.randint(0, bg_width - temp_width)
            y = random.randint(0, bg_height - temp_height)
            
            # Check if the placement overlaps with existing placements
            if not check_overlap(x, y, temp_width, temp_height):
                # Mark the area as occupied
                mask[y:y+temp_height, x:x+temp_width] = True
                
                # Add the placement to our list
                placements.append((x, y, scale))
                placed = True
            
            attempts += 1
        
        # If we couldn't place the image after max attempts, we might need to adjust scales
        if not placed:
            print(f"Warning: Could not place image {len(placements) + 1}. Consider reducing the number of images or their sizes.")
            break
    
    return placements

def place_images_on_background(bg_image_path, transparent_images, output_path):
    """
    Place multiple transparent images on a background image.
    
    Args:
        bg_image_path (str): Path to the background image
        transparent_images (list): List of paths to transparent images
        output_path (str): Path to save the output image
    """
    # Load the background image
    bg = Image.open(bg_image_path).convert("RGBA")
    bg_width, bg_height = bg.size
    
    # Generate placements for images
    num_images = len(transparent_images)
    placements = distribute_images(bg_width, bg_height, num_images)
    
    # Place each image on the background
    for i, (image_path, (x, y, scale)) in enumerate(zip(transparent_images, placements)):
        # Load the transparent image
        img = Image.open(image_path).convert("RGBA")
        
        # Calculate new dimensions
        new_width = int(img.width * scale)
        new_height = int(img.height * scale)
        
        # Resize the image
        img_resized = img.resize((new_width, new_height), Image.LANCZOS)
        
        # Paste the transparent image onto the background
        # The mask is used to preserve transparency
        bg.paste(img_resized, (x, y), img_resized)
    
    # Save the result
    bg.save(output_path)
    
    return bg


images = list(os.listdir("/Users/soasme/Downloads/test/build"))
images = [f"/Users/soasme/Downloads/test/build/{image}" for image in images if image.endswith(".png")]
print(images)
place_images_on_background(
        "/Users/soasme/Downloads/test/background.png",
        images,
        "/tmp/output.png")
