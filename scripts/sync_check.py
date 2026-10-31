#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-200/T2（trend #1001）：跨工具同步检查——一键输出同步状态表最小实现。

按 PRD-200/T1 设计实现 T2 范围：C 组（存在完整）/ V 组（版本指纹）/ 四工具覆盖。
零写入、零网络；路径表可配置。示例全虚构。
"""
import hashlib
import json
import os
from pathlib import Path

TOOL_PATHS = {
    "claude": "~/.claude/skills",
    "cursor": ".cursor/skills",
    "codex": "~/.codex/skills",
    "pi": "~/.pi/skills",
}


def fp(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def scan_expected(skills_dir):
    r = {}
    for d in sorted(Path(skills_dir).iterdir()):
        md = d / "SKILL.md"
        if d.is_dir() and md.exists():
            r[d.name] = hashlib.sha256(md.read_bytes()).hexdigest()[:16]
    return r


def scan_tool(tool, root, expected):
    root = Path(os.path.expanduser(root))
    out = []
    if not root.exists():
        return [{"tool": tool, "skill": s, "status": "missing",
                  "note": "技能根目录不存在"} for s in expected]
    for s in sorted(expected):
        sp = root / s
        md = sp / "SKILL.md"
        if sp.is_dir() and md.exists():
            match = "match" if hashlib.sha256(md.read_bytes()).hexdigest()[:16] == expected[s] else "content_mismatch"
            out.append({"tool": tool, "skill": s, "status": "installed", "fp_match": match})
        elif sp.is_dir():
            out.append({"tool": tool, "skill": s, "status": "incomplete"})
        else:
            out.append({"tool": tool, "skill": s, "status": "missing"})
    return out


def sync_check(expected_dir, roots=None):
    expected = scan_expected(expected_dir)
    roots = roots or TOOL_PATHS
    instances = []
    for tool, root in roots.items():
        instances.extend(scan_tool(tool, root, expected))
    return {"schema": "sync-check-v1", "expected_count": len(expected), "instances": instances}


def status_table(report):
    lines = ["tool    skill               status    fp_match          note"]
    for i in report["instances"]:
        lines.append(f"{i['tool']:<8} {i['skill']:<20} {i['status']:<10} {i.get('fp_match','-'):<18} {i.get('note','')}")
    return "\n".join(lines) + "\n"
