"""JPEG thumbnails (long edge <= 256) for image assets; skip when up to date."""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageOps

from .model import IMAGE_EXT

MAX_EDGE = 256
Image.MAX_IMAGE_PIXELS = 400_000_000


def wants_thumb(a: dict) -> bool:
    return bool(a.get('file_exists')) and a['rel_path'].lower().endswith(IMAGE_EXT)


def _one(src: str, dst: str) -> str | None:
    try:
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            return None
        with Image.open(src) as im:
            im.draft('RGB', (MAX_EDGE * 2, MAX_EDGE * 2))
            im = ImageOps.exif_transpose(im)
            if im.mode in ('RGBA', 'LA', 'P', 'PA'):
                rgba = im.convert('RGBA')
                bg = Image.new('RGB', rgba.size, (40, 40, 44))
                bg.paste(rgba, mask=rgba.getchannel('A'))
                im = bg
            else:
                im = im.convert('RGB')
            im.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
            im.save(dst, 'JPEG', quality=82, optimize=True)
        return None
    except Exception as e:  # noqa: BLE001 - one bad image must not stop the scan
        return f'thumb failed {src}: {type(e).__name__}: {str(e)[:100]}'


def build(assets: list[dict], out_dir: str, abs_of, warn) -> int:
    tdir = os.path.join(out_dir, 'thumbs')
    os.makedirs(tdir, exist_ok=True)
    jobs = [(abs_of(a['rel_path']), os.path.join(tdir, a['id'] + '.jpg')) for a in assets if wants_thumb(a)]
    with ThreadPoolExecutor(max_workers=min(16, (os.cpu_count() or 4) * 2)) as ex:
        for err in ex.map(lambda j: _one(*j), jobs):
            if err:
                warn(err)
    return len(jobs)
