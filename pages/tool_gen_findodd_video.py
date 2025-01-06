import os
import streamlit as st
import requests
from PIL import Image
import io
from moviepy import *
from streamlit_image_coordinates import streamlit_image_coordinates
import random
from pathlib import Path

# Create assets directory if it doesn't exist
Path("assets").mkdir(exist_ok=True)

# Background music options
# https://pixabay.com/music/search/kids/
BACKGROUND_MUSIC = {
    "Better Kids Day": "https://cdn.pixabay.com/audio/2024/12/19/audio_4e9237d491.mp3",
}

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
    ).with_position(('center', 50)).with_duration(13)
    
    # Load highlight gif
    highlight = VideoFileClip("assets/highlight.gif", has_mask=True)
    highlight_scale_factor = abs(center_point['height'] - top_point['height']) / highlight.size[1]
    # Calculate scale based on points
    highlight_scale_factor = 0.5
    highlight = highlight.with_effects([vfx.Resize(highlight_scale_factor)])
    highlight_duration = 3
    highlight_loop_count = int(highlight_duration // highlight.duration + 1)
    highlight = concatenate_videoclips([highlight] * highlight_loop_count).with_duration(highlight_duration)
    
    # Position highlight gif for last 3 seconds
    highlight = highlight.with_position((center_point['width'] - highlight.size[0]/2, 
                                      center_point['height'] - highlight.size[1]/2))
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

def main():
    st.title("Quiz Video Generator")

    # Image input
    image_source = st.file_uploader("Upload image:")
    title = st.text_area("Enter quiz title:")
    
    # Color input
    title_color = st.color_picker("Pick title color", "#ffffff")
    
    # Music selection
    music_options = list(BACKGROUND_MUSIC.keys())
    selected_music = st.selectbox(
        "Choose background music:",
        ["Random"] + music_options
    )
    
    if selected_music == "Random":
        selected_music = random.choice(music_options)
    
    music_url = BACKGROUND_MUSIC[selected_music]
        
    # Only show preview and continue if image is provided
    if image_source:
        try:
            img = load_image(image_source)
            
            st.write("Click to set points:")
            st.write("1. Center of highlight")
            st.write("2. Top of highlight")
            
            # Get click coordinates
            coords = streamlit_image_coordinates(img, width=300)

            if 'clicks' not in st.session_state:
                st.session_state.clicks = []

            if st.button("Clear Points"):
                st.session_state.clicks = []
            
            if coords:
                st.session_state.clicks.append(coords)
                if len(st.session_state.clicks) > 2:
                    st.session_state.clicks = st.session_state.clicks[-1:]
                
                # Preview points
                st.write(f"Points selected: {len(st.session_state.clicks)}/2")
                for i, point in enumerate(st.session_state.clicks):
                    st.write(f"Point {i+1}: {point}")
            
            # Generate video button
            if len(st.session_state.clicks) == 2 and st.button("Generate Video"):
                center_point = st.session_state.clicks[0]
                top_point = st.session_state.clicks[1]
                
                video_path = create_quiz_video(
                    image_source,
                    title,
                    center_point,
                    top_point,
                    title_color,
                    music_url
                )

                st.video(video_path)
                
                # Provide download link
                with open(video_path, 'rb') as f:
                    st.download_button(
                        label="Download Video",
                        data=f,
                        file_name="/tmp/quiz_video.mp4",
                        mime="video/mp4"
                    )
            else:
                st.warning("Please select both points to generate video.")
                
        finally:
            st.write("Complete")

if __name__ == "__main__":
    main()
