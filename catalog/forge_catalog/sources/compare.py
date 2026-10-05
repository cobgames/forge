"""`_COMPARE_*` decision montages and orphan images (no sidecar) in assets/_inbox|_work."""
from __future__ import annotations

import datetime as dt
import re
from collections import Counter

from ..model import IMAGE_EXT, Ctx, jdump, new_asset
from .imgen import tags_for

ORPHAN_RE = re.compile(r'/assets/(_inbox|_work)/')


def _iso(ts) -> str | None:
    if ts is None:
        return None
    return dt.datetime.fromtimestamp(ts).astimezone().isoformat(timespec='seconds')


def collect_compare(ctx: Ctx) -> list[dict]:
    out = []
    for project, files in ctx.files.items():
        for f in files:
            name = f.rsplit('/', 1)[-1]
            if not name.startswith('_COMPARE_') or not name.lower().endswith(IMAGE_EXT):
                continue
            batch = f.rsplit('/', 2)[-2] if f.count('/') >= 1 else None
            a = ctx.fill_file(new_asset(project, 'compare', f, batch=batch,
                                        tags_json=jdump(tags_for('compare', None, batch))))
            a['created_at'] = _iso(a['mtime'])
            out.append(a)
    return out


def orphans(ctx: Ctx, known: set[str], include: bool) -> tuple[Counter, list[dict]]:
    """Images under assets/_inbox|_work not covered by any asset row."""
    counts: Counter = Counter()
    rows = []
    for project, files in ctx.files.items():
        for f in files:
            if f in known or not ORPHAN_RE.search(f) or not f.lower().endswith(IMAGE_EXT):
                continue
            if f.rsplit('/', 1)[-1].startswith('_COMPARE_'):
                continue
            counts[project] += 1
            if include:
                parts = f.split('/')
                i = max(i for i, p in enumerate(parts) if p in ('_inbox', '_work'))
                batch = parts[i + 1] if i + 2 < len(parts) else None
                a = ctx.fill_file(new_asset(project, 'image2d', f, batch=batch,
                                            tags_json=jdump(tags_for('image2d', None, batch, ['orphan']))))
                a['created_at'] = _iso(a['mtime'])
                rows.append(a)
    return counts, rows
