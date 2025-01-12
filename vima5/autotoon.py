# Beat tracking example
import librosa
import moviepy as mp
import whisper_timestamped as whisper
import argparse

def segment_song(filename):
    audio = whisper.load_audio(filename)
    model = whisper.load_model("tiny", device="cpu")
    result = whisper.transcribe(model, audio)
    return result

def generate(song_file, keyframes, out_file):
    segments = segment_song(song_file)

    beat_times = []
    for segment in segments['segments']:
        for word in segment['words']:
            beat_times.append(word['start'])
            beat_times.append(word['end'])
    
    beat_img = mp.ImageClip(keyframes['beat'])
    non_beat_img = mp.ImageClip(keyframes['non_beat'])
    audio = mp.AudioFileClip(song_file)
    
    # 6. Set base clip to #00b140
    base_clip = mp.ColorClip(size=(1920, 1080), color=(0, 177, 64)).with_duration(audio.duration)
    
    # 7. Create a video clip with the beat image and non-beat image
    #   according to the beat times. Render beat image when beat, duration is 0.1s;
    #   Otherwise render non-beat image, fill the gap between beats.
    clips = [base_clip]
    previous_stop = 0.0
    for beat_time in beat_times:
        if beat_time < previous_stop:
            continue
    
        non_beat_clp = non_beat_img.with_duration(beat_time - previous_stop).with_start(previous_stop).with_position("center")
        beat_clp = beat_img.with_duration(0.1).with_start(beat_time).with_position("center")
    
        previous_stop = beat_time + 0.1
    
        clips.append(non_beat_clp)
        clips.append(beat_clp)
    
    final_clip = mp.CompositeVideoClip(clips)
    flnal_clip = final_clip.with_audio(audio)
    final_clip.write_videofile(out_file, codec="libx264", audio_codec="aac", fps=30)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("song_file", help="The song file to generate video")
    parser.add_argument("beat_keyframe", help="The keyframe for beat")
    parser.add_argument("non_beat_keyframe", help="The keyframe for non-beat")
    parser.add_argument("out_file", help="The output video file")
    args = parser.parse_args()
    generate(args.song_file, {
        "beat": args.beat_keyframe,
        "non_beat": args.non_beat_keyframe,
    }, args.out_file)
