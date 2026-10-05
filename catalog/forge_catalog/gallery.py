"""Single-file static gallery: inline JSON + vanilla JS/CSS, thumbs via relative paths."""
from __future__ import annotations

import html
import json
import os

from .gallery_js import JS
from .model import license_color

DROP = ('raw_json',)

CSS = """
:root{--bg:#121316;--panel:#1b1d22;--card:#22252b;--fg:#e6e6e9;--mute:#9a9ca4;--line:#30333a;
--acc:#6aa7ff;--red:#e5534b;--grey:#7d8088;--green:#46c46c;--fs:clamp(13px,.72vw,24px)}
@media (prefers-color-scheme:light){:root{--bg:#f4f4f6;--panel:#fff;--card:#fff;--fg:#1d1e22;
--mute:#62646c;--line:#dcdde2;--acc:#2563eb}}
*{box-sizing:border-box}html,body{margin:0;height:100%}
body{background:var(--bg);color:var(--fg);font:var(--fs)/1.45 system-ui,"Segoe UI","Microsoft YaHei",sans-serif;
display:grid;grid-template-rows:auto 1fr;overflow:hidden}
header{display:flex;gap:1.5em;align-items:center;padding:.6em 1em;background:var(--panel);
border-bottom:1px solid var(--line);flex-wrap:wrap}
header h1{font-size:1.15em;margin:0}.stat{color:var(--mute)}.stat b{color:var(--fg);font-size:1.15em}
.tabs{margin-left:auto;display:flex;gap:.4em}.tabs button,.btn{background:var(--card);color:var(--fg);
border:1px solid var(--line);border-radius:6px;padding:.3em .8em;font:inherit;cursor:pointer}
.tabs button.on{background:var(--acc);color:#fff;border-color:var(--acc)}
main{display:grid;grid-template-columns:clamp(220px,15vw,520px) 1fr;min-height:0}
aside{overflow:auto;padding:.6em .8em;border-right:1px solid var(--line);background:var(--panel)}
aside h3{font-size:.85em;text-transform:uppercase;letter-spacing:.05em;color:var(--mute);margin:1em 0 .3em}
aside input[type=text],aside input[type=date]{width:100%;font:inherit;padding:.3em .5em;background:var(--card);
color:var(--fg);border:1px solid var(--line);border-radius:5px}
.opts{max-height:13em;overflow:auto;border:1px solid var(--line);border-radius:5px;padding:.2em .4em}
.opts label{display:flex;gap:.4em;align-items:center;white-space:nowrap;cursor:pointer;font-size:.92em}
.opts label span.n{margin-left:auto;color:var(--mute)}.opts input[type=text]{margin:.2em 0}
#gridwrap{overflow:auto;padding:.8em}#count{color:var(--mute);margin-bottom:.6em}
#grid{display:grid;gap:.7em;grid-template-columns:repeat(auto-fill,minmax(clamp(150px,10.5vw,380px),1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;overflow:hidden;cursor:pointer;
display:flex;flex-direction:column}.card:hover{border-color:var(--acc)}
.thumb{aspect-ratio:1;background:#0004;display:flex;align-items:center;justify-content:center;
color:var(--mute);font-size:1.6em;font-weight:600}.thumb img{width:100%;height:100%;object-fit:contain}
.meta{padding:.35em .5em;font-size:.85em;display:grid;gap:.1em}.meta div{overflow:hidden;
text-overflow:ellipsis;white-space:nowrap}.lic{display:inline-block;width:.75em;height:.75em;border-radius:50%;
margin-right:.35em;vertical-align:middle}.lic.red{background:var(--red)}.lic.grey{background:var(--grey)}
.lic.green{background:var(--green)}.mute{color:var(--mute)}.missing{outline:2px dashed var(--red)}
#drawer{position:fixed;top:0;right:0;height:100%;width:clamp(380px,32vw,1300px);background:var(--panel);
border-left:1px solid var(--line);box-shadow:-8px 0 24px #0006;transform:translateX(105%);
transition:transform .18s;overflow:auto;padding:1em;z-index:5}#drawer.on{transform:none}
#drawer img{max-width:100%;max-height:40vh;display:block;margin:0 auto .8em;background:#0004}
#drawer table{border-collapse:collapse;width:100%;font-size:.9em}#drawer td{border-top:1px solid var(--line);
padding:.25em .4em;vertical-align:top;word-break:break-all}#drawer td:first-child{color:var(--mute);
white-space:nowrap;width:1%}#drawer pre{white-space:pre-wrap;word-break:break-word;background:var(--card);
padding:.6em;border-radius:6px;font-size:.88em;max-height:40vh;overflow:auto}
a.jump{color:var(--acc);cursor:pointer;text-decoration:underline}
#more{margin:1em auto;display:block}
"""


def _compact(a: dict, thumbs_dir: str) -> dict:
    d = {k: v for k, v in a.items() if k not in DROP and v is not None}
    d['lc'] = license_color(a.get('license'))
    if os.path.exists(os.path.join(thumbs_dir, a['id'] + '.jpg')):
        d['thumb'] = 1
    return d


def payload(data: dict, thumbs_dir: str) -> dict:
    counts = data['run']['counts']
    return {
        'run': {k: data['run'][k] for k in ('run_id', 'started_at', 'root')},
        'orphans_total': counts.get('orphans_total', 0),
        'orphans': counts.get('orphans', {}),
        'ledger_rows': counts.get('ledger_rows', 0),
        'dup_groups': len(data['duplicates']),
        'assets': [_compact(a, thumbs_dir) for a in data['assets']],
    }


def render(data: dict, thumbs_dir: str) -> str:
    blob = json.dumps(payload(data, thumbs_dir), ensure_ascii=False, separators=(',', ':'))
    blob = blob.replace('</', '<\\/')
    title = html.escape(f"forge catalog · {data['run']['started_at']}")
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>{CSS}</style></head>
<body>
<header><h1>forge catalog</h1><div id="stats"></div>
<div class="tabs"><button data-tab="assets" class="on">资产</button><button data-tab="compare">_COMPARE_ 对比图</button></div>
</header>
<main><aside id="filters"></aside>
<section id="gridwrap"><div id="count"></div><div id="grid"></div>
<button id="more" class="btn">加载更多</button></section></main>
<div id="drawer"></div>
<script type="application/json" id="catalog-data">{blob}</script>
<script>{JS}</script>
</body></html>
"""


def write(path: str, data: dict, thumbs_dir: str) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(render(data, thumbs_dir))
