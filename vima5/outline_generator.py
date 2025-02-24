"""
Convert a list of images under a directory to black outline images with transparent background.

$ python vima5/outline_generator.py /path/to/images
"""

import sys
import os

from PIL import Image
from rembg import remove as rembg

from vima5.utils import mask_alpha

def main():
    datadir = sys.argv[1]
    for file in os.listdir(datadir):
        if not file.endswith(".png"):
            continue

        rembg_path = datadir + '/build/' + file
        black_path = datadir + '/build/' + file.replace('.png', '_black.png')

        if not os.path.exists(rembg_path):
            image = Image.open(datadir + '/' + file).convert("RGBA")
            rembg_image = rembg(image)
            rembg_image.save(rembg_path)

        mask_alpha(rembg_path, black_path,
            translucency_mask_color=(0, 0, 0),
            transparent_mask_color=(0, 0, 0, 0),
            opacity_mask_color=(0, 0, 0),
        )


if __name__ == '__main__':
    main()
