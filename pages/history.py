import streamlit as st
from vima5.utils import display_sidebar

def page_content():
    st.header("History")

    st.markdown("""
    This page shows the history of your generated content.
    """)

    for i, element in enumerate(reversed(st.session_state.history)):
        st.write(f"Step {i+1}")
        st.write(element)

display_sidebar()
page_content()
