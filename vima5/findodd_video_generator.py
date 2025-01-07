import os
from PIL import Image
from tempfile import NamedTemporaryFile
from moviepy import *
from pathlib import Path

# Create assets directory if it doesn't exist
Path("assets").mkdir(exist_ok=True)

def load_image(image_source):
    return Image.open(image_source)

RATIO_MAP = {
    '16:9': 16/9,
    '9:16': 9/16,
    '4:3': 4/3,
    '3:4': 3/4,
    '1:1': 1/1,
}

RESOLUTION_MAP = {
    '1080p': {
        '16:9': (1920, 1080),
        '9:16': (1080, 1920),
        '4:3': (1440, 1080),
        '3:4': (810, 1080),
        '1:1': (1080, 1080),
    },
    '720p': {
        '16:9': (1280, 720),
        '9:16': (720, 1280),
        '4:3': (960, 720),
        '3:4': (540, 720),
        '1:1': (720, 720),
    },
    '480p': {
        '16:9': (640, 480),
        '9:16': (480, 640),
        '4:3': (640, 480),
        '3:4': (360, 480),
        '1:1': (480, 480),
    },
}

def create_quiz_video(image_path, title, title_bg_color, answer_box, title_color, music_url, ratio='9:16', resolution='1080p', font_size=70):
    # Load the image and create video clip
    image_clip = ImageClip(image_path).with_duration(15)
    
    # Resize to aspect ratio while maintaining image within bounds
    target_ratio = RATIO_MAP.get(ratio, 9/16)
    target_resolution = RESOLUTION_MAP.get(resolution, RESOLUTION_MAP['1080p']).get(ratio, RESOLUTION_MAP['1080p']['9:16'])

    img_w, img_h = image_clip.size
    current_ratio = img_w/img_h
    
    image_scale = max(target_resolution[0]/img_w, target_resolution[1] / img_h)
    image_clip = image_clip.with_effects([vfx.Resize(image_scale)])
    
    # Add title text
    txt_clip = TextClip(
        font='./assets/from-cartoon-blocks.ttf',
        text=title, 
        font_size=font_size, 
        bg_color=title_bg_color,
        color=title_color,
        margin=(10, 10),
    ).with_position(('center', 50)).with_duration(15)
    
    # Load highlight gif
    highlight = VideoFileClip("assets/highlight.gif", has_mask=True)
    highlight_scale_factor = (answer_box['bottom'] - answer_box['top']) / highlight.size[1] * image_scale
    highlight_scale_factor = 1.0 if highlight_scale_factor == 0.0 else highlight_scale_factor
    # Calculate scale based on points
    highlight = highlight.with_effects([vfx.Resize(highlight_scale_factor)])
    highlight_duration = 5
    highlight_loop_count = int(highlight_duration // highlight.duration + 1)
    highlight = concatenate_videoclips([highlight] * highlight_loop_count).with_duration(highlight_duration)
    
    # Position highlight gif for last 5 seconds
    highlight = highlight.with_position((answer_box['left']*image_scale, answer_box['top']*image_scale))
    highlight = highlight.with_start(10).with_duration(5)

    # Combine all elements
    final_clip = CompositeVideoClip([image_clip, txt_clip, highlight])
    
    # Load and set audio

    if music_url:
        bingo_sound = AudioFileClip("assets/win.mp3").with_start(10).with_duration(1)
        background_music = AudioFileClip(music_url).with_duration(15)
        audio_clip = CompositeAudioClip([background_music, bingo_sound])
        final_clip = final_clip.with_audio(audio_clip)
    
    # Write video file
    with NamedTemporaryFile(suffix='.mp4') as fp:
        final_clip.write_videofile(fp.name, fps=24, codec="libx264", temp_audiofile="temp-audio.m4a", remove_temp=True, audio_codec="aac")
        fp.seek(0)
        return fp.read()

def create_quiz_video_set(
    pages, # array, each element is a dict with keys: image_path, title, title_bg_color, answer_box, title_color
    music_url, ratio='9:16', resolution='1080p',
):
    # Resize to aspect ratio while maintaining image within bounds
    target_ratio = RATIO_MAP.get(ratio, 9/16)
    target_resolution = RESOLUTION_MAP.get(resolution, RESOLUTION_MAP['1080p']).get(ratio, RESOLUTION_MAP['1080p']['9:16'])

    clips = []
    for page in pages:
        print(page)
        title = page['title']
        title_bg_color = page['title_bg_color']
        title_color = page['title_color']
        font_size = page['title_font_size']
        image_path = page['image']
        index = page['index']
        answer_box = page['answer_box']

        # Load the image and create video clip
        image_clip = ImageClip(image_path).with_duration(15).with_start(index * 15)

        # Resize to aspect ratio while maintaining image within bounds
        img_w, img_h = image_clip.size
        current_ratio = img_w/img_h
        image_scale = max(target_resolution[0]/img_w, target_resolution[1] / img_h)
        image_clip = image_clip.with_effects([vfx.Resize(image_scale)])
    
        # Add title text
        txt_clip = TextClip(
            font='./assets/from-cartoon-blocks.ttf',
            text=title, 
            font_size=font_size, 
            bg_color=title_bg_color,
            color=title_color,
            margin=(10, 10),
        ).with_position(('center', 50)).with_duration(15).with_start(index * 15)
    
        # Load highlight gif
        highlight = VideoFileClip("assets/highlight.gif", has_mask=True)
        highlight_scale_factor = (answer_box['bottom'] - answer_box['top']) / highlight.size[1] * image_scale
        highlight_scale_factor = 1.0 if highlight_scale_factor == 0.0 else highlight_scale_factor
        # Calculate scale based on points
        highlight = highlight.with_effects([vfx.Resize(highlight_scale_factor)])
        highlight_duration = 5
        highlight_loop_count = int(highlight_duration // highlight.duration + 1)
        highlight = concatenate_videoclips([highlight] * highlight_loop_count).with_duration(highlight_duration)
        
        # Position highlight gif for last 5 seconds
        highlight = highlight.with_position((answer_box['left']*image_scale, answer_box['top']*image_scale))
        highlight = highlight.with_start(index * 15 + 10).with_duration(5)

        clips.extend([image_clip, txt_clip, highlight])

    # Combine all elements
    final_clip = CompositeVideoClip(clips)
    
    # Load and set audio
    if music_url:
        background_music = AudioFileClip(music_url).with_duration(15 * len(pages))
        final_clip = final_clip.with_audio(background_music)
    
    # Write video file
    with NamedTemporaryFile(suffix='.mp4') as fp:
        final_clip.write_videofile(fp.name, fps=24, codec="libx264", temp_audiofile="temp-audio.m4a", remove_temp=True, audio_codec="aac")
        fp.seek(0)
        return fp.read()
