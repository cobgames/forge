---
adr: 0001
title: forge 以 git subtree 发布到独立公开仓，开发仍在 workspace 内
status: accepted
date: 2026-10-05
---

# ADR-0001: 以 git subtree 发布到独立公开仓

## Context

[workspace ADR-0013](../../../../docs/kb/decisions/0013-production-platform-direction.md) 决定 P1 起 forge 在独立公开仓开发，
同时 [ADR-0003](../../../../docs/kb/decisions/0003-works-layer-for-self-built-projects.md) 要求 `works/` 一次 `git pull` 全同步。
两个诉求冲突点在"开发位置"：

- **submodule**：works/forge 变成指针，workspace 拉取后还要 `submodule update`；Claude Code 会话在 workspace 根运行，跨仓改动要两次 commit。
- **平行 clone**：forge 在 workspace 外单独 clone，registry 的实现路径（`works/<project>/...`）与 catalog 扫描根都失去相对位置。
- **subtree**：works/forge 仍是 workspace 的普通目录，用 `git subtree split/push` 把它的历史投影到公开仓；外部贡献用 `git subtree pull` 合回。

## Decision

**开发在 `works/forge/`（workspace 内），发布用 git subtree。** 公开仓 `github.com/cobgames/forge`，分支 `main`。

```bash
# 首次 / 每次发布（在 workspace 根）
git subtree split --prefix=works/forge -b forge-public
git push forge forge-public:main
git branch -D forge-public
# 合回外部贡献
git subtree pull --prefix=works/forge forge main --squash
```

远程名 `forge`：`git remote add forge https://github.com/cobgames/forge.git`。

**公开边界**（与 ADR-0013 一致）：`skills/ registry/ catalog/ console/ docs/` 公开；`shared-assets/`、任何 prompt 配方、
`catalog/out/` 永远 gitignore。`registry/pipelines/*.yaml` 的 `implementations` 指向 workspace 内路径，对外是"来源索引"而非可运行入口，
`canonical` 指向 `skills/<id>` 后才是对外可用的实现。发布前跑 `scripts/publish-check.sh`（P1 建）：grep 密钥 / 内网地址 / 绝对本机路径。

## Consequences

- 公开仓历史由 split 生成，commit message 会带 workspace 语境（项目代号等），可接受。
- subtree split 每次全量重算，仓库小时几秒；增长后可加 `--rejoin`。
- 外部 PR 合回后，workspace 侧会多一个 squash commit；registry 路径冲突由人工处理。
- 若后续需要在 forge 内跑独立 CI，CI 配置放 `works/forge/.github/`，随 subtree 一起发布。
