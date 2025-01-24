import io
import argparse
from tempfile import NamedTemporaryFile

import streamlit as st
from streamlit_extras.switch_page_button import switch_page
import requests
import whisper_timestamped as whisper
from whisper_timestamped.make_subtitles import write_vtt

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

def convert_srt(result):
    srt = []
    for i, segment in enumerate(result):
        # write srt lines
        start_text = format_timestamp(segment['start'], always_include_hours=True, decimal_marker=',')
        end_text = format_timestamp(segment['end'], always_include_hours=True, decimal_marker=',')
        lyrics = segment['text'].strip().replace('-->', '->')
        srt.append(f'{i+1}')
        srt.append(f'{start_text} --> {end_text}')
        srt.append(lyrics)
        srt.append('')
    return '\n'.join(srt)


def gen_srt(args):
    audio = whisper.load_audio(args.audio_path)
    model = whisper.load_model("tiny", device="cpu")
    result = whisper.transcribe(model, audio)
    srt = convert_srt(result['segments'])
    return srt

def gen_prompt(args):
    srt = gen_srt(args)
    lyrics = ''
    prompt = f"""
    I have this lyrics with some wrong text because auto transcribe is not perfect. Please reserve all timings and update the text.

    ## Original Lyrics:

    {lyrics}

    ## SRT:

    {srt}"""
    return prompt



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='GEN SRT')
    parser.add_argument('command', type=str, help='Command to run')
    parser.add_argument('--audio-path', type=str, help='mp3 path')
    args = parser.parse_args()

    if args.command == 'gensrt':
        print(gen_srt(args))
    elif args.command =='genprompt':
        print(gen_prompt(args))
