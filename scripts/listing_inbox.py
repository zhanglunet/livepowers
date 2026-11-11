# -*- coding: utf-8 -*-
"""PRD-363/T2（trend issue #1642 的 T2 环节）：上架审批收件箱最小实现。

按 T1 设计（docs/plans/2026-11-11-prd-363-listing-inbox-design.md）
§3.1/§3.2/§4 实现：

  - collect(*, security_reviews=None, dropped_reviews=None, edge_cases=None)：
    三源只读汇聚（R2）——插件安检「需人工复核」项（PRD-247/253/255）、
    生成式 UI dropped 复核（PRD-335 genui_gate 产物）、市场收录边界案例 →
    条目五件套 {item_id, kind, source_ref, report_ref, diff_digest?, reason,
    state} 缺一 INBOX_ITEM_INCOMPLETE 拒绝入箱（R3）；
  - InboxLedger：append-only（R4）——add/approve/reject 人批留痕；重复裁决
    INBOX_DOUBLE_DECIDE、未知 id、携带上架/skillpack 写载荷
    INBOX_AUTO_EXEC_ATTEMPT（R1 零上架零 skillpack 变更——approved 只是
    「人已拍板」记录，上架走既有发布流程）显形拒绝；
  - view(kind)：kind 过滤视图。

kind 词表封闭：security_manual_review / dropped_props_review /
market_edge_case。零网络；示例全虚构占位。
测试：tests/test_prd363_t2_listing_inbox.py
"""
from __future__ import annotations

import copy
from typing import Any

INBOX_SCHEMA = "listing-inbox/v1"
ITEM_KINDS = ("security_manual_review", "dropped_props_review",
              "market_edge_case")
ERROR_CODES = ("INBOX_ITEM_INCOMPLETE", "INBOX_DOUBLE_DECIDE",
               "INBOX_AUTO_EXEC_ATTEMPT")
_EXEC_KEYS = ("action", "publish", "install", "execute", "apply")


class InboxError(ValueError):
    """收件箱违规——显形拒绝。"""


def _item(item_id: str, kind: str, source_ref: str, report_ref: str,
          diff_digest: str | None, reason: str) -> dict[str, Any]:
    return {"item_id": item_id, "kind": kind, "source_ref": source_ref,
            "report_ref": report_ref, "diff_digest": diff_digest,
            "reason": reason, "state": "pending",
            "decided_by": None, "decided_at": None, "reject_reason": None}


def collect(*, security_reviews: list[dict[str, Any]] | None = None,
            dropped_reviews: list[dict[str, Any]] | None = None,
            edge_cases: list[dict[str, Any]] | None = None,
            at: str = "") -> list[dict[str, Any]]:
    """三源只读汇聚（R2）；五件套缺一拒绝入箱并显形。"""
    items: list[dict[str, Any]] = []
    incomplete: list[str] = []
    n = 0

    def _add(kind: str, source_ref: str, report_ref: str,
             diff_digest: str | None, reason: str):
        nonlocal n
        n += 1
        it = _item(f"item-{n:03d}", kind, source_ref, report_ref,
                   diff_digest, reason)
        missing = [k for k in ("item_id", "kind", "source_ref", "report_ref",
                               "reason") if not it.get(k)]
        if missing or kind not in ITEM_KINDS:
            incomplete.append(f"{kind or '(空 kind)'} 缺 {missing or 'kind 非法'}")
            return
        items.append(it)

    for s in security_reviews or []:
        _add("security_manual_review",
             str(s.get("source_ref") or "security-scan"),
             str(s.get("report_ref") or ""),
             s.get("diff_digest"),
             str(s.get("reason") or "安检需人工复核（占位）"))
    for d in dropped_reviews or []:
        _add("dropped_props_review",
             f"genui-product/v1#dropped[{d.get('index', 0)}]",
             str(d.get("report_ref") or "genui-product/v1（占位）"),
             d.get("diff_digest"),
             f"白名单外属性 {d.get('prop')} 丢弃待复核（占位）")
    for e in edge_cases or []:
        _add("market_edge_case", str(e.get("source_ref") or "market-review"),
             str(e.get("report_ref") or ""),
             e.get("diff_digest"),
             str(e.get("reason") or "市场收录边界案例（占位）"))
    if incomplete:
        raise InboxError(f"INBOX_ITEM_INCOMPLETE：{'；'.join(incomplete)}")
    return items


class InboxLedger:
    """收件箱账本（R4）：append-only；approve/reject 只改状态零上架（R1）。"""

    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}
        self._events: list[dict[str, Any]] = []

    def add(self, items: list[dict[str, Any]]) -> list[str]:
        added = []
        for it in items:
            if it["item_id"] in self._items:
                raise InboxError(f"INBOX_DOUBLE_DECIDE：{it['item_id']} 已在箱")
            self._items[it["item_id"]] = copy.deepcopy(it)
            self._events.append({"op": "add", "item_id": it["item_id"]})
            added.append(it["item_id"])
        return added

    def _decide(self, item_id: str, state: str, *, by: str, at: str,
                reason: str = "",
                payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if payload and any(k in payload for k in _EXEC_KEYS):
            raise InboxError("INBOX_AUTO_EXEC_ATTEMPT：裁决携带上架/skillpack 写"
                             "载荷——收件箱零自动执行（R1），上架走既有发布流程")
        it = self._items.get(item_id)
        if not it:
            raise InboxError(f"未知 item_id：{item_id!r}")
        if it["state"] != "pending":
            raise InboxError(f"INBOX_DOUBLE_DECIDE：{item_id} 已裁决"
                             f"（{it['state']}）——重复裁决显形拒绝")
        it["state"] = state
        it["decided_by"] = by
        it["decided_at"] = at
        if reason:
            it["reject_reason"] = reason
        self._events.append({"op": state.lower(), "item_id": item_id,
                             "by": by, "at": at})
        return dict(it)

    def approve(self, item_id: str, *, by: str, at: str,
                payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._decide(item_id, "approved", by=by, at=at,
                            payload=payload)

    def reject(self, item_id: str, *, by: str, at: str, reason: str = "",
               payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._decide(item_id, "rejected", by=by, at=at, reason=reason,
                            payload=payload)

    def view(self, kind: str | None = None) -> list[dict[str, Any]]:
        return [copy.deepcopy(it) for it in self._items.values()
                if kind is None or it["kind"] == kind]

    @property
    def events(self) -> list[dict[str, Any]]:
        return [dict(e) for e in self._events]
