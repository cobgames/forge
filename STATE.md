---
project: forge
last_updated: 2026-10-05
---

# forge — STATE

生产管线与资产的共享层（[ADR-0013](../../docs/kb/decisions/0013-production-platform-direction.md)）。

## Focus

**P0 看见：registry + catalog 索引器。**

## 最近做了什么

- 2026-10-05 ADR-0013 拍板（accepted），P0 开工。
- 建骨架；`registry/pipelines/` 登记 12 条管线（imgen / shots / compare / cutout / sprite / comfy /
  img2three / blender / glb / char3d / audio / mining），`validate.py` 通过；坑单总表 `docs/pitfalls.md`。
- 2026-10-05 P0-B catalog 完成：`catalog scan` 全量 4895 条资产，license 覆盖率 9.4%（462，含 qwen 自动规则 25 条），
  红色（非商用类）66，孤儿图 5172（只计数），跨项目重复 0，台账 335 行；18 个测试通过。

## 下一步

1. 按 summary 补 license：pawkov / war3-labs / xmlt / poelike 四个 0% 项目先写 LICENSES.md。
2. P1 起建独立公开仓（forge 公开；shared-assets / prompts 私有）。
3. P1 三条管线收敛：shots / cutout / comfy。

## 开放问题

- 独立仓与 workspace 的链接方式：submodule 还是平行 clone。
- `.gen3d.json` sidecar 的 schema（源图 hash / 工作流 / seed / 面数 / rig 状态）。
- gallery 8.5MB 是否 gzip 内联。

## 关键文件

- [README.md](./README.md) — 定位 / 三原则 / 目录
- [registry/README.md](./registry/README.md) — schema 说明、成熟度、新增流程
- [registry/pipelines/](./registry/pipelines/) — 12 条管线
- [registry/validate.py](./registry/validate.py) — 校验
- [docs/pitfalls.md](./docs/pitfalls.md) — 跨管线坑单
- [catalog/README.md](./catalog/README.md) — 资产索引器用法 / 数据源 / 限制
- `catalog/out/gallery.html` — 资产画廊（scan 生成，gitignore）
- [ADR-0013](../../docs/kb/decisions/0013-production-platform-direction.md) — 方向与分期
