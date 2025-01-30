import argparse
from moviepy import *
from vima5.canva import *
from types import SimpleNamespace

parser = argparse.ArgumentParser(description='Gen Game Scene')
parser.add_argument('--background', type=str, help='Background color in hex or path to image or path to video')
params = parser.parse_args()

# Page 1: Show Shadows and Select One
# Show BG
# Move Shadows to Center
# One goes blink with color.
add_page(
    duration=1.0,
    background=params.background
)
# elem 1's shadow
elem1_pos = anchor_center(0, 0, 810, 540, 192, 108)
add_elem(
    ColorClip((192, 108), color=(0, 0, 0))
    .with_position(elem1_pos)
    .with_effects([
        vfx.Blink(0.1, 0.1),
    ])
)
# elem 2's shadow
elem2_pos = anchor_center(810, 0, 810, 540, 192, 108)
add_elem(
    ColorClip((192, 108), color=(0, 0, 0))
    .with_position(elem2_pos)
)
# elem 3's shadow
elem3_pos = anchor_center(0, 540, 810, 540, 192, 108)
add_elem(
    ColorClip((192, 108), color=(0, 0, 0))
    .with_position(elem3_pos)
)
# elem 4's shadow
elem4_pos = anchor_center(810, 540, 810, 540, 192, 108)
add_elem(
    ColorClip((192, 108), color=(0, 0, 0))
    .with_position(elem4_pos)
)

# Page 2: Transition to Game Scene
# Show BG
add_page(
    duration=1.0,
    background=params.background
)
# elem 1's shadow
# move and scale elem 1's Shadow to the center
elem1_pos = anchor_center(0, 0, 810, 540, 192, 108)
elem1_center_pos = anchor_center(0, 0, 1920, 1080, 1920*0.8, 1080*0.8)
add_elem(
    ColorClip((192, 108), color=(0, 0, 0))
    .with_position(lambda t: (
        elem1_pos[0] + (elem1_center_pos[0] - elem1_pos[0]) * t,
        elem1_pos[1] + (elem1_center_pos[1] - elem1_pos[1]) * t,
    ))
    .with_effects([
        vfx.Resize(lambda t: (
            192 + (1920*0.8 - 192) * t,
            108 + (1080*0.8 - 108) * t,
        )),
    ])
)
# elem 2's shadow
elem2_pos = anchor_center(810, 0, 810, 540, 192, 108)
add_elem(
    ColorClip((192, 108), color=(0, 0, 0))
    .with_position(elem2_pos)
)
# elem 3's shadow
elem3_pos = anchor_center(0, 540, 810, 540, 192, 108)
add_elem(
    ColorClip((192, 108), color=(0, 0, 0))
    .with_position(elem3_pos)
)
# elem 4's shadow
elem4_pos = anchor_center(810, 540, 810, 540, 192, 108)
add_elem(
    ColorClip((192, 108), color=(0, 0, 0))
    .with_position(elem4_pos)
)
# Move transition asset from up to bottom
add_elem(
    ColorClip((1920, 540), color=(128, 128, 128))
    .with_position(lambda t: (
        0,
        t / current_page().duration * 1080
    ))
    .with_duration(current_page().duration)
    .with_effects([
        vfx.CrossFadeOut(0.1),
    ])
)

# Page 3: Quick Scroll of Diced Chunks at all Three Lanes.
# Show BG
line_size = (6, int(1080*0.8))
chunk_size = (int(1920*0.8/3), int(1080*0.8))
chunk_margin = int((1920-1920*0.8)/2), int(1080-1080*0.8)/2
line1_pos = (chunk_margin[0] + chunk_size[0], chunk_margin[1])
line2_pos = (chunk_margin[0] + chunk_size[0]*2, chunk_margin[1])
elem1_center_pos = anchor_center(0, 0, 1920, 1080, 1920*0.8, 1080*0.8)
step = 0.1
elems = [
    ColorClip(chunk_size, color=(255, 0, 0)),
    ColorClip(chunk_size, color=(0, 255, 0)),
    ColorClip(chunk_size, color=(0, 0, 255)),
    ColorClip(chunk_size, color=(0, 255, 255)),
]

add_page(
    duration=1.2,
    background=params.background
)

# Show elem 1's Shadow in the center
add_elem(
    ColorClip((192, 108), color=(0, 0, 0))
    .with_position(elem1_center_pos)
    .with_effects([
        vfx.Resize((1920*0.8, 1080*0.8))
    ])
)

# Each lane places four blurred target image x 4. Pop out and squash.
# Each lane's last two assets are not blurred.
for lane in range(3):
    for round in range(3):
        for elem_i, elem in enumerate(elems):
            start = round * step * 4 + elem_i * step
            add_elem(
                elems[elem_i]
                .with_duration(step)
                .with_position((
                    chunk_margin[0] + lane * chunk_size[0],
                    chunk_margin[1],
                )),
                start=start,
                end=start+step,
            )

# Show two lines
add_elem(
    ColorClip(line_size, color=(128, 128, 128))
    .with_position(line1_pos)
)
add_elem(
    ColorClip(line_size, color=(128, 128, 128))
    .with_position(line2_pos)
)

# Page 4/5/6: 
# Start from Page 3 Last Frame.
# Show a Hand from [Left Bottom, Middle, Right Bottom] with a little rotate to the center.
# Carry image for four times.
# For the last time, move hand out of the screen.
add_page(
    duration=1,
    background=params.background
)


# Page 7: Reveal the answer
# Fade out dash.
# Squash the whole image and resize, move down a bit.
# Pan answer text from top.

# Repeat 2~7 for the remaining three.

# Page 24: Walk through all the answers again.
# Move hand to the center of each image.
# Show confetti.

render_pages('/tmp/output.mp4', filter='4')
