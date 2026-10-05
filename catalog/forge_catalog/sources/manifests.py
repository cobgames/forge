"""Best-effort project manifests -> kind=manifest-entry rows.

Formats (each confirmed against a real sample before writing):
- terraweave `art/asset-manifest.json`: {project, version, schema, assets:[{id, source, license, ...}]}
- clone-lab `public/assets/hero/*.manifest.json`: one object per glb {asset, sha256, date, generator, seed, ...}
- zcds `imagegen-index.json`: {entries:[{id, generated_at, archived_path, revised_prompt, faction, ...}]}
- taoyuan `assets/_index/catalog_*.csv`: category,bundle,type,name,path_id,exported (rows with exported only)
- war3 `tools/art/*-asset-map.mjs`: not parsed, presence recorded
"""
from __future__ import annotations

import csv
import re

from ..model import Ctx, jdump, kind_by_ext, new_asset, norm_hash
from .imgen import tags_for

HERO_RE = re.compile(r'/public/assets/hero/[^/]+\.manifest\.json$')
CSV_RE = re.compile(r'/assets/_index/catalog_[^/]+\.csv$')
MJS_RE = re.compile(r'/tools/art/[^/]+-asset-map\.mjs$')


def _row(ctx: Ctx, project, rel_path, manifest_rel, **kw) -> dict:
    a = new_asset(project, 'manifest-entry', rel_path, sidecar_path=manifest_rel, **kw)
    return ctx.fill_file(a)


def terraweave(ctx: Ctx, project, rel) -> list[dict]:
    d = ctx.read_json(rel)
    if not isinstance(d, dict) or not isinstance(d.get('assets'), list):
        return []
    mdir = rel.rsplit('/', 1)[0]
    out = []
    for e in d['assets']:
        if not isinstance(e, dict):
            continue
        src = ctx.resolve_ref(e.get('source'), mdir, project) or f"{rel}#{e.get('id')}"
        out.append(_row(ctx, project, src, rel, source_tool='manifest', license=e.get('license') or 'unknown',
                        license_source=rel if e.get('license') else None, params_json=jdump(e),
                        batch=e.get('tileDefinition'), raw_json=jdump(e),
                        tags_json=jdump(tags_for('manifest-entry', None, None,
                                                 [e.get('tileDefinition')] + list(e.get('sockets') or [])))))
    return out


def hero_manifest(ctx: Ctx, project, rel) -> list[dict]:
    d = ctx.read_json(rel)
    if not isinstance(d, dict):
        return []
    mdir = rel.rsplit('/', 1)[0]
    asset = ctx.resolve_ref(d.get('asset'), mdir, project) or rel
    gen = str(d.get('generator') or '')
    weights = d.get('model_weights')
    model = weights[0] if isinstance(weights, list) and weights else None
    ref = ctx.resolve_ref(d.get('reference'), mdir, project)
    params = {k: d[k] for k in ('generator', 'workflow', 'shape_resolution', 'faces', 'source_faces',
                                'texture_limit', 'blender', 'model_weights') if k in d}
    return [_row(ctx, project, asset, rel,
                 source_tool='comfyui-trellis2' if 'trellis' in gen.lower() else 'manifest',
                 model=model, seed=None if d.get('seed') is None else str(d['seed']),
                 created_at=d.get('date'), content_hash=norm_hash(d.get('sha256')),
                 params_json=jdump(params), input_refs_json=jdump([ref] if ref else None),
                 batch=mdir.rsplit('/', 1)[-1], raw_json=jdump(d),
                 tags_json=jdump(tags_for('manifest-entry', model, None, ['model3d'])))]


def imagegen_index(ctx: Ctx, project, rel) -> list[dict]:
    d = ctx.read_json(rel)
    if not isinstance(d, dict) or not isinstance(d.get('entries'), list):
        return []
    mdir = rel.rsplit('/', 1)[0]
    root = mdir.rsplit('/', 1)[0]   # archived_path is "source/<file>" relative to the v2 dir
    out = []
    for e in d['entries']:
        if not isinstance(e, dict) or not e.get('archived_path'):
            continue
        p = ctx.resolve_ref(e['archived_path'], root, project)
        meta = {k: v for k, v in e.items() if k != 'revised_prompt'}
        out.append(_row(ctx, project, p, rel, source_tool='manifest', prompt=e.get('revised_prompt'),
                        created_at=e.get('generated_at'), params_json=jdump(meta),
                        batch=e.get('faction'), raw_json=jdump(e),
                        tags_json=jdump(tags_for('manifest-entry', None, None,
                                                 [e.get('stage'), e.get('faction'), e.get('status')]))))
    return out


def taoyuan_csv(ctx: Ctx, project, rel, files) -> list[dict]:
    out, seen = [], set()
    try:
        with open(ctx.abs(rel), encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f))
    except (OSError, csv.Error) as e:
        ctx.warn(f'bad csv {rel}: {e}')
        return out
    for r in rows:
        exp = (r.get('exported') or '').strip().replace('\\', '/')
        if not exp:
            continue
        hit = next((f for f in files if f.endswith('/' + exp)), None)
        path = hit or f'{rel}#{exp}'
        if path in seen:   # same export listed once per Unity object type (Sprite + Texture2D)
            continue
        seen.add(path)
        out.append(_row(ctx, project, path, rel, source_tool='manifest', batch=r.get('bundle'),
                        params_json=jdump(r), raw_json=jdump(r),
                        tags_json=jdump(tags_for('manifest-entry', None, None,
                                                 [r.get('category'), r.get('type'), kind_by_ext(exp)]))))
    return out


def collect(ctx: Ctx) -> list[dict]:
    out = []
    for project, files in ctx.files.items():
        for r in files:
            name = r.rsplit('/', 1)[-1]
            if name == 'asset-manifest.json':
                out += terraweave(ctx, project, r)
            elif HERO_RE.search(r):
                out += hero_manifest(ctx, project, r)
            elif name == 'imagegen-index.json':
                out += imagegen_index(ctx, project, r)
            elif CSV_RE.search(r):
                out += taoyuan_csv(ctx, project, r, files)
            elif MJS_RE.search(r):
                ctx.warn(f'manifest 存在，未解析: {r}')
                out.append(_row(ctx, project, r, r, source_tool='manifest',
                                tags_json=jdump(['manifest-entry', 'unparsed'])))
    return out
