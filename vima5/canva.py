"""
This module reads a json config file and generates a video similar to Canva data structure.
"""

import logging
import argparse
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union
import moviepy as mpy
from moviepy import *
from pathlib import Path
import importlib.util
from PIL import ImageColor
from vima5.utils import RESOLUTION_MAP, save_mp4
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@dataclass
class Element:
    align: str = 'none'
    width: float = 810
    height: float = 540
    x: float = 0.0
    y: float = 0.0
    rotate: float = 0.0
    opacity: float = 1.0
    start_time: float = 0.0 # Relative to page start
    end_time: float = 0.0 # Relative to page end
    flip_horizontal: bool = False
    flip_vertical: bool = False
    clip: Optional[VideoClip] = None
    builder: 'CanvaBuilder' = None
    
    def position(self) -> tuple:
        """Calculate final position based on alignment and coordinates"""
        if self.align == 'center':
            return (self.x - self.width/2, self.y - self.height/2)
        elif self.align == 'top-left':
            return (self.x, self.y)
        # Add more alignment options as needed
        return (self.x, self.y)

    def render(self) -> List[VideoClip]:
        """Render the element into a list of clips"""
        clip = self.clip
        if self.opacity != 1.0:
            clip = clip.with_opacity(self.opacity)

        fx = []
        if self.flip_horizontal:
            fx.append(vfx.MirroX())
        if self.flip_vertical:
            fx.append(vfx.MirroY())
        if self.rotate != 0:
            fx.append(vfx.Rotate(self.rotate))

        clip = clip.with_effects(fx)

        pos = self.position()
        clip = clip.with_position(pos)

        return [clip]

@dataclass
class Page:
    color: str = 'white'
    duration: float = 5.0
    background: str = 'white'
    animate: str = 'none'
    animate_config: Dict = field(default_factory=dict)
    elements: List[Element] = field(default_factory=list)
    builder: 'CanvaBuilder' = None
    
    def add(self, element: Element) -> 'Page':
        """Add an element to the page and return self for chaining"""
        self.elements.append(element)
        return self

    def render(self):
        clips = []

        # Page always has a background.
        # XXX: support attaching image/video as background
        background = (
            ColorClip(
                size=(1920, 1080),
                color=ImageColor.getcolor(self.background, "RGB"),
            )
            .with_duration(self.duration)
        )
        clips.append(background)

        # Append all elements to the page
        for element in self.elements:
            element_clips = element.render()

            # XXX: apply page animation to elements.
            clips.extend(element_clips)

        return clips

class CanvaBuilder:
    def __init__(self):
        self.pages: List[Page] = []
        self.width: int = 1920
        self.height: int = 1080
    
    def page(self, **kwargs) -> Page:
        """Create and add a new page"""
        page = Page(builder=self, **kwargs)
        self.pages.append(page)
        return page
    
    def text(self, text: str, **kwargs) -> Element:
        """Create a text element"""
        clip = TextClip(
            text=text,
            font='Arial',
            font_size=kwargs.pop('font_size', 24),
            color=kwargs.pop('color', 'black'),
            size=(kwargs.get('width', 400),
                  kwargs.get('height', 100)))
        return Element(builder=self, clip=clip, **kwargs)
    
    def image(self, path: str, **kwargs) -> Element:
        """Create an image element"""
        clip = ImageClip(path)
        return Element(builder=self, clip=clip, **kwargs)
    
    def video(self, path: str, **kwargs) -> Element:
        """Create a video element"""
        clip = VideoFileClip(path)
        return Element(builder=self, clip=clip, **kwargs)
    
    def _apply_animations(self, clip: VideoClip, animate: str, config: Dict) -> VideoClip:
        """Apply animations to a clip"""
        if animate == 'pan':
            start_pos = config.get('start_pos', (0, 0))
            end_pos = config.get('end_pos', (100, 100))
            return clip.with_position(lambda t: (
                start_pos[0] + (end_pos[0] - start_pos[0]) * t/clip.duration,
                start_pos[1] + (end_pos[1] - start_pos[1]) * t/clip.duration
            ))
        elif animate == 'fade':
            return clip.fadeout(config.get('duration', 1.0))
        return clip

    def _render(self, output_path: str = 'output.mp4'):
        clips = []
        current_time = 0.0
        for page in self.pages:
            page_clips = []

            # Turn all clip relative start_time/end_time to absolute
            for clip in page.render():
                clip = clip.with_start(clip.start + current_time)
                if clip.duration is None:
                    clip = clip.with_duration(page.duration)
                if clip.end is None or clip.end == 0:
                    clip = clip.with_end(clip.start + clip.duration)
                elif clip.end > 0:
                    clip = clip.with_end(clip.end + clip.end)
                page_clips.append(clip)

            # Make sure all page clips are within the page duration
            page_clips = [
                (clip if not clip.duration or clip.duration <= page.duration else clip.with_duration(page.duration))
                for clip in page_clips
            ]

            clips.extend(page_clips)

            current_time += page.duration

        for clip in clips:
            logger.debug(f"Clip: {clip}, start: {clip.start}, end: {clip.end}, duration: {clip.duration}, pos {clip.pos}, size {clip.size}")

        # Concatenate all pages
        if not clips:
            logger.warning("No pages to render")
            return

        final = concatenate_videoclips(clips)
        save_mp4(final, output_path)

    def render(self):
        """Render the video to a file"""
        parser = argparse.ArgumentParser(description='Canva-like video creator')
        parser.add_argument('--aspect-ratio', default='16:9', help='Video aspect ratio (e.g., 16:9)')
        parser.add_argument('--resolution', default='1080p', help='Video resolution (e.g., 1080p)')
        parser.add_argument('--output', default='output.mp4', help='Output video file')
        args = parser.parse_args()

        # Set up canvas dimensions based on arguments
        width, height = RESOLUTION_MAP[args.resolution].get(args.aspect_ratio, RESOLUTION_MAP[args.resolution]['16:9'])
        
        # Create global canva instance
        self.width = width
        self.height = height
        
        # Load and execute user script
        logger.debug(f"Rendering video with {len(self.pages)} pages, resolution {width}x{height}, aspect ratio {args.aspect_ratio}")
        self._render(args.output)


canva = CanvaBuilder()

"""
Example: To create a white/black flashing video,

```
from vima5.canva import *

canva.page(background='white', duration=1)
canva.page(background='black', duration=1)
canva.page(background='white', duration=1)
canva.page(background='black', duration=1)

canva.render()
```

"""
