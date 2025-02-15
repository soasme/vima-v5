# Create a video clip for learning words.
# display sequence:
# [                background               ]
#      [ text              ][ highlight     ]
#      [ voiceover ][ sfx  ][ voiceover     ]
# [   background music (optional)           ]
"""
[
  {
    "background": "/path/Horn_GoatInsertHorns.png",
    "text": "Mr. Goat has three horns.\nHe has two horns on his head.\nHe inserted the other horn into his nose.",
    "highlight": "Horn",
    "text_voiceover_mp3": "auto:Whimsy",
    "highlight_voiceover_mp3": "auto:Whimsy",
    "reaction_sfx_mp3": "/path/kids-giggle-0001.mp3",
    "background_mp3": ""
  }
]
"""

import numpy as np
import math
import json
import argparse
from moviepy import *
from vima5.canva import *
from vima5.utils import make_voiceover
from types import SimpleNamespace

DEFAULT_VALUES = {
    'text_delay_seconds': 3.0,
    'text_font': 'Arial',
    'text_voiceover_mp3': '',
    'reaction_sfx_mp3': '',
    'highlight': '',
    'highlight_font': 'Arial Black',
    'highlight_color': 'red',
    'highlight_voiceover_mp3': '',
    'background_mp3': '',
}
def parse_args():
    parser = argparse.ArgumentParser(description='Gen Game Scene')
    parser.add_argument('--config', type=str, help='Config file')
    parser.add_argument('--output', type=str, help='Output video file', default='/tmp/output.mp4')
    parser.add_argument('--background', type=str, help='Path to the background image/video file')
    parser.add_argument('--text', type=str, help='Text to display')
    parser.add_argument('--text-delay-seconds', type=float, help='Delay N Seconds after the clip starts.', default=3.0)
    parser.add_argument('--text-font', type=str, help='Font to use', default='Arial')
    parser.add_argument('--text-voiceover-mp3', type=str, help='Voiceover MP3 file to play', default='')
    parser.add_argument('--reaction-sfx-mp3', type=str, help='Reaction SFX MP3 file to play', default='')
    parser.add_argument('--highlight', type=str, help='Text to highlight, use diffrent color and bold.', default='')
    parser.add_argument('--highlight-font', type=str, help='Font to use for the highlight', default='Arial Black')
    parser.add_argument('--highlight-color', type=str, help='Color to highlight the text', default='red')
    parser.add_argument('--highlight-voiceover-mp3', type=str, help='Voiceover MP3 file to play', default='')
    parser.add_argument('--background-mp3', type=str, help='Background MP3 file to play', default='')
    args = parser.parse_args()
    return args

def make_page(args):
    text_voiceover_mp3 = args.text_voiceover_mp3
    if text_voiceover_mp3.startswith('auto:'):
        voice = text_voiceover_mp3.split(':')[1]
        text_voiceover_mp3 = make_voiceover(args.text, voice)
        text_voiceover_clip = AudioFileClip(text_voiceover_mp3)
    elif text_voiceover_mp3.endswith('.mp3'):
        text_voiceover_clip = AudioFileClip(text_voiceover_mp3)
    elif text_voiceover_mp3 == '':
        text_voiceover_clip = None
    else:
        raise ValueError(f"Invalid text_voiceover_mp3: {text_voiceover_mp3}")

    highlight_voiceover_mp3 = args.highlight_voiceover_mp3
    if highlight_voiceover_mp3.startswith('auto:'):
        voice = highlight_voiceover_mp3.split(':')[1]
        highlight_voiceover_mp3 = make_voiceover(args.highlight, voice)
        highlight_voiceover_clip = AudioFileClip(highlight_voiceover_mp3)
    elif highlight_voiceover_mp3.endswith('.mp3'):
        highlight_voiceover_clip = AudioFileClip(highlight_voiceover_mp3)
    elif highlight_voiceover_mp3 == '':
        highlight_voiceover_clip = None
    else:
        raise ValueError(f"Invalid highlight_voiceover_mp3: {highlight_voiceover_mp3}")

    # XXX: read from asset library.
    reaction_sfx_clip = AudioFileClip(args.reaction_sfx_mp3) if args.reaction_sfx_mp3 else None
    bg_mp3_clip = AudioFileClip(args.background_mp3) if args.background_mp3 else None
    
    text_delay_duration = args.text_delay_seconds
    text_voiceover_duration = text_voiceover_clip.duration if text_voiceover_clip else 5
    
    reaction_sfx_duration = reaction_sfx_clip.duration if reaction_sfx_clip else 0
    
    highlight_voiceover_duration = highlight_voiceover_clip.duration if highlight_voiceover_clip else 2
    highlight_duration = round(highlight_voiceover_duration + 1.5)
    
    total_duration = (
        text_delay_duration
        + text_voiceover_duration
        + reaction_sfx_duration
        + highlight_duration
    )
    
    add_page(
        duration=total_duration,
        background='#ffffff',
    )
    
    if text_voiceover_clip:
        add_elem(
            text_voiceover_clip
            .with_effects([
                afx.MultiplyVolume(2),
            ]),
            start=args.text_delay_seconds,
            duration=text_voiceover_duration,
        )
    
    if reaction_sfx_clip:
        add_elem(
            reaction_sfx_clip,
            start=args.text_delay_seconds + text_voiceover_duration,
            duration=reaction_sfx_duration,
        )
    
    if highlight_voiceover_clip:
        add_elem(
            highlight_voiceover_clip
            .with_effects([
                afx.MultiplyVolume(2),
            ]),
            start=args.text_delay_seconds + text_voiceover_duration + reaction_sfx_duration,
            duration=highlight_voiceover_duration,
        )

    if bg_mp3_clip:
        add_elem(
            bg_mp3_clip
            .with_effects([
                afx.MultiplyVolume(0.3),
                afx.AudioLoop(duration=total_duration),
            ]),
            start=0,
            duration=total_duration,
        )

    
    if args.background.endswith('.mp4'):
        bg_clip = VideoFileClip(args.background)
        bg_duration = min(total_duration, bg_clip.duration)
        add_elem(
            bg_clip
            .with_effects([
                vfx.Resize((1920, 1080)),
            ]),
            start=0,
            duration=bg_duration,
        )
        if total_duration > bg_clip.duration:
            lastframe = bg_clip.get_frame(bg_clip.duration - 0.1)
            add_elem(
                ImageClip(lastframe)
                .with_effects([
                    vfx.Resize((1920, 1080)),
                ]),
                start=bg_duration,
                duration=total_duration - bg_duration,
            )
    else:
        add_elem(
            ImageClip(args.background)
            .with_duration(total_duration)
            .with_effects([
                vfx.Resize((1920, 1080)),
                vfx.CrossFadeIn(1),
                vfx.CrossFadeOut(0.5),
            ]),
        )
    
    add_elem(
        TextClip(
            font=args.text_font,
            text=args.text.replace('\\n', '\n'),
            font_size=50,
            color='#000000',
            stroke_color='#ffffff',
            stroke_width=10,
        )
        .with_duration(text_voiceover_duration + reaction_sfx_duration)
        .with_effects([
            vfx.CrossFadeIn(0.5),
        ])
        .with_position((100, 100)),
        start=args.text_delay_seconds,
        duration=text_voiceover_duration,
    )
    
    add_elem(
        TextClip(
            font='Arial Black',
            text=args.highlight,
            font_size=100,
            color='#000000',
            stroke_color='#ffffff',
            stroke_width=10,
        )
        .with_duration(highlight_duration)
        .with_position((100, 100)),
        start=args.text_delay_seconds + text_voiceover_duration,
        duration=reaction_sfx_duration + highlight_duration,
    )


if __name__ == '__main__':
    args = parse_args()
    if not args.config:
        make_page(args)
    else:
        with open(args.config) as f:
            config = json.loads(f.read())
        if isinstance(config, dict):
            _config = dict(DEFAULT_VALUES)
            _config.update(config)
            make_page(SimpleNamespace(**_config))
        elif isinstance(config, list):
            for c in config:
                _config = dict(DEFAULT_VALUES)
                _config.update(c)
                make_page(SimpleNamespace(**_config))
    render_pages(args.output, fps=24)
