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
from moviepy import ImageSequenceClip

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
                 limb_color: str = "#000000"):
        self.torso = Image.open(torso_path)
        self.points = points
        self.limb_width = 3
        self.limb_color = limb_color
        self.foot_length = 20
        # Initialize all joint positions
        self._initialize_joints()
    
    def _initialize_joints(self):
        """Initialize all joint positions based on provided anchor points."""
        # Default positions for joints not provided in input
        default_lengths = {
            "shoulder_to_elbow": 40,
            "elbow_to_wrist": 35,
            "hip_to_knee": 45,
            "knee_to_ankle": 40
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

    def _calculate_foot_points(self, ankle_point: Tuple[int, int],
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
        frame = Image.new('RGBA', frame_size, (255, 255, 255, 0))

        # Paste torso
        frame.paste(self.torso, (0, 0), self.torso)

        draw = ImageDraw.Draw(frame)
        
        # Update all joint positions based on angles
        current_points = self.points.copy()
        
        # Define limb lengths
        limb_lengths = {
            ("left_shoulder", "left_elbow"): 40,
            ("left_elbow", "left_wrist"): 35,
            ("right_shoulder", "right_elbow"): 40,
            ("right_elbow", "right_wrist"): 35,
            ("left_hip", "left_knee"): 45,
            ("left_knee", "left_ankle"): 40,
            ("right_hip", "right_knee"): 45,
            ("right_knee", "right_ankle"): 40,
        }
        
        # Draw limbs
        for (start_joint, end_joint), length in limb_lengths.items():
            if start_joint in current_points and angles.get(start_joint) is not None:
                end_point = self._draw_limb(
                    draw, 
                    current_points[start_joint],
                    angles[start_joint],
                    length
                )
                current_points[end_joint] = end_point
                
                # Draw fingers at wrist positions
                if end_joint.endswith('wrist'):
                    fingers = self._calculate_finger_points(
                        end_point,
                        angles[start_joint]  # Use the same angle as the forearm
                    )
                    for finger_points in fingers:
                        self._draw_bezier_curve(draw, finger_points, width=self.limb_width, color=self.limb_color)

                # Draw feet at ankle positions
                if end_joint.endswith('ankle'):
                    foot = self._calculate_foot_points(end_point, angles[end_joint], foot_length=self.foot_length)
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
                
                frames.append(np.array(self.generate_frame(current_angles)))
        
        # Create GIF using moviepy
        clip = ImageSequenceClip(frames, fps=motion.fps)
        clip.write_gif(output_path, fps=motion.fps)

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
    generator = AnimationGenerator(args.torso, points, limb_color=args.limb_color)
    generator.generate_animation(motion, args.path)

if __name__ == '__main__':
    main()
