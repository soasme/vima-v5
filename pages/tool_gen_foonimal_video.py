import os
import streamlit as st
import requests
from PIL import Image
import io
from moviepy import *
from streamlit_image_coordinates import streamlit_image_coordinates
import random
from pathlib import Path

from vima5.foonimal_video_generator import load_image, create_quiz_video_set

# Background music options
# https://pixabay.com/music/search/kids/
BACKGROUND_MUSIC = {
    "Better Kids Day": "https://cdn.pixabay.com/audio/2024/12/19/audio_4e9237d491.mp3",
    # 96kps, needs improvement.
    "Bike Rides": "https://directory.audio/media/fc_local_media/audio_preview/the green orbs - bike rides -bright-.mp3",
    "Bunny Hop": "https://directory.audio/media/fc_local_media/audio_preview/quincas moreira - bunny hop -happy-.mp3",
    "Get Outside": "https://directory.audio/media/fc_local_media/audio_preview/jason farnham - get outside -happy-.mp3",
    "The Farmer In The Dell": "https://directory.audio/media/fc_local_media/audio_preview/the green orbs - the farmer in the dell instrumental -happy-.mp3",
    "Sugar Zone": "https://directory.audio/media/fc_local_media/audio_preview/silent partner - sugar zone -happy-.mp3",
}

def main():

    st.title("Foonimal Quiz Generator")


    image_files = st.file_uploader("Upload image files", accept_multiple_files=True)
    level_data = st.file_uploader("Upload level data")
    music_files = list(BACKGROUND_MUSIC.values())

    if st.button("Generate Video"):
        with st.spinner("Generating video..."):
            video_bytes = create_quiz_video_set(
                image_files=image_files,
                level_data=level_data,
                music_urls=music_urls,
                ratio=ratio,
                resolution=resolution,
            )

            st.video(video_bytes)
            
            # Provide download link
            st.download_button(
                label="Download Video",
                data=video_bytes,
                mime="video/mp4",
            )
                

if __name__ == "__main__":
    main()

