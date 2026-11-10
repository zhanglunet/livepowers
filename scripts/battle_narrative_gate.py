# -*- coding: utf-8 -*-
"""PRD-321/T3：实战验证叙事生成器闸门（trend #650 区段）。

T2（battle_narrative.generate_narrative 产物）在对外发布面前必过本闸门：
字段完整（skill/scenario 非空 + evidence_refs 必须有——实战验证叙事无证据
不发布）+ install_command 形态钉值 + verification 指向测试面。
MATCH 唯一放行；NARRATIVE_GATE_REFUSED 逐条点名，零静默。
"""
from __future__ import annotations
from typing import Any

GATE_ALLOWED = "MATCH"
REFUSED = "NARRATIVE_GATE_REFUSED"


def verify_narrative(n: Any) -> dict[str, Any]:
    if not isinstance(n, dict):
        return {"status": "REFUSED", "evidence": ["叙事不是 JSON 对象"]}
    evidence: list[str] = []
    skill = str(n.get("skill", "")).strip()
    if not skill:
        evidence.append("skill 为空")
    if not str(n.get("scenario", "")).strip():
        evidence.append("scenario 为空")
    refs = n.get("evidence_refs")
    if not isinstance(refs, list) or not refs:
        evidence.append("evidence_refs 缺失或为空——实战验证叙事无证据不发布")
    expected = f"npx skills add zhanglunet/livepowers/{skill}"
    if str(n.get("install_command", "")) != expected:
        evidence.append(f"install_command 形态不符：{n.get('install_command')!r}（应为 {expected!r}）")
    verification = str(n.get("verification", ""))
    if "tests/" not in verification:
        evidence.append("verification 未指向测试面（tests/）——实战验证口径缺失")
    if evidence:
        return {"status": "REFUSED", "evidence": evidence}
    return {"status": GATE_ALLOWED, "skill": skill}


def narrative_gate(n: Any) -> dict[str, Any]:
    verdict = verify_narrative(n)
    if verdict["status"] == GATE_ALLOWED:
        return {"allow": True, "code": None, "status": GATE_ALLOWED, "skill": verdict["skill"]}
    return {"allow": False, "code": REFUSED, "status": verdict["status"],
            "evidence": verdict["evidence"]}
