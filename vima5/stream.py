"""
Stream multiple video files to YouTube using FFmpeg.

$ export YOUTUBE_STREAM_KEY=your_stream_key
$ echo "video1.mp4" > video_files.txt
$ echo "video2.mp4" >> video_files.txt
$ python stream.py video_files.txt
"""

import json
import sys
import subprocess
import time
import os
from typing import List
import logging

class YouTubeStreamer:
    def __init__(self, stream_key: str, video_files: List[str]):
        """
        Initialize the YouTube streamer
        
        Args:
            stream_key: YouTube stream key
            video_files: List of paths to video files to stream
        """
        self.stream_key = stream_key
        self.video_files = video_files
        self.rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def validate_files(self) -> bool:
        """Validate that all video files exist"""
        for video_file in self.video_files:
            if not os.path.exists(video_file):
                self.logger.error(f"File not found: {video_file}")
                return False
        return True

    def stream_video(self, video_file: str) -> subprocess.Popen:
        """
        Start streaming a single video file
        
        Args:
            video_file: Path to video file
            
        Returns:
            subprocess.Popen: The ffmpeg process
        """
        ffmpeg_cmd = [
            'ffmpeg',
            '-re',  # Read input at native frame rate
            '-i', video_file,
            '-c:v', 'libx264',  # Video codec
            '-preset', 'veryfast',  # Encoding preset
            '-b:v', '3000k',  # Video bitrate
            '-maxrate', '3000k',
            '-bufsize', '6000k',
            '-pix_fmt', 'yuv420p',
            '-g', '50',  # Keyframe interval
            '-c:a', 'aac',  # Audio codec
            '-b:a', '160k',  # Audio bitrate
            '-ar', '44100',  # Audio sample rate
            '-map', '0:v:0',  # Explicitly map video stream
            '-map', '0:a:0',  # Explicitly map audio stream
            '-f', 'flv',  # Output format
            '-flvflags', 'no_duration_filesize',  # Prevent duration/filesize metadata
            '-shortest',  # End encoding when shortest input stream ends
            self.rtmp_url
        ]
        
        self.logger.info(f"Starting stream for: {video_file}")
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return process

    def run(self):
        """Start streaming all videos in sequence"""
        if not self.validate_files():
            return

        for video_file in self.video_files:
            try:
                process = self.stream_video(video_file)
                
                # Wait for the stream to finish
                while process.poll() is None:
                    time.sleep(0.1)
                
                # Check if process ended with error
                if process.returncode != 0:
                    stderr = process.stderr.read().decode()
                    self.logger.error(f"FFmpeg error: {stderr}")
                    break
                    
            except Exception as e:
                self.logger.error(f"Error streaming {video_file}: {str(e)}")
                break

        self.logger.info("Streaming completed")

def main(video_files):
    # Example usage
    stream_key = os.environ.get('YOUTUBE_STREAM_KEY')
    if not stream_key:
        print("Please set the YOUTUBE_STREAM_KEY environment variable")
        return

    streamer = YouTubeStreamer(stream_key, video_files)
    streamer.run()

if __name__ == "__main__":
    video_files_list = sys.argv[1:]
    with open(video_files_list) as f:
        video_files = [l for l in f.read().splitlines() if l.strip()]
    main(video_files)
