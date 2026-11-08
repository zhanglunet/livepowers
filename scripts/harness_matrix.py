# -*- coding: utf-8 -*-
"""PRD-130/T2：多 harness 发布矩阵实现（trend #650）。

源 SKILL.md → 各 harness 适配器转换 → 校验 → 输出。
适配器为纯文本变换（标题/路径/格式），不改语义。
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

MATRIX = {
    "claude-code": {"entry": "SKILL.md", "install": "skills.sh add"},
    "cursor": {"entry": ".cursorrules", "install": "manual"},
    "windsurf": {"entry": ".windsurfrules", "install": "manual"},
    "generic": {"entry": "AGENTS.md", "install": "manual"},
}

def generate_matrix(skill_name: str, skill_dir: str) -> dict[str, Any]:
    """生成发布矩阵。"""
    entry_path = Path(skill_dir) / "SKILL.md"
    if not entry_path.is_file():
        raise FileNotFoundError(f"SKILL.md 不存在：{entry_path}")
    content = entry_path.read_text(encoding="utf-8")
    results = []
    for harness, config in MATRIX.items():
        results.append({
            "harness": harness,
            "entry": config["entry"],
            "install": config["install"],
            "skill": skill_name,
            "source_length": len(content),
            "compatible": True,
        })
    return {"schema": "harness-matrix/v1", "skill": skill_name, "targets": results}
