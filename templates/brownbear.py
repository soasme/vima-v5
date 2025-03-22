import os
import numpy as np
import math
import json
import argparse
from PIL import Image, ImageOps, ImageFilter
from moviepy import *
from vima5.canva import *
from vima5.utils import make_voiceover, get_asset_path, get_build_path
from types import SimpleNamespace

CANVA_WIDTH = 1920
CANVA_HEIGHT = 1080
#FPS = 12
FPS = 60

movie = Movie()

def parse_args():
    parser = argparse.ArgumentParser(description='Finger Family')
    parser.add_argument('--input-dir', type=str, help='Input Directory having all the images and config')
    parser.add_argument('--output', type=str, help='Output video file', default='/tmp/brownbear.mp4')
    parser.add_argument('--compile', action='store_true', help='Compile the video')

    args = parser.parse_args()
    return args

def calculate_position(direction, type):
    if direction == 'left' and type == 'question':
        return (-CANVA_WIDTH/2, 0), (0, 0)
    elif direction == 'right' and type == 'question':
        return (CANVA_WIDTH/2, 0), (0, 0)
    elif direction == 'left' and type == 'answer':
        return (0, 0), (-CANVA_WIDTH/2, 0)
    elif direction == 'right' and type == 'answer':
        return (0, 0), (CANVA_WIDTH/2, 0)

def get_image_clip(config, idx):
    img_path = get_asset_path(config['objects'][idx]['image'])
    img = Image.open(img_path) if idx % 2 == 0 else ImageOps.mirror(Image.open(img_path))
    clip = ImageClip(np.array(img)).resized((CANVA_WIDTH, CANVA_HEIGHT))
    return clip

def make_question(config, idx):
    total_duration = config['objects'][idx].get('question_duration') or 4
    with movie.page(duration=total_duration, background='#ffffff') as page:
        image_clip = get_image_clip(config, idx)
        page.elem(
            image_clip
            .with_position((0, 0))
            .with_duration(total_duration)
            .with_effects([
                SquishBounceEffect(frequency=1),
            ]),
            start=0,
            duration=total_duration,
        )
        page.elem(
            TextClip(
                text=config['objects'][idx]['question_text'],
                font_size=80,
                color='black',
                margin=tuple([50, 50]),
                font='Arial',
            )
            .with_position(('center', CANVA_HEIGHT - 200))
            .with_duration(total_duration)
            .with_effects([
                vfx.CrossFadeIn(0.5),
                vfx.CrossFadeOut(0.5),
            ]),
            start=0,
            duration=total_duration,
        )

def make_answer(config, idx):
    # 0 ~ 1: idx move from center to one side, idx+1 move from outside to the other side.
    # 1 ~ n-1: idx, idx+1 both squish and bounce.
    # n-1 ~ n: idxx move from one side to outside, idx+1 from the other side to center.
    # assume image size is 1920x1080 and object facing direction is always from left to right. if not facing correct, can use `Preview` to flip the image.
    # center pos: 0, 0
    # idx % 2 == 0: one side pos: -960, 0
    # idx % 2 == 1: one side pos: 960, 0
    # idx % 2 == 0: the other side pos: 960, 0
    # idx % 2 == 1: the other side pos: -960, 0
    # idx % 2 == 0: outside pos: -1920, 0
    # idx % 2 == 1: outside pos: 1920, 0
    # idx % 2 == 1: apply MirrorX() effect to image_clip
    total_duration = config['objects'][idx].get('answer_duration') or 4
    with movie.page(duration=total_duration, background='#ffffff') as page:
        image_clip = get_image_clip(config, idx)
        if 'next_image' in config['objects'][idx]:
            next_image_clip = ImageClip(
                get_asset_path(config['objects'][idx]['next_image'])
            )
        else:
            next_image_clip = get_image_clip(config, (idx + 1) % len(config['objects']))
        image_one_side_pos = (-CANVA_WIDTH/2, 0) if idx % 2 == 0 else (CANVA_WIDTH/2, 0)
        image_the_other_side_pos = (CANVA_WIDTH/2, 0) if idx % 2 == 0 else (-CANVA_WIDTH/2, 0)
        image_outside_pos = (-CANVA_WIDTH, 0) if idx % 2 == 0 else (CANVA_WIDTH, 0)
        next_image_one_side_pos = (CANVA_WIDTH/2, 0) if (idx + 1) % 2 == 0 else (-CANVA_WIDTH/2, 0)
        next_image_the_other_side_pos = (-CANVA_WIDTH/2, 0) if (idx + 1) % 2 == 0 else (CANVA_WIDTH/2, 0)
        next_image_outside_pos = (-CANVA_WIDTH, 0) if (idx + 1) % 2 == 0 else (CANVA_WIDTH, 0)
        center_pos = (0, 0)
        page.elem(
            image_clip
            .with_position(center_pos)
            .with_duration(1)
            .with_effects([
                UniformMotion(center_pos, image_one_side_pos),
            ]),
            start=0,
            duration=1,
        )
        page.elem(
            next_image_clip
            .with_position(next_image_outside_pos)
            .with_duration(1)
            .with_effects([
                UniformMotion(next_image_outside_pos, next_image_the_other_side_pos),
            ]),
            start=0,
            duration=1,
        )
        page.elem(
            image_clip
            .with_position(image_one_side_pos)
            .with_duration(total_duration-2)
            .with_effects([
                SquishBounceEffect(frequency=1),
            ]),
            start=1,
            duration=total_duration-2,
        )
        page.elem(
            next_image_clip
            .with_position(next_image_the_other_side_pos)
            .with_duration(total_duration-2)
            .with_effects([
                SquishBounceEffect(frequency=1),
            ]),
            start=1,
            duration=total_duration-2,
        )
        page.elem(
            image_clip
            .with_position(image_one_side_pos)
            .with_duration(1)
            .with_effects([
                UniformMotion(image_one_side_pos, image_outside_pos),
            ]),
            start=total_duration-1,
            duration=1,
        )
        page.elem(
            next_image_clip
            .with_position(next_image_the_other_side_pos)
            .with_duration(1)
            .with_effects([
                UniformMotion(next_image_the_other_side_pos, center_pos),
            ]),
            start=total_duration-1,
            duration=1,
        )
        page.elem(
            TextClip(
                text=config['objects'][idx]['answer_text'],
                font_size=80,
                color='black',
                margin=tuple([50, 50]),
                font='Arial',
            )
            .with_position(('center', CANVA_HEIGHT - 200))
            .with_duration(total_duration)
            .with_effects([
                vfx.CrossFadeIn(0.5),
                vfx.CrossFadeOut(0.5),
            ]),
            start=0,
            duration=total_duration,
        )
        

def make_page(config, idx):
    make_question(config, idx)
    make_answer(config, idx)

def main():
    args = parse_args()

    with open(args.input_dir + '/config.json') as f:
        config = json.load(f)

    os.environ['ASSET_PATH'] = os.environ.get('ASSET_PATH') + ',' + args.input_dir

    config['input_dir'] = args.input_dir
    config['output'] = args.output
    config['compile'] = args.compile

    build_dir = get_build_path('')
    if not os.path.exists(build_dir):
        os.makedirs(build_dir)

    for i in range(len(config['objects'])):
        if i != 7:
            continue
        make_page(config, i)

    if args.compile:
        movie.render(args.output, fps=FPS)
    else:
        movie.render_each_page(args.output, fps=FPS)


if __name__ == "__main__":
    main()
