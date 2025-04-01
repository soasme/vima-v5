#!/usr/bin/env python3
import argparse
import os
import sys
from playwright.sync_api import sync_playwright
import requests
from tqdm import tqdm
import time

def download_video(url, output_path):
    """
    Download a video from a given URL using Playwright.
    
    Args:
        url (str): The Sora URL to download from
        output_path (str): The local path to save the video
    """
    print(f"Launching browser to access {url}")
    
    with sync_playwright() as p:
        # Launch the browser
        #browser = p.chromium.launch(headless=True)
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        page = browser.contexts[0].new_page()
        
        try:
            # Navigate to the URL
            page.goto(url, wait_until="networkidle")
            print("Page loaded, waiting for video element...")
            # print html
            print(page.content())

            page.screenshot(path="/tmp/screenshot.png")
            
            # Wait for the video element to be present
            page.wait_for_selector("video", state="visible", timeout=30000)
            
            # Get the video source URL
            video_src = page.eval_on_selector("video", "el => el.src")
            
            if not video_src:
                # If direct src not available, try to find it in the source element
                video_src = page.eval_on_selector("video > source", "el => el.src", timeout=5000)
            
            if not video_src:
                print("Could not find video source URL")
                browser.close()
                return False
            
            print(f"Found video source: {video_src}")
            
            # Download the video
            download_file(video_src, output_path)
            
            print(f"Video downloaded successfully to {output_path}")
            browser.close()
            return True
            
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            browser.close()
            return False

def download_file(url, output_path):
    """
    Download a file from a URL with progress bar
    
    Args:
        url (str): The URL of the file to download
        output_path (str): The local path to save the file
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Send a HEAD request to get the file size
    response = requests.head(url)
    file_size = int(response.headers.get('content-length', 0))
    
    # Download the file with progress bar
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(output_path, 'wb') as f:
        with tqdm(total=file_size, unit='B', unit_scale=True, desc="Downloading") as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))

def main():
    parser = argparse.ArgumentParser(description='Download a video from a Sora URL')
    parser.add_argument('--input', required=True, help='Sora URL (e.g., https://sora.com/g/gen_01jqn4ae2dejmt6kckyn4mx28b)')
    parser.add_argument('--output', required=True, help='Local path to save the video')
    
    args = parser.parse_args()
    
    # Check if the URL is valid
    #if not args.input.startswith('https://sora.com/'):
    #    print("Error: Invalid Sora URL. URL should start with 'https://sora.com/'")
    #    sys.exit(1)
    
    # Set default extension if not provided
    if not os.path.splitext(args.output)[1]:
        args.output = args.output + '.mp4'
    
    if args.input.startswith('https://'):
        # Download the video
        if download_video(args.input, args.output):
            print("✅ Process completed successfully!")
        else:
            print("❌ Failed to download the video")
            sys.exit(1)
    elif args.input.endswith('.txt'):
        with open(args.input, 'r') as f:
            urls = [u for u in f.read().splitlines() if u.strip()]
            for i, url in enumerate(urls):
                output_path = f"{os.path.splitext(args.output)[0]}_{i+1}.mp4"
                if download_video(url, output_path):
                    print(f"✅ Video {i+1} downloaded successfully to {output_path}")
                else:
                    print(f"❌ Failed to download video {i+1}")

if __name__ == "__main__":
    main()
