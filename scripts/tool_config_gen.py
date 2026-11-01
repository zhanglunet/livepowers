#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-228/T2（trend #1141）：一份源配置生成各工具配置（Claude/Cursor/Codex/Pi）。

按 T1 设计（gentle-ai 只借鉴「配一次、处处用」形态，不复用代码）实现：
  SOURCE_CONFIG → 四工具配置生成器（Claude Code / Cursor / Codex / Pi）：
    - 源配置声明通用意图（skills_root / model / allowed_commands / 遥测开关）；
    - generate_tool_configs(source, out_dir) → 每工具一份配置文件（目录约定按各
      工具惯例；内容只映射字段，不做超集）；
  - 差异映射：Claude Code 用 settings.json + skills 符链清单；Cursor 用 rules 目录；
    Codex 用 agents.md + config.toml；Pi 用 agent.toml；幂等（二次生成零 diff）。
只写 out_dir（调用方给临时目录）；零网络。

测试：tests/test_prd228_t2_config_gen.py
"""
from __future__ import annotations

import json
from pathlib import Path

TARGET_TOOLS = ("claude", "cursor", "codex", "pi")


class ConfigGenError(ValueError):
    """源配置缺字段或工具名非法。"""


def generate_tool_configs(source: dict, out_dir: str | Path) -> dict[str, str]:
    """源配置 → 四工具配置文件（幂等）。返回 {tool: 生成的文件路径}。"""
    for key in ("skills_root", "model"):
        if not source.get(key):
            raise ConfigGenError(f"源配置缺必填字段 {key!r}")
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    for tool in TARGET_TOOLS:
        content = _render(tool, source)
        target = root / tool
        target.mkdir(parents=True, exist_ok=True)
        file = target / _FILENAMES[tool]
        file.write_text(content, encoding="utf-8")
        written[tool] = str(file)
    return written


_FILENAMES = {
    "claude": "settings.json",
    "cursor": "rules.md",
    "codex": "config.toml",
    "pi": "agent.toml",
}


def _render(tool: str, source: dict) -> str:
    skills_root = source["skills_root"]
    model = source["model"]
    commands = source.get("allowed_commands", [])
    telemetry = source.get("telemetry_enabled", False)
    if tool == "claude":
        return json.dumps({
            "model": model,
            "permissions": {"allow": list(commands)},
            "skillsPath": skills_root,
            "telemetry": {"enabled": telemetry},
        }, ensure_ascii=False, indent=2) + "\n"
    if tool == "cursor":
        lines = [f"# Cursor rules（由源配置生成，勿手改）", "",
                 f"- 技能根目录：`{skills_root}`", f"- 默认模型：`{model}`"]
        for c in commands:
            lines.append(f"- 允许命令：`{c}`")
        return "\n".join(lines) + "\n"
    if tool == "codex":
        toml = [f'model = "{model}"', "", "[skills]", f'root = "{skills_root}"', ""]
        toml.append("allowed_commands = [")
        toml += [f'  "{c}",' for c in commands]
        toml.append("]")
        return "\n".join(toml) + "\n"
    # pi
    toml = [f'model = "{model}"', "", "[telemetry]", f"enabled = {str(telemetry).lower()}"]
    return "\n".join(toml) + "\n"


def source_config(skills_root: str, model: str,
                  allowed_commands: list[str] | None = None,
                  telemetry_enabled: bool = False) -> dict:
    return {"skills_root": skills_root, "model": model,
            "allowed_commands": list(allowed_commands or []),
            "telemetry_enabled": telemetry_enabled}
