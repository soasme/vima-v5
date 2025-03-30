import os
import json
import streamlit as st


st.title('Balloon Pop Video Generator')

# project id
project_id = st.text_input('Project ID')

# create build dir
if project_id:
    build_dir = f'/tmp/{project_id}'
    os.environ['ASSET_PATH'] = os.getcwd() + '/assets' + ',' + build_dir
    if not os.path.exists(build_dir):
        os.makedirs(build_dir)

# video type
video_type = st.selectbox('Video Type', ['balloonpop', 'brownbear', 'sharkinthewater', 'findodd', 'fingerfamily'])
if video_type:
    # import make_page function from respective template
    if video_type == 'balloonpop':
        from templates.balloonpop import movie, make_page
    elif video_type == 'brownbear':
        from templates.brownbear import movie, make_page
    elif video_type == 'sharkinthewater':
        from templates.sharkinthewater import movie, make_page
    elif video_type == 'findodd':
        from templates.findodd import movie, make_page
    elif video_type == 'fingerfamily':
        from templates.fingerfamily import movie, make_page
    else:
        raise ValueError('Invalid video type')

# textarea for JSON config

config_text = st.text_area('Paste JSON config here')
config = {}
if project_id and config_text:
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
if project_id and files:
    for file in files:
        with open(f'{build_dir}/{file.name}', 'wb') as f:
            f.write(file.getbuffer())

# click button to generate video
if project_id and st.button('Generate Video'):
    config['input_dir'] = build_dir
    for i in range(len(config['clips'])):
        make_page(config, i)

    movie.render_each_page(f'{build_dir}/output.mp4', fps=60)

    # List all files matching `output*.mp4` in the build directory
    if os.path.exists(build_dir):
        st.write('Generated files:')
        st.spinner('Generating...')
        for file in os.listdir(build_dir):
            if file.startswith('output') and file.endswith('.mp4'):
                st.video(f'{build_dir}/{file}')
                st.download_button('Download', f'{build_dir}/{file}')
