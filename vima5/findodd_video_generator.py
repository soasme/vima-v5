import os
from PIL import Image
from moviepy import *
from pathlib import Path

# Create assets directory if it doesn't exist
Path("assets").mkdir(exist_ok=True)

def load_image(image_source):
    return Image.open(image_source)

def create_quiz_video(image_path, title, center_point, top_point, title_color, music_url):
    # Load the image and create video clip
    image_clip = ImageClip(image_path).with_duration(13)
    
    # Resize to 9:16 aspect ratio while maintaining image within bounds
    target_ratio = 9/16
    img_w, img_h = image_clip.size
    current_ratio = img_w/img_h
    
    if current_ratio > target_ratio:
        new_width = int(img_h * target_ratio)
        new_height = img_h
    else:
        new_width = img_w
        new_height = int(img_w / target_ratio)
    
    image_scale = new_height / img_h
    image_clip = image_clip.with_effects([vfx.Resize(image_scale)])
    
    # Add title text
    txt_clip = TextClip(
        font='Arial',
        text=title, 
        font_size=70, 
        bg_color='#f0f0f0',
        color=title_color,
        margin=(10, 10),
    ).with_position(('center', 50)).with_duration(13)
    
    # Load highlight gif
    highlight = VideoFileClip("assets/highlight.gif", has_mask=True)
    highlight_scale_factor = abs(center_point['y'] - top_point['y']) / highlight.size[1] * 2.0
    highlight_scale_factor = 1.0 if highlight_scale_factor == 0.0 else highlight_scale_factor
    # Calculate scale based on points
    highlight = highlight.with_effects([vfx.Resize(highlight_scale_factor)])
    highlight_duration = 3
    highlight_loop_count = int(highlight_duration // highlight.duration + 1)
    highlight = concatenate_videoclips([highlight] * highlight_loop_count).with_duration(highlight_duration)
    
    # Position highlight gif for last 3 seconds
    highlight = highlight.with_position((center_point['x'] - highlight.size[0]/2, 
                                      center_point['y'] - highlight.size[1]/2))
    highlight = highlight.with_start(10).with_duration(3)
    
    # Load and set audio
    background_music = AudioFileClip(music_url).with_duration(13)
    #bingo_sound = AudioFileClip("assets/bingo.wav").set_start(10)
    
    # Combine all elements
    final_clip = CompositeVideoClip([image_clip, txt_clip, highlight])
    final_clip = final_clip.with_audio(CompositeAudioClip([
        background_music,
        #bingo_sound
    ]))
    
    # Write video file
    out_dir = "/tmp"
    output_filename = "quiz_video.mp4"
    output_path = os.path.join(out_dir, output_filename)
    final_clip.write_videofile(output_path, fps=24, codec="libx264", temp_audiofile="temp-audio.m4a", remove_temp=True, audio_codec="aac")
    
    return "/tmp/quiz_video.mp4"
