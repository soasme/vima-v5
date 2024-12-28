import streamlit as st
import json
import os
from enum import IntEnum
from moviepy import *
import whisper
import time
from openai import OpenAI
from datetime import datetime
from streamlit_extras.switch_page_button import switch_page

from utils import *

# Initialize OpenAI client
openai_client = OpenAI()

STAGE_LYRICS = 1
STAGE_SONG = 2
STAGE_TIMESTAMP = 3
STAGE_STORYBOARD = 4



# [Previous template definitions remain the same]
TEMPLATES = {
    'lyrics': """Write a nursery song for {topic},
Remember to write one has very short intro and can hook interest in first 30 seconds.
Use some meaningless but catchy sound in chorus.
Use a lot of repetitions.
Has a strcucture of intro-verse1-chorus-verse2-chorus-bridge-chorus-outtro.
Use simple words.
Ideal length is 2min.
Format verse, chorus, bridge, etc with square brackets.
{extra_input}""",
    
    'style': """Write a suno prompt for making this catchy kids song. Make it under 200 characters and short words separated by comma.
{extra_input}""",
    
    'sora': """write a sora prompt in text for {section}.
Remember to describe the looking feel of the character.
The prompt is a {num_pages} page storyboard, with lyrics:
{lyrics}"""
}

# [Previous function definitions remain the same]
def generate_lyrics(topic, extra_input=""):
    prompt = TEMPLATES['lyrics'].format(
        topic=topic,
        extra_input=extra_input
    )
    
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def main():
    sidebar()

    st.markdown("""
    # 🎵 Kids Song Video Generator
    """)

    gen_lyrics = st.button("Stage 1: Generate Lyrics")
    if gen_lyrics:
        switch_page("stage_lyrics")

    gen_song_style = st.button("Stage 2: Generate Song Style")
    if gen_song_style:
        switch_page("stage_song_style")

    gen_song = st.button("Stage 3: Generate Song")
    if gen_song:
        switch_page("stage_gensong")



if __name__ == "__main__":
    main()
