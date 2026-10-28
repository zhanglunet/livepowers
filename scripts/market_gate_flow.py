#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-255/T3 接入 + T4 白名单（trend #1277/#1278）：收录流程单一入口。

按 PRD-255/T1 设计（docs/plans/2026-10-28-prd-255-market-gate.md）T3/T4 范围：
  admission_flow(skill_dir, declared, verified, *, whitelist=None)：
    调 T2 scan_skill 产 market-gate-report-v1 报告 →
    decision=blocked（HIGH/CRITICAL）→ 拒绝收录，返回 {admitted: False, report, checklist}；
    decision=admitted → 收录，返回 {admitted: True, report, checklist}。
    T4 白名单（whitelist=scripts/market_whitelist.py 的 WhitelistManager）：
    blocked 报告有 finding 命中未过期条目时，**只放行单条规则**——被命中 finding
    移出计分，其余 finding 照常参与计分与门槛（floor 不稀释），重算仍 HIGH+ 照拦；
    命中在报告 whitelist_applied 与清单 gate_whitelist 留痕，放行永不静默。
  checklist 为 PRD-094 收录清单 gate_* 六字段（checklist_mapping）。

红线（T1 §4）：HIGH+ 不收录（硬闸门，白名单须有理由+复核人签字才可复核放行）；
被拒技能报告仍在案（可复核/修正重扫）；拒绝态清单不得呈现 admitted；
收录清单消费方只看 admission_flow 这一个入口。
零网络（license 实测值由调用方传入）；示例全虚构。
"""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from market_gate_scan import RULES, checklist_mapping, scan_skill


def _apply_whitelist(report: dict[str, Any], whitelist: Any) -> dict[str, Any]:
    """白名单复核放行（T1 §3.3）：只放行命中条目的单条规则，重算计分与门槛。

    返回新报告（不动原报告）；未命中任何条目时原样返回。
    重算仍 blocked 时报告 decision 保持 blocked，但 whitelist_applied 照实留痕。
    """
    skill_name = (report.get("skill") or {}).get("name", "")
    now = datetime.datetime.now().astimezone()
    applied: list[dict[str, str]] = []
    pardoned: set[str] = set()
    for finding in report.get("findings") or []:
        rule_id = finding.get("rule_id", "")
        hit = whitelist.match(rule_id, skill_name, now)
        if hit:
            applied.append({"rule_id": rule_id, "entry_id": hit.get("entry_id", "")})
            pardoned.add(rule_id)
    if not applied:
        return report

    remaining = [f for f in (report.get("findings") or []) if f.get("rule_id") not in pardoned]
    score = max(0, 100 - sum(f.get("deduct", 0) for f in remaining))
    risk = 100 - score
    floor = any(RULES.get(f.get("rule_id"), {}).get("floor") for f in remaining)
    if risk >= 80:
        severity = "CRITICAL"
    elif risk >= 60 or floor:
        severity = "HIGH"
    elif risk >= 30:
        severity = "MEDIUM"
    else:
        severity = "LOW"
    waived = dict(report)
    waived.update({
        "score": score,
        "severity": severity,
        "decision": "blocked" if severity in ("HIGH", "CRITICAL") else "admitted",
        "findings": remaining,
        "whitelist_applied": applied,
    })
    return waived


def admission_flow(skill_dir: Path, declared: str | None, verified: str | None, *,
                   declared_name: str | None = None,
                   declared_version: str | None = None,
                   whitelist: Any | None = None) -> dict[str, Any]:
    """收录流程唯一入口：扫描 → 闸门判定 →（可选白名单复核）→ 清单字段。

    declared/verified：收录申请单声明 license 与上游实测 license（License API 结果，
    调用方传入）。whitelist（T4）：WhitelistManager 实例，blocked 报告按单条规则
    复核放行（理由+复核人签字在白名单条目里，可审计）。返回：
      { "admitted": bool, "report": market-gate-report-v1, "checklist": gate_* 六字段 }
    admitted=False 时报告仍随返回在案（进待复核清单，供白名单/修正重扫），
    checklist.gate_decision 恒为 "blocked"——拒绝态绝不产生 admitted 清单。
    不传 whitelist 行为与 T3 完全一致。
    """
    report = scan_skill(skill_dir, declared_license=declared,
                        verified_license=verified,
                        declared_name=declared_name,
                        declared_version=declared_version)
    if whitelist is not None and report["decision"] == "blocked":
        report = _apply_whitelist(report, whitelist)
    checklist = checklist_mapping(report)
    admitted = report["decision"] == "admitted"
    return {"admitted": admitted, "report": report, "checklist": checklist}
