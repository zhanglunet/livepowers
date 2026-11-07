#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-228/T3（trend #1142）：配置同步检查——与 PRD-200 清单衔接，检出漂移。

按 T1 设计（gentle-ai 形态借鉴声明同 T2）实现：
  - config_sync_check(source, config_dir)：把 T2 generate_tool_configs 的**期望输出**
    （内存重渲染，幂等）与磁盘上已分发的四工具配置逐一比对——
    status 三态沿用 PRD-200 sync-check-v1 口径（missing / content_mismatch / match），
    content_mismatch 附 note（首个差异行的字段名提示，人工可读）；
  - 与 PRD-200 清单衔接（可选）：传入 expected_skills_dir + skills_roots 时，
    复用 scripts/sync_check.py 的装机口径把技能漂移实例并入同一清单
    （同 schema 族、同 status 词表），一次检查同时覆盖「配置漂移」与「技能漂移」；
  - 漂移即提示：summary 汇总 + prompts[]（人工可执行提示：用
    tool_config_gen.generate_tool_configs 重新分发；技能漂移指向 PRD-200 的
    sync_remediate 补救）。

零网络；无墙钟（同输入必同输出）；路径全部由调用方注入。
测试：tests/test_prd228_t3_sync_check.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tool_config_gen import ConfigGenError, TARGET_TOOLS, _FILENAMES, _render

#: 技能装机现状口径（PRD-200/T2，复用其 schema 与 status 词表）
from sync_check import sync_check  # noqa: E402


def _canonical(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def source_fingerprint(source: dict) -> str:
    """源配置指纹（规范化 JSON sha256 前 16 位；源变更即全量漂移的可判据）。"""
    return hashlib.sha256(_canonical(source).encode("utf-8")).hexdigest()[:16]


def _first_diff_line(expected: str, actual: str) -> str:
    """首个差异行的简述（note 用；identical 返回空串）。"""
    exp_lines = expected.splitlines()
    act_lines = actual.splitlines()
    for i in range(max(len(exp_lines), len(act_lines))):
        e = exp_lines[i] if i < len(exp_lines) else "<缺行>"
        a = act_lines[i] if i < len(act_lines) else "<多行>"
        if e != a:
            return f"第 {i + 1} 行不一致：期望 {e.strip()!r}，实际 {a.strip()!r}"
    return ""


def config_sync_check(source: dict, config_dir: str | Path,
                      expected_skills_dir: str | Path | None = None,
                      skills_roots: dict[str, str] | None = None) -> dict:
    """源配置 vs 已分发配置的漂移检查（+ 可选技能装机衔接清单）。

    返回 config-sync-check/v1：instances（配置 + 可选技能两段，status 词表与
    PRD-200 sync-check-v1 一致）、summary、prompts（有漂移才非空）。
    """
    for key in ("skills_root", "model"):
        if not source.get(key):
            raise ConfigGenError(f"源配置缺必填字段 {key!r}")
    root = Path(config_dir)
    instances: list[dict] = []
    for tool in TARGET_TOOLS:
        expected = _render(tool, source)
        target = root / tool / _FILENAMES[tool]
        if not target.is_file():
            instances.append({
                "tool": tool, "file": str(target), "status": "missing",
                "note": "配置文件不存在（未分发或被删除）",
            })
            continue
        actual = target.read_text(encoding="utf-8")
        if actual == expected:
            instances.append({
                "tool": tool, "file": str(target), "status": "match",
                "fp_match": "match",
            })
        else:
            instances.append({
                "tool": tool, "file": str(target), "status": "content_mismatch",
                "fp_match": "content_mismatch",
                "note": _first_diff_line(expected, actual)
                or "内容不一致（行尾/编码差异）",
            })
    if expected_skills_dir is not None:
        # PRD-200 清单衔接：技能装机现状并入同一报告（同 schema 族）
        skills_report = sync_check(expected_skills_dir, skills_roots)
        for instance in skills_report.get("instances", []):
            instances.append({"scope": "skills", **instance})

    drift = [i for i in instances if i["status"] in ("content_mismatch", "missing")
             or i.get("fp_match") == "content_mismatch"]
    match = [i for i in instances if i not in drift]
    prompts: list[str] = []
    config_drift = [i for i in drift if i.get("scope") != "skills"]
    if config_drift:
        prompts.append(
            "配置漂移检出（%d 项）：%s——用 tool_config_gen.generate_tool_configs(source, out_dir) "
            "重新分发（生成幂等，二次生成零 diff）；勿手改生成文件，改源配置后重发。"
            % (len(config_drift), "、".join(i["tool"] for i in config_drift)))
    skills_drift = [i for i in drift if i.get("scope") == "skills"]
    if skills_drift:
        prompts.append(
            "技能装机漂移检出（%d 项）：按 PRD-200 清单处理——sync_remediate 给出逐项补救建议。"
            % len(skills_drift))
    return {
        "schema": "config-sync-check/v1",
        "source_fingerprint": source_fingerprint(source),
        "config_dir": str(root),
        "instances": instances,
        "summary": {
            "total": len(instances),
            "match": len(match),
            "drift": len(drift),
            "config_drift": len(config_drift),
            "skills_drift": len(skills_drift),
        },
        "prompts": prompts,
    }
