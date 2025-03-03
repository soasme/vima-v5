import os
import numpy as np
import random
from PIL import Image
import math

def distribute_images(bg_width, bg_height, num_images, min_scale=0.5, max_scale=1.0, 
                      max_attempts=1000, coverage_target=0.99, three_pass=True):
    """
    Generate coordinates and scales for placing multiple images on a background
    without overlap, maximizing coverage with a three-pass approach.
    
    Args:
        bg_width (int): Width of the background image
        bg_height (int): Height of the background image
        num_images (int): Number of images to place
        min_scale (float): Minimum scale factor for images
        max_scale (float): Maximum scale factor for images
        max_attempts (int): Maximum number of placement attempts before giving up
        coverage_target (float): Target coverage of background (0-1)
        three_pass (bool): Whether to perform optimization passes
        
    Returns:
        list: List of tuples (x, y, scale) for each image
        float: Final coverage percentage achieved
    """
    # Create a mask to track occupied areas
    mask = np.zeros((bg_height, bg_width), dtype=bool)
    
    # List to store coordinates and scales
    placements = []
    
    # Calculate total background area
    total_area = bg_width * bg_height
    covered_area = 0
    current_coverage = 0
    
    # Calculate initial scales - aim higher for first pass
    avg_image_count = num_images * 1.2  # Account for potential failures
    avg_area_per_image = (total_area * coverage_target) / avg_image_count
    
    base_scale = math.sqrt(avg_area_per_image / total_area)
    
    # Set a wider range for better diversity
    adjusted_min_scale = max(min_scale, base_scale * 0.6)
    adjusted_max_scale = min(max_scale, base_scale * 1.8)
    
    print(f"Initial scale range: {adjusted_min_scale:.3f} to {adjusted_max_scale:.3f}")
    
    # Helper function to check if a new placement overlaps with existing ones
    def check_overlap(x, y, width, height, current_mask=None):
        if current_mask is None:
            current_mask = mask
            
        # Check if the placement is within bounds
        if x < 0 or y < 0 or x + width > bg_width or y + height > bg_height:
            return True
        
        # Check if the placement overlaps with any existing placement
        if np.any(current_mask[y:y+height, x:x+width]):
            return True
        
        return False
    
    # Helper function to calculate area of the placement
    def calculate_area(width, height):
        return width * height
    
    # FIRST PASS: Place initial images with standard approach
    print("Starting first pass: Initial placement...")
    for i in range(num_images):
        placed = False
        attempts = 0
        
        # Adjust scale factor based on progress
        scale_factor = 1.0
        if current_coverage < (coverage_target * 0.5) and i > num_images // 3:
            scale_factor = 1.2  # Increase scales if we're behind
        
        current_min_scale = adjusted_min_scale * scale_factor
        current_max_scale = adjusted_max_scale * scale_factor
        
        # Try multiple scales, starting from larger ones
        scale_ranges = [
            (current_max_scale * 0.8, current_max_scale),  # Try larger scales first
            (current_min_scale, current_max_scale),        # Try full range
            (current_min_scale * 0.7, current_min_scale)   # Try smaller scales as last resort
        ]
        
        for min_s, max_s in scale_ranges:
            if placed:
                break
                
            for _ in range(max_attempts // 3):
                if attempts >= max_attempts:
                    break
                    
                # Generate a random scale for this image
                scale = random.uniform(min_s, max_s)
                
                # Calculate dimensions
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
                    placements.append((x, y, scale, temp_width, temp_height))
                    
                    # Update coverage statistics
                    image_area = calculate_area(temp_width, temp_height)
                    covered_area += image_area
                    current_coverage = covered_area / total_area
                    
                    placed = True
                    break
                
                attempts += 1
        
        if not placed:
            print(f"Warning: Could not place image {i+1} in first pass. Current coverage: {current_coverage:.2%}")
    
    print(f"First pass coverage: {current_coverage:.2%}")
    
    if not three_pass:
        # Convert the placements to the required format and return
        final_placements = [(x, y, scale) for x, y, scale, _, _ in placements]
        return final_placements, current_coverage
    
    # SECOND PASS: Move images closer to edges if possible
    print("Starting second pass: Moving images to edges...")
    
    # Create a copy of the mask to work with
    edge_mask = np.zeros_like(mask)
    edge_placements = []
    
    # Define what we consider close to the edge (percentage of dimension)
    edge_threshold = 0.1
    edge_pixels_w = int(bg_width * edge_threshold)
    edge_pixels_h = int(bg_height * edge_threshold)
    
    # Helper function to determine if a placement is near an edge
    def is_near_edge(x, y, width, height):
        # Check if any part of the image is within edge_threshold of any edge
        near_left = x < edge_pixels_w
        near_right = (x + width) > (bg_width - edge_pixels_w)
        near_top = y < edge_pixels_h
        near_bottom = (y + height) > (bg_height - edge_pixels_h)
        
        return near_left or near_right or near_top or near_bottom
    
    # Helper function to find the nearest edge for a placement
    def find_nearest_edge(x, y, width, height):
        # Calculate distance to each edge
        dist_left = x
        dist_right = bg_width - (x + width)
        dist_top = y
        dist_bottom = bg_height - (y + height)
        
        # Find the minimum distance
        min_dist = min(dist_left, dist_right, dist_top, dist_bottom)
        
        # Return the direction of the nearest edge
        if min_dist == dist_left:
            return "left"
        elif min_dist == dist_right:
            return "right"
        elif min_dist == dist_top:
            return "top"
        else:
            return "bottom"
    
    # Process each placement
    for i, (x, y, scale, width, height) in enumerate(placements):
        # Check if this placement is not already near an edge
        if not is_near_edge(x, y, width, height):
            # Find the nearest edge
            nearest_edge = find_nearest_edge(x, y, width, height)
            
            # Try to move closer to that edge
            moved = False
            
            # Temporary remove this placement from consideration
            temp_mask = mask.copy()
            temp_mask[y:y+height, x:x+width] = False
            
            # Calculate move distance (up to halfway to the edge)
            if nearest_edge == "left":
                max_move = max(1, x // 2)
                for move in range(max_move, 0, -1):
                    new_x = x - move
                    new_y = y
                    if not check_overlap(new_x, new_y, width, height, temp_mask):
                        x = new_x
                        moved = True
                        break
            elif nearest_edge == "right":
                max_move = max(1, (bg_width - (x + width)) // 2)
                for move in range(max_move, 0, -1):
                    new_x = x + move
                    new_y = y
                    if not check_overlap(new_x, new_y, width, height, temp_mask):
                        x = new_x
                        moved = True
                        break
            elif nearest_edge == "top":
                max_move = max(1, y // 2)
                for move in range(max_move, 0, -1):
                    new_x = x
                    new_y = y - move
                    if not check_overlap(new_x, new_y, width, height, temp_mask):
                        y = new_y
                        moved = True
                        break
            elif nearest_edge == "bottom":
                max_move = max(1, (bg_height - (y + height)) // 2)
                for move in range(max_move, 0, -1):
                    new_x = x
                    new_y = y + move
                    if not check_overlap(new_x, new_y, width, height, temp_mask):
                        y = new_y
                        moved = True
                        break
            
            if moved:
                print(f"Moved image {i+1} closer to {nearest_edge} edge")
        
        # Add to the new placements and mask
        edge_mask[y:y+height, x:x+width] = True
        edge_placements.append((x, y, scale, width, height))
    
    # Update our mask and placements
    mask = edge_mask
    placements = edge_placements
    
    print(f"Second pass complete - images repositioned closer to edges")
    
    # THIRD PASS: Try to expand all images where possible
    print("Starting third pass: Expanding images...")
    
    # Create a copy of the mask to work with
    expanded_mask = np.zeros_like(mask)
    expanded_placements = []
    
    # Try to expand each image
    for i, (x, y, scale, width, height) in enumerate(placements):
        # Remove this image from the mask temporarily
        temp_mask = mask.copy()
        temp_mask[y:y+height, x:x+width] = False
        
        # Try different expansion percentages
        expansion_factors = [1.1, 1.0, 0.8, 0.7, 0.6]
        expanded = False
        
        for factor in expansion_factors:
            if expanded:
                break
            
            new_width = int(width * factor)
            new_height = int(height * factor)
            new_scale = scale * factor
            print(i, x, y, scale, new_scale)
            
            # Calculate new position to keep the image centered
            new_x = max(0, x - (new_width - width) // 2)
            new_y = max(0, y - (new_height - height) // 2)
            
            # Ensure we stay within bounds
            if new_x + new_width > bg_width:
                new_x = bg_width - new_width
            if new_y + new_height > bg_height:
                new_y = bg_height - new_height
            
            # Check if the expanded placement overlaps with other images
            if not check_overlap(new_x, new_y, new_width, new_height, temp_mask):
                # Update placement
                x, y = new_x, new_y
                width, height = new_width, new_height
                scale = new_scale
                
                # Update coverage calculations
                old_area = calculate_area(width // factor, height // factor)
                new_area = calculate_area(width, height)
                covered_area += (new_area - old_area)
                current_coverage = covered_area / total_area
                
                expanded = True
                print(f"Expanded image {i+1} by factor {factor}")
        
        # Add to the new placements and mask
        expanded_mask[y:y+height, x:x+width] = True
        expanded_placements.append((x, y, scale, width, height))
    
    # Update our mask and placements
    mask = expanded_mask
    placements = expanded_placements
    
    print(f"Final coverage achieved: {current_coverage:.2%}")
    
    # Convert the placements to the required format
    final_placements = [(x, y, scale) for x, y, scale, _, _ in placements]
    return final_placements, current_coverage

def place_images_on_background(bg_image_path, transparent_images, output_path, 
                               min_scale=0.1, max_scale=0.3, coverage_target=0.99,
                               show_coverage_map=False):
    """
    Place multiple transparent images on a background image, maximizing coverage.
    
    Args:
        bg_image_path (str): Path to the background image
        transparent_images (list): List of paths to transparent images
        output_path (str): Path to save the output image
        min_scale (float): Minimum scale factor for images
        max_scale (float): Maximum scale factor for images
        coverage_target (float): Target coverage percentage (0-1)
        show_coverage_map (bool): Whether to output a visualization of the coverage
    """
    # Load the background image
    bg = Image.open(bg_image_path).convert("RGBA")
    bg_width, bg_height = bg.size
    
    # Generate placements for images
    num_images = len(transparent_images)
    placements, coverage = distribute_images(bg_width, bg_height, num_images, 
                                           min_scale, max_scale, 
                                           coverage_target=coverage_target)
    
    # If we don't have enough transparent images, repeat them
    #while len(transparent_images) < len(placements):
    #    transparent_images = transparent_images * 2
    #transparent_images = transparent_images[:len(placements)]
    
    # Place each image on the background
    for i, (image_path, (x, y, scale)) in enumerate(zip(transparent_images, placements)):
        # Load the transparent image
        img = Image.open(image_path).convert("RGBA")
        
        # Calculate new dimensions based on the original image dimensions
        new_width = int(img.width * scale)
        new_height = int(img.height * scale)
        
        # Resize the image
        img_resized = img.resize((new_width, new_height), Image.LANCZOS)
        
        # Paste the transparent image onto the background
        # The mask is used to preserve transparency
        bg.paste(img_resized, (x, y), img_resized)
    
    # Save the result
    bg.save(output_path)
    
    # Create a coverage visualization if requested
    if show_coverage_map:
        # Create a mask visualization
        coverage_map = np.zeros((bg_height, bg_width, 3), dtype=np.uint8)
        
        for x, y, scale in placements:
            # We need to recalculate width and height based on original image
            # For visualization, we'll estimate using the average aspect ratio
            est_width = int(bg_width * scale)
            est_height = int(bg_height * scale)
            coverage_map[y:y+est_height, x:x+est_width] = [0, 255, 0]  # Green for covered areas
        
        # Convert to PIL image and save
        coverage_image = Image.fromarray(coverage_map)
        coverage_path = output_path.rsplit('.', 1)[0] + '_coverage.png'
        coverage_image.save(coverage_path)
        
        print(f"Coverage map saved to {coverage_path}")
    
    print(f"Image completed with {coverage:.2%} coverage")
    return bg

#place_images_on_background(
#        "/path/to//background.png",
#        [images],
#        "/tmp/output.png")
