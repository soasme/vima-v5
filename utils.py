import os
import json
from datetime import datetime

import streamlit as st

STAGE_LYRICS = 1
STAGE_SONG = 2
STAGE_TIMESTAMP = 3
STAGE_STORYBOARD = 4

def get_openai_client():
    return OpenAI(api_key=st.session_state.openai_key)

def init_session_state():
    if 'stage' not in st.session_state:
        st.session_state.stage = 1
    if 'generated_content' not in st.session_state:
        st.session_state.generated_content = {
            'lyrics': None,
            'song_title': None,
            'song_style': None,
            'song_url': None,
            'song_mp3': None,
            'style_prompt': None,
            'song': None,
            'timestamps': None,
            'storyboard': None
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
        'stage': st.session_state.stage,
        'topic': st.session_state.topic,
        'topic_extra_input': st.session_state.topic_extra_input,
        'song_style': st.session_state.song_style,
    }
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return json.dumps(session_data), f"kids_song_session_{timestamp}.json"

def load_session(file):
    try:
        content = file.read().decode('utf-8')
        session_data = json.loads(content)
        
        # Check for version, default to 1 if not present
        version = session_data.get('version', 1)
        
        st.session_state.generated_content = session_data['generated_content']
        st.session_state.history = session_data['history']
        st.session_state.stage = session_data['stage']
        st.session_state.topic = session_data.get('topic', "")
        st.session_state.topic_extra_input = session_data.get('topic_extra_input', "")
        st.session_state.song_style = session_data.get('song_style', "")

        return True
    except Exception as e:
        st.error(f"Error loading session: {str(e)}")
        return False

def sidebar():
    init_session_state()

    with st.sidebar:
        # Session management
        st.header("Session Management")

        # Session import (only in Stage 1)
        uploaded_file = st.file_uploader("Import previous session", type=['json'])
        if uploaded_file is not None:
            if load_session(uploaded_file):
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
                'style_prompt': None,
                'song': None,
                'timestamps': None,
                'storyboard': None
            }
            st.session_state.stage = 1
            st.session_state.history = []

        st.header("Key Management")

        # TODO(Ju): keep it in localstorage https://pypi.org/project/streamlit-local-storage/
        env_openai_api_key = os.getenv("OPENAI_API_KEY")
        openai_key = st.text_input("OpenAI API Key", type="password", value=env_openai_api_key or '')
        st.session_state.openai_key = openai_key
