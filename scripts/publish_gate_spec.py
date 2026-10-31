#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-199/T3（trend #997）：agentskills 规范校验进发布门。

按 PRD-199/T1 设计扩展 T2 的规范校验器（agentskills_align.validate_all，PR #126 已合并）：
发布门——**不合规 skill 无法发布**：

  gate(skills_root)：全部 SKILL.md 过四项规范校验（license / when_not_to_use /
    output / compatibility），任一缺口 → ok=False 且逐条列出；
  main：exit 0 = 可发布；exit 1 = 存在不合规 skill（发布清单机器化，与
    check_release_readiness.py「未通过不可进发行清单」同口径）；
  gate_report_for(manifest, skills_root)：对 manifest 中状态为 published 的角色包
    成员 skill 逐个校验（与发行清单联动）。

零写入、零网络；示例全虚构。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from agentskills_align import SKILLS_ROOT, gaps_for, parse_frontmatter, validate_all  # noqa: E402


def gate(skills_root: Path = SKILLS_ROOT) -> dict[str, Any]:
    """发布门：任一 skill 有规范缺口 → ok=False（不合规 skill 无法发布）。"""
    errors = validate_all(Path(skills_root))
    return {"ok": not errors, "errors": errors, "checked_root": str(skills_root)}


def gate_report_for(manifest_path: Path, skills_root: Path = SKILLS_ROOT) -> dict[str, Any]:
    """对 manifest 中 published 角色包的成员 skill 逐个过门（联动发行清单）。"""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    results = []
    for pack in manifest.get("packs", []):
        if pack.get("status") != "published":
            continue
        for skill_name in pack.get("skills", []):
            skill_md = Path(skills_root) / skill_name / "SKILL.md"
            if not skill_md.exists():
                results.append({"pack": pack.get("name"), "skill": skill_name,
                                "ok": False, "gaps": ["SKILL.md 缺失"]})
                continue
            meta, _, _ = parse_frontmatter(skill_md)
            gaps = gaps_for(skill_name, meta)
            results.append({"pack": pack.get("name"), "skill": skill_name,
                            "ok": not gaps, "gaps": gaps})
    return {"ok": all(r["ok"] for r in results), "results": results}


def main(argv: list[str]) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="agentskills 规范发布门（不合规不可发布）")
    parser.add_argument("--skills-root", default=str(SKILLS_ROOT))
    parser.add_argument("--manifest", default=None, help="可选：联动发行清单逐成员校验")
    args = parser.parse_args(argv)
    report = gate(Path(args.skills_root))
    if args.manifest:
        mreport = gate_report_for(Path(args.manifest), Path(args.skills_root))
        report["errors"] += [f"{r['pack']}/{r['skill']}: {g}"
                             for r in mreport["results"] if not r["ok"] for g in r["gaps"]]
        report["ok"] = report["ok"] and mreport["ok"]
    if report["ok"]:
        print("发布门通过：全部 skill 规范合规")
        return 0
    print("发布门拒绝：存在不合规 skill（不合规无法发布）", file=sys.stderr)
    for e in report["errors"]:
        print(f"  - {e}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
