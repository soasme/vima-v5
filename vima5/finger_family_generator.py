"""
Example config:

[
  {
    "type": "finger",
    "object": "w01.png",
    "background": "c01a.png",
    "finger": 0,
    "duration": 2.5,
    "prev_background": "intro.png",
    "text": "ABC"
  },
  {
    "type": "object",
    "object": "w01.png",
    "background": "c01b.png",
    "finger": 0,
    "duration": 3.1,
    "text": "XYZ"
  }
]
"""

import numpy as np
import math
import json
import argparse
from PIL import Image, ImageOps, ImageFilter
from moviepy import *
from vima5.canva import *
from vima5.utils import make_voiceover, get_asset_path
from types import SimpleNamespace

DEFAULT_CONFIG = {
}

CANVA_WIDTH = 1920
CANVA_HEIGHT = 1080
HAND_ANCHORS = [
        (335,477),
        (474,210),
        (610,149),
        (749,215),
        (919,418),
]

def parse_args():
    parser = argparse.ArgumentParser(description='Finger Family')
    parser.add_argument('--input-dir', type=str, help='Input Directory having all the images and config')
    parser.add_argument('--output', type=str, help='Output video file', default='/tmp/output.mp4')

    args = parser.parse_args()
    return args


def make_object_page(context, duration, obj, background,  prev_background=None, text=''):
    add_page(
        duration=duration,
        background='#ffffff',
    )

    bg_slide_in = 0.5

    # XXX: This should be a subclip of last bg_slide_in seconds of the previous page.
    if prev_background:
        add_elem(
            ImageClip(prev_background)
            .with_effects([
                vfx.Resize((CANVA_WIDTH, CANVA_HEIGHT)),
            ])
        )

    add_elem(
        ImageClip(background)
        .with_effects([
            vfx.Resize((CANVA_WIDTH, CANVA_HEIGHT)),
            vfx.SlideIn(bg_slide_in, side='right'),
        ])
    )

    obj_clip = ImageClip(obj).with_effects([
        vfx.Resize(0.8), # Assume using Midjourney 16:9 default size.
    ])

    margin_w, margin_h = 0, 50
    add_elem(
        obj_clip
        .with_duration(duration-bg_slide_in)
        .with_position((
            CANVA_WIDTH/2-obj_clip.w/2,
            CANVA_HEIGHT-obj_clip.h-margin_h
        ))
        .with_effects([
            vfx.CrossFadeIn(bg_slide_in),
            FloatAnimation('y')
        ]),
        start=bg_slide_in,
    )

    if text:
        text_clip = TextClip(
            font='Arial',
            text=text,
            font_size=140,
            color='#ffffff',
            stroke_color='#000000',
            stroke_width=5,
            margin=(10, 10),
        )
        add_elem(
            text_clip
            .with_duration(duration)
            .with_position(('center', 100))
            .with_effects([
                vfx.CrossFadeIn(1),
            ])
        )



def make_finger_page(context, duration, obj, hand, finger, background, prev_background=None, text=''):
    add_page(
        duration=duration,
        background='#ffffff',
    )

    bg_slide_in = 0.5

    if prev_background:
        add_elem(
            ImageClip(prev_background)
            .with_effects([
                vfx.Resize((CANVA_WIDTH, CANVA_HEIGHT)),
            ])
        )

    add_elem(
        ImageClip(background)
        .with_effects([
            vfx.Resize((CANVA_WIDTH, CANVA_HEIGHT)),
            vfx.SlideIn(bg_slide_in, side='right'),
        ])
    )

    hand = Image.open(hand)
    obj = Image.open(obj)
    obj = obj.resize((int(obj.width * 0.3), int(obj.height * 0.3)))
    hand_anchor = HAND_ANCHORS[finger]
    point = (
        int(hand_anchor[0] - obj.size[0]/2),
        int(hand_anchor[1] - obj.size[1]/2),
    )
    paste_non_transparent(obj, hand, point)
    hand_clip = ImageClip(np.array(hand))
    hand_clip = hand_clip.with_position(( 346, 170 ))
    add_elem(
        hand_clip.with_effects([
            Swing(
                start_angle=-15,
                end_angle=15,
                period=1,
                center=(981, 1044),
            )
        ])
    )

    if text:
        text_clip = TextClip(
            font='Arial',
            text=text,
            font_size=140,
            color='#ffffff',
            stroke_color='#000000',
            stroke_width=5,
            margin=(10, 10),
        )
        add_elem(
            text_clip
            .with_duration(duration)
            .with_position(('center', 100))
            .with_effects([
                vfx.CrossFadeIn(1),
            ])
        )


def main():
    args = parse_args()
    with open(f'{args.input_dir}/config.json') as f:
        pages = json.load(f)
    config = {}
    for index, page in enumerate(pages):
        if page['type'] == 'object':
            make_object_page(
                config,
                page['duration'],
                obj=f"{args.input_dir}/{page['object']}",
                background=f"{args.input_dir}/{page['background']}",
                prev_background=(
                    f"{args.input_dir}/{page.get('prev_background')}"
                    if page.get('prev_background') else
                    f"{args.input_dir}/{pages[index-1]['background']}"
                ),
                text=page.get('text', ''),
            )
        elif page['type'] == 'finger':
            make_finger_page(
                config,
                page['duration'],
                obj=f"{args.input_dir}/{page['object']}",
                hand=get_asset_path('Hand.png'),
                finger=page['finger'],
                background=f"{args.input_dir}/{page['background']}",
                prev_background=(
                    f"{args.input_dir}/{page.get('prev_background')}"
                    if page.get('prev_background')
                    else
                    f"{args.input_dir}/{pages[index-1]['background']}"
                ),
                text=page.get('text', ''),
            )
    render_each_page(args.output, fps=30)

if __name__ == '__main__':
    main()
