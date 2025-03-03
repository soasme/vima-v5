# Let user split video by pages.
# Adjust start/end time of each clip to be relative to the page.

import math
import numpy as np
from contextlib import contextmanager
from PIL import Image, ImageColor, ImageFilter
from typing import Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from skimage.transform import resize
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
    movie: 'Movie' = None
    num: int = 1
    name: str = ''
    color: str = 'white'
    duration: float = 5.0
    background: str = ''
    animate: str = 'none'
    animate_config: Dict = field(default_factory=dict)
    elements: List[Element] = field(default_factory=list)

    def elem(self, clip, pagenum=0, duration=0, with_=None, **kwargs):
        if not pagenum:
            page = self.movie.current_page
    
        if duration != 0:
            kwargs['end'] = kwargs['start'] + duration
    
        elem = Element(page=page, **kwargs)
        elem.clip = clip
        page.elements.append(elem)
        return elem

@dataclass
class Movie:
    title: str = ''
    pages: List[Page] = field(default_factory=list)


    @contextmanager
    def page(self, name='', **kwargs):
        num = len(self.pages) + 1
        page = Page(
            movie=self,
            num=num,
            name=f'Page {num}' if not name else name,
            **kwargs
        )
        self.pages.append(page)
        yield page

    @property
    def current_page(self):
        if not self.pages:
            return None
        return self.pages[-1]

    def render(self, output='output.mp4', aspect_ratio='16:9', fps=30, resolution='1080p', filter='', extra_vclips=None, extra_aclips=None, upscaler=1):
        size = RESOLUTION_MAP.get(resolution, RESOLUTION_MAP['1080p']).get(aspect_ratio, RESOLUTION_MAP['1080p']['16:9'])
    
        clips = []
    
        filter = [int(f) for f in filter.split(',') if f]
    
        # Set start/end for each clip
        page_start_time = 0.0
        video_clips, audio_clips = [], []
        for page in self.pages:
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
    
        final = CompositeVideoClip(video_clips + (extra_vclips if extra_vclips else []))

        if upscaler != 1:
            final = final.resized(upscaler)

        if audio_clips:
            audio_clips = audio_clips + (extra_aclips if extra_aclips else [])
            final = final.with_audio(CompositeAudioClip(audio_clips))
    
        save_mp4(final, output, fps=fps)

    def render_each_page(self, output, *args, **kwargs):
        for page_num in range(1, len(self.pages) + 1):
            out = output.replace('.mp4', f'-{page_num}.mp4')
            self.render(filter=str(page_num), output=out, *args, **kwargs)

movie = Movie('Untitled Movie')

def add_page(name='', **kwargs):
    with movie.page(name=name, **kwargs) as page:
        return page

def current_page():
    return movie.current_page

def add_elem(clip, pagenum=0, duration=0, with_=None, **kwargs):
    page = current_page()
    return page.elem(clip, pagenum=pagenum, duration=duration, with_=with_, **kwargs)

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

def render_pages(output='output.mp4', aspect_ratio='16:9', fps=30, resolution='1080p', filter='', extra_vclips=None, extra_aclips=None):
    return movie.render(output=output, aspect_ratio=aspect_ratio, fps=fps, resolution=resolution, filter=filter, extra_vclips=extra_vclips, extra_aclips=extra_aclips)

def render_each_page(output, *args, **kwargs):
    return movie.render_each_page(output, *args, **kwargs)

@dataclass
class Blur(Effect):
    sigma: float = 3.0

    def apply(self, clip):
        def blur(get_frame, t):
            frame = get_frame(t)
            img = Image.fromarray(frame)
            return np.array(img.filter(ImageFilter.GaussianBlur(self.sigma)))

        return clip.transform(blur)

@dataclass
class FloatAnimation(Effect):
    axis: str = 'y'
    scale: float = 10.0

    def apply(self, clip):
        if self.axis == 'x':
            return clip.with_position(lambda t: (
                clip.pos(t)[0] - self.scale * math.sin(3 * t),
                clip.pos(t)[1]
            ))
        elif self.axis == 'y':
            return clip.with_position(lambda t: (
                clip.pos(t)[0],
                clip.pos(t)[1] - self.scale * math.sin(3 * t)
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


# This implemenentation is slow.
# Also, it shows a black bg.
@dataclass
class Flip(Effect):
    duration: float
    rotation_axis: str = 'vertical'

    def apply(self, clip: Clip) -> Clip:
        def make_frame(get_frame, t):
            img = get_frame(t)
            img_width, img_height = img.shape[1], img.shape[0]

            # Calculate rotation angle based on time
            angle = (t / self.duration) * 360  # Complete 360-degree rotation
            
            # Create transformation matrix
            if self.rotation_axis == 'vertical':
                # Scale factor changes based on sine of angle to simulate perspective
                scale = abs(np.cos(np.radians(angle)))
                new_width = int(img_width * scale)
                if new_width < 1:  # Prevent width from becoming 0
                    new_width = 1
                
                # Resize image based on perspective
                frame = resize(img, (img_height, new_width), anti_aliasing=True)
                
                # Create background
                background = np.zeros((img_height, img_width, 3), dtype=np.uint8)
                
                # Calculate position to paste the resized image
                x_offset = (img_width - new_width) // 2
                background[:, x_offset:x_offset + new_width] = frame
                
            else:  # horizontal rotation
                # Scale factor changes based on sine of angle to simulate perspective
                scale = abs(np.cos(np.radians(angle)))
                new_height = int(img_height * scale)
                if new_height < 1:  # Prevent height from becoming 0
                    new_height = 1
                
                # Resize image based on perspective
                frame = resize(img, (img_width, new_height), anti_aliasing=True)
                
                # Create background
                background = np.zeros((img_height, img_width, 3), dtype=np.uint8)
                
                # Calculate position to paste the resized image
                y_offset = (img_height - new_height) // 2
                background[y_offset:y_offset + new_height, :] = frame
            
            return background
        return clip.transform(make_frame)

@dataclass
class SquishBounceEffect(Effect):

    #:param frequency: How fast the bouncing occurs (Hz, cycles per second)
    frequency: float = 2

    #:param amplitude: Maximum stretch/squish factor by unit vector.
    amplitude: float = 10

    def apply(self, clip):
        w, h = clip.size
        def resize(t):
            new_w = int(w + 10 * np.sin(2 * np.pi * self.frequency * t))
            new_h = int(h + 10 * np.cos(2 * np.pi * self.frequency * t))
            return (new_w, new_h)
        # fix the left bottom corner
        def newpos(t):
            x, y = clip.pos(t)
            new_w = int(w + 10 * np.sin(2 * np.pi * self.frequency * t))
            new_h = int(h + 10 * np.cos(2 * np.pi * self.frequency * t))
            delta_w = new_w - w
            delta_h = new_h - h
            return x - delta_w, y - delta_h
        return clip.with_effects([
            vfx.Resize(resize),
        ]).with_position(newpos)

@dataclass
class UniformMotion(Effect):
    from_position: tuple
    to_position: tuple

    def apply(self, clip):
        def newpos(t):
            x = int(self.from_position[0] + (self.to_position[0] - self.from_position[0]) * t/clip.duration)
            y = int(self.from_position[1] + (self.to_position[1] - self.from_position[1]) * t/clip.duration)
            return x, y
        return clip.with_position(newpos)

@dataclass
class UniformScale(Effect):
    from_scale: float
    to_scale: float
    duration: float = 0.0

    def apply(self, clip):
        def get_size(t):
            duration = self.duration or clip.duration
            if t >= duration:
                return self.to_scale
            return self.from_scale + (self.to_scale - self.from_scale) * t/duration
        return clip.resized(get_size)



@dataclass
class RemoveColor(Effect):
    color: Tuple[int, int, int]

    def apply(self, clip):
        def transform(frame):
            frame = np.array(frame, copy=True)
            mask = np.all(frame[..., :3] == np.array(self.color[:3]), axis=-1)
            if frame.shape[-1] == 3:
                alpha = np.ones(frame.shape[:2], dtype=np.uint8) * 255
                frame = np.dstack((frame, alpha))

            frame[mask, 3] = 0  # Set alpha to 0 where mask is True
            return frame.astype(np.uint8)

            #mask = np.all(frame == np.array(self.color), axis=-1)
            #frame = frame.astype(np.uint8) * ~mask[:, :, None]
            #frame[mask, 3] = 0
            #frame = np.dstack((frame, (~mask * 255).astype(np.uint8)))
            #mask = np.all(frame == self.color, axis=-1)
            #frame[mask] = [0, 0, 0, 0]
            return frame
        return clip.image_transform(transform)

# Buggy implementation, not working.
class Spring(Effect):
    """
    Effect that simulates spring physics to move a clip from one position to another.
    The clip will bounce around the target position before settling.
    
    Parameters:
    -----------
    from_position : tuple (x,y), optional
        Initial position
    to_position : tuple (x,y), optional
        Target position
    stiffness : float, optional
        Spring stiffness coefficient (higher = stronger spring)
    damping : float, optional
        Damping factor (higher = more damping, less oscillation)
    mass : float, optional
        Mass of the object (higher = more inertia)
    fps : int, optional
        Frames per second for physics calculation. Higher values give more accurate simulation.
    initial_velocity : tuple (vx, vy), optional
        Initial velocity of the clip
    """
    
    def __init__(self, from_position=(0,0), to_position=(0,0), 
                 stiffness=5.0, damping=0.5, mass=1.0, fps=24, 
                 initial_velocity=(0,0)):
        # Store parameters
        self.from_position = np.array(from_position, dtype=float)
        self.to_position = np.array(to_position, dtype=float)
        self.stiffness = stiffness
        self.damping = damping
        self.mass = mass
        self.fps = fps
        self.initial_velocity = np.array(initial_velocity, dtype=float)
         
    def _calculate_positions(self, clip):
        """Calculate all positions for the spring physics simulation"""
        # Initialize physics parameters
        pos = self.from_position.copy()
        vel = self.initial_velocity.copy()
        dt = 1.0 / self.fps
        
        # Pre-calculate all positions for smoothness
        t = np.arange(0, clip.duration, dt)
        positions = []
        
        # Run physics simulation
        for _ in t:
            # Spring force (Hooke's law): F = -k * (pos - equilibrium)
            spring_force = self.stiffness * (self.to_position - pos)
            
            # Damping force: F = -c * velocity
            damping_force = -self.damping * vel
            
            # Total force
            force = spring_force + damping_force
            
            # Acceleration (F = ma)
            acc = force / self.mass
            
            # Update velocity and position (Euler integration)
            vel = vel + acc * dt
            pos = pos + vel * dt
            
            positions.append(pos.copy())
        
        return np.array(positions)
    
 
    def apply(self, clip):
        """Apply the effect at time t (required by the Effect class)"""
        # This method doesn't need to do any transformation since we're using 
        # the with_position method in make_frame below
        # The frame transformation happens via the clip's position

        positions = self._calculate_positions(clip)

        def get_position(t):
            """Get the position at time t"""
            if t >= clip.duration:
                return tuple(self.to_position)
        
            idx = min(int(t * self.fps), len(positions) - 1)
            x = min(0, max(1920, positions[idx][0]))
            y = min(0, max(1080, positions[idx][1]))
            return int(x), int(y)

        return clip.with_position(get_position)
    

# Create a convenience function for moviepy's standard fx interface
def spring(clip, from_position=(0,0), to_position=(0,0), stiffness=5.0, 
           damping=0.5, mass=1.0, fps=None, initial_velocity=(0,0)):
    """Applies spring effect to the clip"""
    return Spring(clip, from_position, to_position, stiffness, 
                 damping, mass, fps, initial_velocity)

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


def anchor_center(box_top_left_x, box_top_left_y, box_width, box_height, width, height):
    return (
        box_top_left_x + box_width / 2 - width / 2,
        box_top_left_y + box_height / 2 - height / 2,
    )

