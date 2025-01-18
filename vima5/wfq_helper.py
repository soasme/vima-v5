import csv
import os
import math
import json
import sys
import random
import multiprocessing
from moviepy import *
import whisper_timestamped as whisper
from tempfile import NamedTemporaryFile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

asset_path = os.environ['ASSET_PATH']
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


def make_bulk_csv(data):
    rows = [
        ['Question 1', 'Question 2', 'Question 3', 'Answer', 'Correct Answer', 'Explanation', 'Explanation Source', 'Fun Fact']
    ]
    for elem in data:
        row = [
            elem['Questions'][0],
            elem['Questions'][1],
            elem['Questions'][2],
            elem['Answer'],
            ANSWER_HANDLES[elem['Questions'].index(elem['Answer']) + 1],
            elem['Explain'].split(', ')[0],
            elem['Explain'].split(', ')[1],
            elem['Fun Fact']
        ]
        rows.append(row)
    writer = csv.writer(sys.stdout)
    writer.writerows(rows)

def make_script(data):
    res = []
    for idx, elem in enumerate(data):
        answer = ANSWER_HANDLES[elem['Questions'].index(elem['Answer']) + 1]
        fusion1 = elem['Explain'].split(', ')[0]
        fusion2 = elem['Explain'].split(', ')[1]
        congrats = random.choice(CONGRATS)
        line = []
        line.append(f'LEVEL {idx + 1}. ')
        line.append('... ' )
        line.append('Guess who I am?')
        line.append('... ' )
        line.append(f'A. {elem["Questions"][0]}.')
        line.append('... ' )
        line.append(f'B. {elem["Questions"][1]}.')
        line.append('... ' )
        line.append(f'C. {elem["Questions"][2]}.')
        line.append('... ' )
        line.append(congrats)
        line.append(f'The answer is {answer}, {elem["Answer"]}. ')
        line.append(f"It's the fusion of {fusion1} and {fusion2}. ")
        res.append(' '.join(line))

    print('\n'.join(res))

def make_level(data):
    level = data['Level']
    bg_path = asset_path + data['Background']
    image_path = asset_path + data['Image']
    logo_path = asset_path + data['Logo']
    level_intro_path = asset_path + data['LevelIntro']
    subscribe_path = asset_path + data['Subscribe']
    intro_duration = 4 # set later based on intro.mp4
    que_duration = 0 # set later based on voiceover
    timer_duration = data['Duration']
    reveal_duration = data['RevealDuration']
    ans_duration = 0 # set later based on voiceover
    level_intro_sound = data['LevelIntroSound']
    timer_sound = data['TimerSound']
    que_voiceover = data['QueVoiceover']
    ans_voiceover = data['AnsVoiceover']
    question = data['Question']
    voiceover_bg = data['VoiceoverBackground']

    # Move level intro out. Can concat videos in final stage.
    level_intro_clip = VideoFileClip(level_intro_path)

    level_number_clip = TextClip(
        font='./assets/04b_30.ttf',
        text=f'{level}',
        font_size=140,
        color='#d02d83',
    ).with_duration(1.5).with_start(2.5).with_effects([vfx.CrossFadeIn(0.1)]).with_position(('center', 600))

    # TODO: should use relative position
    level_number_shadow_clip = TextClip(
        font='./assets/04b_30.ttf',
        text=f'{level}',
        font_size=144,
        color='#000000',
    ).with_duration(1.5).with_start(2.5).with_effects([vfx.CrossFadeIn(0.1)]).with_position(('center', 600))

    intro_duration = level_intro_clip.duration

    que_audio_clip = AudioFileClip(asset_path + que_voiceover)
    que_duration = que_audio_clip.duration

    ans_audio_clip = AudioFileClip(asset_path + ans_voiceover)
    ans_duration = ans_audio_clip.duration + 0.5

    # TODO: update this to the length of voiceover of questions and answers.
    duration = intro_duration + que_duration + timer_duration + reveal_duration # + explain_duration
    world_duration = que_duration + timer_duration + reveal_duration  + ans_duration
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
            .with_duration(1)
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
            .with_duration(reveal_duration-1 + ans_duration)
            .with_start(intro_duration + que_duration + timer_duration + 1)
            .with_position((
                1920-image_clip_margin_left-image_clip.size[0]-txt_margin[2],
                1080-image_clip.size[1]-subscribe_margin[1]-subscribe_clip.size[1]-image_clip_margin_bottom+txt_margin[1]
            ))
        )

        answers_clip.append(correct_blink_clip)
        answers_clip.append(correct_moveup_clip)

        # TODO: show fusion words
        for index, fusion_word in enumerate(data['FusionWords']):
            answer_clip = (
                TextClip(
                    font='./assets/04b_30.ttf',
                    text=fusion_word,
                    font_size=50,
                    color='#040273',
                )
                .with_duration(reveal_duration-1 + ans_duration)
                .with_start(intro_duration + que_duration + timer_duration + 1)
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


    # TODO: add voiceover for question and answers.
    # TODO: add voiceover for revealing correct answer.
    # TODO: add drum and guitar cords for the two voiceovers.

    clips = []
    clips.extend([level_intro_clip, level_number_shadow_clip, level_number_clip])
    clips.extend([background_clip, logo_clip, subscribe_clip, image_clip, quiz_txt_bg_clip, question_clip] + answers_clip + timer_clips)

    level_intro_sound_clip = AudioFileClip(asset_path + level_intro_sound)
    que_audio_clip = que_audio_clip.with_start(intro_duration)
    que_bg_clip = AudioFileClip(asset_path + voiceover_bg).with_start(intro_duration).with_duration(que_duration)
    timer_sound_clip = AudioFileClip(asset_path + timer_sound).with_start(level_intro_clip.duration + que_duration)
    ans_audio_clip = ans_audio_clip.with_start(intro_duration + que_duration + timer_duration + reveal_duration)
    ans_bg_clip = AudioFileClip(asset_path + voiceover_bg).with_start(intro_duration + que_duration + timer_duration + reveal_duration).with_duration(ans_duration)
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
        final_clip.write_videofile(fp.name, fps=24, codec="libx264", temp_audiofile="temp-audio.m4a", remove_temp=True, audio_codec="aac")
        fp.seek(0)
        data = fp.read()

    with open(f'level_{level}.mp4', 'wb') as f:
        f.write(data)

def convertmp3(path):
    # convert canva mp4 to mp3.
    for i in range(0, 40):
        video = VideoFileClip(f'{asset_path}/{i+1}.mp4')
        audio = video.audio
        if i % 2 == 0:
            audio.write_audiofile(f'{asset_path}LevelQue_{int((i+1)/2+1)}.mp3')
        else:
            audio.write_audiofile(f'{asset_path}LevelAns_{int(i/2)+1}.mp3')

def make_all_levels(data):
    level_cfgs = []
    for i, level in enumerate(data):
        level_cfg = {
        	"Level": 20-i,
        	"LevelIntro": "LevelIntro.mp4",
        	"LevelIntroSound": "levelandshowup.mp3",
        	"QueVoiceover": f"LevelQue_{i+1}.mp3",
        	"AnsVoiceover": f"LevelAns_{i+1}.mp3",
        	"VoiceoverBackground": "Chord.mp3",
        	"TimerSound": "drumpluswin.mp3",
        	"Background": "Background.png",
        	"Image": "foonimal_%02d.png" % (i+1),
        	"Logo": "Logo.png",
        	"Subscribe": "Subscribe.gif",
        	"Question": "Guess who I am?",
        	"Answers": level['Questions'],
            "FusionWords": level['Explain'].split(', ')[0:2],
        	"CorrectAnswer": level['Answer'],
        	"RevealDuration": 4.7,
        	"Duration": 10.0
        }
        level_cfgs.append(level_cfg)
        print(level_cfg)

    for level_cfg in level_cfgs:
        make_level(level_cfg)

    #with multiprocessing.Pool(4) as pool:
    #    pool.map(make_level, level_cfgs)

def concat_levels(data):
    # add optional intro videos, outtro videos
    # write to videolist.txt for ffmpeg concat
    intros = data['intros']
    outros = data['outros']
    videos = intros + ['Level_%d.mp4' % (i+1) for i in range(20)] + outros
    videos = [f'{asset_path}/{video}' for video in videos]
    with open(f'{asset_path}/videolist.txt', 'w') as f:
        content = '\n'.join([
            f"file '{video}'" for video in videos
        ])
        f.write(content)
    subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', 'videolist.txt', '-c', 'copy', f'{asset_path}/final.mp4'])

    

if __name__ == '__main__':
    if sys.argv[1] == 'csv':
        make_bulk_csv(json.load(sys.stdin))
    elif sys.argv[1] == 'script':
        make_script(json.load(sys.stdin))
    elif sys.argv[1] == 'convertmp3':
        convertmp3(sys.argv[2])

    elif sys.argv[1].startswith('level'):
        make_level(json.load(sys.stdin))
    elif sys.argv[1] == 'alllevels':
        make_all_levels(json.load(sys.stdin)) # use quiz.json
    elif sys.argv[1] == 'concatlevels':
        concat_levels(json.load(sys.stdin))


    # TODO: output, level mp4 must be put into asset_path
    # TODO: add api to call eleven labs to download voiceover.
    # TODO: add selenium client to download images from midjourney.
    # TODO: add api to call chatgpt to generate questions and answers in json format.
    # TODO: add readme on how to use it.
    # TODO: performance improvement. see how to run faster.
