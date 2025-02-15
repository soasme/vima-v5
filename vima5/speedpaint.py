# Create a speedpaint video from an image using the Speedpaint.co.
#
# Usage: 
# $ export SPEEDPAINT_UID=your_uid # Go to speedpaint.co and open the browser console and type `document.cookie` to get uid.
# $ python speedpaint.py image.jpg --sketching-duration 5 --color-fill-duration 5 --hand-style 1

# Assume the account has enough credit.

import os
import time
import logging
import argparse
import requests

logger = logging.getLogger(__name__)
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'

UID = os.environ.get('SPEEDPAINT_UID', '')

class SpeedpaintError(Exception):
    pass

def speedpaint_upload_image(image):
    url = 'https://speedpaint.co/upload_preview'
    files = {'file': open(image, 'rb')}
    session = requests.Session()
    headers = {
        'User-Agent': USER_AGENT,
    }
    cookies = {
        'uid': UID,
    }
    preview_res = session.post(url, files=files, headers=headers, cookies=cookies)

    if preview_res.status_code != 200:
        raise SpeedpaintError(f'Failed to upload image. status_code={preview_res.status_code}')

    # "file_id", "filename", "message", "redirect_url", "status" == "success"
    data = preview_res.json() 
    print(data)
    return data


def speedpaint_convert_image(file_id, sketching_duration, color_fill_duration, hand_style):
    url = 'https://speedpaint.co/convert'
    cookies = {
        'uid': UID,
    }
    data = {
        'uid': cookies['uid'],
        'file_id': file_id,
        'fps': 60,
        'background': '#ffffff',
        'color_duration': color_fill_duration,
        'colorEnding': 'WithoutColor',
        'sketch_duration': sketching_duration,
        'hand': hand_style,
        'quality': str(1),
        'value_scale': str(0),
        'color_animation': str(1),
    }
    session = requests.Session()
    headers = {
        'User-Agent': USER_AGENT,
    }
    convert_res = session.post(url, data=data, headers=headers, cookies=cookies)
    if convert_res.status_code != 200:
        raise SpeedpaintError(f'Failed to convert image. status_code={convert_res.status_code}')
    data = convert_res.json()
    print(data)
    return data

def download_url(url, path):
    session = requests.Session()
    headers = {
        'User-Agent': USER_AGENT,
    }
    url = f'https://speedpaint.co{url}'
    cookies = {
        'uid': UID,
    }
    res = session.get(url, headers=headers, cookies=cookies, allow_redirects=True)
    if res.status_code != 200:
        raise SpeedpaintError(f'Failed to download image. status_code={res.status_code}')
    with open(path, 'wb') as f:
        f.write(res.content)

def speedpaint_image(image, sketching_duration, color_fill_duration, hand_style):
    preview_data = speedpaint_upload_image(image)
    file_id = preview_data['file_id']
    convert_data = speedpaint_convert_image(file_id, sketching_duration, color_fill_duration, hand_style)
    token = convert_data['token']
    new_file_id = convert_data['file_id']
    cookies = {
        'uid': UID,
    }
    while True:
        progress = speedpaint_check_progress(cookies['uid'], new_file_id, token)
        if progress['status'] == 'success':
            url = progress['download_url']
            path = image + '.mp4'
            download_url(url, path)
            return path
        if progress['status'] == 'pending':
            time.sleep(5)
            continue
        raise SpeedpaintError(f'Failed to convert image. status={progress["status"]}')

def speedpaint_check_progress(uid, file_id, token):
    url = 'https://speedpaint.co/check_download_preview'
    session = requests.Session()
    headers = {
        'User-Agent': USER_AGENT,
    }
    data = {
        'uid': uid,
        'file_id': file_id,
        'token': token,
    }
    cookies = {
        'uid': UID,
    }
    res = session.post(url, data=data, headers=headers, cookies=cookies)
    if res.status_code != 200:
        raise SpeedpaintError(f'Failed to check progress. status_code={res.status_code}')
    data = res.json()
    print(data)
    return data


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser()
    parser.add_argument('image', type=str)
    parser.add_argument('--sketching-duration', type=int, default=5)
    parser.add_argument('--color-fill-duration', type=int, default=5)
    parser.add_argument('--hand-style', type=str, default='1')
    args = parser.parse_args()
    path = speedpaint_image(
        args.image,
        args.sketching_duration,
        args.color_fill_duration,
        args.hand_style,
    )

    print(path)
