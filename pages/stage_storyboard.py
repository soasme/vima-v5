import streamlit as st
from streamlit_extras.switch_page_button import switch_page

from vima5.utils import display_sidebar, update_session, get_session, get_openai_client

TEMPLATE_GROUP="""
Given lyrics, split them into groups of storyboards. Format it as storyboard number, duration, recommended sora duration (either 5s, 10s, 15s, 20s), and a list of subtitle ids. like `1|13s|15s|1,2`. The recommended sora duration is always greather than or equal to the duration. The subtitle ids are the ids of the subtitles that are part of the storyboard. The storyboard should be split into multiple storyboards if it is longer than 5s
ONLY Return the results without any other helpful information. This is for further code processing.
Lyrics:
{lyrics}
"""

TEMPLATE="""
Write video storyboard prompts for sora.com in text format for the given lyrics.
Remember to mention "The entire scene is whimsical and 2D animated and hand-drawn, with soft, vibrating outlines that bring a charming, magical touch to the visuals and matches to the imperfection of the frame-by-frame animation" for the first storyboard prompt.
You should avoid mentioning "kids" or "children" or asking to show any text in the prompt.
Always describe the looking feel of the character and the camera movement and style.
Be nice to sora: Don't use too complicated character actions, keep it simple like jumping, running, swimming, etc.
Remember, we are making a kids song video, so the storyboard should be simple and easy to understand, with a lot of visual cues, and the character should be cute and charming, with a lot of expressions, and the background should be colorful and vibrant.
Always start from 0s.
Format as a list of multiple storyboard prompts. Each storyboard prompt should be separated as Start, End, Visual Style, Scene Description, Camera Movement, Character Action, and Character Expression.

Song title: {song_title}
Song requirement: {song_extra}
Lyrics:
{lyrics}
"""

def generate_storyboard(song_title, song_extra, lyrics):
    prompt = TEMPLATE.format(
        song_title=song_title,
        song_extra=song_extra,
        lyrics=lyrics,
    )
    client = get_openai_client()
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def page_content():
    st.header("Stage 5: Storyboard")

    song_title = get_session('user_input', 'topic')
    song_extra = get_session('user_input', 'topic_extra_input')
    lyrics = st.text_area("Lyrics")
    if st.button("Generate Storyboard"):
        with st.spinner("Generating storyboard..."):
            storyboard = generate_storyboard(song_title, song_extra, lyrics)
            update_session(
                history=[{"stage": "storyboard", "content": storyboard}]
            )
            st.success("Storyboard generated!")

        st.write(storyboard)



display_sidebar()
page_content()
