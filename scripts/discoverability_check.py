#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-199/T4（trend #998）：agentskills 规范对齐——跨工具可发现性验证。

按 PRD-199/T1 设计扩展 T2（agentskills_align.py）/T3（publish_gate_spec.py）：
发布装上后还要「各工具发现得了、触发得起」：

  verify_discoverability(skills_root, tool_roots, invoke_fn, *, utterance=None)：
    对 Claude/Cursor/Codex/Pi 逐工具逐 skill 验证——
      ① 可发现：工具目录下 SKILL.md 存在，frontmatter name 与目录一致、
         description 含触发关键词（T2 规范字段的发现口径）；
      ② 可触发：invoke_fn(tool, skill_id, utterance) → 是否唤起该 skill
         （注入式，离线可跑；真机实测归 T5）；
    汇总 {tool: {discoverable, triggered, reasons}}——验收口径「四工具均可发现
    并触发」= 全部工具两项皆真。

零写入、零网络；示例全虚构。测试：tests/test_prd199_t4_discoverability.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).parent))

from agentskills_align import parse_frontmatter  # noqa: E402

DEFAULT_UTTERANCE = "帮我按 {skill} 的说明来一份示例输出"


def _tool_skills(tool_root: str | Path) -> dict[str, dict[str, Any]]:
    """工具目录下已装 skill 的 frontmatter（缺 SKILL.md 的条目记缺失）。"""
    out: dict[str, dict[str, Any]] = {}
    root = Path(tool_root)
    if not root.exists():
        return out
    for d in sorted(root.iterdir()):
        md = d / "SKILL.md"
        if d.is_dir() and md.exists():
            meta, _, _ = parse_frontmatter(md)
            out[d.name] = meta
        elif d.is_dir():
            out[d.name] = None  # 有目录无 SKILL.md = 未正确安装（同缺失口径）
    return out


def verify_discoverability(skills_root: str | Path,
                           tool_roots: dict[str, str | Path],
                           invoke_fn: Callable[[str, str, str], bool], *,
                           utterance: str | None = None) -> dict[str, Any]:
    """逐工具逐 skill：① 可发现（元数据齐+触发词在） ② 可触发（注入式唤起）。"""
    src = Path(skills_root)
    report: dict[str, Any] = {}
    for skill_dir in sorted(src.glob("*/SKILL.md")):
        skill_id = skill_dir.parent.name
        meta, _, _ = parse_frontmatter(skill_dir)
        keywords = [skill_id, (meta.get("name") or skill_id)]
        desc = meta.get("description") or ""
        per_tool = {}
        for tool, root in tool_roots.items():
            installed_meta = _tool_skills(root).get(skill_id)
            reasons: list[str] = []
            discoverable = True
            if installed_meta is None:
                discoverable = False
                reasons.append("SKILL.md 缺失或目录不存在")
            else:
                if installed_meta.get("name") != skill_id:
                    discoverable = False
                    reasons.append("frontmatter name 与目录名不一致")
                if not desc or not any(k in desc for k in keywords):
                    discoverable = False
                    reasons.append("description 缺触发关键词")
            triggered = discoverable and bool(invoke_fn(tool, skill_id,
                                                        utterance or
                                                        DEFAULT_UTTERANCE.format(skill=skill_id)))
            if discoverable and not triggered:
                reasons.append("唤起未命中（invoke_fn 返回 False）")
            per_tool[tool] = {"discoverable": discoverable, "triggered": triggered,
                              "reasons": reasons}
        report[skill_id] = {"tools": per_tool,
                            "all_ok": all(t["discoverable"] and t["triggered"]
                                          for t in per_tool.values())}
    return {"schema": "discoverability-report/v1", "skills": report,
            "all_ok": all(s["all_ok"] for s in report.values())}
