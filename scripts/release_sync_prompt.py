#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-200/T4（trend #1003）：跨工具同步——与发布流水线对接（新版发布后提示同步）。

按 PRD-200/T1 设计扩展 T2 sync_check / T3 sync_remediate（PR #127/#129）：
  release_sync_prompt(expected_dir, tool_roots, release, *, source_dir)：
    新版发布后（release = {skill_id, version}），对照各工具装机现状生成同步提示——
      期望清单已更新到新版（发布流水线写入 expected_dir），本机指纹仍旧版
        → 提示「新版已发布，本机为旧版，建议同步」+ 可执行步骤（T3 口径）；
      本机缺失 → 提示安装；本机与新版一致 → 不打扰（不制造提示噪音）；
    提示链路：发布流水线产物（expected_dir 更新）→ 本函数 → 用户提示清单，
      全离线确定性可跑。
零写入、零网络；示例全虚构。测试：tests/test_prd200_t4_release_prompt.py
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sync_check import sync_check  # noqa: F401  （装机现状口径与 T2 一致）
from sync_remediate import remediation_advice, scan_residue


def release_sync_prompt(expected_dir: str | Path, tool_roots: dict[str, str],
                        release: dict[str, Any], *,
                        source_dir: str | Path | None = None) -> dict[str, Any]:
    """新版发布后的同步提示清单（提示链路跑通；由人决定是否执行）。"""
    skill_id = release.get("skill_id")
    version = release.get("version")
    if not skill_id or not version:
        raise ValueError("release 须含 skill_id 与 version")
    report = sync_check(expected_dir, tool_roots)
    residues = scan_residue(expected_dir, tool_roots)
    prompts = []
    for inst in report["instances"]:
        if inst["skill"] != skill_id:
            continue
        tool = inst["tool"]
        base = {"tool": tool, "skill": skill_id, "release_version": version}
        if inst["status"] == "missing" or inst.get("fp_match") == "content_mismatch":
            steps = remediation_advice({"instances": [inst]}, tool_roots, source_dir)
            prompts.append({**base, "status": inst["status"],
                            "fp_match": inst.get("fp_match", ""),
                            "message": f"新版 {version} 已发布，本机为旧版或缺失，建议同步",
                            "steps": steps[0]["steps"] if steps else []})
        elif inst["status"] == "incomplete":
            steps = remediation_advice({"instances": [inst]}, tool_roots, source_dir)
            prompts.append({**base, "status": "incomplete", "fp_match": "",
                            "message": f"新版 {version} 已发布，本机安装不完整，建议补齐",
                            "steps": steps[0]["steps"] if steps else []})
        # installed + fp_match=match → 已是新版，不打扰（不制造提示噪音）
    return {"schema": "release-sync-prompt/v1", "release": release,
            "prompts": prompts,
            "residues": [r for r in residues if r["skill"] == skill_id],
            "policy": "提示由人决定是否执行；本函数零写入（命令不自动跑）"}
