import io
from tempfile import NamedTemporaryFile

import streamlit as st
from streamlit_extras.switch_page_button import switch_page
import requests
import whisper_timestamped as whisper
from whisper_timestamped.make_subtitles import write_vtt

from vima5.utils import display_sidebar, update_session, get_session

def parse_timestamp(timestamp: str, decimal_marker: str = '.'):
    parts = timestamp.split(':')
    assert len(parts) == 3, "timestamp should have 3 parts"
    hours, minutes, seconds = parts
    hours = int(hours)
    minutes = int(minutes)
    seconds, milliseconds = map(int, seconds.split(decimal_marker))
    return (hours * 3_600) + (minutes * 60) + seconds + (milliseconds / 1000)

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
        srt.append({
            'index': i+1,
            'start': format_timestamp(segment['start'], always_include_hours=True, decimal_marker=','),
            'start_seconds': segment['start'],
            'end': format_timestamp(segment['end'], always_include_hours=True, decimal_marker=','),
            'end_seconds': segment['end'],
            'text': segment['text'].strip().replace('-->', '->')
        })
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

    for idx, line in enumerate(get_session('generated_content', 'song_srt')):
        with st.form(f"form_{idx}"):
            start, end, text = line['start'], line['end'], line['text']
            new_range = st.slider(f"Range_{idx}", min_value=0.0, max_value=150.0, value=(line['start_seconds'], line['end_seconds']))
            new_start, new_end = new_range
            new_lyric = st.text_input(f"Lyric_{idx}", value=text)

            st.audio(get_session('generated_content', 'song_mp3'), format='audio/mp3', start_time=new_start, end_time=new_end, loop=True)

            submitted = st.form_submit_button("Submit")
            if submitted:
                srt = get_session('generated_content', 'song_srt')
                srt[idx] = {
                    'index': idx+1,
                    'start': format_timestamp(new_start, always_include_hours=True, decimal_marker=','),
                    'start_seconds': new_start,
                    'end': format_timestamp(new_end, always_include_hours=True, decimal_marker=','),
                    'end_seconds': new_end,
                    'text': new_lyric,
                }
                ## update start and start_seconds for idx+1 if exists.
                if idx+1 < len(srt):
                    srt[idx+1]['start_seconds'] = new_end
                    srt[idx+1]['start'] = format_timestamp(new_end, always_include_hours=True, decimal_marker=',')
                ## Update end and end_seconds for idx-1 if exists.
                if idx-1 >= 0:
                    srt[idx-1]['end_seconds'] = new_start
                    srt[idx-1]['end'] = format_timestamp(new_start, always_include_hours=True, decimal_marker=',')


                update_session(generated_content={'song_srt': srt})

    st.divider()

    st.header("Whisper Transcription")
    st.write(get_session('generated_content', 'song_srt'))




display_sidebar()
page_content()
