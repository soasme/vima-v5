import streamlit as st
from streamlit_extras.switch_page_button import switch_page
import pyquery as pq
import requests

from vima5.utils import display_sidebar

def extract_mp3_from_url(url):
    if not url:
        return None

    r = requests.get(url)
    r.raise_for_status()
    html = pq.PyQuery(r.text)
    return html('meta[name="twitter:player:stream"]').attr('content')

def page_content():
    st.header("Stage 3: Generate Song")

    st.write("Note: Auto gen via https://suno.com is still in development. For now, you can manually generate the song url.")
    st.write("Step 1. Go to https://suno.com/create")
    st.write("Step 2. Enter song title, song lyrics and song style and click Create button.")
    st.write("Step 3. Keep generating until get satisfied song. Click share button to copy link. It has a form like this: https://suno.com/song/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")

    song_url = st.text_input("Song URL", value=st.session_state.generated_content.get('song_url', ""))
    if st.button("Save Song URL"):
        st.session_state.generated_content['song_url'] = song_url
        st.session_state.history.append({"stage": "gensong", "content": song_url})
        st.success("Song URL saved!")

    if not st.session_state.generated_content.get('song_mp3'):
        extract_mp3 = extract_mp3_from_url(st.session_state.generated_content['song_url'])
        st.session_state.generated_content['song_mp3'] = extract_mp3

        if extract_mp3:
            st.success("Song MP3 extracted!")

    if st.session_state.generated_content.get('song_mp3'):
        st.audio(st.session_state.generated_content['song_mp3'], format='audio/mp3')

    if st.button("Continue to Stage 4: Segment Song"):
        switch_page("stage_segment_song")

display_sidebar()
page_content()
