# forge/skills（占位）

P1 起迁入。每条管线一个目录，沿用 Claude Code skill 布局（与 threejs-game-skills 同款）：

```
skills/<id>/
├── SKILL.md        # 何时用 / 不用、入口命令、输入输出契约（与 registry/pipelines/<id>.yaml 对应）
├── references/     # SOP、pitfalls.md（每条：现象 / 根因 / 规避 / 量化证据 / 来源项目）
├── scripts/        # 确定性 CLI
└── checks/         # 可执行门（如 check_cutout.py）
```

- `<id>` 与 registry 的 id 一致；迁入后把对应 yaml 的 `canonical` 指向 `works/forge/skills/<id>`，
  `maturity` 改为 `consolidated`。
- 已在 `.claude/skills/` 的 image-generation / unity-asset-mining 迁入时保留原路径符号链接，
  避免各项目引用断掉（ADR-0013「后续动作」）。
- 顺序：P1 shots / cutout / comfy；P2 blender / char3d / sprite / audio / mining。
