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
from rembg import remove as rembg
from PIL import Image, ImageFilter, ImageDraw
from vima5.utils import get_asset_path, get_build_path, save_mp4, blacken_image, mask_alpha
from vima5.particles.particle_effect import ParticleEffect
from vima5.particles.renderers.image_effect_renderer import ImageEffectRenderer
from moviepy import *
logger = logging.getLogger(__name__)

import cv2

def find_top_y(image, start_x, end_x):
    """
    Finds the topmost y coordinate with non-zero alpha within a given x range in a PIL Image.
  
    Args:
      image: A PIL Image object.
      start_x: The starting x coordinate.
      end_x: The ending x coordinate.
  
    Returns:
      The topmost y coordinate with non-zero alpha, or None if no such pixel is found.
    """
    width, height = image.size
    for y in range(height):
        for x in range(start_x, end_x + 1):
            r, g, b, a = image.getpixel((x, y))
            if a != 0:
                return y
    return 0 # Defaults to top, if no non-zero alpha pixel found

def find_bottom_y(image, start_x, end_x):
    """
    Finds the bottommost y coordinate with non-zero alpha within a given x range in a PIL Image.
    
    Args:
        image: A PIL Image object.
        start_x: The starting x coordinate.
        end_x: The ending x coordinate.
    
    Returns:
        The bottommost y coordinate with non-zero alpha, or None if no such pixel is found.
    """
    width, height = image.size
    for y in range(height - 1, -1, -1):
        for x in range(start_x, end_x + 1):
            r, g, b, a = image.getpixel((x, y))
            if a != 0:
                return y
    return height - 1  # Defaults to bottom, if no non-zero alpha pixel found

def generate_doodle_speedpaint(final_image, duration=5, brush_size=5, fps=24, cols=10, ):
    """
  Generates a doodle speedpaint video with row-by-row circle drawing and optimized performance.

  Args:
    final_image: Path to the final image.
    output_file: Path to the output video file.
    duration: Duration of the video in seconds.
    brush_size: Size of the simulated brush.
    steps: Number of steps in the animation.

    TODO:
    * Add particles.

    """

    # Load images
    final_img = Image.open(final_image).convert('RGBA')
    steps = fps * duration
    trails = []

    width, height = final_img.size
    chunk_width = width // cols

    # Create a list of frames
    frames = []
    temp_frame = Image.new('RGBA', (width, height))
    draw = ImageDraw.Draw(temp_frame)

    for col in range(cols):
        start_frame = int(col * steps // cols)
        end_frame = int((col + 1) * steps // cols)
        top_y = find_top_y(final_img, col * chunk_width, (col + 1) * chunk_width)
        bottom_y = find_bottom_y(final_img, col * chunk_width, (col + 1) * chunk_width)
        col_height = bottom_y - top_y
        chunk_height = col_height // (end_frame - start_frame)
        for frame in range(start_frame, end_frame):
            progress = (frame - start_frame) / (end_frame - start_frame)
            box = (
                col * chunk_width,
                top_y + col_height * progress,
                (col + 1) * chunk_width,
                # draw a little extra to avoid gaps
                top_y + col_height * progress + math.ceil(col_height / (end_frame - start_frame)),
            )
            crop = final_img.crop(box)
            temp_frame.paste(crop, (int(col * chunk_width), int(top_y + col_height * progress)))
            this_frame = temp_frame.copy()
            trails.append((
                int(box[0] + chunk_width // 2),
                int(box[3]), 
            ))
            frames.append(np.array(this_frame))

    # Create a clip from the frames
    return ImageSequenceClip(frames, fps=fps), trails

def get_crayon_effect_clip(trails, fps):
    r = ImageEffectRenderer()

    crayon_particle_cfg = {
    	"loops": -1,
    	"emitters": [
    		{
    			"width": 100,
    			"height": 200,
    			"frames": 2,
    			"spawn_amount": 4,
    			"spawns": -1,
    			"particle_settings": {
    				"lifetime": 50,
    				"x_speed": 0,
    				"y_speed": -0.5,
    				"y_acceleration": -0.02,
    				"scale": [0.4, 0],
    				"shape": "circle",
    				"colourise": False,
    				"red": 150,
    				"green": 150,
    				"blue": 150,
    			},
    			"particle_variation": {
    				"lifetime": 10,
    				"x_speed": 0.3,
    				"x_acceleration": 0.05,
    				"y_speed": 0.4,
    				"scale": [0.2, 0]
    			}
    		}
    	]
    }
    particle_effect = ParticleEffect.load_from_dict(crayon_particle_cfg)
    r.register_effect(particle_effect)
    frames = []
    for i, pos in enumerate(trails):
        particle_effect.update()
        image = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
        x = pos[0] - 50
        y = pos[1] - 200
        particle_effect.set_pos(x, y)
        r.render_effect(particle_effect, image)
        frames.append(np.array(image))
    return ImageSequenceClip(frames, fps=fps)



def make_alpha_mask(args):
    output_path = os.path.splitext(args.image)[0] + "_masked.png"
    mask_alpha(args.image, get_build_path(output_path))

def make_rembg(args):
    image_path = get_asset_path(args.image)
    black_path = get_build_path(os.path.splitext(os.path.basename(args.image))[0] + "_black.png")
    rembg_path = get_build_path(os.path.splitext(os.path.basename(args.image))[0] + "_rembg.png")
    image = Image.open(image_path).convert("RGBA")
    rembg_image = rembg(image)
    rembg_image.save(rembg_path)
    mask_alpha(rembg_path, black_path,
        translucency_mask_color=(0, 0, 0),
        transparent_mask_color=(0, 0, 0, 0),
        opacity_mask_color=(0, 0, 0),
    )

def make_video(args):
    """
    """
    image_path = get_asset_path(args.image)
    rembg_path = get_build_path(os.path.splitext(os.path.basename(args.image))[0] + "_rembg.png")
    black_path = get_build_path(os.path.splitext(os.path.basename(args.image))[0] + "_black.png")
    crayon_path = get_asset_path('Crayon.png')

    image = Image.open(image_path).convert("RGBA")

    if not os.path.exists(rembg_path):
        rembg_image = rembg(image)
        rembg_image.save(rembg_path)

    if not os.path.exists(black_path):
        mask_alpha(rembg_path, black_path,
            translucency_mask_color=(0, 0, 0),
            transparent_mask_color=(0, 0, 0, 0),
            opacity_mask_color=(0, 0, 0),
        )

    if args.background_image:
        bg_clip = ImageClip(get_asset_path(args.background_image))
        bg_clip = bg_clip.with_effects([vfx.Resize(height=1080)])
    elif args.background_color:
        bg_clip = ColorClip(size=(1920, 1080), color=args.background_color)
    else: # defaults to chroma key green #00b140, 0, 177, 64
        bg_clip = ColorClip(size=(1920, 1080), color=(0, 177, 64))

    black_clip = ImageClip(black_path)
    black_clip = (
        black_clip
        .with_position('center')
        .with_duration(args.duration)
    )

    fps = args.fps
    draw_clip, trails = generate_doodle_speedpaint(
        rembg_path,
        duration=args.draw_duration,
        fps=fps,
        cols=args.cols,
    )
    draw_clip = draw_clip.with_position('center')

    reveal_clip = ImageClip(rembg_path)
    reveal_clip = (
        reveal_clip
        .with_position('center')
        .with_start(args.draw_duration)
        .with_duration(args.duration-args.draw_duration)
    )

    crayon_clip = (
        ImageClip(crayon_path)
        .with_effects([vfx.Resize(height=300)])
    )
    margin = (1920 - draw_clip.size[0]) // 2
    def crayon_position(t):
        idx = int(t * fps)
        if idx >= len(trails):
            return -300, -300
        x, y = trails[int(t * fps)]
        tweak = 100 # not sure why this is needed
        return margin + x, margin + y - crayon_clip.size[1] - tweak
    crayon_clip = (
        crayon_clip
        .with_duration(args.draw_duration)
        .with_position(crayon_position)
    )

    # This is not ready. :)
    #crayon_effect_clip = get_crayon_effect_clip(trails, fps=fps)

    base_clip = ColorClip(size=(1920, 1080), color=(255, 255, 255))
    final_clip = CompositeVideoClip([
        base_clip,
        bg_clip,
        black_clip,
        draw_clip,
        crayon_clip,
        reveal_clip,
        #crayon_effect_clip,
    ])
    final_clip = final_clip.with_duration(args.duration)

    output_path = args.reveal_text.replace(" ", "_") + ".mp4"
    save_mp4(final_clip, get_build_path(output_path), fps=fps)


def main():
    parser = argparse.ArgumentParser(description='WFQ Helper')
    parser.add_argument('command', type=str, help='Command to run')
    parser.add_argument('--fps', type=int, help='FPS', default=24)
    parser.add_argument('--draw-duration', type=float, help='FPS', default=5)
    parser.add_argument('--duration', type=float, help='FPS', default=6)
    parser.add_argument('--cols', type=int, help='FPS', default=10)
    parser.add_argument('--reveal-text', type=str, help='RevealText')
    parser.add_argument('--no-color-mode', type=str, help='NoColorMode, can be black, line_art')
    parser.add_argument('--image', type=str, help='Path to image file')
    parser.add_argument('--background-color', type=str, help='Hex color for background.')
    parser.add_argument('--background-image', type=str, help='Path to background image file. Overwrites background color.')
    parser.add_argument('--shorts', action='store_true', help='Concat levels')
    parser.add_argument('--line-art-duration', type=str, help='Duration of showing line_art still image.')
    parser.add_argument('--draw-speed', type=str, help='Pixels of coloring brush per second.')
    args = parser.parse_args()

    build_dir = get_build_path('')
    if not os.path.exists(build_dir):
        os.makedirs(build_dir)

    if args.command == 'video':
        make_video(args)
    if args.command == 'rembg':
        make_rembg(args)
    elif args.command == 'alphamask':
        make_alpha_mask(args)


if __name__ == '__main__':
    main()
