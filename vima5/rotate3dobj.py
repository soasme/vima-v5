import argparse
import sys
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import NodePath, WindowProperties, LColor, LPoint3
import numpy as np
import os
from PIL import Image
from moviepy import vfx, ImageSequenceClip
from vima5.canva import *
import tempfile
import time

class ModelToGif(ShowBase):
    def __init__(self, model_path, output_path="output.gif", duration=3.0, fps=30, 
                 scale=1.0,
                 canvas_width=1920, canvas_height=1080, 
                 background_color="#00b140", transparent=False):
        """
        Initialize the Panda3D application to load a model and create a GIF.
        
        Args:
            model_path (str): Path to the 3D model file
            output_path (str): Path where the GIF will be saved
            duration (float): Duration of the GIF in seconds
            fps (int): Frames per second
            canvas_width (int): Width of the canvas/window
            canvas_height (int): Height of the canvas/window
            background_color (str): Background color in hex format
        """
        # Initialize ShowBase
        ShowBase.__init__(self)
        
        # Store parameters
        self.output_path = output_path
        self.duration = duration
        self.fps = fps
        self.scale = scale
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.background_color = background_color
        self.transparent = transparent
        
        # Parse background color (hex to RGB)
        bg_hex = background_color.lstrip('#')
        bg_rgb = tuple(int(bg_hex[i:i+2], 16) for i in (0, 2, 4))
        self.bg_rgb = bg_rgb
        self.bg_color = LColor(bg_rgb[0]/255.0, bg_rgb[1]/255.0, bg_rgb[2]/255.0, 1)
        
        # Set the background color to chroma key green
        self.setBackgroundColor(self.bg_color)
        
        # Set window properties
        props = WindowProperties()
        props.setSize(canvas_width, canvas_height)
        props.setUndecorated(True)
        props.setFixedSize(True)  # Prevent window resizing
        self.win.requestProperties(props)
        
        # Wait for the window size to be applied
        self.ready_to_capture = False
        self.taskMgr.add(self.waitForWindowTask, "WaitForWindowTask")
        
        # Calculate total frames needed
        self.total_frames = int(duration * fps)
        self.frames_captured = 0
        
        # Create a temporary directory to store frames
        self.temp_dir = tempfile.mkdtemp()
        print(self.temp_dir)
        
        # Disable mouse control
        self.disableMouse()
        
        # Load the model
        self.model = self.loader.loadModel(model_path)
        
        # Reparent model to render
        self.model.reparentTo(self.render)
        self.model.setScale(self.scale, self.scale, self.scale)
        
        # Initialize model positioning as False
        self.model_positioned = False

    def waitForWindowTask(self, task):
        """Wait for window properties to be applied before starting capture."""
        # Check if window has reached target size
        if (self.win.getXSize() == self.canvas_width and 
            self.win.getYSize() == self.canvas_height):
            print(f"Window resized to {self.canvas_width}x{self.canvas_height}")
            
            # Position the model now that window size is correct
            if not self.model_positioned:
                self.position_model_in_frame()
                self.model_positioned = True
            
            # Wait an additional frame to ensure everything is stable
            if not hasattr(self, 'wait_count'):
                self.wait_count = 0
            
            self.wait_count += 1
            if self.wait_count >= 5:  # Wait 5 frames to be safe
                # Start the spinning and capturing tasks
                self.taskMgr.add(self.spinModelTask, "SpinModelTask")
                self.taskMgr.add(self.captureFrameTask, "CaptureFrameTask")
                self.ready_to_capture = True
                return Task.done
        
        return Task.cont
        
    def position_model_in_frame(self):
        """
        Position the model in the center of the frame and adjust camera
        to make sure all of the model is visible during rotation.
        """
        # Get the model's bounding volume
        min_point, max_point = self.get_model_bounds()
        
        # Calculate model dimensions
        width = max_point.getX() - min_point.getX()
        height = max_point.getZ() - min_point.getZ()
        depth = max_point.getY() - min_point.getY()
        
        # Find the largest dimension for proper scaling
        max_dimension = max(width, height, depth)
        
        # Center the model at origin
        center_x = (min_point.getX() + max_point.getX()) / 2
        center_y = (min_point.getY() + max_point.getY()) / 2
        center_z = (min_point.getZ() + max_point.getZ()) / 2
        self.model.setPos(-center_x, -center_y, -center_z)
        
        # Position the camera to see the whole model
        # Use the larger of width and height to ensure model stays in frame while rotating
        # Add a safety margin of 20%
        camera_distance = max_dimension * 1.2
        self.camera.setPos(0, -camera_distance, 0)
        self.camera.lookAt(0, 0, 0)
        
        # If model is taller than wide, adjust camera height
        aspect_ratio = self.canvas_width / self.canvas_height
        if height > width * aspect_ratio:
            self.camera.setZ(center_z)
        
        print(f"Model positioned: Camera at distance {camera_distance}")
    
    def get_model_bounds(self):
        """
        Get the bounding box of the model by calculating its extremes
        during a full rotation to ensure it stays in frame while spinning.
        """
        # Create a copy of the model to analyze rotation bounds
        test_model = NodePath("test_model")
        model_copy = self.model.copyTo(test_model)
        
        # Get initial bounds
        bounds = model_copy.getTightBounds()
        if not bounds:
            print("Warning: Could not get initial bounds, using defaults")
            return LPoint3(-1, -1, -1), LPoint3(1, 1, 1)
            
        min_point, max_point = bounds
        
        # Check bounds at different rotation angles
        for angle in range(0, 360, 15):  # Check every 15 degrees
            model_copy.setH(angle)
            angle_bounds = model_copy.getTightBounds()
            
            if angle_bounds:
                angle_min, angle_max = angle_bounds
                
                # Update min and max points
                min_point = LPoint3(
                    min(min_point.getX(), angle_min.getX()),
                    min(min_point.getY(), angle_min.getY()),
                    min(min_point.getZ(), angle_min.getZ())
                )
                
                max_point = LPoint3(
                    max(max_point.getX(), angle_max.getX()),
                    max(max_point.getY(), angle_max.getY()),
                    max(max_point.getZ(), angle_max.getZ())
                )
        
        # Clean up the test model
        test_model.removeNode()
        
        return min_point, max_point

    def spinModelTask(self, task):
        """Task to spin the model around its Z-axis."""
        angle_per_frame = 360.0 / self.total_frames
        self.model.setH(self.model, angle_per_frame)  # Rotate around Z-axis (H)
        return Task.cont
    
    def captureFrameTask(self, task):
        """Task to capture frames for the GIF."""
        if not self.ready_to_capture:
            return Task.cont
            
        if self.frames_captured < self.total_frames:
            # Capture the current frame
            frame_path = os.path.join(self.temp_dir, f"frame_{self.frames_captured:04d}.png")
            
            # Save screenshot with exact dimensions
            image = self.win.getScreenshot()
            if image:
                # Verify image size
                if image.getXSize() != self.canvas_width or image.getYSize() != self.canvas_height:
                    print(f"Warning: Image size mismatch: {image.getXSize()}x{image.getYSize()} vs expected {self.canvas_width}x{self.canvas_height}")
                    
                # Save the image
                image.write(frame_path)
                print(f"Captured frame {self.frames_captured+1}/{self.total_frames}")
                self.frames_captured += 1
            else:
                print("Failed to capture screenshot")
                
            return Task.cont
        else:
            # All frames captured, create the GIF
            self.create_gif()
            return Task.done
    
    def create_gif(self):
        """Create a GIF from the captured frames."""
        frame_files = sorted([os.path.join(self.temp_dir, f) for f in os.listdir(self.temp_dir) 
                             if f.startswith("frame_") and f.endswith(".png")])
        
        if not frame_files:
            print("Error: No frames were captured!")
            self.userExit()
            return
            
        # Verify all images have the same size
        first_img = Image.open(frame_files[0])
        first_size = first_img.size
        uniform_size = True
        
        for file in frame_files[1:]:
            img = Image.open(file)
            if img.size != first_size:
                print(f"Size mismatch detected: {file} has size {img.size}, expected {first_size}")
                uniform_size = False
                # Resize the image to match the first one
                resized_img = img.resize(first_size)
                resized_img.save(file)
        
        if not uniform_size:
            print("Warning: Some frames had different sizes and were resized to ensure consistency")
        
        # Create a GIF from frames
        try:
            clip = ImageSequenceClip(frame_files, fps=self.fps)
            clip = clip.with_effects([
                RemoveColor(self.bg_rgb)
            ])

            # Write the GIF
            clip.write_gif(self.output_path, fps=self.fps)
            print(f"GIF saved to {self.output_path}")
        except Exception as e:
            print(f"Error creating GIF: {e}")
        
        # Clean up
        for f in os.listdir(self.temp_dir):
            try:
                os.remove(os.path.join(self.temp_dir, f))
            except Exception as e:
                print(f"Error removing file {f}: {e}")
                
        try:
            os.rmdir(self.temp_dir)
        except Exception as e:
            print(f"Error removing temp directory: {e}")
        
        # Exit the application
        self.userExit()

def parse_args():
    parser = argparse.ArgumentParser(description="Create a spinning GIF from a 3D model.")
    parser.add_argument("model_path", type=str, help="Path to the 3D model file")
    parser.add_argument("-o", "--output", type=str, default="/tmp/output.gif", help="Path to save the GIF")
    parser.add_argument("-d", "--duration", type=float, default=3.0, help="Duration of the GIF in seconds")
    parser.add_argument("-f", "--fps", type=int, default=30, help="Frames per second")
    parser.add_argument("--width", type=int, default=1920, help="Width of the canvas/window")
    parser.add_argument("--height", type=int, default=1080, help="Height of the canvas/window")
    parser.add_argument("--scale", type=float, default=1.0, help="Scale factor for the model")
    parser.add_argument("--background", type=str, default="#00b140", help="Background color in hex format")
    parser.add_argument("--transparent", action="store_true", default=True, help="Create a transparent GIF")

    return parser.parse_args()

def main():
    args = parse_args()
    app = ModelToGif(
        model_path=args.model_path,
        output_path=args.output,
        duration=args.duration,  # 3 seconds of animation
        fps=args.fps,        # 30 frames per second
        scale=args.scale,
        canvas_width=args.width,
        canvas_height=args.height,
        background_color=args.background,
        transparent=args.transparent,
    )
    app.run()

if __name__ == '__main__':
    main()
