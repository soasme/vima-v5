import csv
import os
import math
import json
import sys
import random
from moviepy import *
from tempfile import NamedTemporaryFile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

asset_path = os.environ['ASSET_PATH']

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


def make_bulk_csv():
    data = json.load(sys.stdin)
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

def make_script():
    res = []
    data = json.load(sys.stdin)
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

def make_level():
    data = json.load(sys.stdin)
    level = data['Level']
    bg_path = asset_path + data['Background']
    image_path = asset_path + data['Image']
    logo_path = asset_path + data['Logo']
    subscribe_path = asset_path + data['Subscribe']
    question = data['Question']
    duration = data['Duration']

    # Display background
    background_clip = ImageClip(bg_path).with_duration(duration)
    background_clip = background_clip.with_effects([vfx.Resize((1920, 1080))])

    # Display logo
    logo_clip = ImageClip(logo_path).with_duration(duration).with_effects([vfx.CrossFadeIn(0.5)])
    logo_margin = (10, 10)
    logo_clip = logo_clip.with_position((logo_margin[0], 1080-logo_clip.size[1]-logo_margin[1]))

    # Display subscribe
    subscribe_margin = (10, 30)
    subscribe_clip = VideoFileClip(subscribe_path, has_mask=True).with_duration(duration).with_effects([vfx.CrossFadeIn(0.5)])
    subscribe_clip = subscribe_clip.with_position((
        logo_clip.size[0]+logo_margin[0]+subscribe_margin[0],
        1080-subscribe_clip.size[1]-subscribe_margin[1]
    ))

    # Display Image
    image = Image.open(image_path)
    rounded_image = round_corners(image, radius=50)
    image_clip = ImageClip(np.array(rounded_image)).with_duration(duration)
    image_clip = image_clip.with_effects([vfx.Resize(lambda t: (710 - 10 * math.sin(t), 710))])
    image_clip_margin_bottom = 100
    image_clip = image_clip.with_position(lambda t: (
        logo_clip.size[0]+logo_margin[0]+subscribe_margin[0],
        1080-image_clip.size[1]-subscribe_margin[1]-subscribe_clip.size[1]-image_clip_margin_bottom + 10 * math.sin(3 * t)
    ))
    image_clip = image_clip.with_effects([
        vfx.CrossFadeIn(0.5),
    ])

    #image_shadow = ImageClip(np.array(create_shadow_from_alpha(extract_alpha(rounded_image), 50))).with_duration(duration)
    #image_shadow = image_shadow.with_effects([vfx.Resize((710, 710))])
    #image_shadow = image_shadow.with_position(lambda t: (
    #    logo_clip.size[0]+logo_margin[0]+subscribe_margin[0]+10,
    #    1080-subscribe_margin[1]-image_clip.size[1]-20 + 10 * math.sin(3 * t)
    #))

    # Display Quiz Quesion
    txt_margin = (100, 200)
    question_clip = (
        TextClip(
            font='./assets/04b_30.ttf',
            text=question,
            font_size=70,
            color='#040273',
        )
        .with_duration(duration)
        .with_position((
        logo_clip.size[0]+logo_margin[0]+subscribe_margin[0]+image_clip.size[0]+txt_margin[0],
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
            .with_duration(duration)
            .with_position((
                logo_clip.size[0]+logo_margin[0]+subscribe_margin[0]+image_clip.size[0]+txt_margin[0],
                1080-image_clip.size[1]-subscribe_margin[1]-subscribe_clip.size[1]-image_clip_margin_bottom + 100 * (index+1) + txt_margin[1]
            ))
            .with_effects([vfx.CrossFadeIn(0.5)])
        )
        answers_clip.append(answer_clip)


    # TODO: add optional bg assets (like clouds, trees, etc),
    # TODO: add sound effect of showup.
    # TODO: add voiceover for question and answers.
    # TODO: add drum and guitar cords for voiceover.
    # TODO: add timer (countdown).
    # TODO: add timer sound.
    # TODO: add sound effect for correct answer.
    # TODO: add voiceover for revealing correct answer.
    # TODO: add drum and guitar cords for voiceover.
    # TODO: add level intro.

    final_clip = CompositeVideoClip([background_clip, logo_clip, subscribe_clip, image_clip, question_clip] + answers_clip)
    # Write video file
    with NamedTemporaryFile(suffix='.mp4') as fp:
        final_clip.write_videofile(fp.name, fps=24, codec="libx264", temp_audiofile="temp-audio.m4a", remove_temp=True, audio_codec="aac")
        fp.seek(0)
        data = fp.read()

    with open(f'level_{level}.mp4', 'wb') as f:
        f.write(data)

if __name__ == '__main__':
    if sys.argv[1] == 'csv':
        make_bulk_csv()
    elif sys.argv[1] == 'script':
        make_script()
    elif sys.argv[1].startswith('level'):
        make_level()
