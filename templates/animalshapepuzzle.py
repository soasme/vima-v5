"""
Require assets:
* background
* 10~15 objects (animals) with a transparent background.

Can use `python vima5/outline_generator.py` to generate the transparent & outline images.

Example config:
{
	"background": "background.png",
	"animals": [
		{
			"name": "Bull",
			"pos": [1243, 694],
			"size": [633, 354]
		},

# Get pos/size in Adobe Animate or Canva.

"""

import os
import numpy as np
import math
import json
import argparse
from PIL import Image, ImageOps, ImageFilter
from moviepy import *
from vima5.canva import *
from rembg import remove as rembg
import random
from typing import List, Tuple, Optional
from elevenlabs.types import VoiceSettings

from vima5.utils import mask_alpha
from vima5.utils import make_voiceover, get_asset_path
from types import SimpleNamespace

CANVA_WIDTH = 1920
CANVA_HEIGHT = 1080
VOICEOVER_MODEL = 'Natsumi'
VOICEOVER_SETTINGS = VoiceSettings(
    stability=0.9,
    similarity_boost=0.5,
    style=0.0,
    speed=0.75,
    use_speaker_boost=True
)

#FPS = 12
FPS = 30

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

def find_left_x(image, start_y, end_y):
    """
    Finds the leftmost x coordinate with non-zero alpha within a given y range in a PIL Image.
    
    Args:
        image: A PIL Image object.
        start_y: The starting y coordinate.
        end_y: The ending y coordinate.
    
    Returns:
        The leftmost x coordinate with non-zero alpha, or None if no such pixel is found.
    """
    width, height = image.size
    for x in range(width):
        for y in range(start_y, end_y + 1):
            r, g, b, a = image.getpixel((x, y))
            if a != 0:
                return x
    return 0  # Defaults to left, if no non-zero alpha pixel found

def find_right_x(image, start_y, end_y):
    """
    Finds the rightmost x coordinate with non-zero alpha within a given y range in a PIL Image.
    
    Args:
        image: A PIL Image object.
        start_y: The starting y coordinate.
        end_y: The ending y coordinate.
    
    Returns:
        The rightmost x coordinate with non-zero alpha, or None if no such pixel is found.
    """
    width, height = image.size
    for x in range(width - 1, -1, -1):
        for y in range(start_y, end_y + 1):
            r, g, b, a = image.getpixel((x, y))
            if a != 0:
                return x
    return width - 1  # Defaults to right, if no non-zero alpha pixel found

def find_nontransparent_box(image):
    """
    Finds the bounding box of non-transparent pixels in a PIL Image.
    
    Args:
        image: A PIL Image object.
    
    Returns:
        A tuple (x, y, width, height) of the bounding box.
    """
    width, height = image.size
    left = find_left_x(image, 0, height - 1)
    right = find_right_x(image, 0, height - 1)
    top = find_top_y(image, left, right)
    bottom = find_bottom_y(image, left, right)
    return (left, top, right - left + 1, bottom - top + 1)

def distribute_images(
    images: List[Image.Image],
    canvas_size: Tuple[int, int] = (1920, 1080),
    cols: int = 5,
    rows: int = 3,
) -> List[Tuple[float, int, int, int, int]]:
    grid_height = canvas_size[1] // rows
    grid_width = canvas_size[0] // cols
    placements = []

    margin = (50, 50)
    for i, img in enumerate(images):
        img = img.convert('RGBA')
        box = find_nontransparent_box(img)
        box = (
            max(0, box[0] - margin[0]),
            max(0, box[1] - margin[1]),
            box[2] + 2 * margin[0],
            box[3] + 2 * margin[1],
        )
        if box[2] > grid_width or box[3] > grid_height:
            scale = min(grid_width / box[2], grid_height / box[3])
        else:
            scale = 1.0
        placements.append((
            grid_width * (i % cols),
            grid_height * (i // cols),
            scale,
        ))

    return placements

def parse_args():
    parser = argparse.ArgumentParser(description='Finger Family')
    parser.add_argument('--input-dir', type=str, help='Input Directory having all the images and config')
    parser.add_argument('--output', type=str, help='Output video file', default='/tmp/animalshapepuzzle.mp4')
    parser.add_argument('--compile', action='store_true', help='Compile the video')

    args = parser.parse_args()
    return args

def get_image_path(config, input_dir, idx, name):
    if 'image' in config['animals'][idx]:
        return '%s/%s' % (input_dir, config['animals'][idx]['image'])
    return '%s/build/%02d_%s.png' % (input_dir, idx+1, name.replace(' ', '').lower())

def get_outline_path(config, input_dir, idx, name):
    if 'image' in config['animals'][idx]:
        return '%s/%s' % (input_dir, config['animals'][idx]['image'].replace('.png', '_black.png'))
    return '%s/build/%02d_%s_black.png' % (input_dir, idx+1, name.replace(' ', '').lower())

def add_animal_outline(page, config, input_dir, main_char_idx, outline_idx, animal):
    image_path = get_image_path(config, input_dir, outline_idx, animal['name'])
    outline_path = get_outline_path(config, input_dir, outline_idx, animal['name'])
    image_pos = animal['pos']
    image_size = animal['size']

    page.elem(
        ImageClip(outline_path if main_char_idx <= outline_idx else image_path)
        .resized(image_size)
        .with_position(image_pos),
    )

def make_page(config, idx):
    movie = Movie()
    move_in_duration = 5
    move_to_duration = 3
    congrats_duration = 2
    total_duration = move_in_duration + move_to_duration + congrats_duration
    started_at = 0
    revealed_at = move_in_duration
    congrats_at = move_in_duration + move_to_duration

    with movie.page(
        duration=total_duration,
        background='#ffffff',
        ) as page:
        page.elem(
            ImageClip(config['input_dir'] + '/' + config['background'])
            .resized((CANVA_WIDTH, CANVA_HEIGHT))
        )
    
        for j, animal in enumerate(config['animals']):
            add_animal_outline(page, config, config['input_dir'], idx, j, animal)
    
        main_character = config['animals'][idx]
        image_path = get_image_path(config, config['input_dir'], idx, main_character['name'])
        image_clip = ImageClip(image_path)
    
        page.elem(
            image_clip
            .with_duration(move_in_duration)
            .with_effects([
                vfx.SlideIn(1, side='left'),
                Swing(-5, 5, 1),
            ]),
            start=started_at,
            duration=move_in_duration,
        )
    
        movein_sound = 'magic-ascend-1-259521.mp3'
        move_to_pos_sound = 'funny-pipe-effect-229173.mp3'
        yay_sound = 'short-success-sound-glockenspiel-treasure-video-game-6346.mp3'
    
        page.elem(
            AudioFileClip(get_asset_path(movein_sound)),
            start=started_at,
            duration=3,
        )
    
        image_pos = int(main_character['pos'][0]), int(main_character['pos'][1])
        image_size = int(main_character['size'][0]), int(main_character['size'][1])
        init_pos = anchor_center(0, 0, CANVA_WIDTH, CANVA_HEIGHT, image_clip.w, image_clip.h)
    
        page.elem(
            AudioFileClip(get_asset_path(move_to_pos_sound)),
            start=revealed_at,
            duration=2,
        )
    
        page.elem(
            image_clip
            .with_duration(move_to_duration)
            .with_effects([
                UniformMotion(init_pos, image_pos),
                UniformScale(1.0, image_size[0] / image_clip.w),
            ])
            ,
            start=revealed_at,
            duration=move_to_duration,
        )
    
        confetti = VideoFileClip(
            get_asset_path('Confetti.gif'),
            has_mask=True,
        )
        page.elem(
            confetti
            .with_start(congrats_at)
            .with_position(anchor_center(
                image_pos[0], image_pos[1],
                main_character['size'][0], main_character['size'][1],
                confetti.w, confetti.h,
            )),
            start=congrats_at,
            duration=congrats_duration,
        )
        page.elem(
            image_clip
            .with_duration(2)
            .with_position(image_pos)
            .resized(main_character['size']),
            start=congrats_at,
            duration=congrats_duration,
        )
        page.elem(
            AudioFileClip(get_asset_path(yay_sound)),
            start=congrats_at,
            duration=2,
        )
    
        page.elem(
            TextClip(
                text=main_character['name'],
                font_size=200,
                color='white',
                stroke_color='black',
                stroke_width=5,
                margin=tuple([50, 50]),
                font='Arial',
            )
            .with_position(('center', CANVA_HEIGHT - 400))
            .with_duration(2)
            .with_effects([
                vfx.CrossFadeIn(0.5),
            ]),
            start=3,
            duration=2,
        )
        voiceover_mp3 = make_voiceover(main_character['name'], VOICEOVER_MODEL)
        voiceover_clip = AudioFileClip(voiceover_mp3)
        page.elem(
            voiceover_clip,
            start=3,
            duration=voiceover_clip.duration,
        )

    output = config['output'].replace('.mp4', f'_{idx+1}.mp4')
    movie.render(output, fps=FPS)

def generate_config(args, config):
    files = sorted(os.listdir(args.input_dir))
    files = [f for f in files if f.endswith('.png')]
    data = {}
    for file in files:
        if 'background' in file.lower():
            data['background'] = file
            continue
        if 'animals' not in data:
            data['animals'] = []
        data['animals'].append({
            'id': os.path.basename(file).replace('.png', '')[:2],
            'name': os.path.basename(file).replace('.png', '')[3:].title(),
            'file': file,
            'pos': [0, 0],
            'size': [0, 0],
        })
    data['animals'].sort(key=lambda x: int(x['id']))
    images = [f['file'] for f in data['animals']]
    placements = distribute_images([
        Image.open(args.input_dir + '/' + f) for f in images
    ], [CANVA_WIDTH, CANVA_HEIGHT])
    print(placements)
    for i, animal in enumerate(data['animals']):
        x, y, scale = placements[i]
        animal['scale'] = scale
        animal['pos'] = x, y
        image = Image.open(args.input_dir + '/' + animal['file'])
        animal['size'] = image.size[0] * scale, image.size[1] * scale

        rembg_path = args.input_dir + '/build/' + animal['file']
        black_path = args.input_dir + '/build/' + animal['file'].replace('.png', '_black.png')

        if not os.path.exists(rembg_path):
            rembg_image = rembg(image, model='isnet-anime')
            rembg_image.save(rembg_path)

        if not os.path.exists(black_path):
            mask_alpha(rembg_path, black_path,
                translucency_mask_color=(0, 0, 0),
                transparent_mask_color=(0, 0, 0, 0),
                opacity_mask_color=(0, 0, 0),
            )


    with open(config, 'w') as f:
        json.dump(data, f, indent=2)
        print('Config file generated at', config)

def main():
    args = parse_args()
    config = f'{args.input_dir}/config.json'
    if not os.path.exists(config):
        print('Config file not found, generating one')
        generate_config(args, config)

    with open(config) as f:
        config = json.load(f)

    config['input_dir'] = args.input_dir
    config['output'] = args.output

    for i in range(len(config['animals'])):
        if i > 11:
            make_page(config, i)


if __name__ == '__main__':
    main()

