# registry 字段表

一份 `pipelines/<id>.yaml` 的字段。路径一律相对 workspace 根（`D:\maxb_workspace\github-project-research`），
git 外的绝对路径允许但须在 `notes` 说明。路径可含 glob（`*` / `**`）与 `{a,b}` 花括号展开。

| 字段 | 必填 | 类型 | 说明 |
|---|---|---|---|
| `id` | 是 | str | kebab-case，等于文件名 |
| `name` | 是 | str | 中文名 |
| `stage` | 是 | enum | `research` / `2d-asset` / `3d-asset` / `animation` / `audio` / `acceptance` / `mining` / `build` |
| `maturity` | 是 | enum | `duplicated` / `candidate` / `consolidated` / `standard`，定义见 README |
| `summary` | 是 | str | 一句话：做什么 + 现存几份 |
| `inputs` | 否 | list[str] | 输入物 |
| `outputs` | 否 | list[str] | 产出物 |
| `gates` | 否 | list[obj] | 可执行门（现存的或应有的） |
| `gates[].name` | 是 | str | 门名 |
| `gates[].path` | 否 | str \| null | 脚本 / 测试路径；还没有就写 `null` 并在 note 说明 |
| `gates[].note` | 否 | str | 门检查什么 |
| `implementations` | 是（≥1） | list[obj] | 现存实现，全部列出 |
| `implementations[].project` | 是 | str | `works/` 下的项目目录名；workspace 级 skill 写 `workspace-skill` |
| `implementations[].path` | 是 | str | 路径（可 glob） |
| `implementations[].notes` | 否 | str | 来源 / 移植关系 / 是否在 gitignore 内 / 与盘点的出入 |
| `implementations[].exists` | 否 | bool | 已知不存在时写 `false`（校验降为 INFO） |
| `canonical` | 否 | str \| null | 收敛后的单一实现，P1 起指向 `works/forge/skills/<id>` |
| `baseline_candidate` | 否 | str \| null | 合并时以哪份为基准 |
| `pitfalls` | 否 | list[obj] | 本管线专属坑 |
| `pitfalls[].text` | 是 | str | 现象 + 规避 |
| `pitfalls[].evidence` | 是 | str | 量化证据；没有写"未量化" |
| `pitfalls[].source` | 是 | str | 出处（auto-memory 条目名 / 文档路径） |
| `related_kb` | 否 | list[str] | 相关 kb / 项目文档路径 |
| `related_skills` | 否 | list[str] | `.claude/skills/` 或 forge skill 名 |
| `consumers` | 否 | list[str] | 用到该管线的项目 |

YAML 注释（`#`）用于记录不适合进字段的盘点事实（如 shots 的"另 8 个项目直调无头 Chrome"）。
