"""License ledgers: LICENSES.md / CREDITS.md / _licenses.md under works/<p>/{assets,public}/.

Two formats seen in the workspace:
- markdown tables (avatar-lab: 资产|来源|许可|商用|再分发|登记日期|备注; blender-lab / inkexile variants)
- manju-lab headings: "## 许可证：X" then "### n. title" sections with "- 文件：`f`" / "来源页：<url>"
"""
from __future__ import annotations

import os
import re

from ..model import Ctx, jdump, kind_by_ext, new_asset

NAMES = ('LICENSES.md', 'CREDITS.md', '_licenses.md')
DATE_RE = re.compile(r'20\d\d-\d\d-\d\d')
FILE_RE = re.compile(r'[\w.@\-/]+\.(?:glb|gltf|fbx|vrm|png|jpe?g|webp|mp3|wav|ogg|flac)\b', re.I)
URL_RE = re.compile(r'https?://[^\s<>|）)]+')
HEAD_LIC_RE = re.compile(r'(CC0[\w .\-]*|CC[ -]BY[\w .\-]*|[A-Za-z][A-Za-z0-9 .\-]*License|MIT)')
COLS = [  # (field, header keywords) - first match wins per column
    ('asset_name', ('资产', '包', '件', '文件', '产物', 'asset', 'name')),
    ('source_url', ('来源', 'url', 'source')),
    ('license', ('许可', '授权', 'license')),
    ('commercial', ('商用',)),
    ('redistribution', ('再分发',)),
    ('registered_at', ('日期', 'date')),
]


def in_scope(rel: str, works_rel: str) -> bool:
    parts = rel.split('/')
    base = len(works_rel.split('/'))
    return parts[-1] in NAMES and len(parts) > base + 2 and parts[base + 1] in ('assets', 'public')


def _cells(line: str) -> list[str]:
    s = line.strip()
    return [c.strip() for c in s.strip('|').split('|')]


def _clean(s: str) -> str:
    return re.sub(r'\*\*', '', s or '').strip()


def _finish(row: dict) -> dict:
    lic = _clean(row.get('license') or '')
    if lic in ('', '—', '-') and '不判' in ' '.join(str(v) for v in row.values()):
        lic = '研究阶段不判'
    row['license'] = '' if lic in ('—', '-') else lic
    return row


def parse_tables(text: str) -> list[dict]:
    lines = text.splitlines()
    rows, i, head_lic = [], 0, ''
    while i < len(lines) - 1:
        if lines[i].startswith('#'):
            m = HEAD_LIC_RE.search(lines[i])
            head_lic = m.group(1).strip() if m else ''
        if lines[i].lstrip().startswith('|') and re.match(r'^\s*\|[\s:\-|]+\|\s*$', lines[i + 1]):
            header = [h.lower() for h in _cells(lines[i])]
            cmap = {}
            for ci, h in enumerate(header):
                for field, keys in COLS:
                    if field not in cmap.values() and any(k in h for k in keys):
                        cmap[ci] = field
                        break
            if 0 not in cmap:
                cmap[0] = 'asset_name'
            i += 2
            while i < len(lines) and lines[i].lstrip().startswith('|'):
                cells = _cells(lines[i])
                row = {'line': i + 1, 'note': ''}
                if 'license' not in cmap.values() and head_lic:
                    row['license'] = head_lic   # licence stated by the section heading
                for ci, c in enumerate(cells):
                    f = cmap.get(ci)
                    if f and not row.get(f):
                        row[f] = c
                    elif c:
                        row['note'] = (row['note'] + ' | ' + c).strip(' |')
                if _clean(row.get('asset_name', '')):
                    rows.append(_finish(row))
                i += 1
        else:
            i += 1
    return rows


def parse_headings(text: str) -> list[dict]:
    """manju-lab format: license heading + per-item ### sections."""
    rows, lic, cur = [], None, None
    for n, line in enumerate(text.splitlines(), 1):
        m = re.match(r'^##\s*许可证[:：]\s*(.+)$', line)
        if m:
            lic = re.sub(r'[（(].*$', '', m.group(1)).strip()
            continue
        if line.startswith('## '):   # licence stays in force until the next 许可证 heading
            cur = None
            continue
        if line.startswith('### ') and lic:
            cur = {'line': n, 'asset_name': line[4:].strip(), 'license': lic, 'note': ''}
            rows.append(cur)
            continue
        if cur is not None and line.lstrip().startswith('-'):
            if '文件' in line:
                cur['asset_name'] += ' ' + line.split('：', 1)[-1].strip()
            if '来源' in line and URL_RE.search(line):
                cur['source_url'] = URL_RE.search(line).group(0)
            cur['note'] = (cur['note'] + ' ' + line.strip('- ').strip()).strip()[:400]
    return rows


def collect(ctx: Ctx) -> list[dict]:
    out = []
    for project, files in ctx.files.items():
        for rel in files:
            if not in_scope(rel, ctx.works_rel):
                continue
            try:
                with open(ctx.abs(rel), encoding='utf-8-sig') as f:
                    text = f.read()
            except OSError as e:
                ctx.warn(f'ledger unreadable {rel}: {e}')
                continue
            rows = parse_tables(text) + parse_headings(text)
            first_date = DATE_RE.search(text)
            for r in rows:
                reg = r.get('registered_at') or ''
                dm = DATE_RE.search(reg)
                url = URL_RE.search(r.get('source_url') or '')
                out.append({
                    'project': project, 'ledger_path': rel, 'line': r['line'],
                    'asset_name': _clean(r.get('asset_name')),
                    'source_url': url.group(0) if url else _clean(r.get('source_url')) or None,
                    'license': r.get('license') or '', 'commercial': _clean(r.get('commercial')) or None,
                    'redistribution': _clean(r.get('redistribution')) or None,
                    'registered_at': dm.group(0) if dm else (first_date.group(0) if first_date else None),
                    'note': (r.get('note') or '')[:1000] or None,
                })
            if not rows:
                ctx.warn(f'ledger has no parsable rows: {rel}')
    return out


def file_tokens(name: str) -> list[str]:
    toks = re.findall(r'`([^`]+)`', name) + FILE_RE.findall(name)
    out = []
    for t in toks:
        t = t.strip().replace('\\', '/')
        if '{' in t or not FILE_RE.fullmatch(t):
            continue
        out.append(t.rsplit('/', 1)[-1].lower())
    return list(dict.fromkeys(out))


def apply(ctx: Ctx, assets: list[dict], ledgers: list[dict]) -> list[dict]:
    """Back-fill license onto matched assets; unmatched ledger rows become rows of their own."""
    by_base: dict[tuple, list[dict]] = {}
    for a in assets:
        by_base.setdefault((a['project'], a['rel_path'].rsplit('/', 1)[-1].lower()), []).append(a)
    file_base: dict[tuple, list[str]] = {}
    for project, files in ctx.files.items():
        for f in files:
            file_base.setdefault((project, f.rsplit('/', 1)[-1].lower()), []).append(f)
    extra = []
    for lg in ledgers:
        lic = lg['license'] or 'unknown'
        hit = False
        for tok in file_tokens(lg['asset_name']):
            key = (lg['project'], tok)
            for a in by_base.get(key, []):
                a['license'], a['license_source'], hit = lic, lg['ledger_path'], True
            if key in by_base:
                continue
            for f in file_base.get(key, []):
                kind = kind_by_ext(f) or 'ledger-entry'
                a = ctx.fill_file(new_asset(lg['project'], kind, f, license=lic,
                                            license_source=lg['ledger_path'], created_at=lg['registered_at'],
                                            sidecar_path=lg['ledger_path'], raw_json=jdump(lg),
                                            tags_json=jdump([kind, 'ledger'])))
                by_base.setdefault(key, []).append(a)
                extra.append(a)
                hit = True
        if not hit:
            p = f"{lg['ledger_path']}#L{lg['line']}"
            extra.append(new_asset(lg['project'], 'ledger-entry', p, license=lic,
                                   license_source=lg['ledger_path'], created_at=lg['registered_at'],
                                   prompt=None, params_json=jdump({'asset_name': lg['asset_name']}),
                                   sidecar_path=lg['ledger_path'], raw_json=jdump(lg),
                                   tags_json=jdump(['ledger-entry'])))
    return extra
