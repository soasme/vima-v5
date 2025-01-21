# Try implement this: https://www.canva.com/design/DAGcxSAGTR8/5pS2Q5W-8ZRwQgT3b_UdlA/edit

"""
Example config:

{
  "id": "dino-matchme",
  "seed": 1,
  "aspect_ratio": "16:9",
  "background_image": "Background.png",
  "cursor_image": "Cursor.png",
  "speak_bubble_image": "",
  "character_image": "Character.png",
  "sticker_images": [
    "Ankylo.png",
    "Brachio.png",
    "Parasaur.png",
    "Pterasaurus.png",
    "Tricera.png",
    "Tyran.png"
  ],
  "answers": [
    "Ankylosaurus",
    "Brachiosaurus",
    "Parasaurolophus",
    "Pterasaurus",
    "Triceratops",
    "Tyrannosaurus"
  ],
  "ack_scene": {
    "min_duration": 5,
    "character": "ACK.mp4"
  }
}
"""

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
from PIL import Image
from vima5.utils import get_asset_path, get_build_path
from moviepy import *
logger = logging.getLogger(__name__)

@dataclass
class Config:
    id: str = 'default'
    aspect_ratio: str = '16:9'
    background_image: str = 'Background.png'
    cursor_image: str = 'Cursor.png'
    speak_bubble_image: str = 'SpeakBubble.png'
    character_image: str = 'Character.png'
    sticker_images: List[str] = field(default_factory=lambda: [
        'Sticker1.png',
        'Sticker2.png',
        'Sticker3.png',
        'Sticker4.png',
        'Sticker5.png',
        'Sticker6.png',
    ])
    answers: List[str] = field(default_factory=lambda: [
        'Answer1',
        'Answer2',
        'Answer3',
        'Answer4',
        'Answer5',
        'Answer6',
    ])
    seed: int = 0 # This is used to seed the random number generator
                  # so that the same sequence of answers is generated.
    help_scene: Dict[str, str] = field(default_factory=lambda: {
        'voiceover_text': 'Here is some text',
        'min_duration': 5,
    })
    ack_scene: Dict[str, str] = field(default_factory=lambda: {
        'voiceover_text': 'Here is some text',
        'min_duration': 5,
    })
    pop_scene: Dict[str, str] = field(default_factory=lambda: {
        'min_duration': 5,
    })

@dataclass
class Context:
    config: Config
    index: int = 0
    attempts: List[int] = field(default_factory=[])

def read_config(path):
    with open(path, 'r') as f:
        data = json.load(f)
        return Config(**data)

def save_mp4(clip, path):
    clip.write_videofile(path, fps=24, codec="libx264", temp_audiofile="temp-audio.m4a", remove_temp=True, audio_codec="aac", threads=4)

def blacken_image_fast(image):
  """
  Given a PIL.Image, return a new PIL.Image with black color 
  for any pixel in the parameter image. Transparent parts are left untouched.

  This version uses NumPy for faster processing.

  Args:
    image: The input PIL.Image object.

  Returns:
    A new PIL.Image object with black color for non-transparent pixels.
  """
  import numpy as np

  # Convert image to NumPy array
  img_array = np.array(image) 

  # Create a mask for non-transparent pixels
  alpha_mask = img_array[:, :, 3] > 0 

  # Create a black image with the same shape
  black_img = np.zeros_like(img_array)

  # Set non-transparent pixels to black
  black_img[alpha_mask] = [0, 0, 0, 255] 

  # Convert back to PIL Image
  new_image = Image.fromarray(black_img.astype('uint8')) 

  return new_image

def get_video_size(aspect_ratio: str) -> tuple:
    """Convert aspect ratio string to video dimensions."""
    width, height = map(int, aspect_ratio.split(':'))
    base_width = 1920
    base_height = int(base_width * height / width)
    return (base_width, base_height)

def create_bounce_animation(clip: VideoClip, duration: float, bounce_height: float = 50) -> VideoClip:
    """Create a bouncing animation for a clip."""
    def bounce(t):
        # Simple sine wave for bouncing effect
        return np.array([0, -bounce_height * abs(np.sin(2 * np.pi * t))])
    
    return clip.with_position(lambda t: (clip.pos(t)[0], clip.pos(t)[1] + bounce(t)[1]))

def create_wiggle_animation(clip: VideoClip, duration: float, wiggle_amount: float = 10) -> VideoClip:
    """Create a wiggling animation for a clip."""
    def wiggle(t):
        # Random wiggle effect
        angle = wiggle_amount * np.sin(2 * np.pi * 4 * t)
        return angle
    return clip.with_effects([vfx.Rotate(lambda t: wiggle(t))])

def get_background_clip(config):
    video_size = get_video_size(config.aspect_ratio)
    background = ImageClip(get_asset_path(config.background_image))
    background = (
        background
        .with_effects([vfx.Resize(video_size)])
    )
    return background
    

def get_sticker_grid_position(config, i):
    margin = (100, 100)
    video_size = get_video_size(config.aspect_ratio)

    cols = 3
    w = (video_size[0] - margin[0]*2) / 3
    h = (video_size[1] - margin[1]*2) / 2
    x = margin[0] + w * (i % cols)
    y = margin[1] + h * (i // cols)

    return {'w': w, 'h': h, 'x': x, 'y': y}

def get_sticker_position(config, i, sticker):
    """Get ith sticker position."""
    grid = get_sticker_grid_position(config, i)

    # Put sticker in the center of the grid and scale down
    scale = 0.85
    x = grid['x']
    y = grid['y']

    w = sticker.size[0] * scale
    h = sticker.size[1] * scale

    rel_x = sticker.size[0] * (1 - scale) / 2
    rel_y = sticker.size[1] * (1 - scale) / 2

    return {'x': x+rel_x, 'y': y+rel_y, 'w': w, 'h': h}

def make_help_scene(args):
    """Create Help Scene.

    Render background image;
    all stickers are applied with black color, and bounce these black stickers up and down.
    """
    config = read_config(args.config)
    video_size = get_video_size(config.aspect_ratio)
    
    # Load background
    background = get_background_clip(config)
    
    # Create black stickers
    sticker_clips = []
    margin = (100, 100)
    for i, sticker_path in enumerate(config.sticker_images):
        sticker_image = Image.open(get_asset_path(sticker_path))
        black_sticker = ImageClip(np.array(blacken_image_fast(sticker_image)))
        pos = get_sticker_position(config, i, black_sticker)
        black_sticker = (
            black_sticker.with_position((pos['x'], pos['y']))
            .with_effects([vfx.Resize((pos['w'], pos['h']))])
        )
        
        # Add bounce animation
        bouncing_sticker = create_bounce_animation(
            black_sticker,
            config.help_scene['min_duration'],
            10
        )
        sticker_clips.append(bouncing_sticker)
    
    # Combine all clips
    final_clip = CompositeVideoClip(
        [background] + sticker_clips,
        size=video_size
    ).with_duration(config.help_scene['min_duration'])
    
    save_mp4(final_clip, get_build_path(f'help_scene_{config.id}.mp4'))

def get_character(config, duration):
    character = ImageClip(get_asset_path(config.character_image))

    def character_pos_animation(t):
        # Pop in from corner, stay, then pop out
        if t < 0.5:  # pop in
            return (video_size[0], video_size[1])
        elif t < duration - 0.5:  # stay
            return (video_size[0] - character.size[0], video_size[1] - character.size[1])
        else:  # pop out
            return (video_size[0], video_size[1])

    def character_scale_animation(t):
        # Wiggle effect
        if t < 0.5 or t > duration - 0.5:
            return 1.0
        else:
            return math.sin(2 * np.pi * t) * 0.01 + 1.0

    character = (
        character
        .with_position(character_pos_animation)
        .with_effects([vfx.Resize(character_scale_animation)])
    )
    return character

def make_ack_scene(args):
    """Render background image, all stickers are applied with black color and show character in speak bubble, pop from corner, wiggle, then pop back to corner (disappear)."""
    config = read_config(args.config)
    video_size = get_video_size(config.aspect_ratio)
    
    # Load background
    background = get_background_clip(config)
    
    # Create black stickers
    sticker_clips = []
    margin = (100, 100)
    for i, sticker_path in enumerate(config.sticker_images):
        sticker_image = Image.open(get_asset_path(sticker_path))
        black_sticker = ImageClip(np.array(blacken_image_fast(sticker_image)))
        pos = get_sticker_position(config, i, black_sticker)
        black_sticker = (
            black_sticker.with_position((pos['x'], pos['y']))
            .with_effects([vfx.Resize((pos['w'], pos['h']))])
        )
        sticker_clips.append(black_sticker)

    # Create a 50% transparent black mask
    mask_image = Image.new('RGBA', video_size, (0, 0, 0, 174))
    mask = ImageClip(np.array(mask_image)).with_position((0, 0))

    # Add character in speak bubble
    if config.ack_scene.get('character'):
        character = (
            VideoFileClip(get_asset_path(config.ack_scene['character']))
            .with_position('center')
            .with_duration(config.ack_scene['min_duration'])
            .with_effects([
                vfx.MaskColor((0, 252, 20), 50, 2),
                vfx.Resize((500, 500))
                ]) # assume it's 1:1
        )
    else:
        character = get_character(config, config.ack_scene['min_duration'])
    
    # Combine all clips
    final_clip = CompositeVideoClip(
        [background] + sticker_clips + [mask, character],
        size=video_size
    ).with_duration(config.help_scene['min_duration'])
    
    save_mp4(final_clip, get_build_path(f'ack_scene_{config.id}.mp4'))

def make_pop_scene(args):
    """Render background image, show black sticker (original sticker if passed), move cursor to the center, pop out a sticker.
    """
    logger.info('Making pop scene')

def make_carry_scene(args):
    """Render background image, show black sticker (color sticker if passed), let cursor carry sticker to some locations (may be wrong at first, use random with seed to determine). Optionally, if wrong location, show a red cross, move sticker back to center, then move cursor back to center. The last attempt will always let cursor carry sticker to the right position."""
    logger.info('Making carry scene')

def make_reveal_scene(args):
    """Render background image, show black sticker (color sticker if passed), show a black mask on top of the images and stickers, slide in answer and sticker (may horizontal flipped), show character in speak bubble, pop from corner, wiggle, then pop back to corner (disappear)."""
    logger.info('Making reveal scene')


def main():
    parser = argparse.ArgumentParser(description='WFQ Helper')
    parser.add_argument('command', type=str, help='Command to run')
    parser.add_argument('--config', type=str, help='Path to config file')
    parser.add_argument('--shorts', action='store_true', help='Concat levels')
    parser.add_argument('--ith', type=int, default=0, help='ith of sticker to show')
    args = parser.parse_args()

    if args.command == 'helpscene':
        make_help_scene(args)
    elif args.command == 'ackscene':
        make_ack_scene(args)
    elif args.command == 'popscene':
        make_pop_scene(args)
    elif args.command == 'carryscene':
        make_carry_scene(args)
    elif args.command == 'revealscene':
        make_reveal_scene(args)


if __name__ == '__main__':
    main()
