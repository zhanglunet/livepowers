# -*- coding: utf-8 -*-
"""PRD-321/T2：实战验证叙事生成器（trend #650）。"""
from __future__ import annotations
from typing import Any

def generate_narrative(skill_name: str, scenario: str, evidence: list[str]) -> dict[str, Any]:
    """生成实战叙事：场景+证据+安装命令。"""
    return {
        "skill": skill_name,
        "scenario": scenario,
        "evidence_refs": evidence,
        "install_command": f"npx skills add zhanglunet/livepowers/{skill_name}",
        "verification": f"参见 tests/ 中 {skill_name} 相关测试",
    }
