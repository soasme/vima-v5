import os
import json
import streamlit as st
from templates.balloonpop import movie, make_page


st.title('Balloon Pop Video Generator')

# project id
project_id = st.text_input('Project ID')

# create build dir
if project_id:
    build_dir = f'/tmp/{project_id}'
    if not os.path.exists(build_dir):
        os.makedirs(build_dir)

# textarea for JSON config

config_text = st.text_area('Paste JSON config here')
config = {}
if config_text:
    try:
        config = json.loads(config_text)
        config['input_dir'] = build_dir
        config['output'] = f'{build_dir}/output.mp4'
        config['compile'] = False
    except json.JSONDecodeError:
        st.error('Invalid JSON config')
        st.stop()

# upload files
st.write('Upload assets')
files = st.file_uploader('Upload assets', accept_multiple_files=True)
if files:
    for file in files:
        with open(f'{build_dir}/{file.name}', 'wb') as f:
            f.write(file.getbuffer())

# click button to generate video
if st.button('Generate Video'):
    for i in range(len(config['objects'])):
        make_page(config, i)

    movie.render_each_page(f'{build_dir}/output.mp4', fps=60)

    # List all files matching `output*.mp4` in the build directory
    if os.path.exists(build_dir):
        st.write('Generated files:')
        for file in os.listdir(build_dir):
            if file.startswith('output') and file.endswith('.mp4'):
                st.video(f'{build_dir}/{file}')
