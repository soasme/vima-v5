import hashlib
from pathlib import Path
import os
import json
from streamlit_local_storage import LocalStorage
from datetime import datetime
from openai import OpenAI
from rembg import remove as rembg
from tempfile import NamedTemporaryFile
import numpy as np
from PIL import Image
from elevenlabs.client import ElevenLabs
from elevenlabs import save as save_voiceover
import diskcache as dc

import streamlit as st

STAGE_LYRICS = 1
STAGE_SONG = 2
STAGE_TIMESTAMP = 3
STAGE_STORYBOARD = 4

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

def get_openai_client():
    return OpenAI(api_key=st.session_state.openai_key)

def init_session_state():
    local_storage = LocalStorage()
    previous_session = local_storage.getItem('session')
    if previous_session:
        previous_session = json.loads(previous_session)
        st.session_state.generated_content = previous_session['generated_content']
        st.session_state.history = previous_session['history']
        st.session_state.stage = previous_session['stage']
        st.session_state.user_input = previous_session['user_input']
    if 'stage' not in st.session_state:
        st.session_state.stage = 1
    if 'generated_content' not in st.session_state:
        st.session_state.generated_content = {
            'lyrics': None,
            'song_title': None,
            'song_style': None,
            'song_url': None,
            'song_mp3': None,
            'song_segmentation': None,
            'song_vtt': None,
            'style_prompt': None,
            'song': None,
            'timestamps': None,
            'storyboard': None
        }
    if 'user_input' not in st.session_state:
        st.session_state.user_input = {
            'topic': "",
            'topic_extra_input': "",
            'song_style': "",
        }
    if 'history' not in st.session_state:
        st.session_state.history = []
    if 'topic' not in st.session_state:
        st.session_state.topic = ""
    if 'topic_extra_input' not in st.session_state:
        st.session_state.topic_extra_input = ""
    if 'song_style' not in st.session_state:
        st.session_state.song_style = ""


def save_session():
    session_data = {
        'version': 1,
        'generated_content': st.session_state.generated_content,
        'history': st.session_state.history,
        'user_input': st.session_state.user_input,
        'stage': st.session_state.stage,
        'topic': st.session_state.topic,
        'topic_extra_input': st.session_state.topic_extra_input,
        'song_style': st.session_state.song_style,
    }
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return json.dumps(session_data), f"kids_song_session_{timestamp}.json"

def update_session(generated_content=None, history=None, user_input=None):
    st.session_state.generated_content.update(generated_content or {})
    st.session_state.history.extend(history or [])
    st.session_state.user_input.update(user_input or {})

    local_storage = LocalStorage()
    local_storage.setItem('session', save_session()[0])


def get_session(type, key):
    if type == 'generated_content':
        return st.session_state.generated_content.get(key)
    elif type == 'history':
        return st.session_state.history.get(key)
    elif type == 'user_input':
        return st.session_state.user_input.get(key)
    else:
        return None
    

def load_session(file):
    try:
        content = file.read().decode('utf-8')
        session_data = json.loads(content)
        
        # Check for version, default to 1 if not present
        version = session_data.get('version', 1)
        
        st.session_state.generated_content = session_data['generated_content']
        st.session_state.history = session_data['history']
        st.session_state.stage = session_data['stage']
        st.session_state.user_input = session_data['user_input']

        return True
    except Exception as e:
        st.error(f"Error loading session: {str(e)}")
        return False

def display_sidebar():
    init_session_state()

    with st.sidebar:
        # Session management
        st.header("Session Management")

        # Session import (only in Stage 1)
        uploaded_file = st.file_uploader("Import previous session", type=['json'])
        if uploaded_file is not None:
            if load_session(uploaded_file):
                update_session()
                st.success("Session loaded successfully!")
        
        # Export session
        if st.button("Export Session"):
            session_json, filename = save_session()
            st.download_button(
                label="Download Session File",
                data=session_json,
                file_name=filename,
                mime="application/json"
            )
        
        if st.button("Clear Session"):
            st.session_state.generated_content = {
                'lyrics': None,
                'song_title': None,
                'song_style': None,
                'song_url': None,
                'song_mp3': None,
                'song_segmentation': None,
                'song_srt': None,
                'style_prompt': None,
                'song': None,
                'timestamps': None,
                'storyboard': None
            }
            st.session_state.user_input = {
                'topic': "",
                'topic_extra_input': "",
                'song_style': "",
            }
            st.session_state.stage = 1
            st.session_state.history = []

        st.header("Key Management")

        # TODO(Ju): keep it in localstorage https://pypi.org/project/streamlit-local-storage/
        env_openai_api_key = os.getenv("OPENAI_API_KEY")
        openai_key = st.text_input("OpenAI API Key", type="password", value=env_openai_api_key or '')
        st.session_state.openai_key = openai_key

def get_asset_path(path):
    if not os.environ.get('ASSET_PATH'):
        raise Exception('ASSET_PATH not set')
    search_paths = os.environ['ASSET_PATH'].split(',')
    for search_path in search_paths:
        if Path(search_path).joinpath(path).exists():
            return Path(search_path).joinpath(path)
    raise Exception(f'Asset not found: {path}')

def get_build_path(path):
    if os.environ.get('BUILD_PATH'):
        return Path(os.environ['BUILD_PATH']) / path
    if os.environ.get('ASSET_PATH'):
        search_paths = os.environ['ASSET_PATH'].split(',')
        last_search_path = search_paths[-1]
        return Path(last_search_path) / 'build' / path
    return Path('.') / 'build' / path

def save_mp4(clip, path, fps=24):
    with NamedTemporaryFile(suffix='.m4a') as f:
        clip.write_videofile(path, fps=fps, codec="libx264",
                             temp_audiofile=f.name,
                             remove_temp=True,
                             audio_codec="aac",
                             threads=4)

def blacken_image(image):
  """
  Given a PIL.Image, return a new PIL.Image with black color 
  for any pixel in the parameter image. Transparent parts are left untouched.

  This version uses NumPy for faster processing.

  Args:
    image: The input PIL.Image object.

  Returns:
    A new PIL.Image object with black color for non-transparent pixels.
  """
  # Convert image to NumPy array
  img_array = np.array(image) 

  # Create a mask for non-transparent pixels
  alpha_mask = img_array[:, :, 3] > 0 

  # Create a black image with the same shape
  black_img = np.zeros_like(img_array)

  # Set non-transparent pixels to black
  black_img[alpha_mask] = [0, 0, 0, 255] 

  # Convert back to PIL Image
  new_image = Image.fromarray(black_img.astype('uint8')) 

  return new_image

def mask_alpha(input_image_path, output_mask_path, 
                    transparent_mask_color=(255, 255, 255, 0),
                    translucency_mask_color=(0, 0, 0),
                    opacity_mask_color=(255, 255, 255)):
    """
    Creates an alpha mask from a PNG image.

    Args:
        input_image_path (str): Path to the input PNG image.
        output_mask_path (str): Path to save the generated alpha mask.
        transparent_mask_color (tuple): RGBA color for fully transparent pixels.
        translucency_mask_color (tuple): RGB color for semi-transparent pixels.
        opacity_mask_color (tuple): RGB color for fully opaque pixels.
    """
    # Open the input image
    image = Image.open(input_image_path).convert("RGBA")
    width, height = image.size

    # Create a new image for the alpha mask
    alpha_mask = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pixels = image.load()
    mask_pixels = alpha_mask.load()

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]  # Get the RGBA values

            if a == 0:
                # Fully transparent
                mask_pixels[x, y] = transparent_mask_color
            elif 0 < a < 255:
                # Semi-transparent
                mask_pixels[x, y] = translucency_mask_color + (255,)
            else:
                # Fully opaque
                mask_pixels[x, y] = opacity_mask_color + (255,)

    # Save the alpha mask
    alpha_mask.save(output_mask_path, "PNG")

class Animation:

    @staticmethod
    def pan():
        def _(t):
            if t < 0.5 * t:
                scale = 0.2
            else:
                scale = 0.2 + 0.02 * math.sin(2 * math.pi * t)
            return scale
        return t


def make_rembg(image):
    image_path = get_asset_path(image)
    black_path = get_build_path(os.path.splitext(os.path.basename(image))[0] + "_black.png")
    rembg_path = get_build_path(os.path.splitext(os.path.basename(image))[0] + "_rembg.png")
    image = Image.open(image_path).convert("RGBA")
    rembg_image = rembg(image)
    rembg_image.save(rembg_path)
    mask_alpha(rembg_path, black_path,
        translucency_mask_color=(0, 0, 0),
        transparent_mask_color=(0, 0, 0, 0),
        opacity_mask_color=(0, 0, 0),
    )

elevenlabs_api_key = os.environ.get('ELEVENLABS_API_KEY') or ''
VOICES = {
    'Brian': 'nPczCjzI2devNBz1zQrb',
    'Alice': 'Xb7hH8MSUJpSbSDYk0k2',
    'Bella': 'jF58wCtan46ecp8biibj',
    'Jessica': 'lxYfHSkYm1EzQzGhdbfc',
    'Bill': 'pqHfZKP75CvOlQylNhV4',
    'Lily': 'pFZP5JQG7iQjIQuC4Bku',
    'Daniel': 'onwK4e9ZLuTAKqWW03F9',
    'Natsumi': 'vHHbGTOpiYVBAckPY1IO', # host
    'Whimsy': '542jzeOaLKbcpZhWfJDa',
    'Halley': 'eBvoGh8YGJn1xokno71w', # host, drama
    'KawaiiAerisita': 'vGQNBgLaiM3EdZtxIiuY', # drama
    'FreddyFox': 'KSb3AygB8nlskHweRc7e', # drama
    'Fredi': 'niWq5MaoVuyqimv1YYmn', # drama
    'SimonJ': 'mKYyBSIQcY1JmQlvU7CG', # drama
    'Daria': '9XfYMbJVZqPHaQtYnTAO', # drama
    'Cody': '9XfYMbJVZqPHaQtYnTAO', # host, drama
    'Arthur': 'TtRFBnwQdH1k01vR0hMz', # default
}
TTS_MODEL = 'eleven_flash_v2_5'
cache = dc.Cache(directory='.cache')


def make_voiceover(txt, voice='Arthur', model=TTS_MODEL):
    """Text to speech using Eleven, then save to a file."""
    hash = hashlib.md5(txt.encode()).hexdigest()
    suffix = txt[:10].replace(' ', '_').replace('\n', '_').replace(',', '_').replace('.', '_').replace('?', '_').replace('!', '_')
    cache_key = f'{voice}_{model}_{hash}_{suffix}'
    filename = f'/tmp/{cache_key}.mp3'

    if os.path.exists(filename):
        return filename

    if cache.get(cache_key):
        with open(filename, 'wb') as f:
            f.write(cache.get(cache_key))
        return filename

    client = ElevenLabs()
    audio = client.generate(text=txt, voice=VOICES[voice], model=TTS_MODEL)
    with open(filename, 'wb') as f:
        save_voiceover(audio, f.name)

    if os.stat(filename).st_size == 0:
        os.remove(filename)
        raise ValueError('Voiceover is empty. Please try again.')

    with open(filename, 'rb') as f:
        audio = f.read()
        cache.set(cache_key, audio)

    return filename
