"""summary.md + catalog.json + gallery.html from a loaded catalog."""
from __future__ import annotations

import os
from collections import Counter, defaultdict

from . import db, gallery
from .model import LICENSE_RULES, license_color


def has_license(a: dict) -> bool:
    v = (a.get('license') or '').strip()
    return bool(v) and v.lower() != 'unknown'


def coverage(items) -> str:
    items = list(items)
    if not items:
        return '-'
    n = sum(has_license(a) for a in items)
    return f'{n}/{len(items)} ({100 * n / len(items):.1f}%)'


def _dist(items, key) -> str:
    c = Counter(a.get(key) or 'null' for a in items)
    return ', '.join(f'{k} {v}' for k, v in c.most_common())


def summary_md(data: dict) -> str:
    assets, run, dups = data['assets'], data['run'], data['duplicates']
    counts = run['counts']
    by_id = {a['id']: a for a in assets}
    by_proj = defaultdict(list)
    for a in assets:
        by_proj[a['project']].append(a)
    orphans = counts.get('orphans', {})
    cross = [d for d in dups if len(d['projects']) >= 2]
    L = [
        '# forge catalog summary', '',
        f"- run `{run['run_id']}` started {run['started_at']}, root `{run['root']}`",
        f"- timing: {counts.get('timing')}",
        f"- assets: **{len(assets)}** — {_dist(assets, 'kind')}",
        f"- source_tool: {_dist(assets, 'source_tool')}",
        f'- license coverage (non-unknown): **{coverage(assets)}**',
        f"- duplicate groups (same content hash, >=2 rows): **{len(dups)}**, cross-project: **{len(cross)}**",
        f"- orphan images (assets/_inbox|_work, no sidecar): **{counts.get('orphans_total', 0)}**"
        f"{' (included as rows)' if counts.get('orphans_included') else ' (counted only)'}",
        f"- ledger rows: **{counts.get('ledger_rows', len(data['ledgers']))}**",
        f"- thumbnails: {counts.get('thumbs', 0)}", '',
        '## By project', '',
        '| project | assets | kind | source_tool | license coverage | orphans |',
        '|---|---|---|---|---|---|',
    ]
    for p in sorted(set(by_proj) | set(orphans)):
        items = by_proj.get(p, [])
        L.append(f"| {p} | {len(items)} | {_dist(items, 'kind') if items else '-'} | "
                 f"{_dist(items, 'source_tool') if items else '-'} | {coverage(items)} | {orphans.get(p, 0)} |")
    L += ['', '## License rules applied', '',
          f"- red (non-commercial / 不允许 / 研究阶段不判): **{sum(license_color(a.get('license')) == 'red' for a in assets)}**"]
    for r in LICENSE_RULES:
        n = counts.get('license_rules', {}).get(r['name'], 0)
        act = r['license'] or 'kept unknown'
        L.append(f"- `{r['name']}` /{r['pattern']}/ on {', '.join(r['fields'])} → {act}: **{n}** hits ({r['note']})")
    L += ['', '## Cross-project duplicate groups (top 50)', '']
    if not cross:
        L.append('_none_')
    for d in cross[:50]:
        L.append(f"- `{d['content_hash'][:16]}` · {', '.join(d['projects'])} · {len(d['asset_ids'])} rows")
        for i in d['asset_ids'][:8]:
            if i in by_id:
                L.append(f"  - `{by_id[i]['rel_path']}`")
    L += ['', '## Ledgers', '']
    lc = Counter(lg['ledger_path'] for lg in data['ledgers'])
    L += [f'- `{k}`: {v} rows' for k, v in sorted(lc.items())] or ['_none_']
    warns = run['warnings']
    L += ['', f'## Warnings ({len(warns)})', '']
    L += [f'- {w}' for w in warns[:300]]
    if len(warns) > 300:
        L.append(f'- … {len(warns) - 300} more (see catalog.json meta.run.warnings)')
    return '\n'.join(L) + '\n'


def write_all(out: str, data: dict, with_json: bool = True) -> None:
    if with_json:
        db.export_json(os.path.join(out, 'catalog.json'), data)
    with open(os.path.join(out, 'summary.md'), 'w', encoding='utf-8') as f:
        f.write(summary_md(data))
    gallery.write(os.path.join(out, 'gallery.html'), data, os.path.join(out, 'thumbs'))


def regenerate(out: str) -> dict:
    path = os.path.join(out, 'catalog.sqlite')
    if not os.path.exists(path):
        raise SystemExit(f'no catalog at {path}; run scan first')
    data = db.read(path)
    write_all(out, data, with_json=False)
    return data
