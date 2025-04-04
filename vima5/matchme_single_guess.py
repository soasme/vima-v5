# This script generates a video for guessing what it is given an image and some alternatives.
# Implement this: https://www.canva.com/design/DAGc2lasUYc/n8WZoNWc0JpBXvAnfoo0VA/edit
# Here is the order of the moviepy clips.
#
# [                                   background                              ]
# [                 outline_image           ]
# [                 question_mark           ]
#        [  answer1  ] [  ... ] [  answer3  ]
#                                           [  charater_image                 ]
#                                             [  congrats ]
#                                                         [ mask              ]
#                                                         [ reveal_image_flip ]
#                                                              [ reveal_texxt ]
#
# ---
# 
# Here is the layout:
# * Background image is scaled to fit the screen (16:9 aspect ratio, 1080p).
# * outline_image is derived from the character_image. mask_alpha(input_image_path, output_mask_path, transparent_mask_color=(255, 255, 255, 0), translucency_mask_color=(0, 0, 0), opacity_mask_color=(255, 255, 255)) is used to create the outline_image.
# * outline_image is at the center of the screen.
# * question_mark is at the center of the outline_image and pulse in and out.
# * When showing answers, show up all answers by using a infinite scroll effect (left to right, or top to bottom if in shorts mode).
# * Move cursor from the bottom to the center of the screen. Drag the answer to the left (with a little bounce back effect).
# * Keep doing this until we reach to the end of the guesses, which should be the correct answer.
# * Move the cursor out of the screen. Show some congratulation text/gif.
# * Show a mask on top of the screen. Reveal the character_image from the left to the right.
# * Show the reveal_text at the bottom right of the screen.
     

"""
Example config:

{
  "id": "dino-matchme",
  "size": [1920, 1080],
  "background_image": "Background.png",
  "cursor_image": "Cursor.png",
  "character_image": "Pterasaurus.png",
  "choices": [
    "Brachio.png",
    "Tyrano.png",
    "Pterasaurus.png"
  ],
  "guess_gap_seconds": 1.0,
  "guess_duration": 2.0,
  "outline_border": "black",
  "outline_fill": "white",
  "outline_shadow": "black",
  "first_guess_delay": 3.0,
  "congrats_text": "YES!",
  "congrats_image": "Yes.png",
  "congrats_duration": 2.0,
  "reveal_duration": 7.0,
  "reveal_mask_color": [0, 0, 0, 255],
  "reveal_mask_transparency": 0.5,
  "reveal_text": "Pterasaurus",
  "reveal_text_font_size": 200,
  "reveal_text_stroke_width": 20,
  "reveal_text_stroke_color": "black",
  "reveal_text_fadein": 0.5,
  "reveal_text_delay": 1.0,
  "reveal_text_margin": [100, 100],
  "reveal_text_pos": ["right", "bottom"],
  "reveal_image_flip": true,
  "reveal_image_pos": "left",
  "reveal_image_ratio": 0.8
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
from rembg import remove as rembg
from typing import List, Dict
import numpy as np
from PIL import Image
from vima5.utils import get_asset_path, get_build_path, mask_alpha, make_rembg
from moviepy import *
logger = logging.getLogger(__name__)

QUIZ_RATIO = 0.8

@dataclass
class Config:
    id: str = ""
    size: List[int] = field(default_factory=lambda: [1920, 1080])
    background_image: str = ""
    cursor_image: str = ""
    character_image: str = ""
    choices: List[str] = field(default_factory=lambda: [])
    guess_gap_seconds: float = 1.0
    guess_duration: float = 2.0
    outline_border: str = "black"
    outline_fill: str = "white"
    outline_shadow: str = "black"
    first_guess_delay: float = 3.0
    congrats_text: str = "YES!"
    congrats_image: str = ""
    congrats_duration: float = 2.0
    reveal_duration: float = 7.0
    reveal_mask_color: List[int] = field(default_factory=lambda: [0, 0, 0, 255])
    reveal_mask_transparency: float = 0.5
    reveal_text: str = ""
    reveal_text_font_size: int = 200
    reveal_text_stroke_width: int = 20
    reveal_text_stroke_color: str = "black"
    reveal_text_fadein: float = 0.5
    reveal_text_margin: List[int] = field(default_factory=lambda: [100, 100])
    reveal_text_delay: float = 1.0
    reveal_text_pos: List[str] = field(default_factory=lambda: ["right", "bottom"])
    reveal_image_flip: bool = True
    reveal_image_pos: str = "left"
    reveal_image_ratio: float = QUIZ_RATIO


def read_config(path):
    with open(path, 'r') as f:
        data = json.load(f)
        return Config(**data)

def save_mp4(clip, path):
    clip.write_videofile(path, fps=24, codec="libx264", temp_audiofile="temp-audio.m4a", remove_temp=True, audio_codec="aac", threads=4)

def get_background_clip(config):
    video_size = config.size
    background = ImageClip(get_asset_path(config.background_image))
    background = (
        background
        .with_effects([vfx.Resize(video_size)])
    )
    return background
    
def make_video(args):
    config = read_config(args.config)
    video_size = config.size

    background = get_background_clip(config)

    # Create black and rembg image for all choices.
    for choice in config.choices + [config.character_image]:
        if (os.path.exists(get_build_path(choice.replace('.png', '_black.png'))) and
            os.path.exists(get_build_path(choice.replace('.png', '_rembg.png')))):
            continue
        make_rembg(choice)

    # Create outline image from character image
    outline = ImageClip(get_build_path(config.character_image.replace('.png', '_black.png')))
    outline = (
        outline
        .with_position("center")
        .with_effects([
            vfx.Resize(QUIZ_RATIO),
        ])
    )

    # Create pulsing question mark
    question_text = TextClip(text="?", font_size=200, color='black',
                             font='Arial', margin=(10, 10))
    def pulse_scale(t):
        scale = 1 + 0.2 * math.sin(2 * math.pi * t)  # Pulse between QUIZ_RATIO and 1.2
        return scale
    question_mark = (question_text
                     .with_position('center')
                     .with_effects([vfx.Resize(pulse_scale)]))

    # Create answer cohice popup
    choice_icon_clips = []

    # Create answer choice clips

    choice_clips = []
    current_time = config.first_guess_delay
    # TODO: 1s stay, 0.5 slide x -halfscreen

    for choice in config.choices + [config.character_image]:
        choice_image = ImageClip(get_build_path(choice.replace('.png', '_rembg.png')))

        choice_image = choice_image.with_start(current_time)
        duration = config.guess_duration
        if choice == config.character_image:
            duration += config.reveal_duration

        #def choice_pos(t):
            # 0.5s scroll from top to center (half bottom show up), stay, 0.5s scroll from center to bottom (half top show up)
        #    return ('center', 'center')

        # Show an surprise egg. (632x864)
        # Add a bounce effect.
        #egg = ImageClip(get_asset_path("SurpriseEggPink.png")).with_position(choice_pos).with_start(current_time).with_duration(1.0).with_position(lambda t: (
        #    (1920-632)/2,
        #    (1080-864)/2 + 10 * math.sin(3 * t),
        #))

        # Show an explosion gif
        #explosion = VideoFileClip(get_asset_path("Explode.gif"), has_mask=True)
        #explosion = explosion.with_start(current_time+1.0).with_duration(1.0).with_position('center')

        # Show the choice image
        # TODO: Add a bounce effect.
        choice_image = (
            choice_image
            .with_start(current_time+1.0)
            .with_duration(duration)
            .with_position('center')
        )

        fx = [
            vfx.Resize(QUIZ_RATIO),
            vfx.SlideIn(0.5, side='right'),
            vfx.CrossFadeIn(0.5),
        ]
        if choice != config.character_image:
            fx.append(vfx.SlideOut(0.5, side='right'))
            fx.append(vfx.CrossFadeOut(0.5))

        choice_image = choice_image.with_effects(fx)

        choice_clip = choice_image
        choice_clips.extend([
            #egg,
            choice_clip,
            #explosion,
        ])

        if choice == config.character_image:
            outline = outline.with_end(current_time)
            question_mark = question_mark.with_end(current_time)

            congrats = ImageClip(get_asset_path(config.congrats_image))
            congrats = (
                congrats
                .with_position(("right", "bottom"))
                .with_duration(config.congrats_duration)
                .with_start(current_time + 1.0)
                .with_effects([
                    vfx.CrossFadeIn(0.5),
                    vfx.CrossFadeOut(0.5),
                ])
            )

        current_time += config.guess_duration
        if choice != config.character_image:
            current_time += config.guess_gap_seconds



    mask = ColorClip(video_size, color=config.reveal_mask_color)
    mask = mask.with_opacity(config.reveal_mask_transparency)
    mask = mask.with_start(current_time)
    mask = mask.with_duration(config.reveal_duration)

    character_image = Image.open(get_build_path(config.character_image.replace('.png', '_rembg.png')))
    if config.reveal_image_flip:
        character_image = character_image.transpose(Image.FLIP_LEFT_RIGHT)

    character = ImageClip(np.array(character_image))
    character = (
        character
        .with_duration(config.reveal_duration)
        .with_effects([
            vfx.CrossFadeIn(config.reveal_text_fadein),
            vfx.Resize(QUIZ_RATIO),
        ])
    )
    
    def reveal_position(t):
        if config.reveal_image_pos == 'left':
            return ('left', 'center')
        else:
            return ('right', 'center')
    
    character = (character
                .with_position(reveal_position)
                .with_start(current_time)
                .with_duration(config.reveal_duration))
    
    # Create reveal text
    reveal_text = (TextClip(text=config.reveal_text,
                            font_size=config.reveal_text_font_size,
                            color='white',
                            stroke_color=config.reveal_text_stroke_color,
                            stroke_width=config.reveal_text_stroke_width,
                            margin=tuple(config.reveal_text_margin),
                            font='Arial')
                   .with_position(config.reveal_text_pos)
                   .with_start(current_time + config.reveal_text_delay)
                   .with_duration(config.reveal_duration - config.reveal_text_delay)
                   .with_effects([vfx.CrossFadeIn(config.reveal_text_fadein)])
                   )

    current_time += mask.duration

    # Compose final video
    final = CompositeVideoClip(
        [background, outline, question_mark] +
        choice_icon_clips +
        choice_clips +
        [congrats, mask, character, reveal_text],
        size=video_size
    ).with_duration(current_time)

    print(f"Final duration: {final.duration}")

    
    # Save video
    output_path = get_build_path(f"{config.id}.mp4")
    save_mp4(final, output_path)
    
    return output_path


def main():
    parser = argparse.ArgumentParser(description='WFQ Helper')
    parser.add_argument('command', type=str, help='Command to run')
    parser.add_argument('--config', type=str, help='Path to config file')
    parser.add_argument('--shorts', action='store_true', help='Concat levels')
    args = parser.parse_args()

    build_path = get_build_path('')
    if not os.path.exists(build_path):
        os.makedirs(build_path)

    if args.command == 'video':
        make_video(args)


if __name__ == '__main__':
    main()
