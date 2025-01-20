from PIL import Image, ImageOps, ImageFilter
import numpy as np
from typing import List, Tuple, Dict
import io
from moviepy import ImageSequenceClip
import math

def create_shadow_mask(image: Image.Image) -> Image.Image:
    """Creates a grayscale shadow mask from an RGBA image."""
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    alpha = image.split()[3]
    shadow = alpha.point(lambda x: x * 0.5)
    return shadow

def resize_by_depth(image: Image.Image, depth: float, base_size: Tuple[int, int]) -> Image.Image:
    """Resize image based on its depth value."""
    if depth == 0:
        return image
    scale = 1 + (1 - depth) * 0.2
    new_width = int(image.size[0] * scale)
    new_height = int(image.size[1] * scale)
    print(new_width, new_height)
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

def calculate_swing_position(frame: int, total_frames: int, layer_index: int) -> Tuple[float, float]:
    """
    Calculate position for pendulum swing animation.
    Returns: (y_offset, current_depth)
    """
    # Delay start for each layer
    start_frame = layer_index * 15
    if frame < start_frame:
        return (-1.0, 1.0)  # Above screen
    
    adjusted_frame = frame - start_frame
    
    # Initial drop
    drop_frames = 10
    if adjusted_frame < drop_frames:
        progress = adjusted_frame / drop_frames
        return (progress - 1.0, 1.0)
    
    # Pendulum swing motion
    swing_frame = adjusted_frame - drop_frames
    
    # Natural pendulum period
    swing_period = 30 # Frames per swing (slower swing)
    
    # Calculate angle using pendulum motion
    max_angle = math.pi / 20  # 18 degrees maximum swing
    damping = math.exp(-swing_frame * 0.002)  # Slower damping
    angle = max_angle * math.sin(swing_frame * 2 * math.pi / swing_period) * damping
    
    # Calculate y and z (depth) offset based on angle
    string_length = 0.5  # Virtual string length
    y_offset = (1 - math.cos(angle)) * string_length  # Vertical displacement
    z_offset = math.sin(angle) * string_length  # Depth displacement
    
    # Convert z_offset to depth value (0 to 1)
    base_depth = 0.5
    current_depth = base_depth + z_offset
    current_depth = max(0.1, min(0.9, current_depth))
    
    return (y_offset, current_depth)

def process_frame(layers: List[Dict], frame: int, total_frames: int, base_size: Tuple[int, int]) -> Image.Image:
    """Process a single frame of the animation."""
    final_image = Image.new('RGBA', base_size, (0, 0, 0, 0))
    
    # Sort layers by depth (bottom to top)
    sorted_layers = sorted(layers, key=lambda x: x['depth'], reverse=True)
    
    # Process background first (if it exists)
    if sorted_layers and sorted_layers[0]['depth'] == 1.0:
        bg_layer = sorted_layers[0]
        final_image = Image.alpha_composite(final_image, bg_layer['image'])
        sorted_layers = sorted_layers[1:]
    
    # Process other layers
    for i, layer in enumerate(sorted_layers):
        current_image = layer['image']
        
        # Calculate swing position
        y_offset, current_depth = calculate_swing_position(frame, total_frames, i)
        
        if y_offset > 1.0:  # Skip if above screen
            continue
        
        # Resize image based on current depth
        resized_image = resize_by_depth(current_image, current_depth, base_size)
        
        # Create shadow mask
        shadow_mask = create_shadow_mask(resized_image)
        
        # Calculate shadow offset based on current depth
        shadow_offset = int(20 * (1 - current_depth))
        
        # Create layer canvas
        layer_canvas = Image.new('RGBA', base_size, (0, 0, 0, 0))
        
        # Calculate position with swing offset
        pos_x = (base_size[0] - resized_image.size[0]) // 2
        pos_y = int((base_size[1] - resized_image.size[1]) * (1 + y_offset))
        
        # Paste shadow
        shadow_image = Image.new('RGBA', base_size, (0, 0, 0, 0))
        shadow_pos_y = min(pos_y + shadow_offset, base_size[1] - shadow_mask.size[1])
        shadow_image.paste((0, 0, 0, 255), (pos_x + shadow_offset, shadow_pos_y), shadow_mask)
        shadow_image = shadow_image.filter(ImageFilter.BoxBlur(radius=10))
        
        # Composite shadow and image
        layer_canvas = Image.alpha_composite(layer_canvas, shadow_image)
        layer_canvas.paste(resized_image, (pos_x, pos_y), resized_image)
        
        # Add to final image
        final_image = Image.alpha_composite(final_image, layer_canvas)
    
    return final_image

def create_animation(layers: List[Dict], output_path: str, fps: int = 30, duration: int = 5):
    """
    Create an animated MP4 with swinging layers.
    
    Args:
        layers: List of dicts with 'image' (PIL Image or path) and 'depth' (float 0-1)
        output_path: Path to save the MP4 file
        fps: Frames per second
        duration: Duration in seconds
    """
    # Process input layers
    processed_layers = []
    base_size = None
    
    for layer in layers:
        if isinstance(layer['image'], str):
            img = Image.open(layer['image'])
        else:
            img = layer['image']
            
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
            
        if base_size is None and layer['depth'] == 1.0:  # Use background size
            base_size = img.size
            
        processed_layers.append({'image': img, 'depth': layer['depth']})
    
    if base_size is None:
        base_size = (800, 600)  # Default size
    
    # Generate frames
    total_frames = fps * duration
    frames = []
    
    for frame in range(total_frames):
        img = process_frame(processed_layers, frame, total_frames, base_size)
        # Convert PIL image to numpy array for MoviePy
        frames.append(np.array(img))
    
    # Create video
    clip = ImageSequenceClip(frames, fps=fps)
    clip.write_videofile(output_path, fps=fps)

# Example usage
def example_usage():
    # Create sample images
    bg = Image.new('RGBA', (800, 600), (255, 255, 255, 255))
    circle = Image.new('RGBA', (200, 200), (0, 0, 0, 0))
    square = Image.new('RGBA', (150, 150), (255, 0, 0, 255))
    
    # Draw a circle
    for x in range(200):
        for y in range(200):
            if (x-100)**2 + (y-100)**2 < 100**2:
                circle.putpixel((x, y), (0, 255, 0, 255))
    
    layers = [
        {'image': bg, 'depth': 1.0},      # Background (static)
        {'image': square, 'depth': 0.9},   # Middle layer (will swing)
        {'image': circle, 'depth': 0.9}    # Top layer (will swing)
    ]
    
    create_animation(layers, 'output.mp4', fps=30, duration=5)

if __name__ == "__main__":
    example_usage()
