import streamlit as st
from streamlit_extras.switch_page_button import switch_page

from vima5.utils import display_sidebar, get_openai_client

TEMPLATE="""
Write suno music style prompt in 200 characters.
Use short words.
Each item is no more than three words.
Use your brain to list instruments for a catchy tune.
Only format those words separated by comma without any helpful information.
Include user input if provided.
Always include "Partygrip style music, nursery rhyme, robotic sound, high pitch, energetic" in the output.

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
    
    openai_client = get_openai_client()

    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def page_content():
    st.header("Stage 2: Generate Song")

    song_style = st.text_area("Song Style", value=st.session_state.user_input['song_style'])

    if song_style != st.session_state.user_input['song_style']:
        update_session(user_input={"song_style": song_style})

    if st.button("Generate Song Style"):
       with st.spinner("Generating song style..."):
            song_style = generate_song_style(
                    st.session_state.generated_content['lyrics'],
                    st.session_state.user_input['song_style']
            )
            update_session(
                generated_content={"song_style": song_style},
                history=[{"stage": "song_style", "content": song_style}]
            )
            st.success("Song Style generated!")

    if st.session_state.generated_content['song_style']:
        st.write("### Generated Song Style")
        st.write(st.session_state.generated_content['song_style'])
        st.code(st.session_state.generated_content['song_style'])

        if st.button("Continue to Stage 3: Generate Song"):
            switch_page("stage_gensong")



display_sidebar()
page_content()

