
# Page 1:
# Single color, drifting question marks (4/5 - 4/5), a floating black outline. tts: What animal is it? wait 2 seconds, another tts: reveal the name.
# Page 2:
# Congrats color background, a squish and bounce image, tts: Good job, ...Put name on the bottom.
# Page 3:
# Move it to the animal shape puzzle. with two attempts. If failed, Show failed emoji, and crosses. Finally, show correct answer.
# Page 4:
# Put a background, Host show. Left: animal squish and bounce, Right: host. Host squish and bounce. tts: A question for animal. Animal squish and bounce. Host tts: Answer in first persona.

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
FPS = 30

import numpy as np

def change_angle_to_radius_unit(angle):
    angle_radius = angle * (np.pi/180)
    return angle_radius

def rotate(src_img,angle_of_rotation,pivot_point,shape_img):

    #1.create rotation matrix with numpy array
    rotation_mat = np.transpose(np.array([[np.cos(angle_of_rotation),-np.sin(angle_of_rotation)],
                            [np.sin(angle_of_rotation),np.cos(angle_of_rotation)]]))
    h,w = shape_img
    
    pivot_point_x =  pivot_point[0]
    pivot_point_y = pivot_point[1]
    
    new_img = np.zeros(src_img.shape,dtype='u1') 

    for height in range(h): #h = number of row
        for width in range(w): #w = number of col
            xy_mat = np.array([[width-pivot_point_x],[height-pivot_point_y]])
            
            rotate_mat = np.dot(rotation_mat,xy_mat)

            new_x = pivot_point_x + int(rotate_mat[0])
            new_y = pivot_point_y + int(rotate_mat[1])


            if (0<=new_x<=w-1) and (0<=new_y<=h-1): 
                new_img[new_y,new_x] = src_img[height,width]

    return new_img

def page_que(movie, config, idx):

    que_background = config['objects'][idx].get('que_background') or '#ffffff'

    que_question = config['objects'][idx].get('que_question') or 'What animal do you think is it?'
    que_question_clip = AudioFileClip(make_voiceover(que_question, voice=config['host']['voice']))
    que_question_duration = math.ceil(que_question_clip.duration)

    answer = config['objects'][idx].get('que_answer') or 'It is a cat.'
    answer_clip = AudioFileClip(make_voiceover(answer, voice=config['objects'][idx]['voice']))
    answer_duration = math.ceil(answer_clip.duration)

    outline_path = config['objects'][idx].get('image').replace('.png', '_black.png')
    outline_clip = ImageClip(get_build_path(outline_path)).resized((CANVA_WIDTH, CANVA_HEIGHT))

    started_at = 0
    init_padding_duration = 0.5
    thinking_duration = 2

    questioned_at = init_padding_duration
    answered_at = questioned_at + que_question_duration + thinking_duration

    total_duration = (
            init_padding_duration 
            + que_question_duration
            + thinking_duration
            + answer_duration
    )

    with movie.page(duration=total_duration, background=que_background) as page:
        page.elem(
            ImageClip(get_asset_path('QuestionBackground.png'))
            .with_duration(total_duration)
            .with_opacity(0.5)
            .with_position((0, -470))
            .with_effects([
                UniformMotion((0, -470), (0, 0))
            ])
        )
        page.elem(
            outline_clip
            .with_duration(total_duration)
            .with_position((0, 0))
            .with_effects([
                vfx.CrossFadeIn(1),
                FloatAnimation(),
            ]),
            start=0,
            duration=total_duration,
        )

        page.elem(
            que_question_clip,
            start=questioned_at,
            duration=que_question_clip.duration,
        )

        page.elem(
            answer_clip,
            start=answered_at,
            duration=answer_clip.duration,
        )


def page_congrats(movie, config, idx):
    que_background = config['objects'][idx].get('que_background') or '#ffffff'
    congrats = config['objects'][idx].get('congrats') or 'Congratulations! You are right! ' + config['objects'][idx]['que_answer']
    congrats_clip = AudioFileClip(make_voiceover(congrats, voice=config['host']['voice']))
    congrats_duration = math.ceil(congrats_clip.duration)

    started_at = 0
    init_padding_duration = 0.5
    end_padding_duration = 1
    total_duration = init_padding_duration + congrats_duration + end_padding_duration

    with movie.page(duration=total_duration, background=que_background) as page:
        bg = ImageClip(get_asset_path('ExclamationBackground.png'))
        page.elem(
            bg
            .with_duration(total_duration)
            .with_duration(total_duration)
            .with_opacity(0.5)
            .with_position((0, -420))
            .with_effects([
                UniformMotion((0, -420), (0, 0))
            ])
        )

        obj_clip = (
            ImageClip(get_build_path(config['objects'][idx]['image']))
            .resized((CANVA_WIDTH, CANVA_HEIGHT))
        )
        page.elem(
            obj_clip
            .with_position(anchor_center(
                0, 0, CANVA_WIDTH, CANVA_HEIGHT, obj_clip.w, obj_clip.h))
            .with_effects([
                SquishBounceEffect(),
            ]),
        )

        page.elem(
            congrats_clip,
            start=init_padding_duration,
            duration=congrats_clip.duration,
        )

def add_obj_outline(main_char_idx, outline_idx, obj):
    image_path = get_build_path(obj['image'])
    outline_path = get_build_path(obj['image'].replace('.png', '_black.png'))
    return (
        ImageClip(outline_path if main_char_idx <= outline_idx else image_path)
        .resized(obj['size'])
        .with_position(obj['pos'])
    )

def page_puzzle(movie, config, idx):
    # bg: https://stackoverflow.com/questions/69004202/two-color-linear-gradient-positioning-with-pil-python

    challenge_question = config['objects'][idx].get('challenge_question') or 'Now, can you find its shadow?'
    challenge_question_clip = AudioFileClip(make_voiceover(challenge_question, voice=config['host']['voice']))
    challenge_question_duration = math.ceil(challenge_question_clip.duration)

    challenge_failed = config['objects'][idx].get('challenge_failed') or 'Oops! That is not the right shadow.'
    challenge_failed_clip = AudioFileClip(make_voiceover(challenge_failed, voice=config['host']['voice']))
    challenge_failed_duration = math.ceil(challenge_failed_clip.duration)

    challenge_success = config['objects'][idx].get('challenge_success') or 'Great! You found it.'
    challenge_success_clip = AudioFileClip(make_voiceover(challenge_success, voice=config['host']['voice']))
    challenge_success_duration = math.ceil(challenge_success_clip.duration)

    move_in_duration = max(5, challenge_question_duration)
    move_to_wrong1_duration = 2 if idx < len(config['objects']) - 1 else 0
    move_from_wrong1_duration = 0.5 if idx < len(config['objects']) - 1 else 0
    wait_wrong1_duration = max(3, challenge_failed_duration) if idx < len(config['objects']) - 1 else 0
    move_to_duration = 3
    congrats_duration = max(3, challenge_success_duration)
    total_duration = move_in_duration + move_to_wrong1_duration + \
            move_from_wrong1_duration + \
            wait_wrong1_duration + \
            move_to_duration + congrats_duration
    started_at = 0
    attempted_at = move_in_duration
    revealed_at = move_in_duration + move_to_wrong1_duration \
            + move_from_wrong1_duration + wait_wrong1_duration
    congrats_at = revealed_at + move_to_duration

    with movie.page(duration=total_duration, background='#ffffff') as page:
        page.elem(
            ImageClip(get_asset_path(config.get('background')))
            .resized((CANVA_WIDTH, CANVA_HEIGHT))
            .with_position((0, 0)),
            start=0,
            duration=total_duration,
        )

        for j, _obj in enumerate(config['objects']):
            shadow = add_obj_outline(idx, j, _obj).with_effects([
                SquishBounceEffect(frequency=1),
            ])
            if j == idx:
                page.elem(shadow, start=0, duration=(total_duration - congrats_duration))
            else:
                page.elem(shadow)

        obj = config['objects'][idx]
        obj_pos = int(obj['pos'][0]), int(obj['pos'][1])
        obj_size = int(obj['size'][0]), int(obj['size'][1])
        obj_clip = ImageClip(
            get_build_path(config['objects'][idx]['image'])
        )
        init_pos = anchor_center(0, 0, CANVA_WIDTH, CANVA_HEIGHT,
                                 obj_clip.w, obj_clip.h)
        init_pos = 0, init_pos[1]

        page.elem(
            obj_clip
            .with_duration(move_in_duration)
            .with_position((0, 0))
            .with_effects([
                Swing(-2, 2, 1),
                SquishBounceEffect(frequency=1),
                vfx.SlideIn(1, side='left'),
            ]),
            start=started_at,
            duration=move_in_duration,
        )

        page.elem(
            challenge_question_clip,
            start=0,
            duration=challenge_question_clip.duration,
        )

        if idx < len(config['objects']) - 1:
            page.elem(
                obj_clip
                .with_duration(move_to_wrong1_duration)
                .with_effects([
                    UniformMotion(init_pos, config['objects'][idx+1]['pos']),
                    UniformScale(1.0, obj['size'][0] / obj_clip.w),
                ])
                ,
                start=attempted_at,
                duration=move_to_wrong1_duration,
            )
            page.elem(
                obj_clip
                .with_duration(move_from_wrong1_duration)
                .with_effects([
                    UniformMotion(config['objects'][idx+1]['pos'], init_pos),
                    UniformScale(obj['size'][0] / obj_clip.w, 1.0),
                ]),
                start=attempted_at + move_to_wrong1_duration,
                duration=move_from_wrong1_duration,
            )

            page.elem(
                challenge_failed_clip,
                start=attempted_at + move_to_wrong1_duration,
                duration=challenge_failed_clip.duration,
            )

            page.elem(
                obj_clip
                .with_duration(wait_wrong1_duration)
                .with_position(init_pos)
                .with_effects([
                    Swing(-2, 2, 1),
                    SquishBounceEffect(frequency=1),
                ]),
                start=attempted_at + move_to_wrong1_duration + move_from_wrong1_duration,
                duration=wait_wrong1_duration,
            )

        page.elem(
            obj_clip
            .with_duration(move_to_duration)
            .with_effects([
                UniformMotion(init_pos, obj['pos']),
                UniformScale(1.0, obj['size'][0] / obj_clip.w),
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
                obj['pos'][0], obj['pos'][1],
                obj['size'][0], obj['size'][1],
                confetti.w, confetti.h,
            )),
            start=congrats_at,
            duration=congrats_duration,
        )
        page.elem(
            challenge_success_clip,
            start=congrats_at,
            duration=challenge_success_clip.duration,
        )
        page.elem(
            obj_clip
            .with_duration(2)
            .with_position(obj['pos'])
            .resized(obj['size'])
            .with_effects([
                SquishBounceEffect(frequency=1),
            ]),
            start=congrats_at,
            duration=congrats_duration,
        )

def page_funfact(movie, config, idx):
    started_at = 0

    funfact = config['objects'][idx].get('funfact') or 'Hi, I am a ' + config['objects'][idx]['que_answer']
    funfact_clip = AudioFileClip(make_voiceover(funfact, voice=config['objects'][idx]['voice']))
    funfact_clip_duration = math.ceil(funfact_clip.duration)

    init_padding_duration = 0.5
    after_padding_duration = 1

    total_duration = init_padding_duration + funfact_clip_duration + after_padding_duration

    que_background = config['objects'][idx].get('que_background') or '#ffffff'

    with movie.page(duration=total_duration, background=que_background) as page:
        obj = config['objects'][idx]
        obj_clip = ImageClip(
            get_build_path(config['objects'][idx]['image'])
        ).resized((CANVA_WIDTH, CANVA_HEIGHT))
        page.elem(
            obj_clip
            .with_duration(total_duration)
            .with_position((0, 0))
            .with_effects([
                SquishBounceEffect(frequency=1),
            ]),
            start=started_at,
            duration=total_duration,
        )

        page.elem(
            funfact_clip,
            start=init_padding_duration,
            duration=funfact_clip.duration,
        )

def parse_args():
    parser = argparse.ArgumentParser(description='Finger Family')
    parser.add_argument('--input-dir', type=str, help='Input Directory having all the images and config')
    parser.add_argument('--output', type=str, help='Output video file', default='/tmp/output.mp4')
    parser.add_argument('--compile', action='store_true', help='Compile the video')

    args = parser.parse_args()
    return args

def gen_voiceovers(config):
    for obj in config['objects']:
        print('Making voiceovers for:', obj['que_question'], obj['que_answer'])
        make_voiceover(obj['que_question'], voice=config['host']['voice'])
        make_voiceover(obj['que_answer'], voice=obj['voice'])
        print('Making voiceovers for:', obj['congrats'])
        make_voiceover(obj['congrats'], voice=config['host']['voice'])
        print('Makeing voiceovers for:', obj['challenge_question'], obj.get('challenge_failed', ''), obj['challenge_success'])
        make_voiceover(obj['challenge_question'], voice=config['host']['voice'])
        if 'challenge_failed' in obj:
            make_voiceover(obj['challenge_failed'], voice=config['host']['voice'])
        make_voiceover(obj['challenge_success'], voice=config['host']['voice'])
        print('Making voiceovers for:', obj['funfact'])
        make_voiceover(obj['funfact'], voice=obj['voice'])

def gen_level(config, idx):
    movie = Movie()
    page_que(movie, config, idx)
    page_congrats(movie, config, idx)
    page_puzzle(movie, config, idx)
    page_funfact(movie, config, idx)
    movie.render(f'/tmp/animalshadowpuzzle{idx}.mp4', fps=FPS)

def main():
    args = parse_args()
    config = f'{args.input_dir}/config.json'
    with open(config) as f:
        config = json.load(f)

    os.environ['ASSET_PATH'] = os.environ.get('ASSET_PATH') + ',' + args.input_dir
    config['input_dir'] = args.input_dir

    gen_voiceovers(config)

    for idx, obj in enumerate(config['objects']):
        if idx < 18:
            continue
        gen_level(config, idx)


if __name__ == '__main__':
    main()

