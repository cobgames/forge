"""3D provenance: war3-labs `assets-lib/*/*/meta.json` and three-lab `*_hy3d_meta.json`."""
from __future__ import annotations

import os
import re

from ..model import Ctx, jdump, new_asset
from .imgen import tags_for

LIB_RE = re.compile(r'/assets-lib/[^/]+/[^/]+/meta\.json$')


def _seed_text(seeds):
    if seeds is None:
        return None
    if isinstance(seeds, (dict, list)):
        return jdump(seeds)
    return str(seeds)


def war3_meta(ctx: Ctx, project: str, rel: str, fileset: set[str]) -> dict | None:
    d = ctx.read_json(rel)
    if not isinstance(d, dict):
        return None
    mdir = rel.rsplit('/', 1)[0]
    proot = ctx.project_rel(project)
    glb = None
    if isinstance(d.get('glb'), str):
        cand = f"{proot}/{d['glb']}"
        glb = cand if cand in fileset else None
    if not glb:
        glbs = sorted(f for f in fileset if f.startswith(mdir + '/') and f.endswith('.glb')
                      and f.count('/') == mdir.count('/') + 1)
        glbs.sort(key=lambda f: ('.static.' in f, len(f)))
        glb = glbs[0] if glbs else None
    gen = d.get('generation') if isinstance(d.get('generation'), dict) else {}
    faction = d.get('faction')
    src = d.get('source_image')
    refs = [ctx.resolve_ref(src, proot, project)] if src else []
    model = gen.get('weights')
    a = new_asset(
        project, 'model3d', glb or f"{mdir}/{d.get('id') or 'model'}.glb", created_at=d.get('date'),
        source_tool='comfyui-trellis2', model=model,
        seed=_seed_text(gen.get('seeds') if 'seeds' in gen else gen.get('seed')),
        params_json=jdump({'generation': gen, 'build': d.get('build')}),
        input_refs_json=jdump([r for r in refs if r] or None),
        batch=faction, sidecar_path=rel, raw_json=jdump(d),
        tags_json=jdump(tags_for('model3d', model, None, [faction, d.get('kind')])),
    )
    return ctx.fill_file(a)


def hy3d_meta(ctx: Ctx, project: str, rel: str, fileset: set[str]) -> dict | None:
    d = ctx.read_json(rel)
    if not isinstance(d, dict):
        return None
    prefix = rel[:-len('_meta.json')]          # .../manor_hy3d
    cands = [prefix + s for s in ('.glb', '_reduced.glb', '_raw.glb')]
    glb = next((c for c in cands if c in fileset), None)
    if not glb:
        more = sorted(f for f in fileset if f.startswith(prefix) and f.endswith('.glb'))
        glb = more[0] if more else None
    args = d.get('args') if isinstance(d.get('args'), dict) else {}
    mdir = rel.rsplit('/', 1)[0]
    img = args.get('image')
    refs = [ctx.resolve_ref(img, mdir, project)] if img else []
    a = new_asset(
        project, 'model3d', glb or prefix + '.glb', source_tool='hunyuan3d', model='hy3d',
        seed=_seed_text(args.get('seed')), params_json=jdump(args or None),
        input_refs_json=jdump([r for r in refs if r] or None),
        batch=mdir.rsplit('/', 1)[-1], sidecar_path=rel, raw_json=jdump(d),
        tags_json=jdump(tags_for('model3d', 'hy3d', None, [os.path.basename(prefix)])),
    )
    a = ctx.fill_file(a)
    if a['mtime'] is None:   # product missing: date the row by its meta file
        try:
            a['created_at'] = os.path.getmtime(ctx.abs(rel))
        except OSError:
            pass
    return a


def collect(ctx: Ctx) -> list[dict]:
    out = []
    for project, files in ctx.files.items():
        fileset = set(files)
        for r in files:
            a = None
            if LIB_RE.search(r):
                a = war3_meta(ctx, project, r, fileset)
            elif r.endswith('_hy3d_meta.json'):
                a = hy3d_meta(ctx, project, r, fileset)
            if a:
                out.append(a)
    return out
