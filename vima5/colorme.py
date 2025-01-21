import argparse
import os
import math
import json
import sys
import logging
import random
from dataclasses import dataclass, field
from typing import List, Dict
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
from vima5.utils import get_asset_path, get_build_path, save_mp4, blacken_image, mask_alpha
from moviepy import *
logger = logging.getLogger(__name__)

def make_video(args):
    """This function does below things.

    1. Load Image.
    2. Use Pillow/Numpy to get blackpixels and create line_art image.
    3. Show line_art image using ImageClip.
    3. Create animation that color the line_art in ten slices one by one from left to right, brush moves from up to down for each slice.
       3.a You can use Pillow crop for each frame of animation.
       3.b You can use ImageSequenceClip to create animation.
       3.c You overlay ImageSequenceClip on line art ImageClip.
       3.d You should count the top and bottom position of black pixels for each slice when drawing.
    """

    # Step 1: Load Image
    image_path = get_asset_path(args.image)
    image = Image.open(image_path).convert("RGBA")

    # Step 2: Create line art
    black_image = blacken_image(image)

    # Step 3: Show line art image
    line_art_clip = ImageClip(black_image)

    # Step 4: Create animation of coloring
    width, height = line_art.size
    slice_width = width // 10

    frames = []
    brush_speed = int(args.draw_speed)

    for slice_idx in range(10):
        left = slice_idx * slice_width
        right = left + slice_width if slice_idx < 9 else width

        colored_frame = line_art.convert("RGB")
        draw = ImageDraw.Draw(colored_frame)

        for y in range(0, height, brush_speed):
            for x in range(left, right):
                if black_pixels[y, x]:
                    color = tuple(np_image[y, x, :3])
                    draw.point((x, y), fill=color)

            # Convert frame to numpy array and append to frames
            frames.append(np.array(colored_frame))

    # Create ImageSequenceClip
    coloring_animation = ImageSequenceClip(frames, fps=24)

    # Overlay animation on line art
    bg = ColorClip((width, height), color=(255, 255, 255))
    final_clip = CompositeVideoClip([bg, line_art_clip, coloring_animation.with_start(float(args.line_art_duration))])

    # Save the video
    output_path = os.path.splitext(image_path)[0] + "_colored.mp4"
    save_mp4(final_clip, get_build_path(output_path))

def mask_alpha(input_image_path, output_mask_path, 
                    transparent_mask_color=(255, 255, 255, 0),
                    translucency_mask_color=(0, 0, 0),
                    opacity_mask_color=(255, 255, 255)):
    """
    Creates an alpha mask from a PNG image.

    Args:
        input_image_path (str): Path to the input PNG image.
        output_mask_path (str): Path to save the generated alpha mask.
        transparent_mask_color (tuple): RGBA color for fully transparent pixels.
        translucency_mask_color (tuple): RGB color for semi-transparent pixels.
        opacity_mask_color (tuple): RGB color for fully opaque pixels.
    """
    # Open the input image
    image = Image.open(input_image_path).convert("RGBA")
    width, height = image.size

    # Create a new image for the alpha mask
    alpha_mask = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pixels = image.load()
    mask_pixels = alpha_mask.load()

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]  # Get the RGBA values

            if a == 0:
                # Fully transparent
                mask_pixels[x, y] = transparent_mask_color
            elif 0 < a < 255:
                # Semi-transparent
                mask_pixels[x, y] = translucency_mask_color + (255,)
            else:
                # Fully opaque
                mask_pixels[x, y] = opacity_mask_color + (255,)

    # Save the alpha mask
    alpha_mask.save(output_mask_path, "PNG")

# Example usage:
# make_alpha_mask("input.png", "output_mask.png")

def make_alpha_mask(args):
    output_path = os.path.splitext(args.image)[0] + "_masked.png"
    mask_alpha(args.image, get_build_path(output_path))

def main():
    parser = argparse.ArgumentParser(description='WFQ Helper')
    parser.add_argument('command', type=str, help='Command to run')
    parser.add_argument('--image', type=str, help='Path to image file')
    parser.add_argument('--shorts', action='store_true', help='Concat levels')
    parser.add_argument('--line-art-duration', type=str, help='Duration of showing line_art still image.')
    parser.add_argument('--draw-speed', type=str, help='Pixels of coloring brush per second.')
    args = parser.parse_args()

    if args.command == 'video':
        make_video(args)
    elif args.command == 'alphamask':
        make_alpha_mask(args)


if __name__ == '__main__':
    main()
