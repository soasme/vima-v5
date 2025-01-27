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
    align: str = 'center'
    width: float = 1920
    height: float = 1080
    x: float = 0.0
    y: float = 0.0
    rotate: float = 0.0
    opacity: float = 1.0
    start_time: float = 0.0
    end_time: float = 0.0
    flip_horizontal: bool = False
    flip_vertical: bool = False
    clip: Optional[VideoClip] = None
    
    def position(self) -> tuple:
        """Calculate final position based on alignment and coordinates"""
        if self.align == 'center':
            return (self.x - self.width/2, self.y - self.height/2)
        elif self.align == 'top-left':
            return (self.x, self.y)
        # Add more alignment options as needed
        return (self.x, self.y)

@dataclass
class Page:
    color: str = 'white'
    duration: float = 5.0
    background: str = 'white'
    animate: str = 'none'
    animate_config: Dict = field(default_factory=dict)
    elements: List[Element] = field(default_factory=list)
    
    def add_element(self, element: Element) -> 'Page':
        """Add an element to the page and return self for chaining"""
        self.elements.append(element)
        return self

class CanvaBuilder:
    def __init__(self):
        self.pages: List[Page] = []
        self.width: int = 1920
        self.height: int = 1080
    
    def page(self, **kwargs) -> Page:
        """Create and add a new page"""
        page = Page(**kwargs)
        self.pages.append(page)
        return page
    
    def text(self, text: str, **kwargs) -> Element:
        """Create a text element"""
        clip = mpy.TextClip(text, font='Arial', size=(kwargs.get('width', 400), kwargs.get('height', 100)))
        return Element(clip=clip, **kwargs)
    
    def image(self, path: str, **kwargs) -> Element:
        """Create an image element"""
        clip = mpy.ImageClip(path)
        return Element(clip=clip, **kwargs)
    
    def video(self, path: str, **kwargs) -> Element:
        """Create a video element"""
        clip = VideoFileClip(path)
        return Element(clip=clip, **kwargs)
    
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
        """Render all pages into a final video"""
        clips = []
        
        for page in self.pages:
            # Create background
            bg = ColorClip(size=(self.width, self.height), color=ImageColor.getcolor(page.background, "RGB"))
            bg = bg.with_duration(page.duration)
            
            # Process elements
            elements = []
            for elem in page.elements:
                clip = elem.clip
                
                # Apply transformations
                if elem.flip_horizontal:
                    clip = clip.fx(mpy.vfx.mirror_x)
                if elem.flip_vertical:
                    clip = clip.fx(mpy.vfx.mirror_y)
                if elem.rotate != 0:
                    clip = clip.rotate(elem.rotate)
                if elem.opacity != 1.0:
                    clip = clip.with_opacity(elem.opacity)
                
                # Set timing
                if elem.end_time > elem.start_time:
                    clip = clip.with_start(elem.start_time)
                    clip = clip.with_end(elem.end_time)
                else:
                    clip = clip.with_duration(page.duration)
                
                # Set position
                pos = elem.position()
                clip = clip.with_position(pos)
                
                elements.append(clip)
            
            # Compose page
            page_clip = mpy.CompositeVideoClip([bg] + elements)
            
            # Apply page animations
            if page.animate != 'none':
                page_clip = self._apply_animations(page_clip, page.animate, page.animate_config)
            
            clips.append(page_clip)
        
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
