import argparse
import logging
import csv
import subprocess
import os
import math
import json
import sys
import random
import multiprocessing
from tqdm import tqdm
from moviepy import *
import whisper_timestamped as whisper
from tempfile import NamedTemporaryFile
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from elevenlabs.client import ElevenLabs
from elevenlabs import save as save_voiceover

logger = logging.getLogger(__name__)

elevenlabs_api_key = os.environ.get('ELEVENLABS_API_KEY') or ''
VOICE = 'TtRFBnwQdH1k01vR0hMz'
TTS_MODEL = 'eleven_flash_v2_5'

ANSWER_HANDLES = {1: 'A', 2: 'B', 3: 'C'}
CONGRATS = [
    'Congratulations!',
    'Well done!',
    'You are amazing!',
    'You are a genius!',
    'You are a star!',
    'You are a champion!',
    'You are a winner!',
    'You are a superhero!',
    'You are a legend!',
    'Great job!',
    'Excellent!',
    'Fantastic!',
    'Brilliant!',
    'Awesome!',
    'Outstanding!',
    'Impressive!',
    'Incredible!',
    'Unbelievable!',
    'Remarkable!',
    'Extraordinary!',
    "What a performance!",
    "What an achievement!",
    "What a success!",
    "What a victory!",
    "What a triumph!",
    "What a breakthrough!",
    "What a milestone!",
    "Wow, you're on fire!",
    "Wow, you're on a roll!",
    "Wow, you're on a winning streak!",
    "Wow, you're on a winning spree!",
    "Wow, you're on a winning run!",
]

def get_asset_path(path):
    if not os.environ.get('ASSET_PATH'):
        raise Exception('ASSET_PATH not set')
    search_paths = os.environ['ASSET_PATH'].split(',')
    for search_path in search_paths:
        print(search_path)
        if Path(search_path).joinpath(path).exists():
            return Path(search_path).joinpath(path)
    raise Exception(f'Asset not found: {path}')

def get_build_path(path):
    if os.environ.get('BUILD_PATH'):
        return Path(os.environ['BUILD_PATH']) / path
    if os.environ.get('ASSET_PATH'):
        search_paths = os.environ['ASSET_PATH'].split(',')
        last_search_path = search_paths[-1]
        return Path(last_search_path).joinpath('build') / path

def rounded_rectangle_image(size, color='white', radius=0):
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, size[0], size[1]), fill=color, radius=radius)
    return image

def round_corners(image, radius):
  """
  Adds rounded corners to an image.

  Args:
      image: The image to modify (a PIL Image object).
      radius: The radius of the rounded corners.

  Returns:
      A PIL Image object with rounded corners.
  """

  mask = Image.new('L', image.size, 0)  # Create a black mask
  draw = ImageDraw.Draw(mask)

  # Draw four white rectangles to cover the corners outside the rounded area
  draw.rectangle([(radius, 0), (image.size[0] - radius, image.size[1])], fill=255)
  draw.rectangle([(0, radius), (image.size[0], image.size[1] - radius)], fill=255)

  # Draw four white circles at the corners for the rounded effect
  draw.ellipse([(0, 0), (2 * radius, 2 * radius)], fill=255)  # Top-left
  draw.ellipse([(image.size[0] - 2 * radius, 0), (image.size[0], 2 * radius)], fill=255)  # Top-right
  draw.ellipse([(0, image.size[1] - 2 * radius), (2 * radius, image.size[1])], fill=255)  # Bottom-left
  draw.ellipse([(image.size[0] - 2 * radius, image.size[1] - 2 * radius), (image.size[0], image.size[1])], fill=255)  # Bottom-right

  # Ensure the image is in RGBA format to handle transparency
  image = image.convert("RGBA")
  image.putalpha(mask)

  return image

def extract_alpha(image):
    """Extract the alpha channel from an image."""
    return image.split()[-1]

def create_shadow_from_alpha( alpha, blur_radius):
    """Create a shadow based on a blurred version of the alpha channel."""
    alpha_blur = alpha.filter(ImageFilter.BoxBlur(blur_radius))
    shadow = Image.new(mode="RGB", size=alpha_blur.size)
    # set transparency to 10%
    shadow.putalpha(25)
    return shadow

def composite_images( bg, fg, shadow):
    """Composite the shadow and foreground onto the background."""
    bg.paste(shadow, ( 0 , 0), shadow)
    bg.paste(fg, ( 0 , 0), fg)
    return bg

ANSWER_HANDLES = {1: 'A', 2: 'B', 3: 'C'}
CONGRATS = [
    'Congratulations!',
    'Well done!',
    'You are amazing!',
    'You are a genius!',
    'You are a star!',
    'You are a champion!',
    'You are a winner!',
    'You are a superhero!',
    'You are a legend!',
    'Great job!',
    'Excellent!',
    'Fantastic!',
    'Brilliant!',
    'Awesome!',
    'Outstanding!',
    'Impressive!',
    'Incredible!',
    'Unbelievable!',
    'Remarkable!',
    'Extraordinary!',
    "What a performance!",
    "What an achievement!",
    "What a success!",
    "What a victory!",
    "What a triumph!",
    "What a breakthrough!",
    "What a milestone!",
    "Wow, you're on fire!",
    "Wow, you're on a roll!",
    "Wow, you're on a winning streak!",
    "Wow, you're on a winning spree!",
    "Wow, you're on a winning run!",
]


def make_que_voiceover_txt(elem):
    line = []
    line.append(f'LEVEL {elem["Level"]}. ')
    line.append('... ' )
    line.append('Guess who I am?')
    line.append('... ' )
    line.append(f'A. {elem["Answers"][0]}.')
    line.append('... ' )
    line.append(f'B. {elem["Answers"][1]}.')
    line.append('... ' )
    line.append(f'C. {elem["Answers"][2]}.')
    line.append('... ' )
    return ' '.join(line)

def make_ans_voiceover_txt(elem):
    answer = ANSWER_HANDLES[elem['Answers'].index(elem['CorrectAnswer']) + 1]
    fusion1 = elem['Explain'][0]
    fusion2 = elem['Explain'][1]
    congrats = random.choice(CONGRATS)
    line = []
    line.append(congrats)
    line.append(f'The answer is {answer}, {elem["CorrectAnswer"]}. ')
    line.append(f"It's the fusion of {fusion1} and {fusion2}. ")
    return ' '.join(line)

def make_voiceover(txt, filename):
    if os.path.exists(filename):
        return
    client = ElevenLabs()
    audio = client.generate(text=txt, voice=VOICE, model=TTS_MODEL)
    save_voiceover(audio, filename)

def make_que_voiceover(elem):
    level = elem['Level']
    filename = get_build_path(f"LevelQue_{level}.mp3")
    txt = make_que_voiceover_txt(elem)
    make_voiceover(txt, filename)

def make_ans_voiceover(elem):
    level = elem['Level']
    filename = get_build_path(f"LevelAns_{level}.mp3")
    txt = make_ans_voiceover_txt(elem)
    make_voiceover(txt, filename)

def make_all_voiceovers(data):
    # Optimize: cache A. B. C. congrats. The answer is A/B/C.  Guess who I am.
    for elem in tqdm(data):
        make_que_voiceover(elem)
        make_ans_voiceover(elem)

def make_level(data):
    logger.info(f'Making level {data["Level"]}')

    level = data['Level']

    if 'BackgroundImages' in data:
        bg_path = get_asset_path(random.choice(data['BackgroundImages']))
    else:
        bg_path = get_asset_path(data['Background'])

    image_path = get_asset_path(data['Image'])
    logo_path = get_asset_path(data['Logo'])
    level_intro_path = get_asset_path(data['LevelIntro'])
    subscribe_path = get_asset_path(data['Subscribe'])
    intro_duration = 4 # set later based on intro.mp4
    que_duration = 0 # set later based on voiceover
    timer_duration = data['TimerDuration']
    reveal_duration = data['RevealDuration']
    ans_duration = 0 # set later based on voiceover
    level_intro_sound = data['LevelIntroSound']
    timer_sound = data['TimerSound']
    que_voiceover = data['QueVoiceover']
    ans_voiceover = data['AnsVoiceover']
    question = data['Question']
    voiceover_bg = data['VoiceoverBackground']

    output = get_build_path(f'level_{level}.mp4')
    if os.path.exists(output):
        logger.info(f'Level {level} already exists: {output}')
        return

    # Move level intro out. Can concat videos in final stage.
    level_intro_clip = VideoFileClip(level_intro_path)

    level_number_clip = TextClip(
        font='./assets/04b_30.ttf',
        text=f'{level}/20',
        font_size=140,
        color='#d02d83',
    ).with_duration(1.5).with_start(2.5).with_effects([vfx.CrossFadeIn(0.1)]).with_position(('center', 600))

    # TODO: should use relative position
    level_number_shadow_clip = TextClip(
        font='./assets/04b_30.ttf',
        text=f'{level}/20',
        font_size=144,
        color='#000000',
    ).with_duration(1.5).with_start(2.5).with_effects([vfx.CrossFadeIn(0.1)]).with_position(('center', 600))

    intro_duration = level_intro_clip.duration

    que_audio_clip = AudioFileClip(get_asset_path(que_voiceover))
    que_duration = que_audio_clip.duration

    ans_audio_clip = AudioFileClip(get_asset_path(ans_voiceover))
    ans_duration = ans_audio_clip.duration + 0.5

    world_duration = math.ceil(que_duration + timer_duration + reveal_duration  + ans_duration)
    total_duration = intro_duration + world_duration

    # Display background
    background_clip = ImageClip(bg_path).with_duration(world_duration).with_start(level_intro_clip.duration)
    background_clip = background_clip.with_effects([vfx.Resize((1920, 1080))])

    # Display logo
    logo_clip = ImageClip(logo_path).with_duration(world_duration).with_start(level_intro_clip.duration).with_effects([vfx.CrossFadeIn(0.5)])
    logo_margin = (10, 10)
    logo_clip = logo_clip.with_position((logo_margin[0], 1080-logo_clip.size[1]-logo_margin[1]))

    # Display subscribe
    subscribe_margin = (10, 30)
    subscribe_clip = (VideoFileClip(subscribe_path, has_mask=True).with_start(level_intro_clip.duration).with_effects([vfx.CrossFadeIn(0.5)]))
    subscribe_clip = subscribe_clip.with_position((
        logo_clip.size[0]+logo_margin[0]+subscribe_margin[0],
        1080-subscribe_clip.size[1]-subscribe_margin[1]
    ))

    # Display Image
    image = Image.open(image_path)
    rounded_image = round_corners(image, radius=50)
    image_clip = ImageClip(np.array(rounded_image)).with_duration(world_duration).with_start(intro_duration)
    image_clip = image_clip.with_effects([vfx.Resize(lambda t: (710 - 10 * math.sin(t), 710 - 10 * math.sin(t)))])
    image_clip_margin_bottom = 100
    image_clip_margin_left = 100
    image_clip = image_clip.with_position(lambda t: (
        image_clip_margin_left,
        1080-image_clip.size[1]-subscribe_margin[1]-subscribe_clip.size[1]-image_clip_margin_bottom + 10 * math.sin(3 * t)
    ))
    image_clip = image_clip.with_effects([
        vfx.CrossFadeIn(0.5),
    ])

    # Display Quiz Quesion
    txt_margin = (0, 200, 150, 0)
    quiz_txt_bg_margin = (0, 200, 200, 0)

    quiz_txt_bg_clip = (
        ImageClip(
            np.array(rounded_rectangle_image((
                960,
                750,
            ), color='white', radius=50))
        )
        .with_duration(world_duration)
        .with_start(intro_duration)
        .with_position((
            1920-image_clip_margin_left-image_clip.size[0]-quiz_txt_bg_margin[2],
            1080-image_clip.size[1]-subscribe_margin[1]-subscribe_clip.size[1]-image_clip_margin_bottom
        ))
    )

    question_clip = (
        TextClip(
            font='./assets/04b_30.ttf',
            text=question,
            font_size=70,
            color='#040273',
        )
        .with_duration(que_duration + timer_duration)
        .with_start(intro_duration)
        .with_position((
            1920-image_clip_margin_left-image_clip.size[0]-txt_margin[2],
            1080-image_clip.size[1]-subscribe_margin[1]-subscribe_clip.size[1]-image_clip_margin_bottom+txt_margin[1]
        ))
        .with_effects([vfx.CrossFadeIn(0.5)])
    )

    answers_clip = []
    for index, answer in enumerate(data['Answers']):
        txt = f'{chr(65+index)}. {answer}'
        answer_clip = (
            TextClip(
                font='./assets/04b_30.ttf',
                text=txt,
                font_size=50,
                color='#040273',
            )
            .with_duration(que_duration + timer_duration)
            .with_start(intro_duration)
            .with_position((
                1920-image_clip_margin_left-image_clip.size[0]-txt_margin[2],
                1080-image_clip.size[1]-subscribe_margin[1]-subscribe_clip.size[1]-image_clip_margin_bottom + 100 * (index+1) + txt_margin[1]
            ))
            .with_effects([vfx.CrossFadeIn(0.5)])
        )
        answers_clip.append(answer_clip)

        if answer != data['CorrectAnswer']:
            continue

        correct_blink_clip = (
            TextClip(
                font='./assets/04b_30.ttf',
                text=f'{chr(65+index)}. {data["CorrectAnswer"]}',
                font_size=50,
                color='#040273',
            )
            .with_duration(reveal_duration)
            .with_start(intro_duration + que_duration + timer_duration)
            .with_position((
                1920-image_clip_margin_left-image_clip.size[0]-txt_margin[2],
                1080-image_clip.size[1]-subscribe_margin[1]-subscribe_clip.size[1]-image_clip_margin_bottom + 100 * (index+1) + txt_margin[1]
            ))
            .with_effects([vfx.Blink(0.1, 0.1)])
        )
        correct_moveup_clip = (
            TextClip(
                font='./assets/04b_30.ttf',
                text=f'{chr(65+index)}. {data["CorrectAnswer"]}',
                font_size=70,
                color='#040273',
            )
            .with_duration(ans_duration)
            .with_start(intro_duration + que_duration + timer_duration + reveal_duration)
            .with_position((
                1920-image_clip_margin_left-image_clip.size[0]-txt_margin[2],
                1080-image_clip.size[1]-subscribe_margin[1]-subscribe_clip.size[1]-image_clip_margin_bottom+txt_margin[1]
            ))
        )

        answers_clip.append(correct_blink_clip)
        answers_clip.append(correct_moveup_clip)

        for index, fusion_word in enumerate(data['Explain']):
            answer_clip = (
                TextClip(
                    font='./assets/04b_30.ttf',
                    text=fusion_word,
                    font_size=70,
                    color='#040273',
                )
                .with_duration(ans_duration)
                .with_start(intro_duration + que_duration + timer_duration + reveal_duration)
                .with_position((
                    1920-image_clip_margin_left-image_clip.size[0]-txt_margin[2],
                    1080-image_clip.size[1]-subscribe_margin[1]-subscribe_clip.size[1]-image_clip_margin_bottom + 100 * (index+1) + txt_margin[1]
                ))
                .with_effects([vfx.CrossFadeIn(0.5)])
            )

            answers_clip.append(answer_clip)


    timer_clips = []
    for i in range(0, 11):
        timer_clip = (TextClip(
                font='./assets/04b_30.ttf',
                text=f'{10-i}',
                font_size=140,
                color='white',
            )
            .with_duration(1)
            .with_start(que_duration + level_intro_clip.duration + i))

        timer_clip = timer_clip.with_position((
                1920 - timer_clip.size[0] - 10,
                1080 - timer_clip.size[1] - 10
        ))

        timer_clips.append(timer_clip)



    clips = []
    clips.extend([level_intro_clip, level_number_shadow_clip, level_number_clip])
    clips.extend([background_clip, logo_clip, subscribe_clip, image_clip, quiz_txt_bg_clip, question_clip] + answers_clip + timer_clips)

    level_intro_sound_clip = AudioFileClip(get_asset_path(level_intro_sound))
    que_audio_clip = que_audio_clip.with_start(intro_duration)
    que_bg_clip = AudioFileClip(get_asset_path(voiceover_bg)).with_start(intro_duration).with_duration(que_duration)
    timer_sound_clip = AudioFileClip(get_asset_path(timer_sound)).with_start(level_intro_clip.duration + que_duration)
    ans_audio_clip = ans_audio_clip.with_start(intro_duration + que_duration + timer_duration + reveal_duration)
    ans_bg_clip = AudioFileClip(get_asset_path(voiceover_bg)).with_start(intro_duration + que_duration + timer_duration + reveal_duration).with_duration(ans_duration)
    audios = [
        level_intro_sound_clip,
        que_audio_clip,
        que_bg_clip,
        timer_sound_clip,
        ans_audio_clip,
        ans_bg_clip,
    ]

    final_clip = CompositeVideoClip(clips)
    final_clip = final_clip.with_audio(CompositeAudioClip(audios))

    # Write video file
    with NamedTemporaryFile(suffix='.mp4') as fp:
        final_clip.write_videofile(fp.name, fps=24, codec="libx264", temp_audiofile="temp-audio.m4a", remove_temp=True, audio_codec="aac", threads=4)
        fp.seek(0)
        data = fp.read()

    with open(get_build_path(f'level_{level}.mp4'), 'wb') as f:
        f.write(data)

def load_cfg():
    with open(get_asset_path('config.json')) as f:
        return json.load(f)

def make_all_levels(data, args):
    cfg = load_cfg()
    level_cfgs = []
    for level in data:
        if args.level is not None and level['Level'] != args.level:
            continue
        level_cfg = dict(level)
        for k, v in cfg.items():
            if isinstance(v, str):
                level_cfg[k] = v.format(**level)
            else:
                level_cfg[k] = v
        level_cfgs.append(level_cfg)
        print(level_cfg)

    for level_cfg in level_cfgs:
        if args.shorts:
            make_level_shorts(level_cfg)
        else:
            make_level(level_cfg)

    if args.level is not None and args.concat:
        concat_levels(cfg)


def concat_levels(data):
    intros = [get_asset_path(v) for v in data.get('Intro', [])] #["Intro.mp4"]
    outtros = [get_asset_path(v) for v in data.get('Outtro', [])] #["Outtro.mp4"]
    videos = intros + [get_build_path(('Level_%d.mp4' % (i+1))) for i in range(20)] + outtros
    #videos = [build_path / video for video in videos]
    final = get_build_path('final.mp4')
    videolist = get_build_path('videolist.txt')

    if os.path.exists(final):
        os.remove(final)


    with open(videolist, 'w') as f:
        content = '\n'.join([
            f"file '{video}'" for video in videos
        ])
        f.write(content)

    clips = [VideoFileClip(video) for video in videos]
    final_clip = concatenate_videoclips(clips)
    final_clip.write_videofile(final, fps=24, codec="libx264", temp_audiofile="temp-audio.m4a", remove_temp=True, audio_codec="aac", threads=6)

def shuffle_levels(path):
    with open(path) as f:
        data = json.load(f)
    for elem in data:
        random.shuffle(elem['Answers'])
    with open(path, 'w') as f:
        f.write(json.dumps(data, indent=2))



def make_level_images(data):
    prompts = [e['ImagePrompt'] for e in data if e['Level'] > 1]
    # TODO
    

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    if not os.path.exists(get_build_path('')):
        os.makedirs(get_build_path(''))

    parser = argparse.ArgumentParser(description='WFQ Helper')
    parser.add_argument('command', type=str, help='Command to run')
    parser.add_argument('--config', type=str, help='Path to config file')
    parser.add_argument('--levels', type=str, help='Path to levels file')
    parser.add_argument('--outdir', default='./build', type=str, help='Output path')
    parser.add_argument('--level', type=int, help='Level to generate')
    parser.add_argument('--concat', action='store_true', help='Concat levels')
    parser.add_argument('--shorts', action='store_true', help='Concat levels')
    args = parser.parse_args()

    if args.command == 'levelimages': # TODO
        make_level_images(json.load(sys.stdin))
    elif args.command == 'level': # for testing
        make_level(json.load(sys.stdin))
    elif args.command == 'quevoiceover': # for testing
        make_que_voiceover(json.load(sys.stdin))
    elif args.command == 'ansvoiceover': # for testing
        make_ans_voiceover(json.load(sys.stdin))

    elif args.command == "shufflelevels":
        shuffle_levels(args.levels)
    elif args.command == 'voiceovers':
        with open(args.levels) as f:
            levels = json.load(f)
        make_all_voiceovers(levels)
    elif args.command == 'alllevels':
        with open(args.levels) as f:
            levels = json.load(f)
        make_all_levels(levels, args) # use levels.json
        if args.concat:
            with open(args.config) as f:
                config = json.load(f)
            concat_levels(config)
    elif args.command == 'concatlevels':
        with open(args.config) as f:
            config = json.load(f)
        concat_levels(args.config) # use config.json
    elif args.command == 'video': # all at once.
        with open(args.levels) as f:
            levels = json.load(f)
        with open(args.config) as f:
            config = json.load(f)
        shuffle_levels(args.levels)
        make_all_voiceovers(levels)

    # TODO: download images from midjourney.
    # TODO: add api to call chatgpt to generate questions and answers in json format.
    # TODO: add readme on how to use it.
    # TODO: support loading resources from remote url (like google drive).
    # TODO: make thumbnail
    # TODO: make shorts: faster pace: 5 seconds per question.
    # TODO: optimize elevenlabs to reuse some voiceovers.
