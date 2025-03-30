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
    parser.add_argument('--output', type=str, help='Output video file', default='/tmp/balloonpop.mp4')
    parser.add_argument('--compile', action='store_true', help='Compile the video')

    args = parser.parse_args()
    return args


def make_page(config, idx):
    balloons_assets = config.get('balloons_assets') or [
            'BalloonYellow.png',
            'BalloonRed.png',
            'BalloonGreen.png',
            'BalloonBlue.png',
    ]
    congrats_asset = config.get('congrats_asset') or 'Confetti2.gif'
    congrats_duration = config.get('congrats_duration') or 1.2
    balloons_count = config.get('balloons_count') or 40
    intro_duration = config['objects'][idx].get('intro_duration') or 2
    pop_duration = config['objects'][idx].get('pop_duration') or 8
    outtro_duration = config['objects'][idx].get('outtro_duration') or 4
    total_duration = intro_duration + pop_duration + outtro_duration
    started_at = 0
    started_popping_at = intro_duration

    with movie.page(duration=total_duration, background='#ffffff') as page:
        bg = config['objects'][idx].get('background')
        if bg:
            bg_clip = ImageClip(config['input_dir'] + '/' + bg)
            page.elem(
                (bg_clip.with_position('center')
                .resized((CANVA_WIDTH, CANVA_HEIGHT))),
                start=0,
                duration=total_duration,
            )

        obj_clip = ImageClip(config['input_dir'] + '/' + config['objects'][idx]['object'])
        w, h = obj_clip.w, obj_clip.h
        if 'object_scale' in config['objects'][idx]:
            obj_clip = obj_clip.resized(config['objects'][idx]['object_scale'])
            w, h = obj_clip.w, obj_clip.h
        page.elem(
            obj_clip
            .with_position(anchor_center(0, 0, CANVA_WIDTH, CANVA_HEIGHT, w, h))
            .with_effects([
                SquishBounceEffect(),
            ])
        )
    
        confetti = VideoFileClip(
            get_asset_path(congrats_asset),
            has_mask=True,
        ).resized(0.5)
    
        for i in range(balloons_count):
            balloon_asset = balloons_assets[i % len(balloons_assets)]
            angle = np.random.uniform(0, 5.0)
            scale = 30
            margin = 100
            balloon_duration = started_popping_at + pop_duration/balloons_count * (balloons_count-i)
    
            if balloon_asset.endswith('.png'):
                balloon = ImageClip(get_asset_path(balloon_asset))
            else:
                balloon = (
                    VideoFileClip(get_asset_path(balloon_asset), has_mask=True)
                    .with_effects([
                        vfx.Loop(duration=balloon_duration),
                    ])
                )
    
            balloon = balloon.resized(config.get('balloons_scale') or 0.8)
    
            balloon_pos = (
                np.random.randint(margin, CANVA_WIDTH-margin-balloon.w),
                np.random.randint(margin, CANVA_HEIGHT-margin-balloon.h),
            )
    
    
            page.elem(
                balloon
                .with_position(balloon_pos)
                .with_effects([
                    FloatAnimation(scale=scale),
                    Swing(
                        -1.0*angle,
                        angle,
                        1
                    )
                ]),
                start=0,
                duration=balloon_duration,
            )
    
            confetti_pos = anchor_center(
                    balloon_pos[0], balloon_pos[1],
                    balloon.w, balloon.h,
                    confetti.w, confetti.h,
            )
            confetti_pos = (
                max(0, confetti_pos[0]),
                max(0, confetti_pos[1]),
            )
            confetti_start = balloon_duration
            page.elem(
                confetti
                .resized(config.get('congrats_scale') or 0.5)
                .with_position(confetti_pos),
                start=confetti_start,
                duration=congrats_duration,
            )


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
        make_page(config, i)

    if args.compile:
        movie.render(args.output, fps=FPS)
    else:
        movie.render_each_page(args.output, fps=FPS)


if __name__ == "__main__":
    main()
