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

from vima5.utils import mask_alpha
from vima5.utils import make_voiceover, get_asset_path
from vima5.randomplace import distribute_images
from types import SimpleNamespace

CANVA_WIDTH = 1920
CANVA_HEIGHT = 1080
#FPS = 12
FPS = 30

def parse_args():
    parser = argparse.ArgumentParser(description='Finger Family')
    parser.add_argument('--input-dir', type=str, help='Input Directory having all the images and config')
    parser.add_argument('--output', type=str, help='Output video file', default='/tmp/output.mp4')
    parser.add_argument('--compile', action='store_true', help='Compile the video')

    args = parser.parse_args()
    return args

def get_image_path(input_dir, idx, name):
    return '%s/build/%02d_%s.png' % (input_dir, idx+1, name.replace(' ', '').lower())

def get_outline_path(input_dir, idx, name):
    return '%s/build/%02d_%s_black.png' % (input_dir, idx+1, name.replace(' ', '').lower())

def add_animal_outline(input_dir, main_char_idx, outline_idx, animal):
    image_path = get_image_path(input_dir, outline_idx, animal['name'])
    outline_path = get_outline_path(input_dir, outline_idx, animal['name'])
    image_pos = animal['pos']
    image_size = animal['size']

    add_elem(
        ImageClip(outline_path if main_char_idx <= outline_idx else image_path)
        .resized(image_size)
        .with_position(image_pos),
    )

def make_page(config, idx):
    move_in_duration = 5
    move_to_duration = 3
    congrats_duration = 2
    total_duration = move_in_duration + move_to_duration + congrats_duration
    started_at = 0
    revealed_at = move_in_duration
    congrats_at = move_in_duration + move_to_duration

    add_page(
        duration=total_duration,
        background='#ffffff',
    )
    add_elem(
        ImageClip(config['input_dir'] + '/' + config['background'])
        .resized((CANVA_WIDTH, CANVA_HEIGHT))
    )

    for j, animal in enumerate(config['animals']):
        add_animal_outline(config['input_dir'], idx, j, animal)

    main_character = config['animals'][idx]
    image_clip = ImageClip(get_image_path(config['input_dir'], idx, main_character['name']))

    add_elem(
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

    add_elem(
        AudioFileClip(get_asset_path(movein_sound)),
        start=started_at,
        duration=3,
    )

    image_pos = int(main_character['pos'][0]), int(main_character['pos'][1])
    image_size = int(main_character['size'][0]), int(main_character['size'][1])
    init_pos = anchor_center(0, 0, CANVA_WIDTH, CANVA_HEIGHT, image_clip.w, image_clip.h)

    add_elem(
        AudioFileClip(get_asset_path(move_to_pos_sound)),
        start=revealed_at,
        duration=2,
    )

    add_elem(
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
    add_elem(
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
    add_elem(
        image_clip
        .with_duration(2)
        .with_position(image_pos)
        .resized(main_character['size']),
        start=congrats_at,
        duration=congrats_duration,
    )
    add_elem(
        AudioFileClip(get_asset_path(yay_sound)),
        start=congrats_at,
        duration=2,
    )

    add_elem(
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
    voiceover_mp3 = make_voiceover(main_character['name'], 'Whimsy')
    voiceover_clip = AudioFileClip(voiceover_mp3)
    add_elem(
        voiceover_clip,
        start=3,
        duration=voiceover_clip.duration,
    )

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
    placements, coverage = distribute_images(CANVA_WIDTH, CANVA_HEIGHT, len(images))
    for i, animal in enumerate(data['animals']):
        animal['pos'] = placements[i][0], placements[i][1]
        image = Image.open(args.input_dir + '/' + animal['file'])
        size = image.size
        scale = placements[i][2]
        animal['size'] = size[0] * scale, size[1] * scale

        rembg_path = args.input_dir + '/build/' + animal['file']
        black_path = args.input_dir + '/build/' + animal['file'].replace('.png', '_black.png')

        if not os.path.exists(rembg_path):
            image = Image.open(datadir + '/' + file).convert("RGBA")
            rembg_image = rembg(image, model='isnet-anime')
            rembg_image.save(rembg_path)

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

    for i in range(len(config['animals'])):
        make_page(config, i)

    render_pages('/tmp/output.mp4', fps=FPS)

if __name__ == '__main__':
    main()

