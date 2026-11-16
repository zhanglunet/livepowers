# -*- coding: utf-8 -*-
"""PRD-446/T3（trend issue #2152 的 T3 环节）：skill 生成监督台监督回路闸门。

按 T1 设计 §4.4 落地：上架审批队列入口的强制检查。闸门不读包版本的
status 位，只从原始记录（decisions 裁决列表 + tickets 发回单列表）重新
推导「这个包版本是否已点头且未失效」（fail-closed，任一存疑即拦下）：

  1. 无裁决记录 → GATE_NO_DECISION（手写 status 位不作数）；
  2. 最新裁决是发回 → GATE_NOT_LATEST_APPROVE（发回后未重审再点头前拒绝）；
  3. 该版本名下有未闭环发回单（待处理/处理中）→ GATE_TICKET_OPEN；
  4. 回炉出新版后旧点头失效：发回单挂了另一条新版本时，旧版本永久
     作废（GATE_SUPERSEDED），点头对新版本无效；
  5. 发回单闭环后，须有严格晚于发回单最后一次流转的重新点头；时间戳
     缺失或打平 → GATE_STALE_APPROVAL。

T2 的 outlet 保留（只看状态位）；生产出口应走本闸门 approve_via_gate()。
零 LLM 零网络零子进程；示例全虚构占位。
测试：tests/test_prd446_t3_skill_supervision_gate.py
"""
from __future__ import annotations

import copy
from typing import Any

GATE_SCHEMA = "skill-supervision-gate/v1"
GATE_REASONS = ("GATE_ALLOWED", "GATE_NO_DECISION", "GATE_NOT_LATEST_APPROVE",
                "GATE_TICKET_OPEN", "GATE_SUPERSEDED", "GATE_STALE_APPROVAL",
                "GATE_UNKNOWN_VERSION")
_TICKET_OPEN = ("待处理", "处理中")


def _verdict(version: str, allowed: bool, reason: str,
             detail: str) -> dict[str, Any]:
    return {"schema": GATE_SCHEMA, "version": version, "allowed": allowed,
            "reason": reason, "detail": detail}


def evaluate(version: str, decisions: list[dict[str, Any]],
             tickets: list[dict[str, Any]]) -> dict[str, Any]:
    """从裁决 + 发回原始记录推导单包版本的放行结论（fail-closed）。"""
    decisions = decisions or []
    tickets = tickets or []
    mine = [t for t in tickets if t.get("target_version") == version]
    rel = [d for d in decisions if d.get("version") == version]
    if not rel:
        return _verdict(version, False, "GATE_NO_DECISION",
                        "无裁决记录——手写 status 位不作数")
    latest = rel[-1]
    if latest.get("verdict") != "点头":
        return _verdict(version, False, "GATE_NOT_LATEST_APPROVE",
                        "最新裁决不是点头——发回后未重审再点头前拒绝")
    open_t = [t for t in mine if t.get("status") in _TICKET_OPEN]
    if open_t:
        return _verdict(version, False, "GATE_TICKET_OPEN",
                        f"名下有 {len(open_t)} 条未闭环发回单")
    returned = [t for t in mine if t.get("status") == "已回炉"
                and t.get("returned_version")
                and t["returned_version"] != version]
    if returned:
        return _verdict(version, False, "GATE_SUPERSEDED",
                        "发回单已回炉出新版本——旧点头对旧版本失效")
    closed_flow = [t for t in mine if t.get("status") == "已关闭"]
    if closed_flow:
        last_flow = max((str(t.get("at", "")) for t in mine), default="")
        if not latest.get("at") or latest["at"] <= last_flow:
            return _verdict(version, False, "GATE_STALE_APPROVAL",
                            "点头时间未严格晚于发回单最后流转——无法证明重新点头")
    return _verdict(version, True, "GATE_ALLOWED", "裁决与发回闭环齐备")


def approve_via_gate(session: Any, packages: list[dict[str, Any]]) -> dict[str, Any]:
    """上架审批队列入口（R1）：逐包过闸，fail-closed。"""
    passed, blocked = [], []
    for p in packages or []:
        v = str(p.get("version"))
        verdict = evaluate(v, getattr(session, "decisions", []),
                           getattr(session, "tickets", []))
        (passed if verdict["allowed"] else blocked).append(
            dict(copy.deepcopy(p), gate=verdict["reason"]))
    return {"schema": GATE_SCHEMA, "passed": passed, "blocked": blocked,
            "blocked_count": len(blocked)}
