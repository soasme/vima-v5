import argparse
from dataclasses import dataclass
from enum import Enum
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import urllib.request

import numpy as np
from PIL import Image, ImageDraw
from moviepy import ImageSequenceClip, ImageClip

from typing import Tuple, List, Union
from collections import defaultdict
from random import randrange
from itertools import chain


class TransparentAnimatedGifConverter(object):
    _PALETTE_SLOTSET = set(range(256))

    def __init__(self, img_rgba: Image, alpha_threshold: int = 0):
        self._img_rgba = img_rgba
        self._alpha_threshold = alpha_threshold

    def _process_pixels(self):
        """Set the transparent pixels to the color 0."""
        self._transparent_pixels = set(
            idx for idx, alpha in enumerate(
                self._img_rgba.getchannel(channel='A').getdata())
            if alpha <= self._alpha_threshold)

    def _set_parsed_palette(self):
        """Parse the RGB palette color `tuple`s from the palette."""
        palette = self._img_p.getpalette()
        self._img_p_used_palette_idxs = set(
            idx for pal_idx, idx in enumerate(self._img_p_data)
            if pal_idx not in self._transparent_pixels)
        self._img_p_parsedpalette = dict(
            (idx, tuple(palette[idx * 3:idx * 3 + 3]))
            for idx in self._img_p_used_palette_idxs)

    def _get_similar_color_idx(self):
        """Return a palette index with the closest similar color."""
        old_color = self._img_p_parsedpalette[0]
        dict_distance = defaultdict(list)
        for idx in range(1, 256):
            color_item = self._img_p_parsedpalette[idx]
            if color_item == old_color:
                return idx
            distance = sum((
                abs(old_color[0] - color_item[0]),  # Red
                abs(old_color[1] - color_item[1]),  # Green
                abs(old_color[2] - color_item[2])))  # Blue
            dict_distance[distance].append(idx)
        return dict_distance[sorted(dict_distance)[0]][0]

    def _remap_palette_idx_zero(self):
        """Since the first color is used in the palette, remap it."""
        free_slots = self._PALETTE_SLOTSET - self._img_p_used_palette_idxs
        new_idx = free_slots.pop() if free_slots else \
            self._get_similar_color_idx()
        self._img_p_used_palette_idxs.add(new_idx)
        self._palette_replaces['idx_from'].append(0)
        self._palette_replaces['idx_to'].append(new_idx)
        self._img_p_parsedpalette[new_idx] = self._img_p_parsedpalette[0]
        del(self._img_p_parsedpalette[0])

    def _get_unused_color(self) -> tuple:
        """ Return a color for the palette that does not collide with any other already in the palette."""
        used_colors = set(self._img_p_parsedpalette.values())
        while True:
            new_color = (randrange(256), randrange(256), randrange(256))
            if new_color not in used_colors:
                return new_color

    def _process_palette(self):
        """Adjust palette to have the zeroth color set as transparent. Basically, get another palette
        index for the zeroth color."""
        self._set_parsed_palette()
        if 0 in self._img_p_used_palette_idxs:
            self._remap_palette_idx_zero()
        self._img_p_parsedpalette[0] = self._get_unused_color()

    def _adjust_pixels(self):
        """Convert the pixels into their new values."""
        if self._palette_replaces['idx_from']:
            trans_table = bytearray.maketrans(
                bytes(self._palette_replaces['idx_from']),
                bytes(self._palette_replaces['idx_to']))
            self._img_p_data = self._img_p_data.translate(trans_table)
        for idx_pixel in self._transparent_pixels:
            self._img_p_data[idx_pixel] = 0
        self._img_p.frombytes(data=bytes(self._img_p_data))

    def _adjust_palette(self):
        """Modify the palette in the new `Image`."""
        unused_color = self._get_unused_color()
        final_palette = chain.from_iterable(
            self._img_p_parsedpalette.get(x, unused_color) for x in range(256))
        self._img_p.putpalette(data=final_palette)

    def process(self) -> Image:
        """Return the processed mode `P` `Image`."""
        self._img_p = self._img_rgba.convert(mode='P')
        self._img_p_data = bytearray(self._img_p.tobytes())
        self._palette_replaces = dict(idx_from=list(), idx_to=list())
        self._process_pixels()
        self._process_palette()
        self._adjust_pixels()
        self._adjust_palette()
        self._img_p.info['transparency'] = 0
        self._img_p.info['background'] = 0
        return self._img_p


def _create_animated_gif(images: List[Image], durations: Union[int, List[int]]) -> Tuple[Image, dict]:
    """If the image is a GIF, create an its thumbnail here."""
    save_kwargs = dict()
    new_images: List[Image] = []

    for frame in images:
        thumbnail = frame.copy()  # type: Image
        thumbnail_rgba = thumbnail.convert(mode='RGBA')
        thumbnail_rgba.thumbnail(size=frame.size, reducing_gap=3.0)
        converter = TransparentAnimatedGifConverter(img_rgba=thumbnail_rgba)
        thumbnail_p = converter.process()  # type: Image
        new_images.append(thumbnail_p)

    output_image = new_images[0]
    save_kwargs.update(
        format='GIF',
        save_all=True,
        optimize=False,
        append_images=new_images[1:],
        duration=durations,
        disposal=2,  # Other disposals don't work
        loop=0)
    return output_image, save_kwargs


def save_transparent_gif(images: List[Image], durations: Union[int, List[int]], save_file):
    """Creates a transparent GIF, adjusting to avoid transparency issues that are present in the PIL library

    Note that this does NOT work for partial alpha. The partial alpha gets discarded and replaced by solid colors.

    Parameters:
        images: a list of PIL Image objects that compose the GIF frames
        durations: an int or List[int] that describes the animation durations for the frames of this GIF
        save_file: A filename (string), pathlib.Path object or file object. (This parameter corresponds
                   and is passed to the PIL.Image.save() method.)
    Returns:
        Image - The PIL Image object (after first saving the image to the specified target)
    """
    root_frame, save_args = _create_animated_gif(images, durations)
    root_frame.save(save_file, **save_args)

class TransitionType(Enum):
    NONE = "none"
    LINEAR = "linear"
    EASE_IN = "ease-in"
    EASE_OUT = "ease-out"
    EASE_IN_OUT = "ease-in-out"

@dataclass
class PointRotation:
    point_id: str
    angle: float

@dataclass
class Keyframe:
    rotations: List[PointRotation]
    transition: TransitionType
    duration: float  # seconds

@dataclass
class Motion:
    name: str
    keyframes: List[Keyframe]
    fps: int = 30

# Define limb connections
LIMB_CONNECTIONS = [
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
]

# Built-in motions
BUILT_IN_MOTIONS = {
    "simple-dance": Motion(
        name="simple-dance",
        fps=30,
        keyframes=[
            Keyframe(
                rotations=[
                    PointRotation("left_shoulder", 45),
                    PointRotation("left_elbow", 90),
                    PointRotation("left_wrist", 90),
                    PointRotation("right_shoulder", 135),
                    PointRotation("right_elbow", -90),
                    PointRotation("right_wrist", -45),
                    PointRotation("left_hip", 90),
                    PointRotation("left_knee", 45),
                    PointRotation("left_ankle", 0),
                    PointRotation("right_hip", 45),
                    PointRotation("right_knee", 135),
                    PointRotation("right_ankle", 0),
                ],
                transition=TransitionType.EASE_IN_OUT,
                duration=0.5
            ),
            Keyframe(
                rotations=[
                    PointRotation("left_shoulder", 45),
                    PointRotation("left_elbow", 0),
                    PointRotation("left_wrist", 90),
                    PointRotation("right_shoulder", 90),
                    PointRotation("right_elbow", -90),
                    PointRotation("right_wrist", -45),
                    PointRotation("left_hip", 30),
                    PointRotation("left_knee", 45),
                    PointRotation("left_ankle", 30),
                    PointRotation("right_hip", 120),
                    PointRotation("right_knee", 120),
                    PointRotation("right_ankle", 30),
                ],
                transition=TransitionType.EASE_IN_OUT,
                duration=0.5
            ),
            Keyframe(
                rotations=[
                    PointRotation("left_shoulder", 45),
                    PointRotation("left_elbow", 90),
                    PointRotation("left_wrist", 90),
                    PointRotation("right_shoulder", 135),
                    PointRotation("right_elbow", -90),
                    PointRotation("right_wrist", -45),
                    PointRotation("left_hip", 90),
                    PointRotation("left_knee", 45),
                    PointRotation("left_ankle", 0),
                    PointRotation("right_hip", 45),
                    PointRotation("right_knee", 135),
                    PointRotation("right_ankle", 0),
                ],
                transition=TransitionType.EASE_IN_OUT,
                duration=0.5
            ),
            # Add more keyframes for the dance...
        ]
    )
}

def make_bezier(xys):
    """
    Create a Bezier curve function from control points.
    Args:
        xys: sequence of 2-tuples (Bezier control points)
    Returns:
        Function that generates points along the Bezier curve
    """
    n = len(xys)
    combinations = pascal_row(n-1)
    def bezier(ts):
        result = []
        for t in ts:
            tpowers = (t**i for i in range(n))
            upowers = reversed([(1-t)**i for i in range(n)])
            coefs = [c*a*b for c, a, b in zip(combinations, tpowers, upowers)]
            result.append(
                tuple(sum([coef*p for coef, p in zip(coefs, ps)]) for ps in zip(*xys)))
        return result
    return bezier

def pascal_row(n, memo={}):
    """
    Returns the nth row of Pascal's Triangle.
    Uses memoization for efficiency.
    """
    if n in memo:
        return memo[n]
    result = [1]
    x, numerator = 1, n
    for denominator in range(1, n//2+1):
        x *= numerator
        x /= denominator
        result.append(x)
        numerator -= 1
    if n&1 == 0:
        result.extend(reversed(result[:-1]))
    else:
        result.extend(reversed(result))
    memo[n] = result
    return result

class MotionLoader:
    @staticmethod
    def load_motion(motion_source: str) -> Motion:
        """Load motion data from built-in library, file path, or URL."""
        if motion_source in BUILT_IN_MOTIONS:
            return BUILT_IN_MOTIONS[motion_source]
        
        if motion_source.startswith(('http://', 'https://')):
            with urllib.request.urlopen(motion_source) as response:
                motion_data = json.loads(response.read())
        else:
            with open(motion_source, 'r') as f:
                motion_data = json.load(f)
        
        return Motion(
            name=motion_data['name'],
            keyframes=[
                Keyframe(
                    rotations=[PointRotation(**r) for r in kf['rotations']],
                    transition=TransitionType(kf['transition']),
                    duration=kf['duration']
                )
                for kf in motion_data['keyframes']
            ],
            fps=motion_data.get('fps', 30)
        )

class AnimationGenerator:
    def __init__(self, torso_path: str, points: Dict[str, Tuple[int, int]],
                 limb_width: int = 10,
                 limb_color: str = "#000000"):
        self.torso_path = torso_path
        self.torso = Image.open(torso_path)
        self.points = points
        self.limb_width = limb_width
        self.limb_color = limb_color
        self.foot_length = 20
        # Initialize all joint positions
        self._initialize_joints()
    
    def _initialize_joints(self):
        """Initialize all joint positions based on provided anchor points."""
        # Default positions for joints not provided in input
        default_lengths = {
            "shoulder_to_elbow": 100,
            "elbow_to_wrist": 100,
            "hip_to_knee": 100,
            "knee_to_ankle": 100 
        }
        
        # Calculate initial positions for all joints
        if "left_shoulder" in self.points:
            self.points["left_elbow"] = (
                self.points["left_shoulder"][0],
                self.points["left_shoulder"][1] + default_lengths["shoulder_to_elbow"]
            )
            self.points["left_wrist"] = (
                self.points["left_elbow"][0],
                self.points["left_elbow"][1] + default_lengths["elbow_to_wrist"]
            )
        
        if "right_shoulder" in self.points:
            self.points["right_elbow"] = (
                self.points["right_shoulder"][0],
                self.points["right_shoulder"][1] + default_lengths["shoulder_to_elbow"]
            )
            self.points["right_wrist"] = (
                self.points["right_elbow"][0],
                self.points["right_elbow"][1] + default_lengths["elbow_to_wrist"]
            )
        
        if "left_hip" in self.points:
            self.points["left_knee"] = (
                self.points["left_hip"][0],
                self.points["left_hip"][1] + default_lengths["hip_to_knee"]
            )
            self.points["left_ankle"] = (
                self.points["left_knee"][0],
                self.points["left_knee"][1] + default_lengths["knee_to_ankle"]
            )
        
        if "right_hip" in self.points:
            self.points["right_knee"] = (
                self.points["right_hip"][0],
                self.points["right_hip"][1] + default_lengths["hip_to_knee"]
            )
            self.points["right_ankle"] = (
                self.points["right_knee"][0],
                self.points["right_knee"][1] + default_lengths["knee_to_ankle"]
            )
        
    def _interpolate_angle(self, start: float, end: float, 
                          transition: TransitionType, progress: float) -> float:
        """Interpolate between angles based on transition type."""
        if transition == TransitionType.NONE:
            return end if progress >= 1 else start
        
        if transition == TransitionType.LINEAR:
            return start + (end - start) * progress
        
        if transition == TransitionType.EASE_IN:
            t = progress * progress
        elif transition == TransitionType.EASE_OUT:
            t = 1 - (1 - progress) * (1 - progress)
        else:  # EASE_IN_OUT
            t = 2 * progress * progress if progress < 0.5 else 1 - pow(-2 * progress + 2, 2) / 2
            
        return start + (end - start) * t

    def _calculate_foot_points2(self, ankle_point: Tuple[int, int],
                               foot_angle: float = 0,
                               foot_length: int = 20) -> List[Tuple[int, int]]:
        """Calculate points for a foot from ankle position.
        The foot direction is applied with the ankle angle."""
        foot_tip_point = (
            int(ankle_point[0] + foot_length * math.cos(math.radians(foot_angle))),
            int(ankle_point[1] + foot_length * math.sin(math.radians(foot_angle)))
        )
        foot_points = [
            ankle_point,
            foot_tip_point,
        ]
        return foot_points

    def _calculate_foot_points(self, ankle_point: Tuple[int, int], 
                             ankle_angle: float, 
                             foot_length: int) -> List[Tuple[int, int]]:
        """Calculate points for foot shape."""
        rad = math.radians(ankle_angle)  # Adjust angle to make foot perpendicular
        toe_point = (
            int(ankle_point[0] + foot_length * math.cos(rad)),
            int(ankle_point[1] + foot_length * math.sin(rad))
        )
        heel_point = (
            int(ankle_point[0] - (foot_length * 0.3) * math.cos(rad)),
            int(ankle_point[1] - (foot_length * 0.3) * math.sin(rad))
        )
        return [heel_point, ankle_point, toe_point]
    
    def _calculate_finger_points(self, wrist_point: Tuple[int, int], 
                               wrist_angle: float, 
                               finger_length: int = 20) -> List[List[Tuple[int, int]]]:
        """Calculate points for three fingers from wrist position."""
        base_rad = math.radians(wrist_angle)
        finger_angles = [-15, 0, 15]  # Spread fingers by these angles
        fingers = []
        
        for angle_offset in finger_angles:
            rad = base_rad + math.radians(angle_offset)
            finger_end = (
                int(wrist_point[0] + finger_length * math.cos(rad)),
                int(wrist_point[1] + finger_length * math.sin(rad))
            )
            # Create control points for finger curve
            ctrl1 = (
                int(wrist_point[0] + finger_length * 0.3 * math.cos(rad)),
                int(wrist_point[1] + finger_length * 0.3 * math.sin(rad))
            )
            ctrl2 = (
                int(wrist_point[0] + finger_length * 0.7 * math.cos(rad)),
                int(wrist_point[1] + finger_length * 0.7 * math.sin(rad))
            )
            fingers.append([wrist_point, ctrl1, ctrl2, finger_end])
        
        return fingers

    def _calculate_full_arm_points(self, shoulder: Tuple[int, int], elbow: Tuple[int, int], 
                                 wrist: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Calculate control points for a full arm curve from shoulder to wrist."""
        # Add additional control points near the elbow for smoother bending
        ctrl1 = (
            int(shoulder[0] + (elbow[0] - shoulder[0]) * 0.4),
            int(shoulder[1] + (elbow[1] - shoulder[1]) * 0.4)
        )
        ctrl2 = (
            int(shoulder[0] + (elbow[0] - shoulder[0]) * 0.6),
            int(shoulder[1] + (elbow[1] - shoulder[1]) * 0.6)
        )
        ctrl3 = (
            int(elbow[0] + (wrist[0] - elbow[0]) * 0.4),
            int(elbow[1] + (wrist[1] - elbow[1]) * 0.4)
        )
        ctrl4 = (
            int(elbow[0] + (wrist[0] - elbow[0]) * 0.6),
            int(elbow[1] + (wrist[1] - elbow[1]) * 0.6)
        )
        
        return [shoulder, ctrl1, ctrl2, elbow, ctrl3, ctrl4, wrist]

    def _calculate_full_leg_points(self, hip: Tuple[int, int], knee: Tuple[int, int], 
                                 ankle: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Calculate control points for a full leg curve from hip to ankle."""
        # Similar to arm, but adjusted for leg proportions
        ctrl1 = (
            int(hip[0] + (knee[0] - hip[0]) * 0.4),
            int(hip[1] + (knee[1] - hip[1]) * 0.4)
        )
        ctrl2 = (
            int(hip[0] + (knee[0] - hip[0]) * 0.6),
            int(hip[1] + (knee[1] - hip[1]) * 0.6)
        )
        ctrl3 = (
            int(knee[0] + (ankle[0] - knee[0]) * 0.4),
            int(knee[1] + (ankle[1] - knee[1]) * 0.4)
        )
        ctrl4 = (
            int(knee[0] + (ankle[0] - knee[0]) * 0.6),
            int(knee[1] + (ankle[1] - knee[1]) * 0.6)
        )
        
        return [hip, ctrl1, ctrl2, knee, ctrl3, ctrl4, ankle]

    def _calculate_limb_position(self, start_point: Tuple[int, int], 
                               angle: float, length: float) -> Tuple[int, int]:
        """Calculate end position of a limb segment based on angle and length."""
        rad = math.radians(angle)
        return (
            int(start_point[0] + length * math.cos(rad)),
            int(start_point[1] + length * math.sin(rad))
        )
    
    def _draw_bezier_curve(self, draw: ImageDraw, 
                          control_points: List[Tuple[int, int]], 
                          color: Tuple[int, int, int, int] = (0, 0, 0, 255),
                          width: int = 3):
        """Draw a smooth Bezier curve using control points."""
        bezier = make_bezier(control_points)
        points = bezier(np.linspace(0, 1, 100))
        # Convert float tuples to integer tuples
        points = [(int(x), int(y)) for x, y in points]
        draw.line(points, fill=color, width=width, joint="curve")
    
    def _draw_limb(self, draw: ImageDraw, 
                   start_point: Tuple[int, int], 
                   angle: float, 
                   length: float, 
                   thickness: int = 3) -> Tuple[int, int]:
        """Draw a limb segment using Bezier curves for smoothness."""
        rad = math.radians(angle)
        end_x = start_point[0] + length * math.cos(rad)
        end_y = start_point[1] + length * math.sin(rad)
        end_point = (int(end_x), int(end_y))
        
        # Calculate control points for smooth curve
        ctrl1 = (
            int(start_point[0] + length * 0.33 * math.cos(rad)),
            int(start_point[1] + length * 0.33 * math.sin(rad))
        )
        ctrl2 = (
            int(start_point[0] + length * 0.66 * math.cos(rad)),
            int(start_point[1] + length * 0.66 * math.sin(rad))
        )
        
        # Draw the main limb curve
        self._draw_bezier_curve(draw, [start_point, ctrl1, ctrl2, end_point], 
                                color=self.limb_color,
                                width=thickness)
        
        return end_point

    def generate_frame(self, angles: Dict[str, float]) -> Image.Image:
        """Generate a single frame with given angles for all joints including fingers."""
        # frame size is a bit larger than torso image to fit limbs
        frame_size = (self.torso.width + 100, self.torso.height + 100)
        frame = Image.open(self.torso_path)
        #frame = Image.new('RGBA', frame_size, (255, 255, 255, 0))
        #frame.putalpha(0)

        # Paste torso
        #frame.paste(self.torso, (0, 0), self.torso)

        # Calculate positions for all joints
        limb_segments = {
            "left_arm": {
                "joints": ["left_shoulder", "left_elbow", "left_wrist"],
                "lengths": [40, 35]
            },
            "right_arm": {
                "joints": ["right_shoulder", "right_elbow", "right_wrist"],
                "lengths": [40, 35]
            },
            "left_leg": {
                "joints": ["left_hip", "left_knee", "left_ankle"],
                "lengths": [45, 40]
            },
            "right_leg": {
                "joints": ["right_hip", "right_knee", "right_ankle"],
                "lengths": [45, 40]
            }
        }

        draw = ImageDraw.Draw(frame)
        
        # Update all joint positions based on angles
        current_points = self.points.copy()
        
        # Draw full limbs with Bezier curves
        for limb_name, config in limb_segments.items():
            joints = config["joints"]
            lengths = config["lengths"]
            
            if joints[0] in self.points and all(angles.get(j) is not None for j in joints[:-1]):
                # Calculate positions for all joints in the limb
                positions = [self.points[joints[0]]]  # Start with the first joint
                current_point = positions[0]
                
                for i, joint in enumerate(joints[1:]):
                    current_point = self._calculate_limb_position(
                        current_point,
                        angles[joints[i]],
                        lengths[i]
                    )
                    positions.append(current_point)
                
                # Generate and draw the full limb curve
                if "arm" in limb_name:
                    curve_points = self._calculate_full_arm_points(*positions)
                    self._draw_bezier_curve(draw, curve_points, width=self.limb_width, color=self.limb_color)
                    
                    # Add fingers at the wrist
                    fingers = self._calculate_finger_points(
                        positions[-1],  # wrist position
                        angles[joints[-2]]  # use elbow angle
                    )
                    for finger_points in fingers:
                        self._draw_bezier_curve(draw, finger_points, width=self.limb_width-1, color=self.limb_color)
                
                else:  # leg
                    curve_points = self._calculate_full_leg_points(*positions)
                    self._draw_bezier_curve(draw, curve_points, width=self.limb_width, color=self.limb_color)
                    
                    # Add foot at the ankle
                    foot = self._calculate_foot_points(positions[-1], angles[joints[-1]], 
                                                     foot_length=self.foot_length)
                    draw.line(foot, fill=self.limb_color, width=self.limb_width)  
        return frame 

    def generate_animation(self, motion: Motion, output_path: str):
        """Generate full animation from motion data."""
        frames = []
        current_angles = {
            r.point_id: r.angle
            for r in motion.keyframes[0].rotations
        }
        
        for i in range(len(motion.keyframes)):
            current_frame = motion.keyframes[i]
            next_frame = motion.keyframes[(i + 1) % len(motion.keyframes)]
            
            frame_count = int(current_frame.duration * motion.fps)
            
            for f in range(frame_count):
                progress = f / frame_count
                
                # Update angles
                for rotation in current_frame.rotations:
                    current_angles[rotation.point_id] = self._interpolate_angle(
                        current_angles[rotation.point_id],
                        rotation.angle,
                        current_frame.transition,
                        progress
                    )
                
                frame = self.generate_frame(current_angles)
                frames.append(frame)
        
        # Create GIF using moviepy
        #clip = ImageSequenceClip(frames, fps=motion.fps, with_mask=True)
        #clip.write_gif(output_path, fps=motion.fps)
        #clip.write_videofile(output_path, fps=motion.fps, codec="libx264")
        #frames[0].save(output_path, save_all=True, append_images=frames[1:], duration=1000/motion.fps, loop=0)
        save_transparent_gif(frames, 1000/motion.fps, output_path)

def main():
    parser = argparse.ArgumentParser(description='Generate character animation')
    parser.add_argument('--torso', required=True, help='Path to torso image')
    parser.add_argument('--left-shoulder', required=True, help='Left shoulder position (x,y)')
    parser.add_argument('--right-shoulder', required=True, help='Right shoulder position (x,y)')
    parser.add_argument('--left-hip', required=True, help='Left hip position (x,y)')
    parser.add_argument('--right-hip', required=True, help='Right hip position (x,y)')
    parser.add_argument('--motion', required=True, help='Motion source (built-in name, file path, or URL)')
    parser.add_argument('--path', required=True, help='Output GIF path')
    parser.add_argument('--limb-color', required=True, help='Hex color of limbs')
    parser.add_argument('--fps', type=int, default=30, help='Frames per second')
    parser.add_argument('--limb-width', type=int, default=5, help='Width of limb segments')
    
    args = parser.parse_args()
    
    # Parse point coordinates
    points = {
        'left_shoulder': tuple(map(int, args.left_shoulder.split(','))),
        'right_shoulder': tuple(map(int, args.right_shoulder.split(','))),
        'left_hip': tuple(map(int, args.left_hip.split(','))),
        'right_hip': tuple(map(int, args.right_hip.split(','))),
    }
    
    # Load motion and generate animation
    motion = MotionLoader.load_motion(args.motion)
    generator = AnimationGenerator(args.torso, points, limb_color=args.limb_color,
                                   limb_width=args.limb_width)
    generator.generate_animation(motion, args.path)

if __name__ == '__main__':
    main()
