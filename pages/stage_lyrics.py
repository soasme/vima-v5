from openai import OpenAI
import streamlit as st
from streamlit_extras.switch_page_button import switch_page

from utils import sidebar, get_openai_client

TEMPLATE="""Write a nursery song for {topic},
Remember to write one has very short intro and can hook interest in first 30 seconds.
Use some meaningless but catchy sound in chorus.
Use a lot of repetitions.
Has a strcucture of intro-verse1-chorus-verse2-chorus-bridge-chorus-outtro.
Use simple words.
Ideal length is 2min.
Format verse, chorus, bridge, etc with square brackets.
{extra_input}"""

def generate_lyrics(topic, extra_input=""):
    prompt = TEMPLATE.format(
        topic=topic,
        extra_input=extra_input
    )
    client = get_openai_client()
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def page_content():
    st.header("Stage 1: Generate Lyrics")
                    
    topic = st.text_input("What should the song be about?", value=st.session_state.topic)
    
    topic_extra_input = st.text_area("Additional requirements for the lyrics (optional)", value=st.session_state.topic_extra_input)
    
    # Update state variables when input changes
    if topic != st.session_state.topic:
        st.session_state.topic = topic
    if topic_extra_input != st.session_state.topic_extra_input:
        st.session_state.topic_extra_input = topic_extra_input
    
    if st.button("Generate Lyrics"):
        with st.spinner("Generating lyrics..."):
            lyrics = generate_lyrics(
                st.session_state.topic,
                st.session_state.topic_extra_input)
            st.session_state.generated_content['lyrics'] = lyrics
            st.session_state.history.append({"stage": "lyrics", "content": lyrics})
            st.success("Lyrics generated!")

    if st.session_state.generated_content['lyrics']:
        st.text_area("Generated Lyrics", st.session_state.generated_content['lyrics'], height=300)
    
        if st.button("Continue to Next Stage: Generate Song Style"):
            switch_page("stage_song_style")

    st.divider()
    st.header("History")
    for item in st.session_state.history:
        if item['stage'] == 'lyrics':
            st.write(item['content'])
            st.divider()

sidebar()
page_content()
