from openai import OpenAI
import streamlit as st
from streamlit_extras.switch_page_button import switch_page

from vima5.utils import display_sidebar, get_openai_client, update_session

STRUCTURES = [
        "intro-verse1-chorus-verse2-chorus-bridge-chorus-outtro",
        "intro-chorus-verse-chorus-outtro",
]

TEMPLATE="""Write a nursery song for {topic}.

* Remember to write one has very short intro and can hook interest in first 10 seconds.
* Song length is 1 min only.
* Use a lot of repetitions.
* Use lots of lots of repeat and catchy words.
* Use some meaningless but catchy sound in chorus.
* Has a strcucture of intro-chorus-verse-chorus-outtro.
* Use simple words.
* Format verse, chorus, bridge, etc with square brackets.
* Fast-paced, energetic songs with catchy electronic beats
* Humorous lyrics with unexpected twists and punchlines
* Mix of silly and "earworm" qualities that make songs memorable
* Character voices and sound effects that enhance entertainment value.
* Combination of real facts with absurd elements.
* Strong hooks that hit within first 3-5 seconds.
* Memorable catchphrases that kids will want to repeat.
* Clean humor that parents approve of but isn't "babyish".
* High-energy vocals with distinct character voices.
* Simple but catchy choruses that stick in viewers' heads.
* Make it fun and hilarious.

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
                    
    topic = st.text_input("What should the song be about?", value=st.session_state.user_input['topic'])
    
    topic_extra_input = st.text_area("Additional requirements for the lyrics (optional)", value=st.session_state.user_input['topic_extra_input'])
    
    # Update state variables when input changes
    if topic != st.session_state.user_input['topic'] or topic_extra_input != st.session_state.user_input['topic_extra_input']:
        update_session(user_input={"topic": topic, "topic_extra_input": topic_extra_input})

    if st.button("Generate Lyrics"):
        with st.spinner("Generating lyrics..."):
            lyrics = generate_lyrics(
                st.session_state.user_input['topic'],
                st.session_state.user_input['topic_extra_input']
            )
            update_session(
                generated_content={"lyrics": lyrics},
                history=[{"stage": "lyrics", "content": lyrics}]
            )
            st.success("Lyrics generated!")

    if st.session_state.generated_content['lyrics']:
        st.text_area("Generated Lyrics", st.session_state.generated_content['lyrics'], height=300)
    
        if st.button("Continue to Next Stage: Generate Song Style"):
            switch_page("stage_song_style")

    st.divider()
    st.write("### Prompt for OpenAI")
    st.code(f"""
{TEMPLATE.format(topic=st.session_state.user_input['topic'], extra_input=st.session_state.user_input['topic_extra_input'])}
    """)



display_sidebar()
page_content()
