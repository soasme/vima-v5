# TODO:
# Auto generate song/song style/image prompts for the each video types.
# Adapt all existing video types to this tool.

import os
import json
import re
import streamlit as st
import tarfile
import shutil
import time
import subprocess
from multiprocessing import Process
import glob
import threading
import datetime
import pandas as pd
import base64
from PIL import Image
from io import BytesIO
from pathlib import Path

PROJECT_DIR = '/tmp/vima5'


def sort_by_number(filenames):
    def extract_number(filename):
        match = re.search(r'output-(\d+)\.mp4', filename)
        return int(match.group(1)) if match else float('inf')

    return sorted(filenames, key=extract_number)

def clean_old_projects():
    """Delete project directories older than 24 hours"""
    tmp_dir = Path(PROJECT_DIR)
    os.makedirs(tmp_dir, exist_ok=True)

    current_time = time.time()
    one_day_in_seconds = 86400  # 24 hours
    
    for dir_name in os.listdir(tmp_dir):
        dir_path = os.path.join(tmp_dir, dir_name)
        if os.path.isdir(dir_path) and not dir_name.startswith('.'):
            try:
                # Check if this is a project directory
                if os.path.exists(os.path.join(dir_path, 'config.json')):
                    dir_mod_time = os.path.getmtime(dir_path)
                    if current_time - dir_mod_time > one_day_in_seconds:
                        shutil.rmtree(dir_path)
                        print(f"Deleted old project: {dir_name}")
            except Exception as e:
                print(f"Error cleaning directory {dir_path}: {e}")

# Clean old projects on startup
clean_old_projects()

def create_tar_archive(directory, output_filename):
    """Create a tar.gz archive of the directory"""
    with tarfile.open(output_filename, "w:gz") as tar:
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            tar.add(file_path, arcname=file)
    return output_filename

def is_video_generating(project_id):
    """Check if a video generation process is running for the project"""
    process_name = f"videogen_{project_id}"
    try:
        result = subprocess.run(
            ["pgrep", "-f", process_name], 
            capture_output=True, 
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False

def get_generation_progress(build_dir):
    """Count output MP4 files to track progress"""
    pattern = os.path.join(build_dir, "output*.mp4")
    files = glob.glob(pattern)
    return len(files)

def gen_video(config, project_id):
    build_dir = config['input_dir']
    
    # Save config to file
    with open(f"{build_dir}/config.json", 'w') as f:
        json.dump(config, f, indent=2)
    
    # Import the specific template module
    if config.get('video_type') == 'balloonpop':
        from templates.balloonpop import movie, make_page
    elif config.get('video_type') == 'brownbear':
        from templates.brownbear import movie, make_page
    elif config.get('video_type') == 'sharkinthewater':
        from templates.sharkinthewater import movie, make_page
    elif config.get('video_type') == 'findodd':
        from templates.findodd import movie, make_page
    elif config.get('video_type') == 'fingerfamily':
        from templates.fingerfamily import movie, make_page
    else:
        raise ValueError('Invalid video type')
    
    # Generate pages
    for i in range(len(config['clips'])):
        make_page(config, i)

    if config.get('compile'):
        movie.render(config['output'], fps=60)
    else:
        movie.render_each_page(config['output'], fps=60)

def start_video_generation(config, project_id):
    """Start video generation in a separate process"""
    p = Process(target=gen_video, args=(config, project_id))
    p.start()
    
    print(f"Started generation process {p}")
    return p

def get_image_preview(image_path):
    """Generate a thumbnail preview of an image"""
    img = Image.open(image_path)
    img.thumbnail((100, 100))
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    data = buffer.getvalue()
    return 'data:image/png;base64,' + base64.b64encode(data).decode()

# Initialize session state
if 'file_table' not in st.session_state:
    st.session_state.file_table = pd.DataFrame(columns=['filename', 'preview'])
if 'is_generating' not in st.session_state:
    st.session_state.is_generating = False
if 'generation_process' not in st.session_state:
    st.session_state.generation_process = None

st.title('Coofy Video Generator')

# Project ID input
project_id = st.text_input('Project ID', value=st.query_params.get('project_id') or '')

# Create/load build directory
if project_id:
    build_dir = f'/tmp/vima5/{project_id}'
    os.environ['ASSET_PATH'] = os.getcwd() + '/assets' + ',' + build_dir
    
    # Create directory if it doesn't exist
    if not os.path.exists(build_dir):
        os.makedirs(build_dir)
        st.session_state.config = {}
    else:
        # Try to load existing config
        config_path = os.path.join(build_dir, 'config.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    st.session_state.config = json.load(f)
                st.success(f"Loaded existing configuration for project {project_id}")
            except json.JSONDecodeError:
                st.warning("Found config file but it's invalid. Starting with empty config.")
                st.session_state.config = {}
        else:
            st.session_state.config = {}
    
    # Update file table
    files = []
    for filename in os.listdir(build_dir):
        file_path = os.path.join(build_dir, filename)
        if os.path.isfile(file_path) and not filename.startswith('output') and ('.png' in filename or '.jpg' in filename or '.gif' in filename):
            files.append({"filename": filename, "preview": get_image_preview(file_path)})
    
    st.session_state.file_table = pd.DataFrame(files)


# Video type selection
video_type_options = ['balloonpop', 'brownbear', 'sharkinthewater', 'findodd', 'fingerfamily']
video_type = st.selectbox('Video Type',
                          options=video_type_options, 
                         index=video_type_options.index(st.session_state.config.get('video_type', 'balloonpop')) 
                         if 'config' in st.session_state and st.session_state.config.get('video_type') in video_type_options else 0)

# Config textarea
config_default = json.dumps(st.session_state.config, indent=2) if 'config' in st.session_state and st.session_state.config else ""
config_text = st.text_area('Paste JSON config here', value=config_default)
if project_id and config_text:
    try:
        config = json.loads(config_text)
        config['input_dir'] = build_dir
        config['output'] = f'{build_dir}/output.mp4'
        config['compile'] = config.get('compile', False)
        config['video_type'] = video_type
        
        # Save config to session state
        st.session_state.config = config
        
        # Save config to file
        with open(f"{build_dir}/config.json", 'w') as f:
            json.dump(config, f, indent=2)
    except json.JSONDecodeError:
        st.error('Invalid JSON config')

# File uploader
st.write('Upload assets')
uploaded_files = st.file_uploader('Upload assets', accept_multiple_files=True)
if project_id and uploaded_files:
    for file in uploaded_files:
        with open(f'{build_dir}/{file.name}', 'wb') as f:
            f.write(file.getbuffer())
    
    # Refresh file table
    files = []
    for filename in os.listdir(build_dir):
        file_path = os.path.join(build_dir, filename)
        if os.path.isfile(file_path) and not filename.startswith('output') and ('.png' in filename or '.jpg' in filename or '.gif' in filename):
            files.append({"filename": filename, "preview": get_image_preview(file_path)})
    
    st.session_state.file_table = pd.DataFrame(files)

# File management table
if project_id and not st.session_state.file_table.empty:
    st.write("### Uploaded Files")
    
    # Display and allow editing of filenames
    edited_df = st.data_editor(
        st.session_state.file_table,
        column_config={
            "filename": st.column_config.TextColumn("Filename", width="medium"),
            "preview": st.column_config.ImageColumn("Preview", width="medium")
        },
        hide_index=True,
    )
    
    # Handle renamed files
    if not edited_df.equals(st.session_state.file_table):
        for i, row in edited_df.iterrows():
            old_filename = st.session_state.file_table.iloc[i]["filename"]
            new_filename = row["filename"]
            
            if old_filename != new_filename:
                old_path = os.path.join(build_dir, old_filename)
                new_path = os.path.join(build_dir, new_filename)
                
                if os.path.exists(old_path):
                    # Rename the file
                    os.rename(old_path, new_path)
                    st.success(f"Renamed {old_filename} to {new_filename}")
        
        # Update the session state with the new table
        st.session_state.file_table = edited_df

# Archive download button
if project_id and os.path.exists(build_dir) and os.listdir(build_dir):
    st.write("### Export Project")
    
    if st.button("Create Project Archive"):
        archive_path = create_tar_archive(build_dir, f"/tmp/{project_id}.tar.gz")
        
        with open(archive_path, "rb") as f:
            st.download_button(
                label="Download Project Archive",
                data=f,
                file_name=f"{project_id}.tar.gz",
                mime="application/gzip"
            )

# Generate video button
if project_id and 'config' in st.session_state and st.session_state.config:
    st.write("### Video Generation")
    
    # Check if a generation process is running
    is_running = is_video_generating(project_id)
    st.session_state.is_generating = is_running
    
    if is_running:
        st.warning("Video generation is currently in progress")
        
        # Display progress
        progress_placeholder = st.empty()
        progress_count = get_generation_progress(build_dir)
        progress_placeholder.write(f"Generated {progress_count} output files so far")
        
        # Refresh button
        if st.button("Refresh Progress"):
            st.experimental_rerun()
    
    elif st.button('Generate Video'):
        # Start generation
        config = st.session_state.config
        if 'clips' not in config or not config['clips']:
            st.error("Config must contain 'clips' array")
        else:
            try:
                # Indicate generation is starting
                with st.spinner("Starting video generation..."):
                    process = start_video_generation(config, project_id)
                    st.session_state.generation_process = process
                    st.session_state.is_generating = True
                
                st.success("Video generation started")
            except Exception as e:
                st.error(f"Error starting video generation: {str(e)}")
                import traceback; traceback.print_exc()

# Display generated videos
if project_id and os.path.exists(build_dir):
    output_files = glob.glob(f"{build_dir}/output*.mp4")
    
    if output_files:
        st.write('### Generated Videos')
        
        for file_path in sort_by_number(output_files):
            file_name = os.path.basename(file_path)
            create_time = datetime.datetime.fromtimestamp(os.path.getctime(file_path))
            
            st.write(f"**{file_name}** (Created: {create_time})")
            st.video(file_path)

            with open(file_path, "rb") as f:
                st.download_button(
                    label=f"Download {file_name}",
                    data=f,
                    file_name=file_name,
                    mime="video/mp4"
                )

            if st.button(f'Delete {file_name}'):
                os.remove(file_path)
                st.success(f"Deleted {file_name}")

            st.write("---")
