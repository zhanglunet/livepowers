#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-255/T3（trend #1277）：收录流程接入——HIGH 不收录的单一入口。

按 PRD-255/T1 设计（docs/plans/2026-10-28-prd-255-market-gate.md）T3 范围：
  admission_flow(skill_dir, declared, verified)：
    调 T2 scan_skill 产 market-gate-report-v1 报告 →
    decision=blocked（HIGH/CRITICAL）→ 拒绝收录，返回 {admitted: False, report, checklist}；
    decision=admitted → 收录，返回 {admitted: True, report, checklist}。
  checklist 为 PRD-094 收录清单 gate_* 六字段（checklist_mapping）。

红线（T1 §4）：HIGH+ 不收录（硬闸门）；被拒技能报告仍在案（可复核/修正重扫）；
拒绝态清单不得呈现 admitted；收录清单消费方只看 admission_flow 这一个入口。
零网络（license 实测值由调用方传入）；示例全虚构。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from market_gate_scan import checklist_mapping, scan_skill


def admission_flow(skill_dir: Path, declared: str | None, verified: str | None, *,
                   declared_name: str | None = None,
                   declared_version: str | None = None) -> dict[str, Any]:
    """收录流程唯一入口：扫描 → 闸门判定 → 清单字段。

    declared/verified：收录申请单声明 license 与上游实测 license（License API 结果，
    调用方传入）。返回：
      { "admitted": bool, "report": market-gate-report-v1, "checklist": gate_* 六字段 }
    admitted=False 时报告仍随返回在案（进待复核清单，供白名单/修正重扫），
    checklist.gate_decision 恒为 "blocked"——拒绝态绝不产生 admitted 清单。
    """
    report = scan_skill(skill_dir, declared_license=declared,
                        verified_license=verified,
                        declared_name=declared_name,
                        declared_version=declared_version)
    checklist = checklist_mapping(report)
    admitted = report["decision"] == "admitted"
    return {"admitted": admitted, "report": report, "checklist": checklist}
