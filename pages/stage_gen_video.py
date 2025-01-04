import streamlit as st
import traceback
import json
import os
import tempfile
from typing import Dict, Optional
from vima5.video_generator import VideoGenerator, VideoTrack  # Import from previous file

def validate_schema(schema_str: str) -> Optional[Dict]:
    """Validate and parse JSON schema."""
    try:
        schema = json.loads(schema_str)
        if not isinstance(schema, list):
            st.error("Schema must be a list of tracks")
            return None
        return schema
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON: {str(e)}")
        return None

def generate_video(schema: Dict, preview_resolution: str, download_resolution: str) -> tuple:
    """Generate both preview and download versions of the video."""
    # Create temporary directories for assets and output
    with tempfile.TemporaryDirectory() as temp_dir:
        preview_path = os.path.join(temp_dir, "preview.mp4")
        download_path = os.path.join(temp_dir, "download.mp4")
        
        try:
            # Generate preview version
            preview_generator = VideoGenerator(
                resolution=preview_resolution,
                asset_dir=".",  # Use current directory for assets
                out_dir=temp_dir
            )
            preview_generator.load_schema_object(schema)
            preview_generator.generate()
            preview_generator.save("preview.mp4")
            preview_generator.cleanup()
            
            # Generate download version
            download_generator = VideoGenerator(
                resolution=download_resolution,
                asset_dir=".",  # Use current directory for assets
                out_dir=temp_dir
            )
            download_generator.load_schema_object(schema)
            download_generator.generate()
            download_generator.save("download.mp4")
            download_generator.cleanup()
            
            # Read both files
            with open(preview_path, "rb") as f:
                preview_data = f.read()
            with open(download_path, "rb") as f:
                download_data = f.read()
                
            return preview_data, download_data
            
        except Exception as e:
            st.error(f"Error generating video: {str(e)}\n")
            print(traceback.format_exc())
            return None, None

def main():
    st.title("Video Generator")
    
    # Default schema example
    default_schema = '''[
    {
        "type": "fast_pace_color_swap",
        "start_time": 0,
        "end_time": 10,
        "order": 0,
        "parameters": {
            "page_duration": 2,
            "hex_colors": ["##FFD700", "#87CEEB", "#FF69B4", "#32CD32", "#FFA500"]
        }
    },
    {
        "type": "plain_lyrics",
        "start_time": 2,
        "end_time": 8,
        "order": 1,
        "parameters": {
            "text": "Hello World!",
            "position": "center"
        }
    }
]'''

    # Session state initialization
    if 'preview_video' not in st.session_state:
        st.session_state.preview_video = None
    if 'download_video' not in st.session_state:
        st.session_state.download_video = None

    # Sidebar for settings
    with st.sidebar:
        st.header("Settings")
        preview_resolution = st.selectbox(
            "Preview Resolution",
            ["360p", "480p", "720p", "1080p"],
            index=1  # Default to 480p
        )
        download_resolution = st.selectbox(
            "Download Resolution",
            ["360p", "480p", "720p", "1080p"],
            index=3  # Default to 1080p
        )

    # Main content
    with st.expander("JSON Schema Documentation", expanded=False):
        st.markdown("""
        ## Schema Format
        The schema should be a JSON array of tracks. Each track can have:
        
        - `type`: Track type ("fast_pace_color_swap", "plain_lyrics", "plain_gif")
        - `start_time`: Start time in seconds
        - `end_time`: End time in seconds
        - `order`: Layer order (higher numbers overlay lower numbers)
        - `parameters`: Type-specific parameters
        
        ### Track Types
        1. **fast_pace_color_swap**
           - `page_duration`: Duration for each color (default: 2s)
           - `hex_colors`: Array of color hex codes
           
        2. **plain_lyrics**
           - `text`: The text to display
           - `position`: "up", "down", "left", "right", or "center"
           
        3. **plain_gif**
           - `image`: Path to image file
           - `scale`: Scale factor
           - `position`: "up", "down", "left", "right", or "center"
        """)

    # Code editor
    schema_str = st.text_area("JSON Schema", value=default_schema, height=400)
    
    # Generate button
    if st.button("Generate Video"):
        schema = validate_schema(schema_str)
        if schema:
            with st.spinner("Generating video..."):
                preview_data, download_data = generate_video(
                    schema,
                    preview_resolution,
                    download_resolution
                )
                
                if preview_data and download_data:
                    st.session_state.preview_video = preview_data
                    st.session_state.download_video = download_data
                    st.success("Video generated successfully!")

    # Display preview and download button
    if st.session_state.preview_video:
        st.subheader("Preview")
        st.video(st.session_state.preview_video)
        
        st.download_button(
            label=f"Download Video ({download_resolution})",
            data=st.session_state.download_video,
            file_name="generated_video.mp4",
            mime="video/mp4"
        )

main()
