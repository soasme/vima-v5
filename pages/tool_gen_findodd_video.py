import os
import streamlit as st
import requests
from PIL import Image
import io
from moviepy import *
from streamlit_image_coordinates import streamlit_image_coordinates
import random
from pathlib import Path

from vima5.findodd_video_generator import create_quiz_video, load_image, create_quiz_video_set

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

def get_page_crop_coords(idx, scale=1.0):
    img = Image.open('./assets/highlight.gif')
    center_x = st.session_state.tool_findodd_pages[idx]['center_point']['x']
    center_y = st.session_state.tool_findodd_pages[idx]['center_point']['y']
    top_x = st.session_state.tool_findodd_pages[idx]['top_point']['x']
    top_y = st.session_state.tool_findodd_pages[idx]['top_point']['y']

    top = top_y / scale
    bottom = (center_y + abs(top_y - center_y)) / scale
    img_scale = (bottom - top) / img.size[1]
    left = center_x / scale - img.size[0] * img_scale * 0.5
    right = left + img.size[0] * img_scale
    return dict(left=left, top=top, right=right, bottom=bottom)

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

    page_num = st.number_input("Number of pages", min_value=1, value=1)
    st.session_state.tool_findodd_pages = [{
        'index': index,
        'title': '',
        'title_color': '#000000',
        'title_bg_color': '#FFFFFF',
        'title_font_size': 120,
        'image': None,
        'answer_box': {},
    } for index in range(page_num)]

    # Image input
    for page_idx in range(page_num):
        st.write(f"### Page {page_idx + 1}")

        image_source = st.file_uploader(f"Upload image {page_idx}")
        title = st.text_area(f"Enter quiz title {page_idx}:")
        title_color = st.color_picker(f"Pick title color {page_idx}", "#000000")
        title_bg_color = st.color_picker(f"Pick title background color {page_idx}", "#FFFFFF")
        title_font_size = st.number_input(f"Title font size {page_idx}", min_value=10, max_value=200, value=120)
        st.session_state.tool_findodd_pages[page_idx].update({
            'image': image_source,
            'title': title,
            'title_color': title_color,
            'title_bg_color': title_bg_color,
            'title_font_size': title_font_size,
        })
        # Only show preview and continue if image is provided
        if image_source:
            img = load_image(image_source)
            
            st.write("Click to set points:")
            st.write("1. Center of highlight")
            st.write("2. Top of highlight")
            
            # Get click coordinates
            img_scale = 500.0 / img.size[0]
            coords = streamlit_image_coordinates(img, width=500, key=f"answer_box_{page_idx}", click_and_drag=True)
            if coords:
                answer_box = {
                    'left': coords['x1']/img_scale,
                    'top': coords['y1']/img_scale,
                    'right': coords['x2']/img_scale,
                    'bottom': coords['y2']/img_scale,
                }
                st.session_state.tool_findodd_pages[page_idx]['answer_box'] = answer_box 
                st.image(img.crop((
                    answer_box['left'],
                    answer_box['top'],
                    answer_box['right'],
                    answer_box['bottom'],
                )))

    st.write(st.session_state.tool_findodd_pages)

    

    # Generate video button
    ratio = st.radio("Select aspect ratio", ["16:9", "9:16"])
    resolution = st.radio("Select resolution", ["1080p", "720p", "480p"])

    # Music selection
    music_options = list(BACKGROUND_MUSIC.keys())
    selected_music = st.selectbox(
        "Choose background music:",
        ["Random", "No Sound"] + music_options
    )
    
    if selected_music == "Random":
        selected_music = random.choice(music_options)

    music_url = BACKGROUND_MUSIC[selected_music] if selected_music != 'No Sound' else None

    if st.button("Generate Video"):
        with st.spinner("Generating video..."):
            video_bytes = create_quiz_video_set(
                st.session_state.tool_findodd_pages,
                music_url,
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
