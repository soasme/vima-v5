# Let user split video by pages.
# Adjust start/end time of each clip to be relative to the page.

from PIL import ImageColor
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field
from moviepy import *
from vima5.utils import save_mp4, RESOLUTION_MAP

@dataclass
class Element:
    align: str = 'none'
    width: float = 810
    height: float = 540
    x: float = 0.0
    y: float = 0.0
    rotate: float = 0.0
    opacity: float = 1.0
    start: float = 0.0 # Relative to page start
    end: float = 0.0 # Relative to page end
    flip_horizontal: bool = False
    flip_vertical: bool = False
    page: Optional['Page'] = None

@dataclass
class Page:
    num: int = 1
    name: str = ''
    color: str = 'white'
    duration: float = 5.0
    background: str = ''
    animate: str = 'none'
    animate_config: Dict = field(default_factory=dict)
    elements: List[Element] = field(default_factory=list)


pages = []


def add_page(name='', **kwargs):
    num = len(pages) + 1
    page = Page(
        num=num,
        name=f'Page {num}' if not name else name,
        **kwargs
    )
    pages.append(page)
    return page


def add_elem(clip, pagenum=0, **kwargs):
    if not pagenum:
        page = pages[-1]

    elem = Element(page=page, **kwargs)
    elem.clip = clip
    page.elements.append(elem)
    return elem



def get_page_config(pagenum):
    return next(page for page in pages if page.num == pagenum)


def _get_page_background_clip(page, page_start_time, size):
    if '.png' in page.background or '.jpg' in page.background:
        return (
            ImageClip(page.background)
            .with_start(page_start_time)
            .with_duration(page.duration)
            .with_effects([vfx.Resize(size)])
        )
    elif '.mp4' in page.background:
        return (
            VideoFileClip(page.background)
            .with_start(page_start_time)
            .with_duration(page.duration)
            .with_effects([vfx.Resize(size)])
        )
    else:
        return (
            ColorClip(
                size=size,
                color=(
                    page.background if page.background else (0, 0, 0, 0)))
            .with_start(page_start_time)
            .with_duration(page.duration)
        )

def render_pages(output='output.mp4', aspect_ratio='16:9', fps=30, resolution='1080p', pages=''):
    size = RESOLUTION_MAP.get(resolution, RESOLUTION_MAP['1080p']).get(aspect_ratio, RESOLUTION_MAP['1080p']['16:9'])

    clips = []

    # Set start/end for each clip
    page_start_time = 0.0
    for page in pages:
        clips.append(_get_page_background_clip(page, page_start_time, size))
        for elem in page.elements:
            clip = elem.clip
            clip = clip.with_start(page_start_time + elem.start)
            clip = clip.with_end(page_start_time + (elem.end if elem.end else page.duration))
            clips.append(clip)
            
        page_start_time += page.duration

    final = CompositeVideoClip(clips)
    save_mp4(final, output, fps=fps)
