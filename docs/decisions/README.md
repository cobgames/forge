# forge 项目级 ADR

按 [ADR-0003](../../../../docs/kb/decisions/0003-works-layer-for-self-built-projects.md) 的两层 ADR 机制：

- **workspace 级**（`docs/kb/decisions/`）：跨项目 / 基础设施决策。forge 的方向与分期在
  [ADR-0013](../../../../docs/kb/decisions/0013-production-platform-direction.md)。
- **项目级**（本目录）：forge 内部技术选择，不上升到 workspace。例：catalog 用 SQLite 还是
  JSONL、registry 字段增删、某条管线合并时选哪份实现做基准。

命名：`NNNN-kebab-title.md`，从 `0001` 起；frontmatter 含 `adr` / `title` / `status` / `date`。
目前为空。
