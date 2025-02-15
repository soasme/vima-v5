# Let user split video by pages.
# Adjust start/end time of each clip to be relative to the page.

import math
import numpy as np
from PIL import Image, ImageColor, ImageFilter
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field
from moviepy import *
from moviepy.Effect import Effect
from moviepy.Clip import Clip
from vima5.utils import save_mp4, RESOLUTION_MAP

@dataclass
class Element:
    align: str = 'none'
    width: float = 810
    height: float = 540
    x: float = 0.0
    y: float = 0.0
    rotate: float = 0.0
    opacity: float = 1.0
    start: float = 0.0 # Relative to page start
    end: float = 0.0 # Relative to page end
    flip_horizontal: bool = False
    flip_vertical: bool = False
    page: Optional['Page'] = None

@dataclass
class Page:
    num: int = 1
    name: str = ''
    color: str = 'white'
    duration: float = 5.0
    background: str = ''
    animate: str = 'none'
    animate_config: Dict = field(default_factory=dict)
    elements: List[Element] = field(default_factory=list)


pages = []


def add_page(name='', **kwargs):
    num = len(pages) + 1
    page = Page(
        num=num,
        name=f'Page {num}' if not name else name,
        **kwargs
    )
    pages.append(page)
    return page


def anchor_center(box_top_left_x, tox_top_left_y, box_width, box_height, width, height):
    return (
        box_top_left_x + box_width / 2 - width / 2,
        tox_top_left_y + box_height / 2 - height / 2,
    )


def add_elem(clip, pagenum=0, duration=0, **kwargs):
    if not pagenum:
        page = pages[-1]

    if duration != 0:
        kwargs['end'] = kwargs['start'] + duration

    elem = Element(page=page, **kwargs)
    elem.clip = clip
    page.elements.append(elem)
    return elem

def current_page():
    return pages[-1]


def get_page_config(pagenum):
    return next(page for page in pages if page.num == pagenum)


def _get_page_background_clip(page, page_start_time, size):
    if '.png' in page.background or '.jpg' in page.background:
        return (
            ImageClip(page.background)
            .with_start(page_start_time)
            .with_duration(page.duration)
            .with_effects([vfx.Resize(size)])
        )
    elif '.mp4' in page.background:
        return (
            VideoFileClip(page.background)
            .with_start(page_start_time)
            .with_duration(page.duration)
            .with_effects([vfx.Resize(size)])
        )
    else:
        return (
            ColorClip(
                size=size,
                color=(
                    ImageColor.getrgb(page.background)
                    if page.background else (0, 0, 0, 0)))
            .with_start(page_start_time)
            .with_duration(page.duration)
        )

def render_pages(output='output.mp4', aspect_ratio='16:9', fps=30, resolution='1080p', filter=''):
    size = RESOLUTION_MAP.get(resolution, RESOLUTION_MAP['1080p']).get(aspect_ratio, RESOLUTION_MAP['1080p']['16:9'])

    clips = []

    filter = [int(f) for f in filter.split(',') if f]

    # Set start/end for each clip
    page_start_time = 0.0
    video_clips, audio_clips = [], []
    for page in pages:
        if filter and page.num not in filter:
            continue
        video_clips.append(_get_page_background_clip(page, page_start_time, size))
        for elem in page.elements:
            clip = elem.clip
            clip = clip.with_start(page_start_time + elem.start)
            clip = clip.with_end(page_start_time + (elem.end if elem.end else page.duration))
            if isinstance(clip, (AudioFileClip, CompositeAudioClip)):
                audio_clips.append(clip)
            else:
                video_clips.append(clip)
            
        page_start_time += page.duration

    final = CompositeVideoClip(video_clips)
    if audio_clips:
        final = final.with_audio(CompositeAudioClip(audio_clips))

    save_mp4(final, output, fps=fps)


def render_each_page(output, *args, **kwargs):
    for page_num in range(1, len(pages) + 1):
        out = output.replace('.mp4', f'-{page_num}.mp4')
        render_pages(filter=str(page_num), output=out, *args, **kwargs)



@dataclass
class FloatAnimation(Effect):
    axis: str = 'y'

    def apply(self, clip):
        if self.axis == 'x':
            return clip.with_position(lambda t: (
                clip.pos(t)[0] - 10 * math.sin(3 * t),
                clip.pos(t)[1]
            ))
        elif self.axis == 'y':
            return clip.with_position(lambda t: (
                clip.pos(t)[0],
                clip.pos(t)[1] - 10 * math.sin(3 * t)
            ))
        else:
            raise ValueError(f"Invalid axis: {self.axis}")



@dataclass
class Swing(Effect):
    """
    Creates a swinging motion by rotating the clip back and forth between two angles.
    The swing follows a smooth sinusoidal motion for natural-looking animation.

    Parameters
    ----------
    start_angle : float
        Starting angle of the swing motion.
    
    end_angle : float
        Ending angle of the swing motion.
    
    period : float
        Time in seconds for one complete swing cycle (from start to end and back).
    
    unit : str, optional
        Unit of angles (either "deg" for degrees or "rad" for radians).
        Default is "deg".
    
    resample : str, optional
        Resampling filter. One of "nearest", "bilinear", or "bicubic".
        Default is "bicubic".
    
    expand : bool, optional
        If true, expands the output image to hold the entire rotated image.
        Default is True.
    
    center : tuple, optional
        Center of rotation (a 2-tuple). Origin is the upper left corner.
        Default is None.
    
    translate : tuple, optional
        Post-rotate translation (a 2-tuple).
        Default is None.
    
    bg_color : tuple, optional
        Color for area outside the rotated image.
        Default is None.
    """
    
    start_angle: float
    end_angle: float
    period: float
    unit: str = "deg"
    resample: str = "bicubic"
    expand: bool = True
    center: tuple = None
    translate: tuple = None
    bg_color: tuple = None

    def apply(self, clip: Clip) -> Clip:
        """Apply the swinging effect to the clip."""
        # Validate and set up resampling filter
        try:
            resample = {
                "bilinear": Image.BILINEAR,
                "nearest": Image.NEAREST,
                "bicubic": Image.BICUBIC,
            }[self.resample]
        except KeyError:
            raise ValueError(
                "'resample' argument must be either 'bilinear', 'nearest' or 'bicubic'"
            )

        def get_swing_angle(t: float) -> float:
            """Calculate the angle at time t using a sine wave for smooth motion."""
            # Convert time to phase (0 to 2π)
            phase = (t % self.period) * (2 * math.pi / self.period)
            
            # Calculate the midpoint and amplitude of the swing
            mid_angle = (self.start_angle + self.end_angle) / 2
            amplitude = abs(self.end_angle - self.start_angle) / 2
            
            # Use sine wave to create smooth oscillation
            angle = mid_angle + amplitude * math.sin(phase)
            
            # Convert from radians if needed
            if self.unit == "rad":
                angle = math.degrees(angle)
            
            return angle

        def filter(get_frame, t):
            # Get current angle for this frame
            angle = get_swing_angle(t)
            im = get_frame(t)

            # Handle special cases for common angles
            angle %= 360
            if not self.center and not self.translate and not self.bg_color:
                if (angle == 0) and self.expand:
                    return im
                if (angle == 90) and self.expand:
                    transpose = [1, 0] if len(im.shape) == 2 else [1, 0, 2]
                    return np.transpose(im, axes=transpose)[::-1]
                elif (angle == 270) and self.expand:
                    transpose = [1, 0] if len(im.shape) == 2 else [1, 0, 2]
                    return np.transpose(im, axes=transpose)[:, ::-1]
                elif (angle == 180) and self.expand:
                    return im[::-1, ::-1]

            # Set up PIL rotation parameters
            pillow_kwargs = {}
            if self.bg_color is not None:
                pillow_kwargs["fillcolor"] = self.bg_color
            if self.center is not None:
                pillow_kwargs["center"] = self.center
            if self.translate is not None:
                pillow_kwargs["translate"] = self.translate

            # Handle mask images (float64 type)
            if im.dtype == "float64":
                scale_factor = 255.0
            else:
                scale_factor = 1

            # Perform the rotation using PIL
            rotated = np.array(
                Image.fromarray(np.array(scale_factor * im).astype(np.uint8)).rotate(
                    angle, 
                    expand=self.expand, 
                    resample=resample, 
                    **pillow_kwargs
                )
            ) / scale_factor

            return rotated

        return clip.transform(filter, apply_to=["mask"])


def paste_non_transparent(image_a, image_b, position=(0, 0)):
    """
    Pastes the non-transparent pixels of image_a onto image_b.

    Args:
        image_a: The source image (PIL Image object).
        image_b: The destination image (PIL Image object).
        position: The (x, y) coordinates where to paste image_a onto image_b.
    """

    if image_a.mode != "RGBA":
        image_a = image_a.convert("RGBA")  # Ensure image_a has an alpha channel

    if image_b.mode != "RGBA":
        image_b = image_b.convert("RGBA")  # Ensure image_b has an alpha channel

    width_a, height_a = image_a.size
    x_offset, y_offset = position

    for x in range(width_a):
        for y in range(height_a):
            r, g, b, a = image_a.getpixel((x, y))

            if a > 0:  # If pixel is not fully transparent
                # Calculate position in image_b, handling potential out-of-bounds
                x_b = x + x_offset
                y_b = y + y_offset

                if 0 <= x_b < image_b.width and 0 <= y_b < image_b.height:  # Check bounds
                    image_b.putpixel((x_b, y_b), (r, g, b, a))
