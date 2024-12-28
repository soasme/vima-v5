import streamlit as st
from openai import OpenAI

from utils import sidebar

openai_client = OpenAI()

TEMPLATE="""
Write suno music style prompt in 200 characters.
Use short words.
Each item is no more than three words.
Use your brain to list instruments for a catchy tune.
Only format those words separated by comma without any helpful information.
Include user input if provided.

User Input:
{song_style}

Lyrics:
{lyrics}
"""

def generate_song_style(lyrics, style):
    prompt = TEMPLATE.format(
        lyrics=lyrics,
        song_style=style,
    )
    
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def page_content():
    st.header("Stage 2: Generate Song")

    song_style = st.text_area("Song Style", value=st.session_state.song_style)

    if song_style != st.session_state.song_style:
        st.session_state.song_style = song_style

    if st.button("Generate Song Style"):
       with st.spinner("Generating song style..."):
            song_style = generate_song_style(st.session_state.generated_content['lyrics'], st.session_state.song_style)
            st.session_state.generated_content['song_style'] = song_style
            st.session_state.history.append({"stage": "song_style", "content": song_style})
            st.success("Song Style generated!")

    if st.session_state.generated_content['song_style']:
        st.text_area("Generated Song Style", st.session_state.generated_content['song_style'], height=300)

        if st.button("Continue to Stage 3: Generate Song"):
            st.write("TBD")



sidebar()
page_content()

