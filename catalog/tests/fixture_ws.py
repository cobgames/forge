"""Builds a mini workspace (fixtures dir) covering every data source.

Layout under <tmp>/ws/works/:
  alpha/  imgen sidecars + _manifest.json + bad json + _COMPARE_ + orphan + LICENSES.md + assets-lib meta
  beta/   duplicate image (same bytes as alpha cat), hy3d meta, terraweave-style manifest, manju-style ledger
"""
from __future__ import annotations

import json
import os

from PIL import Image

INBOX = 'assets/_inbox/2026-01-01__cats'


def _w(path: str, content) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = 'wb' if isinstance(content, bytes) else 'w'
    with open(path, mode, **({} if mode == 'wb' else {'encoding': 'utf-8'})) as f:
        f.write(content)


def _png(path: str, color) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.new('RGB', (64, 48), color).save(path)


def build(tmp: str) -> str:
    ws = os.path.join(tmp, 'ws')
    a = os.path.join(ws, 'works', 'alpha')
    b = os.path.join(ws, 'works', 'beta')
    inbox = os.path.join(a, *INBOX.split('/'))

    _png(os.path.join(inbox, 'ref__v1.png'), (200, 10, 10))
    _w(os.path.join(inbox, 'ref__v1.gen.json'), json.dumps({
        'version': 1, 'created_at': '2026-01-01T10:00:00+08:00', 'method': 'text_to_image',
        'model': 'gpt-image-2', 'prompt': 'a red reference cat', 'params': {'size': '1024x1024', 'seed': 7}}))
    _png(os.path.join(inbox, 'cat__v1.png'), (10, 200, 10))
    _w(os.path.join(inbox, 'cat__v1.gen.json'), json.dumps({
        'version': 1, 'created_at': '2026-01-01T11:00:00+08:00', 'hash': 'sha256:' + 'ab' * 32,
        'method': 'image_edit', 'model': 'gpt-image-2', 'prompt': 'a green cat from the ref',
        'params': {'size': '1024x1024', 'quality': 'high'},
        'input_images': [os.path.join(inbox, 'ref__v1.png')]}))
    _png(os.path.join(inbox, '001_gpt-image-2.png'), (10, 10, 200))
    _w(os.path.join(inbox, '_manifest.json'), json.dumps([
        {'idx': 1, 'ep': 0, 'model': 'gpt-image-2', 'ok': True, 'dt': 3.0,
         'file': 'works\\alpha\\' + INBOX.replace('/', '\\') + '\\gone.png', 'prompt': 'a green cat from the ref'},
        {'idx': 2, 'ep': 1, 'model': 'gpt-image-2', 'ok': True, 'dt': 4.0,
         'file': 'works\\alpha\\' + INBOX.replace('/', '\\') + '\\001_gpt-image-2.png', 'prompt': 'a blue batch cat'},
    ]))
    _png(os.path.join(inbox, 'bad__v1.png'), (90, 90, 90))
    _w(os.path.join(inbox, 'bad__v1.gen.json'), '{"version": 1, "prompt": ')
    _png(os.path.join(inbox, '_COMPARE_cats.png'), (255, 255, 0))
    for name, color, extra in (('qwen__v1', (30, 60, 90), {'models': {'unet': 'qwen_image_2.1_bf16.safetensors'}}),
                               ('qwenled__v1', (31, 61, 91), {'models': {'unet': 'qwen_image_2.1_int8.safetensors'}}),
                               ('song__v1', (32, 62, 92), {'model': 'minimax-music-03'})):
        _png(os.path.join(inbox, name + '.png'), color)
        _w(os.path.join(inbox, name + '.gen.json'), json.dumps(dict(prompt=name, **extra)))
    _png(os.path.join(a, 'assets', '_work', 'x', 'orphan.png'), (1, 2, 3))

    lib = os.path.join(a, 'assets-lib', 'fac', 'unit')
    _w(os.path.join(lib, 'unit.glb'), b'glTF-fake')
    _w(os.path.join(lib, 'meta.json'), json.dumps({
        'id': 'unit', 'faction': 'fac', 'kind': 'hero', 'date': '2026-01-02',
        'source_image': INBOX + '/cat__v1.png',
        'generation': {'tool': 'TRELLIS.2', 'weights': 'trellis_2_int8', 'seeds': {'shape': 42, 'tex': 43}},
        'glb': 'assets-lib/fac/unit/unit.glb'}))
    _w(os.path.join(a, 'assets', 'LICENSES.md'), '\n'.join([
        '# ledger', '', '| 资产 | 来源（URL） | 许可 | 商用 | 再分发 | 登记日期 | 备注 |',
        '|---|---|---|---|---|---|---|',
        '| `ref__v1.png`（参考图） | https://example.com/ref | 非商用 | 不允许 | 不允许 | 2026-01-03 | test |',
        '| `qwenled__v1.png` | 本仓生成 | 自产 | — | — | 2026-01-03 | ledger wins |',
        '| `missing.fbx` | https://example.com/m | CC0 1.0 | 允许 | 允许 | 2026-01-03 | |', '']))

    with open(os.path.join(inbox, 'cat__v1.png'), 'rb') as f:
        _w(os.path.join(b, INBOX.replace('2026-01-01__cats', '2026-02-02__dup'), 'copy__v1.png'), f.read())
    _w(os.path.join(b, INBOX.replace('2026-01-01__cats', '2026-02-02__dup'), 'copy__v1.gen.json'),
       json.dumps({'model': 'gpt-image-1', 'prompt': 'copied cat', 'created_at': '2026-02-02T00:00:00+08:00'}))
    exp = os.path.join(b, 'exp', 'pipeline', 'out', 'k')
    _png(os.path.join(b, 'exp', 'refs', 'in.png'), (5, 5, 5))
    _w(os.path.join(exp, 'house_hy3d_raw.glb'), b'glTF-raw')
    _w(os.path.join(exp, 'house_hy3d.glb'), b'glTF-final')
    _w(os.path.join(exp, 'house_hy3d_meta.json'), json.dumps(
        {'env': {'python': '3.12'}, 'args': {'image': 'refs/in.png', 'seed': 2024, 'steps': 50}}))
    _w(os.path.join(b, 'art', 'assets', 'TW_x.gltf'), '{}')
    _w(os.path.join(b, 'art', 'asset-manifest.json'), json.dumps({
        'project': 'beta', 'version': '1', 'schema': {},
        'assets': [{'id': 'TW_x', 'source': 'assets/TW_x.gltf', 'license': 'CC0-1.0', 'sockets': ['land']}]}))
    _w(os.path.join(b, 'assets', 'bgm', 'song.mp3'), b'ID3fake')
    _w(os.path.join(b, 'assets', 'bgm', '_licenses.md'), '\n'.join([
        '# BGM', '', '## 许可证：Pixabay Content License（同源）', '', '## 曲目清单', '',
        '### 1. Song', '', '- 文件：`song.mp3`', '- 来源页：<https://pixabay.com/music/song-1/>', '']))
    return ws
