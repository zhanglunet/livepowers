#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-200/T3（trend #1002）：跨工具同步——版本漂移与残留清理建议输出。

按 PRD-200/T1 设计扩展 T2 的 sync_check（PR #127 已合并）：漂移场景给出
**可执行的修复步骤**（逐条带真实路径的命令，可直接照做）：
  remediation_advice(report, roots)：按 instance 状态产出修复建议——
    missing（无根目录）→ 创建目录 + 逐 skill 复制命令；
    missing → cp 复制命令；
    incomplete → 补 SKILL.md 复制命令；
    content_mismatch（版本漂移）→ rm 旧版 + cp 对齐命令（版本对齐建议）；
  scan_residue(roots, expected)：旧版残留检查——工具目录里存在但期望清单
    没有的条目 → rm -rf 清理命令 + 「旧版残留」标注（先给命令、由人执行，
    本脚本零写入）。
零写入、零网络；示例全虚构。
"""
from __future__ import annotations

import os
from pathlib import Path

from sync_check import TOOL_PATHS, scan_expected, sync_check  # noqa: F401


def _exp(user_path: str) -> Path:
    return Path(os.path.expanduser(user_path))


def scan_residue(expected_dir: str | Path, roots: dict[str, str] | None = None) -> list[dict]:
    """旧版残留：工具 skills 根目录下存在、但期望清单没有的条目。"""
    expected = scan_expected(expected_dir)
    roots = roots or TOOL_PATHS
    out = []
    for tool, root in roots.items():
        root_p = _exp(root)
        if not root_p.exists():
            continue
        for child in sorted(root_p.iterdir()):
            if child.is_dir() and child.name not in expected:
                out.append({"tool": tool, "skill": child.name, "path": str(child),
                            "issue": "residue", "note": "旧版残留（期望清单外）"})
    return out


def remediation_advice(report: dict, roots: dict[str, str] | None = None,
                       source_dir: str | Path | None = None) -> list[dict]:
    """漂移场景 → 可执行修复步骤（逐条命令；由人审后执行，本函数零写入）。"""
    roots = roots or TOOL_PATHS
    source = _exp(str(source_dir)) if source_dir else None
    advice = []
    for inst in report.get("instances", []):
        tool, skill, status = inst["tool"], inst["skill"], inst["status"]
        root = _exp(roots[tool])
        dst = root / skill
        steps: list[str] = []
        if status == "missing" and not root.exists():
            steps.append(f"mkdir -p '{root}'")
        if status == "missing":
            if source is not None and (source / skill).is_dir():
                steps.append(f"cp -R '{source / skill}' '{dst}'")
            else:
                steps.append(f"# 从仓库期望目录复制 {skill} 到 {dst}（源目录未提供）")
        elif status == "incomplete":
            if source is not None and (source / skill / "SKILL.md").is_file():
                steps.append(f"mkdir -p '{dst}'")
                steps.append(f"cp '{source / skill / 'SKILL.md'}' '{dst / 'SKILL.md'}'")
            else:
                steps.append(f"# 补齐 {dst / 'SKILL.md'}（源目录未提供，手工核对）")
        elif inst.get("fp_match") == "content_mismatch":
            # 版本漂移：旧版对齐到期望指纹（先删后拷，避免新旧混装）
            if source is not None and (source / skill).is_dir():
                steps.append(f"rm -rf '{dst}'")
                steps.append(f"cp -R '{source / skill}' '{dst}'")
            else:
                steps.append(f"# 版本漂移：将 {dst} 对齐到期望版本（源目录未提供，人工重装）")
        if steps:
            advice.append({"tool": tool, "skill": skill, "issue": status,
                           "steps": steps})
    return advice


def residue_advice(residues: list[dict]) -> list[dict]:
    """残留 → 清理命令（由人审后执行）。"""
    return [{"tool": r["tool"], "skill": r["skill"], "issue": "residue",
             "steps": [f"rm -rf '{r['path']}'  # 旧版残留清理（执行前人工确认）"]}
            for r in residues]


def full_report(expected_dir: str | Path, roots: dict[str, str] | None = None,
                source_dir: str | Path | None = None) -> dict:
    """状态表 + 漂移/残留修复建议一次输出（T3 交付形态）。"""
    report = sync_check(expected_dir, roots)
    residues = scan_residue(expected_dir, roots)
    return {
        **report,
        "residues": residues,
        "remediation": remediation_advice(report, roots, source_dir)
        + residue_advice(residues),
    }
