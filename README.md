# forge — 生产管线与资产的共享层

依据 [ADR-0013](../../docs/kb/decisions/0013-production-platform-direction.md)（accepted 2026-10-05）。
自建项目约定见 [ADR-0003](../../docs/kb/decisions/0003-works-layer-for-self-built-projects.md)。

## 定位

`works/` 下 38 个项目把同几条生产管线（截图验收、抠图、ComfyUI 客户端、Blender headless、
图集打包……）各写了一遍，跨项目复用靠"复制文件 + 一行来源注释"。forge 把这些管线收成
单一实现，并给所有项目的 AI 生成资产建一个带 license 的索引。

imgen（`.claude/skills/image-generation/`）是唯一已收敛的样板：单一实现、MCP + CLI 双入口、
`.gen.json` 旁路、`imgen_batch.py` 被 9 个项目共用。其余管线照这个模式收。

## 三原则

1. **管线单元 = skill**：`SKILL.md`（何时用）+ `references/`（SOP 与坑单）+ `scripts/`
   （确定性 CLI）+ `checks/`（可执行门）。agent 和人走同一入口。
2. **资产库 = 索引，不是仓库**：不搬文件、不改各项目目录；爬 sidecar 建索引，license 必填
   且默认 `unknown`。"公用"靠 `promote` 拷进 `shared-assets/`（gitignore，带 license 闸）。
3. **老项目不迁移，新项目只准用 forge**：消重靠下一个项目从 forge 起，不靠回头改。

## 目录

```
works/forge/
├── README.md           # 本文件
├── STATE.md            # 当前焦点 / 下一步
├── docs/
│   ├── decisions/      # forge 内部技术决策（workspace 级 ADR 在 docs/kb/decisions/）
│   └── pitfalls.md     # 跨管线坑单总表
├── registry/           # 管线登记：每条一份 yaml + 校验脚本
│   ├── README.md / schema.md / validate.py
│   └── pipelines/<id>.yaml
├── catalog/            # 资产索引器（另一批次负责）
└── skills/             # P1 起迁入的管线 skill（现在只有 README 占位）
```

## 怎么用 registry

- 查某条管线现存几份实现、该以哪份为基准：读 `registry/pipelines/<id>.yaml` 的
  `implementations` 与 `baseline_candidate`。
- 查某环节踩过的坑：yaml 的 `pitfalls`，或总表 `docs/pitfalls.md`。
- 改完 yaml 跑校验（在 workspace 根）：

  ```
  python works/forge/registry/validate.py
  ```

  必填 / 枚举 / id 与文件名不一致 → FAIL（退出码 1）；路径不存在 → WARN（部分路径在
  gitignore 的 `_work` 内，换机器会缺）。
- 新增条目流程见 `registry/README.md`，字段表见 `registry/schema.md`。

## 分期（摘自 ADR-0013）

| 期 | 产物 |
|---|---|
| P0 看见 | registry（本目录）+ catalog 索引器 + 静态画廊 |
| P1 收敛 | shots / cutout / comfy 合成单一实现，新项目强制用 |
| P2 续接 | blender / char3d / sprite / audio / mining 迁入；`.gen3d.json`；`promote` + license 闸 |
| P3 平台 | `console/` 薄 Web 壳 |
| P4 开源 | skills + registry + catalog + console 独立仓；shared-assets 与 prompts 私有 |
