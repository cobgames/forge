"""Scan orchestration: walk works/, run sources, link, hash, dedupe, persist."""
from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
import time
import uuid
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

from . import db, report, thumbs
from .model import EXCLUDE_DIRS, Ctx, apply_license_rules, sha256_file
from .sources import compare, imgen, ledgers, manifests, meta3d

SELF_PROJECTS = {'forge'}   # never index the indexer (its test fixtures look like real sidecars)


def walk(ctx: Ctx, works_abs: str) -> None:
    for project in ctx.projects:
        files = []
        for dirpath, dirnames, filenames in os.walk(os.path.join(works_abs, project)):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            rd = ctx.rel(dirpath)
            files += [f'{rd}/{n}' for n in filenames]
        ctx.files[project] = sorted(files)


def _iso(ts) -> str | None:
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return dt.datetime.fromtimestamp(ts).astimezone().isoformat(timespec='seconds')
    return str(ts)


def _prev_hashes(db_path: str) -> dict:
    if not os.path.exists(db_path):
        return {}
    try:
        con = sqlite3.connect(db_path)
        rows = con.execute('SELECT rel_path, bytes, mtime, content_hash FROM assets '
                           'WHERE file_exists=1 AND content_hash IS NOT NULL').fetchall()
        con.close()
        return {(r[0], r[1], r[2]): r[3] for r in rows}
    except sqlite3.Error:
        return {}


def hash_all(ctx: Ctx, assets: list[dict], prev: dict) -> None:
    todo = []
    for a in assets:
        if not a['file_exists']:
            continue
        cached = prev.get((a['rel_path'], a['bytes'], a['mtime']))
        if cached:
            a['content_hash'] = cached
        else:
            todo.append(a)
    with ThreadPoolExecutor(max_workers=8) as ex:
        for a, h in zip(todo, ex.map(lambda x: sha256_file(ctx.abs(x['rel_path'])), todo)):
            a['content_hash'] = h   # >50MB -> None (sidecar hash would describe another file)


def link_derived(assets: list[dict]) -> None:
    by_path = {a['rel_path']: a['id'] for a in assets}
    for a in assets:
        refs = json.loads(a['input_refs_json']) if a['input_refs_json'] else []
        ids = [by_path[r] for r in refs if r in by_path and by_path[r] != a['id']]
        a['derived_from'] = json.dumps(list(dict.fromkeys(ids))) if ids else None


def find_duplicates(assets: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for a in assets:
        if a['content_hash']:
            groups[a['content_hash']].append(a)
    out = []
    for h, items in groups.items():
        if len(items) >= 2:
            out.append({'content_hash': h, 'asset_ids': [a['id'] for a in items],
                        'projects': sorted({a['project'] for a in items})})
    out.sort(key=lambda d: (-len(d['projects']), -len(d['asset_ids']), d['content_hash']))
    return out


def run_scan(root: str, out: str, include_orphans=False, no_thumbs=False, projects=None) -> dict:
    t0 = time.time()
    works_abs = os.path.abspath(root)
    ctx = Ctx(os.path.dirname(works_abs), os.path.basename(works_abs), [])
    all_projects = sorted(d for d in os.listdir(works_abs)
                          if os.path.isdir(os.path.join(works_abs, d)) and d not in EXCLUDE_DIRS)
    wanted = [p.strip() for p in projects.split(',')] if projects else None
    for p in wanted or []:
        if p not in all_projects:
            ctx.warn(f'--projects: {p} not found under {root}')
    ctx.projects = [p for p in all_projects if p not in SELF_PROJECTS and (not wanted or p in wanted)]
    started = dt.datetime.now().astimezone().isoformat(timespec='seconds')
    walk(ctx, works_abs)
    timing = {'walk_s': round(time.time() - t0, 1)}

    assets: list[dict] = []
    for src in (imgen.collect, meta3d.collect, manifests.collect, compare.collect_compare):
        assets += src(ctx)
    ledger_rows = ledgers.collect(ctx)
    assets += ledgers.apply(ctx, assets, ledger_rows)

    seen, uniq = {}, []
    for a in assets:
        if a['id'] in seen:
            ctx.warn(f"duplicate row for {a['rel_path']} ({a['kind']} vs {seen[a['id']]['kind']}); kept first")
            continue
        seen[a['id']] = a
        uniq.append(a)
    orphan_counts, orphan_rows = compare.orphans(ctx, {a['rel_path'] for a in uniq}, include_orphans)
    uniq += orphan_rows
    rule_hits = apply_license_rules(uniq)   # after ledger back-fill: ledger values win
    timing['sources_s'] = round(time.time() - t0, 1)

    os.makedirs(out, exist_ok=True)
    db_path = os.path.join(out, 'catalog.sqlite')
    hash_all(ctx, uniq, _prev_hashes(db_path))
    timing['hash_s'] = round(time.time() - t0, 1)
    for a in uniq:
        a['created_at'] = _iso(a['created_at'] if a['created_at'] is not None else a['mtime'])
    link_derived(uniq)
    dups = find_duplicates(uniq)

    n_thumbs = 0
    if not no_thumbs:
        n_thumbs = thumbs.build(uniq, out, ctx.abs, ctx.warn)
    timing['thumbs_s'] = round(time.time() - t0, 1)

    counts = {
        'assets': len(uniq), 'by_kind': dict(Counter(a['kind'] for a in uniq)),
        'by_project': dict(Counter(a['project'] for a in uniq)),
        'orphans': dict(orphan_counts), 'orphans_total': sum(orphan_counts.values()),
        'orphans_included': include_orphans, 'ledger_rows': len(ledger_rows),
        'duplicate_groups': len(dups), 'license_rules': rule_hits, 'thumbs': n_thumbs, 'projects_scanned': ctx.projects,
        'timing': timing,
    }
    run = {'run_id': uuid.uuid4().hex[:12], 'started_at': started, 'root': root,
           'counts': counts, 'warnings': ctx.warnings}
    uniq.sort(key=lambda a: (a['project'], a['rel_path']))
    timing['scan_total_s'] = round(time.time() - t0, 1)
    db.write(db_path, uniq, ledger_rows, run, dups)
    report.write_all(out, db.read(db_path))
    timing['with_report_s'] = round(time.time() - t0, 1)
    return run
