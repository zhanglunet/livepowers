#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-228/T4（trend issue #1143）：配置校验与默认值——坏配置可检出并回退。

按 T1 设计（docs/plans/2026-10-26-portable-config-design.md）实现，叠加 T2
tool_config_gen.py（SOURCE_CONFIG 四字段）：

  - validate_source(source)：字段级校验——skills_root 非空字符串、model 非空
    字符串、allowed_commands 字符串数组（逐项非空）、telemetry_enabled 布尔；
    返回 {ok, errors: [...]}；
  - sanitize_source(source)：坏配置回退默认——逐字段校验，坏字段回退默认值
    并记入 corrections（「检出并回退」：不崩溃、不静默，回退有据可查）；
  - DEFAULT_SOURCE：内置默认（skills_root="~/.livepowers/skills"、
    model="default"、空命令清单、telemetry=False）；
  - validate_generated(config_dir)：生成产物完整性——四工具配置文件存在且
    JSON 可解析（rules.md/carto.toml 等文本形态查非空）。

零网络；确定性；全部值占位。
测试：tests/test_prd228_t4_validation.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_SOURCE = {
    "skills_root": "~/.livepowers/skills",
    "model": "default",
    "allowed_commands": [],
    "telemetry_enabled": False,
}


def validate_source(source: Any) -> dict[str, Any]:
    """字段级校验，返回 {ok, errors}（ok=True 时 errors 为空）。"""
    errors: list[str] = []
    if not isinstance(source, dict):
        return {"ok": False, "errors": [f"配置须为对象，收到 {type(source).__name__}"]}
    if not isinstance(source.get("skills_root"), str) or not source["skills_root"].strip():
        errors.append("skills_root 须为非空字符串")
    if not isinstance(source.get("model"), str) or not source["model"].strip():
        errors.append("model 须为非空字符串")
    commands = source.get("allowed_commands")
    if not isinstance(commands, list) or not all(
            isinstance(c, str) and c.strip() for c in commands):
        errors.append("allowed_commands 须为非空字符串数组")
    if not isinstance(source.get("telemetry_enabled"), bool):
        errors.append("telemetry_enabled 须为布尔")
    return {"ok": not errors, "errors": errors}


def sanitize_source(source: Any) -> dict[str, Any]:
    """坏配置回退默认：逐字段校验，坏字段回退 DEFAULT_SOURCE 并记 corrections。

    返回 {source（回退后）, corrections: [{field, fallback, original}]}。
    """
    if not isinstance(source, dict):
        source = {}
    corrected = dict(DEFAULT_SOURCE)
    corrections: list[dict] = []
    skills_root = source.get("skills_root")
    if isinstance(skills_root, str) and skills_root.strip():
        corrected["skills_root"] = skills_root
    else:
        corrections.append({"field": "skills_root", "fallback": DEFAULT_SOURCE["skills_root"],
                            "original": skills_root})
    model = source.get("model")
    if isinstance(model, str) and model.strip():
        corrected["model"] = model
    else:
        corrections.append({"field": "model", "fallback": DEFAULT_SOURCE["model"],
                            "original": model})
    commands = source.get("allowed_commands")
    if isinstance(commands, list) and all(isinstance(c, str) and c.strip() for c in commands):
        corrected["allowed_commands"] = list(commands)
    else:
        corrections.append({"field": "allowed_commands",
                            "fallback": DEFAULT_SOURCE["allowed_commands"],
                            "original": commands})
    telemetry = source.get("telemetry_enabled")
    if isinstance(telemetry, bool):
        corrected["telemetry_enabled"] = telemetry
    else:
        corrections.append({"field": "telemetry_enabled",
                            "fallback": DEFAULT_SOURCE["telemetry_enabled"],
                            "original": telemetry})
    return {"source": corrected, "corrections": corrections}


def validate_generated(config_dir: str | Path) -> dict[str, Any]:
    """生成产物完整性：四工具配置文件存在且内容非空（JSON 工具须可解析）。"""
    root = Path(config_dir)
    expected = {
        "claude": ("settings.json", True),
        "cursor": ("rules.md", False),
        "codex": ("config.toml", False),
        "pi": ("agent.toml", False),
    }
    checks: list[dict] = []
    for tool, (filename, is_json) in expected.items():
        path = root / tool / filename
        if not path.is_file():
            checks.append({"tool": tool, "file": filename, "ok": False,
                           "reason": "配置文件缺失"})
            continue
        content = path.read_text(encoding="utf-8")
        if not content.strip():
            checks.append({"tool": tool, "file": filename, "ok": False,
                           "reason": "配置文件为空"})
            continue
        if is_json:
            try:
                json.loads(content)
            except json.JSONDecodeError as exc:
                checks.append({"tool": tool, "file": filename, "ok": False,
                               "reason": f"JSON 不可解析：{exc}"})
                continue
        checks.append({"tool": tool, "file": filename, "ok": True})
    return {
        "schema": "generated-config-check/v1",
        "config_dir": str(root),
        "checks": checks,
        "ok": all(c["ok"] for c in checks),
    }
