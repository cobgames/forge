"""CLI: `python -m forge_catalog scan|report`."""
from __future__ import annotations

import argparse
import sys

from . import report, scan


def main(argv=None) -> int:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    p = argparse.ArgumentParser(prog='forge_catalog', description='Read-only asset provenance index.')
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('scan', help='crawl sidecars/manifests/ledgers and build the catalog')
    s.add_argument('--root', default='works', help='works/ directory (rel_path is relative to its parent)')
    s.add_argument('--out', default='works/forge/catalog/out')
    s.add_argument('--include-orphans', action='store_true', help='also add sidecar-less inbox images as rows')
    s.add_argument('--no-thumbs', action='store_true')
    s.add_argument('--projects', default=None, help='comma-separated subset of project dirs')
    r = sub.add_parser('report', help='regenerate summary.md + gallery.html from catalog.sqlite')
    r.add_argument('--out', default='works/forge/catalog/out')
    a = p.parse_args(argv)

    if a.cmd == 'scan':
        run = scan.run_scan(a.root, a.out, a.include_orphans, a.no_thumbs, a.projects)
        c = run['counts']
        print(f"assets {c['assets']}  by_kind {c['by_kind']}")
        print(f"orphans {c['orphans_total']}  duplicate_groups {c['duplicate_groups']}  "
              f"ledger_rows {c['ledger_rows']}  thumbs {c['thumbs']}")
        print(f"timing {c['timing']}  warnings {len(run['warnings'])}")
        for w in run['warnings'][:10]:
            print('  !', w)
    else:
        data = report.regenerate(a.out)
        print(f"report regenerated: {len(data['assets'])} assets -> {a.out}")
    return 0
