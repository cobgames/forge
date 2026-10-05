"""unittest suite (pytest not installed). Run from works/forge/catalog:
    python -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import fixture_ws  # noqa: E402
from forge_catalog import report, scan  # noqa: E402
from forge_catalog.model import license_color, make_id  # noqa: E402

INBOX = 'works/alpha/' + fixture_ws.INBOX


def _read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


class CatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix='forge_catalog_test_')
        cls.ws = fixture_ws.build(cls.tmp)
        cls.out = os.path.join(cls.tmp, 'out')
        cls.res = scan.run_scan(os.path.join(cls.ws, 'works'), cls.out)
        con = sqlite3.connect(os.path.join(cls.out, 'catalog.sqlite'))
        con.row_factory = sqlite3.Row
        cls.assets = {r['rel_path']: dict(r) for r in con.execute('SELECT * FROM assets')}
        cls.ledgers = [dict(r) for r in con.execute('SELECT * FROM ledgers')]
        cls.dups = [dict(r) for r in con.execute('SELECT * FROM duplicates')]
        con.close()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def a(self, rel):
        self.assertIn(rel, self.assets, f'missing row {rel}; have {sorted(self.assets)}')
        return self.assets[rel]

    # --- parsers -----------------------------------------------------------
    def test_imgen_sidecar_fields(self):
        r = self.a(f'{INBOX}/ref__v1.png')
        self.assertEqual((r['kind'], r['source_tool'], r['model']), ('image2d', 'imgen', 'gpt-image-2'))
        self.assertEqual(r['prompt'], 'a red reference cat')
        self.assertEqual(r['seed'], '7')
        self.assertEqual(r['batch'], '2026-01-01__cats')
        self.assertEqual(r['created_at'], '2026-01-01T10:00:00+08:00')
        self.assertEqual(r['sidecar_path'], f'{INBOX}/ref__v1.gen.json')
        self.assertEqual(r['file_exists'], 1)
        self.assertEqual(r['id'], make_id('alpha', r['rel_path']))
        self.assertRegex(r['content_hash'], r'^[0-9a-f]{64}$')
        self.assertIn('cats', json.loads(r['tags_json']))

    def test_imgen_manifest_enriches_and_adds_entry(self):
        cat = self.a(f'{INBOX}/cat__v1.png')
        self.assertEqual(json.loads(cat['params_json'])['_manifest']['idx'], 1)
        m = self.a(f'{INBOX}/001_gpt-image-2.png')
        self.assertEqual((m['kind'], m['prompt'], m['model']), ('manifest-entry', 'a blue batch cat', 'gpt-image-2'))

    def test_war3_meta(self):
        r = self.a('works/alpha/assets-lib/fac/unit/unit.glb')
        self.assertEqual((r['kind'], r['source_tool'], r['model']), ('model3d', 'comfyui-trellis2', 'trellis_2_int8'))
        self.assertEqual(json.loads(r['seed']), {'shape': 42, 'tex': 43})
        self.assertEqual(r['batch'], 'fac')
        self.assertEqual(r['created_at'], '2026-01-02')

    def test_hy3d_meta(self):
        r = self.a('works/beta/exp/pipeline/out/k/house_hy3d.glb')
        self.assertEqual((r['source_tool'], r['model'], r['seed']), ('hunyuan3d', 'hy3d', '2024'))
        self.assertEqual(json.loads(r['input_refs_json']), ['works/beta/exp/refs/in.png'])

    def test_terraweave_manifest(self):
        r = self.a('works/beta/art/assets/TW_x.gltf')
        self.assertEqual((r['kind'], r['license']), ('manifest-entry', 'CC0-1.0'))
        self.assertEqual(r['license_source'], 'works/beta/art/asset-manifest.json')

    def test_compare(self):
        r = self.a(f'{INBOX}/_COMPARE_cats.png')
        self.assertEqual((r['kind'], r['batch']), ('compare', '2026-01-01__cats'))
        self.assertTrue(r['created_at'])

    # --- linking -------------------------------------------------------------
    def test_derived_chain(self):
        ref, cat = self.a(f'{INBOX}/ref__v1.png'), self.a(f'{INBOX}/cat__v1.png')
        self.assertEqual(json.loads(cat['input_refs_json']), [ref['rel_path']])
        self.assertEqual(json.loads(cat['derived_from']), [ref['id']])
        unit = self.a('works/alpha/assets-lib/fac/unit/unit.glb')
        self.assertEqual(json.loads(unit['derived_from']), [cat['id']])

    def test_ledger_match_and_colors(self):
        ref = self.a(f'{INBOX}/ref__v1.png')
        self.assertEqual(ref['license'], '非商用')
        self.assertEqual(ref['license_source'], 'works/alpha/assets/LICENSES.md')
        self.assertEqual(license_color(ref['license']), 'red')
        lg = next(x for x in self.ledgers if 'ref__v1.png' in x['asset_name'])
        self.assertEqual((lg['commercial'], lg['redistribution'], lg['registered_at']), ('不允许', '不允许', '2026-01-03'))
        unmatched = [r for r in self.assets.values() if r['kind'] == 'ledger-entry']
        self.assertEqual(len(unmatched), 1)
        self.assertEqual(unmatched[0]['license'], 'CC0 1.0')
        song = self.a('works/beta/assets/bgm/song.mp3')
        self.assertEqual((song['kind'], song['license']), ('audio', 'Pixabay Content License'))

    def test_license_auto_rules_hit(self):
        q = self.a(f'{INBOX}/qwen__v1.png')
        self.assertEqual((q['source_tool'], q['license_source']), ('comfyui-qwen', 'rule:model'))
        self.assertTrue(q['license'].startswith('non-commercial (Qwen'))
        self.assertEqual(license_color(q['license']), 'red')
        m = self.a(f'{INBOX}/song__v1.png')
        self.assertTrue(m['license'].startswith('non-commercial (MiniMax'))
        gpt = self.a(f'{INBOX}/ref__v1.png')   # gpt-image: rule leaves ledger/unknown alone
        self.assertNotEqual(gpt['license_source'], 'rule:model')
        hits = self.res['counts']['license_rules']
        self.assertEqual((hits['qwen-image'], hits['minimax-music']), (2, 1))

    def test_ledger_beats_rule(self):
        q = self.a(f'{INBOX}/qwenled__v1.png')
        self.assertEqual((q['license'], q['license_source']), ('自产', 'works/alpha/assets/LICENSES.md'))
        self.assertEqual(q['source_tool'], 'comfyui-qwen')

    def test_license_color_rule(self):
        self.assertEqual(license_color('unknown'), 'grey')
        self.assertEqual(license_color(''), 'grey')
        self.assertEqual(license_color('Non-Commercial research'), 'red')
        self.assertEqual(license_color('技术研究阶段不判'), 'red')
        self.assertEqual(license_color('CC0-1.0'), 'green')

    def test_duplicates_cross_project(self):
        cross = [d for d in self.dups if len(json.loads(d['projects_json'])) >= 2]
        self.assertEqual(len(cross), 1)
        ids = set(json.loads(cross[0]['asset_ids_json']))
        self.assertEqual(ids, {self.a(f'{INBOX}/cat__v1.png')['id'],
                               self.a('works/beta/assets/_inbox/2026-02-02__dup/copy__v1.png')['id']})

    def test_bad_json_only_warns(self):
        self.assertTrue(any('bad__v1.gen.json' in w for w in self.res['warnings']))
        r = self.a(f'{INBOX}/bad__v1.png')
        self.assertIsNone(r['prompt'])

    # --- orphans / outputs -----------------------------------------------------
    def test_orphans_counted_not_rows(self):
        self.assertEqual(self.res['counts']['orphans_total'], 1)
        self.assertNotIn('works/alpha/assets/_work/x/orphan.png', self.assets)

    def test_include_orphans_flag(self):
        out2 = os.path.join(self.tmp, 'out_orphans')
        run = scan.run_scan(os.path.join(self.ws, 'works'), out2, include_orphans=True, no_thumbs=True)
        con = sqlite3.connect(os.path.join(out2, 'catalog.sqlite'))
        row = con.execute("SELECT kind, source_tool FROM assets WHERE rel_path LIKE '%orphan.png'").fetchone()
        con.close()
        self.assertEqual(row, ('image2d', 'unknown'))
        self.assertEqual(run['counts']['assets'], self.res['counts']['assets'] + 1)
        self.assertFalse(os.listdir(os.path.join(out2, 'thumbs')) if os.path.isdir(os.path.join(out2, 'thumbs')) else [])

    def test_summary_numbers(self):
        md = _read(os.path.join(self.out, 'summary.md'))
        self.assertIn(f"- assets: **{len(self.assets)}**", md)
        self.assertIn('orphan images (assets/_inbox|_work, no sidecar): **1**', md)
        self.assertIn('cross-project: **1**', md)
        self.assertIn(f'- ledger rows: **{len(self.ledgers)}**', md)
        self.assertRegex(md, r'\| alpha \| \d+ \|')

    def test_gallery_and_thumbs(self):
        html = _read(os.path.join(self.out, 'gallery.html'))
        self.assertTrue(html.lower().startswith('<!doctype html>'))
        self.assertIn('<meta charset="utf-8">', html)
        m = re.search(r'<script type="application/json" id="catalog-data">(.*?)</script>', html, re.S)
        self.assertIsNotNone(m)
        data = json.loads(m.group(1))
        self.assertEqual(len(data['assets']), len(self.assets))
        self.assertNotIn('http://', html.split('<script type="application/json"')[0])
        cat = self.a(f'{INBOX}/cat__v1.png')
        self.assertTrue(os.path.exists(os.path.join(self.out, 'thumbs', cat['id'] + '.jpg')))
        self.assertTrue(os.path.exists(os.path.join(self.out, 'catalog.json')))

    def test_report_regenerates(self):
        os.remove(os.path.join(self.out, 'gallery.html'))
        report.regenerate(self.out)
        self.assertTrue(os.path.exists(os.path.join(self.out, 'gallery.html')))


if __name__ == '__main__':
    unittest.main()
