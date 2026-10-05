"""imgen sidecars (`*.gen.json`) and imgen_batch `_manifest.json` lists."""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict

from ..model import IMAGE_EXT, Ctx, jdump, new_asset, norm_hash

VER_RE = re.compile(r'__v\d+$')
REF_KEYS = ('input_images', 'input_image', 'refs', 'ref', 'copied_from')


def batch_of(rel_path: str) -> str | None:
    parts = rel_path.split('/')
    if '_inbox' in parts:
        i = parts.index('_inbox')
        if i + 2 < len(parts):
            return parts[i + 1]
    return parts[-2] if len(parts) >= 2 else None


def tags_for(kind: str, model, batch, extra=()) -> list[str]:
    tags = [kind]
    if model:
        tags.append(str(model))
    if batch:
        purpose = batch.split('__', 1)[1] if '__' in batch else batch
        tags += [t for t in re.split(r'[_\-]+', purpose) if t and not t.isdigit()]
    tags += [t for t in extra if t]
    return list(dict.fromkeys(tags))


def find_product(base: str, fileset: set[str]) -> str | None:
    for b in (base, VER_RE.sub('', base)):
        for ext in IMAGE_EXT:
            if b + ext in fileset:
                return b + ext
    return None


def pick_model(d: dict):
    if d.get('method') == 'responses_image' and d.get('image_model'):
        return d['image_model']
    if isinstance(d.get('models'), dict):
        return d['models'].get('unet') or next(iter(d['models'].values()), None)
    return d.get('model')


def collect_refs(ctx: Ctx, d: dict, base_dir: str, project: str) -> list[str]:
    refs = []
    for k in REF_KEYS:
        v = d.get(k)
        for r in (v if isinstance(v, list) else [v]):
            rr = ctx.resolve_ref(r, base_dir, project)
            if rr:
                refs.append(rr)
    return refs


def sidecar_asset(ctx: Ctx, project: str, rel: str, fileset: set[str]) -> dict:
    base = rel[:-len('.gen.json')]
    product = find_product(base, fileset) or base + '.png'
    d = ctx.read_json(rel)
    raw = d
    if not isinstance(d, dict):
        if d is not None:
            ctx.warn(f'sidecar not an object: {rel}')
        d = {}
    params = d.get('params') if isinstance(d.get('params'), dict) else {}
    if not params:
        params = {k: d[k] for k in ('size', 'quality', 'mode') if k in d}
    seed = params.get('seed', d.get('seed'))
    model = pick_model(d)
    batch = batch_of(product)
    base_dir = rel.rsplit('/', 1)[0]
    a = new_asset(
        project, 'image2d', product,
        created_at=d.get('created_at') or d.get('date'),
        source_tool='imgen', model=model,
        prompt=d.get('prompt') or d.get('prompt_raw'),
        seed=None if seed is None else str(seed),
        params_json=jdump(params or None),
        input_refs_json=jdump(collect_refs(ctx, d, base_dir, project) or None),
        content_hash=norm_hash(d.get('hash')),
        batch=batch, sidecar_path=rel, raw_json=jdump(raw),
        tags_json=jdump(tags_for('image2d', model, batch, [d.get('method')])),
    )
    return ctx.fill_file(a)


def manifest_assets(ctx: Ctx, project: str, rel: str, by_dir: dict, known: set[str]) -> list[dict]:
    """imgen_batch `_manifest.json`: list of {idx, ep, model, ok, file, prompt}."""
    d = ctx.read_json(rel)
    if not (isinstance(d, list) and d and isinstance(d[0], dict) and 'idx' in d[0]):
        return []
    out, unresolved = [], 0
    mdir = rel.rsplit('/', 1)[0]
    for e in d:
        if not isinstance(e, dict):
            continue
        meta = {k: v for k, v in e.items() if k != 'prompt'}
        f = e.get('file')
        frel = ctx.resolve_ref(f, mdir, project) if f else None
        if frel in known:
            continue
        match = [a for a in by_dir.get(mdir, []) if e.get('prompt') and a['prompt'] == e.get('prompt')]
        if match:
            for a in match:
                a['_manifest'] = meta
            continue
        if not frel or not os.path.isfile(ctx.abs(frel)):
            unresolved += 1
            continue
        batch = batch_of(frel)
        a = new_asset(project, 'manifest-entry', frel, source_tool='imgen', model=e.get('model'),
                      prompt=e.get('prompt'), params_json=jdump(meta), batch=batch,
                      sidecar_path=rel, raw_json=jdump(e),
                      tags_json=jdump(tags_for('manifest-entry', e.get('model'), batch)))
        out.append(ctx.fill_file(a))
        known.add(frel)
    if unresolved:
        ctx.warn(f'{rel}: {unresolved} manifest entries without file or sidecar match')
    return out


def collect(ctx: Ctx) -> list[dict]:
    assets: list[dict] = []
    for project, files in ctx.files.items():
        fileset = set(files)
        side = [f for f in files if f.endswith('.gen.json')]
        p_assets = [sidecar_asset(ctx, project, r, fileset) for r in side]
        by_dir = defaultdict(list)
        for a in p_assets:
            by_dir[a['sidecar_path'].rsplit('/', 1)[0]].append(a)
        known = {a['rel_path'] for a in p_assets}
        for r in files:
            if r.endswith('/_manifest.json'):
                p_assets += manifest_assets(ctx, project, r, by_dir, known)
        for a in p_assets:
            m = a.pop('_manifest', None)
            if m is not None and a['kind'] == 'image2d':
                p = json.loads(a['params_json']) if a['params_json'] else {}
                p['_manifest'] = m
                a['params_json'] = jdump(p)
        assets += p_assets
    return assets
