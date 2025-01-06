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
            if select_point == "Center":
                coords = streamlit_image_coordinates(img)
                if coords:
                    st.session_state.tool_gen_findodd_video_center_point = coords
            elif select_point == "Top":
                coords = streamlit_image_coordinates(img)
                if coords:
                    st.session_state.tool_gen_findodd_video_top_point = coords
            elif select_point == "Preview":
                top = st.session_state.tool_gen_findodd_video_top_point['y']
                bottom = (st.session_state.tool_gen_findodd_video_center_point['y'] + abs(st.session_state.tool_gen_findodd_video_top_point['y'] - st.session_state.tool_gen_findodd_video_center_point['y']))
                left = st.session_state.tool_gen_findodd_video_center_point['x'] - abs(bottom-top)/img.size[1]*img.size[0]*0.5
                right = st.session_state.tool_gen_findodd_video_center_point['x'] + abs(bottom-top)/img.size[1]*img.size[0]*0.5
                st.image(img.crop((
                    left,
                    top,
                    right,
                    bottom,
                )))


            st.write(f"Center Point: {st.session_state.tool_gen_findodd_video_center_point}")
            st.write(f"Top Point: {st.session_state.tool_gen_findodd_video_top_point}")



            # Generate video button
            if st.button("Generate Video"):
                video_path = create_quiz_video(
                    image_source,
                    title,
                    st.session_state.tool_gen_findodd_video_center_point,
                    st.session_state.tool_gen_findodd_video_top_point,
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
