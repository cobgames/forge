"""SQLite schema + read/write, and catalog.json export."""
from __future__ import annotations

import json
import os
import sqlite3

from .model import FIELDS

LEDGER_FIELDS = ['project', 'ledger_path', 'asset_name', 'source_url', 'license',
                 'commercial', 'redistribution', 'registered_at', 'note']

SCHEMA = f"""
CREATE TABLE assets ({', '.join(f + (' TEXT PRIMARY KEY' if f == 'id' else '') for f in FIELDS)});
CREATE TABLE ledgers ({', '.join(LEDGER_FIELDS)});
CREATE TABLE scan_runs (run_id TEXT PRIMARY KEY, started_at, root, counts_json, warnings_json);
CREATE TABLE duplicates (content_hash TEXT PRIMARY KEY, asset_ids_json, projects_json);
CREATE INDEX ix_assets_project ON assets(project);
CREATE INDEX ix_assets_hash ON assets(content_hash);
"""


def write(path: str, assets, ledgers, run: dict, dups) -> None:
    tmp = path + '.tmp'
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    try:
        con.executescript(SCHEMA)
        con.executemany(f"INSERT INTO assets VALUES ({','.join('?' * len(FIELDS))})",
                        [tuple(a.get(f) for f in FIELDS) for a in assets])
        con.executemany(f"INSERT INTO ledgers VALUES ({','.join('?' * len(LEDGER_FIELDS))})",
                        [tuple(lg.get(f) for f in LEDGER_FIELDS) for lg in ledgers])
        con.execute('INSERT INTO scan_runs VALUES (?,?,?,?,?)',
                    (run['run_id'], run['started_at'], run['root'],
                     json.dumps(run['counts'], ensure_ascii=False),
                     json.dumps(run['warnings'], ensure_ascii=False)))
        con.executemany('INSERT INTO duplicates VALUES (?,?,?)',
                        [(d['content_hash'], json.dumps(d['asset_ids']), json.dumps(d['projects']))
                         for d in dups])
        con.commit()
    finally:
        con.close()
    os.replace(tmp, path)


def read(path: str) -> dict:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    try:
        assets = [dict(r) for r in con.execute('SELECT * FROM assets ORDER BY project, rel_path')]
        ledgers = [dict(r) for r in con.execute('SELECT * FROM ledgers')]
        r = con.execute('SELECT * FROM scan_runs ORDER BY started_at DESC LIMIT 1').fetchone()
        run = {'run_id': r['run_id'], 'started_at': r['started_at'], 'root': r['root'],
               'counts': json.loads(r['counts_json']), 'warnings': json.loads(r['warnings_json'])}
        dups = [{'content_hash': d['content_hash'], 'asset_ids': json.loads(d['asset_ids_json']),
                 'projects': json.loads(d['projects_json'])} for d in con.execute('SELECT * FROM duplicates')]
    finally:
        con.close()
    return {'assets': assets, 'ledgers': ledgers, 'run': run, 'duplicates': dups}


def export_json(path: str, data: dict) -> None:
    doc = {'meta': {'run': data['run'], 'duplicates': data['duplicates'], 'ledgers': data['ledgers']},
           'assets': data['assets']}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False)
