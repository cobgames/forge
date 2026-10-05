"""校验 works/forge/registry/pipelines/*.yaml。

用法（在 workspace 根或任意目录）：
    python works/forge/registry/validate.py

检查：
- 必填字段：id / name / stage / maturity / summary / implementations(>=1)
- 枚举：stage / maturity
- id 与文件名一致（kebab-case）
- implementations[].path 与 gates[].path 相对 workspace 根存在
  （支持 glob 与 {a,b} 花括号展开；不存在只记 WARN，不算 FAIL，
   因为部分路径在 gitignore 的 _work 内，换机器可能不存在）
- 显式标 exists: false 的条目不存在时记 INFO，不重复 WARN

退出码：0 = 无 FAIL；1 = 有 FAIL。
"""
from __future__ import annotations

import glob
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("FAIL: 需要 PyYAML（pip install pyyaml）")
    sys.exit(1)

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]  # works/forge/registry -> workspace 根
PIPELINES = HERE / "pipelines"

STAGES = {"research", "2d-asset", "3d-asset", "animation", "audio",
          "acceptance", "mining", "build"}
MATURITIES = {"duplicated", "candidate", "consolidated", "standard"}
REQUIRED = ["id", "name", "stage", "maturity", "summary", "implementations"]
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def expand_braces(pattern: str) -> list[str]:
    m = re.search(r"\{([^{}]*)\}", pattern)
    if not m:
        return [pattern]
    out: list[str] = []
    for alt in m.group(1).split(","):
        out.extend(expand_braces(pattern[:m.start()] + alt + pattern[m.end():]))
    return out


def path_exists(p: str) -> bool:
    for pat in expand_braces(p):
        full = pat if os.path.isabs(pat) else str(WORKSPACE / pat)
        if any(ch in pat for ch in "*?["):
            if glob.glob(full, recursive=True):
                continue
            return False
        if not os.path.exists(full):
            return False
    return True


def check_file(f: Path, fails: list, warns: list, infos: list) -> None:
    try:
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        fails.append(f"{f.name}: YAML 解析失败: {e}")
        return
    if not isinstance(data, dict):
        fails.append(f"{f.name}: 顶层不是 mapping")
        return
    for k in REQUIRED:
        if data.get(k) in (None, "", []):
            fails.append(f"{f.name}: 缺必填字段 {k}")
    pid = data.get("id")
    if pid is not None:
        if pid != f.stem:
            fails.append(f"{f.name}: id={pid!r} 与文件名不一致")
        if not KEBAB.match(str(pid)):
            fails.append(f"{f.name}: id={pid!r} 不是 kebab-case")
    if data.get("stage") is not None and data["stage"] not in STAGES:
        fails.append(f"{f.name}: stage={data['stage']!r} 不在枚举 {sorted(STAGES)}")
    if data.get("maturity") is not None and data["maturity"] not in MATURITIES:
        fails.append(f"{f.name}: maturity={data['maturity']!r} 不在枚举 {sorted(MATURITIES)}")

    impls = data.get("implementations") or []
    if not isinstance(impls, list):
        fails.append(f"{f.name}: implementations 不是列表")
        impls = []
    for i, it in enumerate(impls):
        if not isinstance(it, dict) or not it.get("project") or not it.get("path"):
            fails.append(f"{f.name}: implementations[{i}] 缺 project 或 path")
            continue
        if not path_exists(it["path"]):
            msg = f"{f.name}: implementations[{i}] ({it['project']}) 路径不存在: {it['path']}"
            (infos if it.get("exists") is False else warns).append(msg)

    for i, g in enumerate(data.get("gates") or []):
        if not isinstance(g, dict) or not g.get("name"):
            fails.append(f"{f.name}: gates[{i}] 缺 name")
            continue
        if g.get("path") and not path_exists(g["path"]):
            warns.append(f"{f.name}: gates[{i}] ({g['name']}) 路径不存在: {g['path']}")

    bc = data.get("baseline_candidate")
    if bc and not path_exists(bc):
        warns.append(f"{f.name}: baseline_candidate 路径不存在: {bc}")

    for i, p in enumerate(data.get("pitfalls") or []):
        if not isinstance(p, dict) or not all(p.get(k) for k in ("text", "evidence", "source")):
            fails.append(f"{f.name}: pitfalls[{i}] 需含 text / evidence / source")

    for kb in data.get("related_kb") or []:
        if not path_exists(kb):
            warns.append(f"{f.name}: related_kb 路径不存在: {kb}")


def main() -> int:
    files = sorted(PIPELINES.glob("*.yaml"))
    if not files:
        print(f"FAIL: {PIPELINES} 下没有 yaml")
        return 1
    fails: list[str] = []
    warns: list[str] = []
    infos: list[str] = []
    for f in files:
        check_file(f, fails, warns, infos)
    for m in infos:
        print("INFO", m)
    for m in warns:
        print("WARN", m)
    for m in fails:
        print("FAIL", m)
    print(f"\n{len(files)} 条管线；FAIL {len(fails)}；WARN {len(warns)}；INFO {len(infos)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
