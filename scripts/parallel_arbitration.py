#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-112/T3：并行专家汇总仲裁规则（trend #561）。

按 T1 契约（examples/parallel-experts/page-review.yaml）实现 writer 汇总三规则：
  1. always > conditional：when=always 的专家产出恒采纳；when={condition} 的
     仅在条件为真时采纳，否则产出标 skipped（不算冲突）；
  2. 模块唯一性：同一 module 若被多个**被采纳**专家产出，取 id 字典序首个，
     其余记入 suppressed[]（可审计，不静默丢）；
  3. 空产出合并：零专家产出 → writer 收到空汇总并显式标注 no_input（不伪造结论）。

红线：仲裁只做**选取**不做**改写**——专家产出原样传递或进 suppressed，不合并措辞；
writer 不看专家的推理过程（只看结构化产出）；本模块零网络零子进程。
"""
from __future__ import annotations

from typing import Any

#: 封闭错误码词表
ERROR_CODES = (
    "ARBITRATION_EMPTY_INPUT",
    "ARBITRATION_MODULE_OVERLAP",
    "ARBITRATION_INVALID_EXPERT",
)


class ArbitrationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        if code not in ERROR_CODES:
            raise ValueError(f"未登记错误码：{code}（词表={ERROR_CODES}）")
        super().__init__(f"{code}: {message}")
        self.code = code


def arbitrate(experts: list[dict[str, Any]], outputs: dict[str, list[dict[str, Any]]],
              conditions: dict[str, bool] | None = None) -> dict[str, Any]:
    """三规则仲裁。

    experts：模板 experts[]（含 id/when/modules）；
    outputs：{expert_id: [{module, ...}]}（每个专家的结构化产出）；
    conditions：{expert_id: bool}（when={condition} 的真值；缺省 False）。

    返回 {"adopted": [...], "suppressed": [...], "no_input": bool}。
    """
    conditions = conditions or {}
    adopted: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    seen_modules: dict[str, str] = {}  # module_id → 首个采纳的 expert_id

    for expert in experts:
        eid = expert.get("id") or ""
        when = expert.get("when", "always")
        if when != "always":
            if not conditions.get(eid, False):
                continue  # conditional 且条件为假 → skipped，不算冲突
        prods = outputs.get(eid) or []
        for prod in prods:
            mid = str(prod.get("module") or "")
            if not mid:
                continue
            if mid in seen_modules:
                suppressed.append({"module": mid, "expert_id": eid,
                                   "winner": seen_modules[mid]})
            else:
                seen_modules[mid] = eid
                adopted.append({**prod, "expert_id": eid})

    return {"adopted": adopted, "suppressed": suppressed,
            "no_input": len(adopted) == 0}


def validate_expert_list(experts: list[dict[str, Any]]) -> list[str]:
    """模板 experts[] 校验：id 唯一、when 合法、modules 非空。"""
    errors: list[str] = []
    ids: list[str] = []
    for e in experts:
        eid = e.get("id") or ""
        if not eid:
            errors.append("expert 缺 id")
        if eid in ids:
            errors.append(f"expert id 重复：{eid}")
        ids.append(eid)
        when = e.get("when", "always")
        if when != "always" and not str(when).startswith("{"):
            errors.append(f"{eid}：when 须为 always 或 {{condition}}，实得 {when!r}")
        if not (e.get("modules") or []):
            errors.append(f"{eid}：modules 不得为空")
    return errors
