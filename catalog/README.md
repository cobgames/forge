# forge catalog — 资产来源 / 许可索引器（P0）

只读爬 `works/*` 已有的 sidecar / meta / manifest / 许可台账，生成一个 SQLite 目录和一个单文件静态画廊。
不搬文件、不改任何项目。依据 [ADR-0013](../../../docs/kb/decisions/0013-production-platform-direction.md) 原则 2。

## 命令（在仓库根目录跑；包在 `works/forge/catalog/` 下，需 `PYTHONPATH`）

```bash
PYTHONPATH=works/forge/catalog python -m forge_catalog scan --root works --out works/forge/catalog/out \
    [--include-orphans] [--no-thumbs] [--projects pawkov,war3-labs]
PYTHONPATH=works/forge/catalog python -m forge_catalog report --out works/forge/catalog/out   # 只重生成 summary + gallery
```

PowerShell：`$env:PYTHONPATH='works/forge/catalog'; python -m forge_catalog scan ...`。依赖 Python 3.14 + Pillow；全量约 35s（首跑，含缩略图），复跑约 6s。
测试：`cd works/forge/catalog && python -m unittest discover -s tests`（pytest 未装）。

## 数据源与取的字段

| 源 | 匹配 | 取的字段 |
|---|---|---|
| imgen sidecar | `**/*.gen.json`，产物 = 同名（或去 `__vN`）png/jpg/webp | created_at, model（qwen 取 `models.unet`，responses 取 `image_model`）, prompt, params, seed, hash, input_images/refs/copied_from |
| imgen_batch 清单 | `**/_manifest.json`（list 型） | 能按 prompt 对上 sidecar → 并入其 params `_manifest`；文件在且无 sidecar → manifest-entry 行 |
| war3 3D meta | `assets-lib/*/*/meta.json` | id, faction, date, source_image, generation{weights, seeds}, build, glb |
| hy3d meta | `*_hy3d_meta.json` | args{image, seed, ...}，产物同前缀 `.glb` |
| terraweave | `asset-manifest.json` | 每项 id / source / license / sockets |
| 其它清单 | clone-lab `hero/*.manifest.json`、zcds `imagegen-index.json`、taoyuan `catalog_*.csv`、war3 `*-asset-map.mjs`（只记存在） | 见 `sources/manifests.py` 文件头 |
| 许可台账 | `works/*/{assets,public}/**/{LICENSES,CREDITS,_licenses}.md` | 表格行 + manju 标题式；按反引号/扩展名文件名匹配同项目资产回填 license |
| 对比图 | `**/_COMPARE_*.png/jpg` | batch = 目录名，created_at = mtime |
| 孤儿图 | `assets/_inbox|_work` 下无任何行覆盖的图片 | 默认只计数 |

排除目录：node_modules / .git / dist / coverage / __pycache__ / repos；`works/forge` 自身不扫。

**License 自动规则**（`model.py` 的 `LICENSE_RULES`，台账回填之后应用，只填 unknown）：
qwen_image → `comfyui-qwen` + non-commercial；minimax / music-03 → non-commercial；gpt-image → 保持 unknown（不猜 OpenAI 条款）。

## 输出（`out/`，已 gitignore）

- `catalog.sqlite` — 表 assets / ledgers / scan_runs / duplicates
- `catalog.json` — assets 数组 + meta（run、duplicates、ledgers、warnings）
- `summary.md` — 按项目计数、kind / source_tool 分布、license 覆盖率、孤儿、规则命中、跨项目重复 top 50、warnings
- `thumbs/<id>.jpg` — 长边 ≤256，未变化跳过
- `gallery.html` — 单文件，`file://` 直接打开；筛选 project/kind/source_tool/model/license/batch + 搜索 + 日期；
  抽屉显示全字段、派生链、同 hash 列表；`_COMPARE_` 独立页签；license 色标 灰=unknown 红=非商用/不允许/研究阶段不判 绿=其它

## 已知限制

- `gallery.html` 约 8.5 MB（主要是 prompt 全文，去重后仍约 4 MB），明文内联未压缩。
- 孤儿只计数（约 5.2k）；`--include-orphans` 才入行。
- qwen 规则按 model 名判定；MiniMax 产物目前没有 sidecar，规则命中 0。
- dict 型 `_manifest.json`（manju startframes、zcds/taskbar 逆向清单等）静默跳过；list 型里找不到文件的条目只记 warning。
- 重复检测靠文件 sha256（>50 MB 不算）；派生链只认能解析到本目录内路径的输入图。
