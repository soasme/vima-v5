import io
from tempfile import NamedTemporaryFile

import streamlit as st
from streamlit_extras.switch_page_button import switch_page
import requests
import whisper_timestamped as whisper
from whisper_timestamped.make_subtitles import write_vtt

from vima5.utils import display_sidebar, update_session, get_session

def format_timestamp(seconds: float, always_include_hours: bool = False, decimal_marker: str = '.'):
    assert seconds >= 0, "non-negative timestamp expected"
    milliseconds = round(seconds * 1000.0)

    hours = milliseconds // 3_600_000
    milliseconds -= hours * 3_600_000

    minutes = milliseconds // 60_000
    milliseconds -= minutes * 60_000

    seconds = milliseconds // 1_000
    milliseconds -= seconds * 1_000

    hours_marker = f"{hours:02d}:" if always_include_hours or hours > 0 else ""
    return f"{hours_marker}{minutes:02d}:{seconds:02d}{decimal_marker}{milliseconds:03d}"

def write_srt(result):
    srt = []
    for i, segment in enumerate(result, start=1):
        # write srt lines
        srt.append(
            f"{i}\n"
            f"{format_timestamp(segment['start'], always_include_hours=True, decimal_marker=',')} --> "
            f"{format_timestamp(segment['end'], always_include_hours=True, decimal_marker=',')}\n"
            f"{segment['text'].strip().replace('-->', '->')}",
        )
    return srt


def download_song(mp3_url, cached_file):
    r = requests.get(mp3_url)
    cached_file.write(r.content)

def segment_song(mp3_url):
    with NamedTemporaryFile(delete=True) as cached_file:
        download_song(st.session_state.generated_content['song_mp3'], cached_file)
        audio = whisper.load_audio(cached_file.name)
        model = whisper.load_model("tiny", device="cpu")
        result = whisper.transcribe(model, audio)
        return result

def page_content():
    st.header("Stage 4: Segment Song")

    if st.session_state.generated_content['song_mp3'] is None:
        st.error("Please generate a song first.")
        if st.button("Go back to Stage 3: Generate Song"):
            switch_page("stage_gensong")
            return

    st.audio(get_session('generated_content', 'song_mp3'), format='audio/mp3')

    if not get_session('generated_content', 'song_segmentation') or (
        st.button("Re-segment Song")
    ):
        with st.spinner('Segmenting song...'):
            result = segment_song(get_session('generated_content', 'song_mp3'))
            fp = io.StringIO()
            update_session(generated_content={
                "song_segmentation": result,
                'song_srt': write_srt(result['segments'])
            })
            st.success("Song segmented successfully!")


    if st.button("Autofix Lyrics"):
        st.success("Lyrics autofixed!")

    if st.button("Continue to Next Stage: Generate Storyboard"):
        switch_page("stage_storyboard")

    col_srt, col2_lyrics = st.columns(2)

    srt = get_session('generated_content', 'song_srt')
    new_srt = col_srt.text_area('SRT Subtitle', value='\n'.join(srt), height=len(srt)*16)

    if new_srt != '\n'.join(srt):
        update_session(generated_content={'song_srt': new_srt.splitlines()})

    col2_lyrics.text_area('Original Lyrics', value=get_session('generated_content', 'lyrics') or '', height=16*len(get_session('generated_content', 'lyrics').splitlines()))

    st.divider()

    st.header("Whisper Transcription")
    st.write(get_session('generated_content', 'song_segmentation'))




display_sidebar()
page_content()
