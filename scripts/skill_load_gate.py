#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-293/T3（trend issue #1468）：失败报错闸门——引用方 fail-closed 装载。

按 T1 设计（docs/plans/2026-11-04-prd-293-at-skill-ref-design.md）§5/§6 实现，
叠加 T2 skill_ref_resolver（解析器不变，闸门消费其产物）：

  - load_with_references(skill_name, registry)：引用方装载闸——解析 skill 自身
    与其 x-references 声明的全部 @引用；任一 refused（NOT_FOUND/CYCLE/
    SELF_LOOP/CORRUPT）→ **引用方整体不可用**（fail-closed：返回 unusable
    + 逐条失败原因清单，不产出部分可用的半成品，R2）；
    全部 resolved → 返回契约包（skill 自身契约 + 逐引用契约）；
  - x_references_consistency(skill_entry, audit_records)：双载体同源机判
    （§6）——frontmatter x-references 声明集 vs 审计成功解析集逐字段比对，
    漂移即列差异（装载失败显形，不静默）；
  - 错误码封闭：沿用 T2 五码（穷举断言无逃逸）。

零网络；示例全虚构占位。
测试：tests/test_prd293_t3_failclosed.py
"""
from __future__ import annotations

from typing import Any

from skill_ref_resolver import (  # noqa: F401  (ERROR_CODES 供闸门词表封闭断言)
    ERROR_CODES,
    resolve,
)


def load_with_references(skill_name: str, registry: dict[str, Any],
                          *, current_chain: list[str] | None = None
                          ) -> dict[str, Any]:
    """引用方装载闸（§5）：自身 + 全部 x-references 逐一解析。

    current_chain：装载链（防环用，调用方传入已装载栈）。
    返回 {usable: True, skill, contracts: {ref_name: contract}} 或
    {usable: False, failures: [{ref, error_code, detail}]}——fail-closed：
    不产出部分可用的半成品（R2）。
    """
    chain = list(current_chain or [])
    failures: list[dict[str, Any]] = []
    contracts: dict[str, Any] = {}
    self_out = resolve(f"@{skill_name}", registry, from_skill=None)
    if self_out["resolution"]["status"] != "resolved":
        failures.append({"ref": skill_name, "error_code":
                         self_out["resolution"].get("error_code", "REF_NOT_FOUND"),
                         "detail": "自身解析失败"})
        return {"usable": False, "failures": failures}
    contracts[skill_name] = {
        "trigger_conditions": self_out["trigger_conditions"],
        "output_contract": self_out["output_contract"],
    }
    entry = _find_entry(registry, skill_name)
    refs = list((entry or {}).get("x-references") or [])
    for raw in refs:
        target = raw[1:] if raw.startswith("@") else raw
        if target in chain or target == skill_name:
            failures.append({"ref": raw, "error_code": "REF_CYCLE",
                             "detail": f"装载链成环：{chain + [skill_name, target]}"})
            continue
        out = resolve(raw, registry, from_skill=skill_name)
        if out["resolution"]["status"] != "resolved":
            failures.append({"ref": raw,
                             "error_code": out["resolution"].get("error_code",
                                                                 "REF_NOT_FOUND"),
                             "detail": out["resolution"].get("detail", "")})
            continue
        contracts[out["skill"]] = {
            "trigger_conditions": out["trigger_conditions"],
            "output_contract": out["output_contract"],
        }
    if failures:
        return {"usable": False, "failures": failures}     # fail-closed：无半成品
    return {"usable": True, "skill": skill_name, "contracts": contracts}


def x_references_consistency(skill_entry: dict[str, Any],
                             audit_records: list[dict[str, Any]]) -> dict[str, Any]:
    """双载体同源机判（§6）：frontmatter 声明集 vs 审计成功解析集逐字段比对。"""
    declared = {(r[1:] if r.startswith("@") else r)
                for r in (skill_entry.get("x-references") or [])}
    resolved = {r["to_skill"] for r in audit_records
                if r.get("status") == "resolved"
                and r.get("from_skill") == skill_entry.get("name")}
    return {
        "consistent": declared == resolved,
        "declared_only": sorted(declared - resolved),
        "resolved_only": sorted(resolved - declared),
    }


def _find_entry(registry: dict[str, Any], name: str) -> dict[str, Any] | None:
    for pack in (registry or {}).get("packs", []):
        for skill in pack.get("skills", []):
            if skill.get("name") == name:
                return skill
    return None
