import argparse
import json
import os
from typing import List, Dict, Tuple
import numpy as np
from moviepy import (
    ColorClip,
    TextClip,
    VideoFileClip,
    CompositeVideoClip,
    concatenate_videoclips
)

class VideoTrack:
    def __init__(self, track_data: Dict, resolution: tuple, asset_dir: str):
        self.type = track_data.get('type')
        self.start_time = track_data.get('start_time', 0)
        self.end_time = track_data.get('end_time', 0)
        self.order = track_data.get('order', 0)
        self.params = track_data.get('parameters', {})
        self.resolution = resolution
        self.asset_dir = asset_dir

    def _get_position(self, pos_str: str) -> tuple:
        """Convert position string to (x, y) coordinates."""
        width, height = self.resolution
        
        position_map = {
            'up': ('center', 50),
            'down': ('center', height - 50),
            'left': (50, 'center'),
            'right': (width - 50, 'center'),
            'center': ('center', 'center')
        }
        
        return position_map.get(pos_str, ('center', 'center'))

    def create_clip(self) -> VideoFileClip:
        """Create appropriate video clip based on track type."""
        clip_creators = {
            'fast_pace_color_swap': self._create_color_swap_clip,
            'plain_lyrics': self._create_lyrics_clip,
            'plain_gif': self._create_gif_clip
        }
        
        creator = clip_creators.get(self.type)
        if not creator:
            raise ValueError(f"Unsupported track type: {self.type}")
            
        clip = creator()
        return clip.set_start(self.start_time)

    def _create_color_swap_clip(self) -> VideoFileClip:
        """Create color swapping clip."""
        page_duration = self.params.get('page_duration', 2)
        hex_colors = self.params.get('hex_colors', ['#FF0000', '#00FF00', '#0000FF'])
        
        clips = []
        current_time = 0
        total_duration = self.end_time - self.start_time
        
        while current_time < total_duration:
            for color in hex_colors:
                duration = min(page_duration, total_duration - current_time)
                if duration <= 0:
                    break
                    
                clip = ColorClip(self.resolution, color, duration)
                clips.append(clip)
                current_time += duration
                
        return concatenate_videoclips(clips)

    def _create_lyrics_clip(self) -> VideoFileClip:
        """Create text clip for lyrics."""
        text = self.params.get('text', '')
        position = self.params.get('position', 'center')
        
        clip = TextClip(
            text,
            fontsize=40,
            color='white',
            size=self.resolution,
            duration=self.end_time - self.start_time
        )
        
        clip = clip.set_position(self._get_position(position))
        return clip

    def _create_gif_clip(self) -> VideoFileClip:
        """Create clip from GIF image."""
        image_path = self.params.get('image', '')
        scale = self.params.get('scale', 1.0)
        position = self.params.get('position', 'center')
        
        # Concatenate asset directory with image path
        full_image_path = os.path.join(self.asset_dir, image_path)
        
        if not os.path.exists(full_image_path):
            raise FileNotFoundError(f"Image file not found: {full_image_path}")
            
        clip = VideoFileClip(full_image_path, duration=self.end_time - self.start_time)
        
        # Scale the clip
        clip = clip.resize(scale)
        clip = clip.set_position(self._get_position(position))
        
        return clip

class VideoGenerator:
    RESOLUTION_MAP = {
        '360p': (480, 360),
        '480p': (640, 480),
        '720p': (1280, 720),
        '1080p': (1920, 1080)
    }

    def __init__(self, resolution: str = '720p', asset_dir: str = '.', out_dir: str = '.'):
        self.resolution = self.RESOLUTION_MAP.get(resolution, (1280, 720))
        self.asset_dir = os.path.abspath(asset_dir)
        self.out_dir = os.path.abspath(out_dir)
        self.tracks = []
        self.final_clip = None

    def load_schema(self, schema_path: str) -> None:
        """Load track data from JSON schema file."""
        with open(schema_path, 'r') as f:
            schema = json.load(f)
            
        self.tracks = []
        for track_data in schema:
            try:
                track = VideoTrack(track_data, self.resolution, self.asset_dir)
                self.tracks.append(track)
            except Exception as e:
                print(f"Error loading track: {e}")

    def generate(self) -> None:
        """Generate the final video by combining all tracks."""
        if not self.tracks:
            raise ValueError("No tracks loaded. Call load_schema first.")

        try:
            # Create clips for all tracks
            track_clips = []
            for track in self.tracks:
                try:
                    clip = track.create_clip()
                    track_clips.append((track.order, clip))
                except Exception as e:
                    print(f"Error processing track: {e}")
                    continue

            # Sort tracks by order (higher order overlays lower order)
            track_clips.sort(key=lambda x: x[0])

            # Create base clip with background color
            max_duration = max(track.end_time for track in self.tracks)
            base_clip = ColorClip(self.resolution, color=(0, 0, 0), duration=max_duration)

            # Combine all clips
            self.final_clip = CompositeVideoClip(
                [base_clip] + [clip for _, clip in track_clips]
            )

        except Exception as e:
            raise RuntimeError(f"Error generating video: {e}")

    def save(self, output_filename: str = 'output.mp4', fps: int = 30) -> None:
        """Save the generated video to file."""
        if self.final_clip is None:
            raise ValueError("No video generated. Call generate first.")

        # Create output directory if it doesn't exist
        os.makedirs(self.out_dir, exist_ok=True)
        
        # Write final video
        output_path = os.path.join(self.out_dir, output_filename)
        self.final_clip.write_videofile(output_path, fps=fps)

    def cleanup(self) -> None:
        """Clean up resources."""
        if self.final_clip is not None:
            self.final_clip.close()
            self.final_clip = None

def parse_args():
    parser = argparse.ArgumentParser(description='Generate video from JSON schema')
    parser.add_argument('--resolution', choices=['360p', '480p', '720p', '1080p'], 
                      default='720p', help='Video resolution')
    parser.add_argument('--asset-dir', default='.', help='Directory containing assets')
    parser.add_argument('--out-dir', default='.', help='Output directory')
    parser.add_argument('--input', required=True, help='Input JSON file')
    return parser.parse_args()

def main():
    args = parse_args()
    
    try:
        # Create video generator
        generator = VideoGenerator(
            resolution=args.resolution,
            asset_dir=args.asset_dir,
            out_dir=args.out_dir
        )
        
        # Generate and save video
        generator.load_schema(args.input)
        generator.generate()
        generator.save()
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        generator.cleanup()
    
    return 0

if __name__ == "__main__":
    exit(main())