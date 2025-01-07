import os
import streamlit as st
import requests
from PIL import Image
import io
from moviepy import *
from streamlit_image_coordinates import streamlit_image_coordinates
import random
from pathlib import Path

from vima5.findodd_video_generator import create_quiz_video, load_image

# Background music options
# https://pixabay.com/music/search/kids/
BACKGROUND_MUSIC = {
    "Better Kids Day": "https://cdn.pixabay.com/audio/2024/12/19/audio_4e9237d491.mp3",
}

def get_crop_coords(scale=1.0):
    img = Image.open('./assets/highlight.gif')
    top = st.session_state.tool_gen_findodd_video_top_point['y'] / scale
    bottom = (st.session_state.tool_gen_findodd_video_center_point['y'] + abs(st.session_state.tool_gen_findodd_video_top_point['y'] - st.session_state.tool_gen_findodd_video_center_point['y'])) / scale
    img_scale = (bottom - top) / img.size[1]
    left = st.session_state.tool_gen_findodd_video_center_point['x'] / scale - img.size[0] * img_scale * 0.5
    right = left + img.size[0] * img_scale
    return dict(left=left, top=top, right=right, bottom=bottom)

def main():

    st.title("Quiz Shorts Generator")


    # Image input
    image_source = st.file_uploader("Upload image:")
    title = st.text_area("Enter quiz title:")
    
    # Color input
    title_color = st.color_picker("Pick title color", "#000000")
    title_bg_color = st.color_picker("Pick title background color", "#FFFFFF")
    title_font_size = st.number_input("Title font size", min_value=10, max_value=200, value=100)
    
    # Music selection
    music_options = list(BACKGROUND_MUSIC.keys())
    selected_music = st.selectbox(
        "Choose background music:",
        ["Random", "No Sound"] + music_options
    )
    
    if selected_music == "Random":
        selected_music = random.choice(music_options)

    music_url = BACKGROUND_MUSIC[selected_music] if selected_music != 'No Sound' else None
        
    # Only show preview and continue if image is provided
    center_point = {}
    top_point = {}

    if image_source:
        try:
            img = load_image(image_source)
            
            st.write("Click to set points:")
            st.write("1. Center of highlight")
            st.write("2. Top of highlight")
            
            # Get click coordinates
            if 'tool_gen_findodd_video_center_point' not in st.session_state:
                st.session_state.tool_gen_findodd_video_center_point = {}
            if 'tool_gen_findodd_video_top_point' not in st.session_state:
                st.session_state.tool_gen_findodd_video_top_point = {}

            select_point = st.radio("Select point", ["Center", "Top", "Preview"])
            img_scale = 500.0 / img.size[0]
            if select_point == "Center":
                coords = streamlit_image_coordinates(img, width=500)
                if coords:
                    st.session_state.tool_gen_findodd_video_center_point = coords
            elif select_point == "Top":
                coords = streamlit_image_coordinates(img, width=500)
                if coords:
                    st.session_state.tool_gen_findodd_video_top_point = coords
            elif select_point == "Preview":
                crop = get_crop_coords(scale=img_scale)
                st.image(img.crop((
                    crop['left'],
                    crop['top'],
                    crop['right'],
                    crop['bottom'],
                )))

            # Generate video button
            ratio = st.radio("Select aspect ratio", ["16:9", "9:16"])
            resolution = st.radio("Select resolution", ["1080p", "720p", "480p"])

            if st.button("Generate Video"):
                st.write('Generating video...')
                with st.spinner("Generating video..."):
                    video_path = create_quiz_video(
                        image_source,
                        title,
                        title_bg_color,
                        get_crop_coords(scale=img_scale),
                        title_color,
                        music_url,
                        font_size=title_font_size,
                        ratio=ratio,
                        resolution=resolution,
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
                
        finally:
            pass

if __name__ == "__main__":
    main()
