# forge/registry — 管线登记

每条生产管线一份 `pipelines/<id>.yaml`，记录：干什么、输入输出、现存所有实现路径、
以哪份为合并基准、可执行门、专属坑单、消费者项目。字段表见 [schema.md](./schema.md)。

P0 的用途是"看见"：一眼看出每条管线在 `works/` 里有几份副本、该以哪份为基准，
不改任何项目代码。

## 成熟度（maturity）

| 值 | 含义 | 升级条件 |
|---|---|---|
| `duplicated` | ≥2 份实现各写各的，没有明显基准 | 指定一份 `baseline_candidate` 且它有可执行门 → `candidate` |
| `candidate` | 有一份可作基准（功能最全 / 有测试或 check） | 在 `works/forge/skills/<id>` 合成单一实现，`canonical` 指过去 → `consolidated` |
| `consolidated` | forge（或等价共享位置）单一实现 | ≥2 个**新**项目实际用 forge 版 → `standard` |
| `standard` | 已成新项目默认做法 | — |

imgen 目前是 `consolidated`（单一实现在 `.claude/skills/image-generation/`，尚未迁入 forge）。

## stage 枚举

`research | 2d-asset | 3d-asset | animation | audio | acceptance | mining | build`

## 新增条目流程

1. 确认是"≥2 个项目各写了一份"的环节；只有一份的不登记（还不是共享问题）。
2. 盘点现存实现：Glob 核对每个路径；路径可用 glob 与 `{a,b}` 花括号；在 gitignore 的
   `_work` 内的在 `notes` 里注明；确实不存在的加 `exists: false`。
3. 选 `baseline_candidate`：功能最全 + 有 check 的那份；判断依据写在行尾注释。
4. 坑写进 `pitfalls`（text / evidence / source），同时追加到 `../docs/pitfalls.md` 总表。
   没有量化证据就写"未量化"，不编数字。
5. 跑校验（workspace 根）：

   ```
   python works/forge/registry/validate.py
   ```

   退出码 0 才算完成；WARN 逐条看是否路径写错。

## 校验规则（validate.py）

- FAIL：缺必填（id / name / stage / maturity / summary / implementations≥1）、枚举不合法、
  id 与文件名不一致、id 非 kebab、pitfall 缺 text/evidence/source、YAML 解析失败
- WARN：`implementations[].path` / `gates[].path` / `baseline_candidate` / `related_kb`
  相对 workspace 根不存在
- INFO：标了 `exists: false` 且确实不存在的实现
