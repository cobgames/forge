"""Asset row model, ids, path helpers and license colour rule."""
from __future__ import annotations

import hashlib
import json
import os
import re

IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.webp')
MODEL_EXT = ('.glb', '.gltf', '.fbx', '.vrm', '.obj', '.blend')
AUDIO_EXT = ('.mp3', '.wav', '.ogg', '.flac', '.m4a')
EXCLUDE_DIRS = {'node_modules', '.git', 'dist', 'coverage', '__pycache__', 'repos'}
HASH_LIMIT = 50 * 1024 * 1024

FIELDS = [
    'id', 'project', 'kind', 'rel_path', 'file_exists', 'bytes', 'mtime',
    'content_hash', 'created_at', 'source_tool', 'model', 'prompt', 'seed',
    'params_json', 'input_refs_json', 'derived_from', 'license', 'license_source',
    'batch', 'tags_json', 'sidecar_path', 'raw_json',
]

RED_RE = re.compile(r'non-commercial|非商用|不允许|研究阶段不判', re.I)


def make_id(project: str, rel_path: str) -> str:
    return hashlib.sha256(f'{project}:{rel_path}'.encode('utf-8')).hexdigest()[:16]


def new_asset(project: str, kind: str, rel_path: str, **kw) -> dict:
    a = {k: None for k in FIELDS}
    a.update(project=project, kind=kind, rel_path=rel_path, file_exists=0,
             license='unknown', source_tool='unknown')
    a.update({k: v for k, v in kw.items() if k in a})
    a['id'] = make_id(project, rel_path)
    return a


def jdump(v) -> str | None:
    if v is None:
        return None
    return json.dumps(v, ensure_ascii=False)


def license_color(value) -> str:
    v = (value or '').strip()
    if RED_RE.search(v):
        return 'red'
    if not v or v.lower() == 'unknown':
        return 'grey'
    return 'green'


def kind_by_ext(path: str) -> str | None:
    p = path.lower()
    if p.endswith(IMAGE_EXT):
        return 'image2d'
    if p.endswith(MODEL_EXT):
        return 'model3d'
    if p.endswith(AUDIO_EXT):
        return 'audio'
    return None


def norm_hash(h) -> str | None:
    if not isinstance(h, str) or not h:
        return None
    h = h.split(':', 1)[1] if h.lower().startswith('sha256:') else h
    return h.lower() if re.fullmatch(r'[0-9a-fA-F]{64}', h) else None


def sha256_file(abs_path: str) -> str | None:
    try:
        if os.path.getsize(abs_path) > HASH_LIMIT:
            return None
        h = hashlib.sha256()
        with open(abs_path, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 20), b''):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


class Ctx:
    """Shared scan context: workspace root, file index, warnings."""

    def __init__(self, ws_root: str, works_rel: str, projects: list[str]):
        self.ws_root = os.path.abspath(ws_root)
        self.works_rel = works_rel.strip('/').replace('\\', '/')
        self.projects = projects
        self.warnings: list[str] = []
        self.files: dict[str, list[str]] = {}   # project -> rel paths (all files)

    def rel(self, abs_path: str) -> str:
        return os.path.relpath(abs_path, self.ws_root).replace('\\', '/')

    def abs(self, rel_path: str) -> str:
        return os.path.join(self.ws_root, rel_path.replace('/', os.sep))

    def project_rel(self, project: str) -> str:
        return f'{self.works_rel}/{project}'

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def read_json(self, rel_path: str):
        try:
            with open(self.abs(rel_path), encoding='utf-8-sig') as f:
                return json.load(f)
        except (OSError, ValueError) as e:
            self.warn(f'bad json {rel_path}: {type(e).__name__}: {str(e)[:120]}')
            return None

    def resolve_ref(self, ref, base_rel: str, project: str) -> str | None:
        """Turn a path string from a sidecar into a workspace-relative path.

        Absolute paths under the workspace are made relative; relative paths are
        tried against base dir and each ancestor up to the project root. Returns
        the normalised string even when nothing exists (raw if outside workspace).
        """
        if not isinstance(ref, str) or not ref.strip():
            return None
        r = ref.strip()
        if os.path.isabs(r) or re.match(r'^[A-Za-z]:[\\/]', r):
            ap = os.path.abspath(r)
            try:
                if os.path.commonpath([ap, self.ws_root]) == self.ws_root:
                    return self.rel(ap)
            except ValueError:
                pass
            return r.replace('\\', '/')
        r = r.replace('\\', '/')
        if r.startswith(self.works_rel + '/'):
            return r
        proot = self.project_rel(project)
        d = base_rel
        while True:
            cand = os.path.normpath(os.path.join(d, r)).replace('\\', '/')
            if os.path.exists(self.abs(cand)):
                return cand
            if d == proot or '/' not in d or not d.startswith(proot):
                break
            d = d.rsplit('/', 1)[0]
        return os.path.normpath(os.path.join(base_rel, r)).replace('\\', '/')

    def fill_file(self, a: dict) -> dict:
        """Fill file_exists/bytes/mtime (content hash is computed later in bulk)."""
        ap = self.abs(a['rel_path'])
        if os.path.isfile(ap):
            st = os.stat(ap)
            a['file_exists'], a['bytes'], a['mtime'] = 1, st.st_size, st.st_mtime
        return a


# --- license auto-rules -------------------------------------------------------
# Applied after ledger back-fill. A rule only fills license when it is still
# unknown (ledger values win); `set` fields (e.g. source_tool) are applied on any hit.
# license=None means "matched, deliberately left unknown" (counted, not changed).
LICENSE_RULES = [
    {'name': 'qwen-image', 'fields': ('model',), 'pattern': r'qwen_image|qwen-image',
     'license': 'non-commercial (Qwen-Image-2.1 license, auto-rule)', 'source': 'rule:model',
     'set': {'source_tool': 'comfyui-qwen'}, 'note': 'Qwen-Image-2.1 weights are non-commercial'},
    {'name': 'minimax-music', 'fields': ('model', 'params_json', 'raw_json'),
     'pattern': r'minimax|music-03|music_03',
     'license': 'non-commercial (MiniMax Music, auto-rule)', 'source': 'rule:model',
     'set': {}, 'note': 'MiniMax Music 3 local weights, non-commercial'},
    {'name': 'gpt-image-kept-unknown', 'fields': ('model',), 'pattern': r'^gpt-image',
     'license': None, 'source': None, 'set': {},
     'note': 'OpenAI terms not in any ledger; do not guess', 'only_sidecar': '.gen.json'},
]


def _is_unknown(v) -> bool:
    return not (v or '').strip() or v.strip().lower() == 'unknown'


def apply_license_rules(assets: list[dict], rules=None) -> dict:
    """First matching rule per asset wins. Returns {rule name: hit count}."""
    rules = LICENSE_RULES if rules is None else rules
    compiled = [(r, re.compile(r['pattern'], re.I)) for r in rules]
    hits = {r['name']: 0 for r in rules}
    for a in assets:
        for r, rx in compiled:
            suffix = r.get('only_sidecar')
            if suffix and not (a.get('sidecar_path') or '').endswith(suffix):
                continue
            text = '\n'.join(str(a.get(f) or '') for f in r['fields'])
            if not rx.search(text):
                continue
            a.update(r['set'])
            if r['license'] and _is_unknown(a.get('license')):
                a['license'], a['license_source'] = r['license'], r['source']
            hits[r['name']] += 1
            break
    return hits
