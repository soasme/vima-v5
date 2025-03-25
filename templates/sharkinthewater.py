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
FPS = 12
FPS = 60

movie = Movie()

def parse_args():
    parser = argparse.ArgumentParser(description='Finger Family')
    parser.add_argument('--input-dir', type=str, help='Input Directory having all the images and config')
    parser.add_argument('--output', type=str, help='Output video file', default='/tmp/sharkinthewater.mp4')
    parser.add_argument('--compile', action='store_true', help='Compile the video')

    args = parser.parse_args()
    return args


def make_level(config, level):
    total_duration = 5
    level_data = config['clips'][level]
    with movie.page(duration=total_duration, background='#ffffff') as page:
        background = level_data['background']
        background_clip = ImageClip(get_asset_path(background))
        page.elem(
            background_clip
            .with_position((0, 0))
            .with_duration(total_duration)
            .resized((CANVA_WIDTH, CANVA_HEIGHT)),
            start=0,
            duration=total_duration,
        )
        baseline = level_data['spawn_baseline']
        for spawn_object in level_data['spawn_objects']:
            obj_clip = ImageClip(get_asset_path(spawn_object['image']))
            obj_clip = obj_clip.resized(spawn_object['init_scale'])
            w, h = obj_clip.size
            for idx in range(spawn_object['count']):
                obj_clip = ImageClip(get_asset_path(spawn_object['image']))
                start = (total_duration-spawn_object['duration']) / spawn_object['count'] * idx
                from_pos = (np.random.randint(0, CANVA_WIDTH - w), baseline+h*spawn_object['init_scale'])
                to_pos = (from_pos[0], CANVA_HEIGHT)
                print(from_pos, to_pos)
                page.elem(
                    obj_clip
                    .with_duration(spawn_object['duration'])
                    .with_effects([
                        UniformMotion(from_pos, to_pos),
                        UniformScale(spawn_object['init_scale'], 1.0),
                    ]),
                    start=start,
                    duration=spawn_object['duration'],
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

    make_level(config, 0)

    if args.compile:
        movie.render(args.output, fps=FPS)
    else:
        movie.render_each_page(args.output, fps=FPS)


if __name__ == "__main__":
    main()

