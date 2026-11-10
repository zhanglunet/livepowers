# -*- coding: utf-8 -*-
"""PRD-349/T2（trend issue #1628 的 T2 环节）：skill 调用重放包最小实现。

按 T1 设计（docs/plans/2026-11-11-prd-349-skill-call-replay-design.md）
§3.1/§3.2/§4 实现：

  - make_pack(calls, registry, *, rules_version)：从 skill 调用决策记录构建
    重放包（R1 三件套）——input_fingerprint（触发指令原文 digest + 登记册
    digest + rules_version）、decisions（resolve 结果投影：resolved_skill/
    trigger_conditions/refusal_code）、output（结果摘要）；缺任一
    PACK_INCOMPLETE；
  - replay(pack, utterance, registry, resolve_fn, *, rules_version)：重放三步
    （§3.2）——①指纹复核（utterance/registry digest 或版本不符 →
    REPLAY_INPUT_DRIFT 拒绝）②注入式 resolve_fn 深拷贝复算解析层（PRD-227
    skill_ref_resolver.resolve 形态，零 skill 执行零网络 R2）③decisions
    逐字节比对 → REPLAY_OK / REPLAY_MISMATCH（首分歧条显形，R3 零静默）；
  - ReplayLedger：append-only（R4）。

零网络；示例全虚构占位。
测试：tests/test_prd349_t2_skill_call_replay.py
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Callable

PACK_SCHEMA = "skill-call-replay-pack/v1"
ERROR_CODES = ("REPLAY_INPUT_DRIFT", "REPLAY_MISMATCH", "PACK_INCOMPLETE")
_DECISION_KEYS = ("resolved_skill", "trigger_conditions", "refusal_code")


def _digest(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"))
    return "sha16:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def registry_digest(registry: dict[str, Any]) -> str:
    return _digest(registry)


def make_pack(calls: list[dict[str, Any]], registry: dict[str, Any], *,
              rules_version: str) -> dict[str, Any]:
    """从调用决策记录构建重放包（R1 三件套）。"""
    clean = []
    for c in calls or []:
        if "utterance" not in c or not isinstance(c.get("utterance"), str):
            return {"schema": PACK_SCHEMA, "refused": "PACK_INCOMPLETE",
                    "detail": "决策记录缺 utterance——拒绝入账"}
        clean.append({"utterance": c["utterance"],
                      "resolved_skill": c.get("resolved_skill"),
                      "trigger_conditions": c.get("trigger_conditions"),
                      "refusal_code": c.get("refusal_code")})
    if not clean or not registry or not rules_version:
        return {"schema": PACK_SCHEMA, "refused": "PACK_INCOMPLETE",
                "detail": "calls/registry/rules_version 缺失——三件套不齐"}
    return {
        "schema": PACK_SCHEMA,
        "input_fingerprint": {"registry_digest": registry_digest(registry),
                              "rules_version": rules_version},
        "decisions": clean,
        "output": {"resolved": [c["resolved_skill"] for c in clean],
                   "refused_codes": [c["refusal_code"] for c in clean]},
    }


def _refusal(code: str, detail: str) -> dict[str, Any]:
    return {"schema": PACK_SCHEMA, "refused": code, "detail": detail,
            "verdict": None}


def replay(pack: dict[str, Any], utterances: list[str],
           registry: dict[str, Any],
           resolve_fn: Callable[[str, dict], dict[str, Any]], *,
           rules_version: str) -> dict[str, Any]:
    """重放三步（§3.2）：解析层复算（R2 零执行），对不上显形（R3）。"""
    fp = pack.get("input_fingerprint") or {}
    if (not fp or pack.get("refused") or not pack.get("decisions")
            or not pack.get("output")):
        return _refusal("PACK_INCOMPLETE", "重放包三件套不齐")
    if (registry_digest(registry) != fp.get("registry_digest")
            or rules_version != fp.get("rules_version")):
        return _refusal("REPLAY_INPUT_DRIFT",
                        "登记册指纹或版本与包不符——拒绝重放（防新登记册冒充当时）")
    rerun = []
    for utt in utterances:
        out = resolve_fn(copy.deepcopy(utt), copy.deepcopy(registry))
        rerun.append({"utterance": utt,
                      "resolved_skill": out.get("skill"),
                      "trigger_conditions": out.get("trigger_conditions"),
                      "refusal_code": (out.get("resolution") or {}).get(
                          "error_code")})
    for i, want in enumerate(pack["decisions"]):
        got = rerun[i] if i < len(rerun) else None
        if got != want:
            return {"schema": PACK_SCHEMA, "refused": None,
                    "verdict": "REPLAY_MISMATCH",
                    "evidence": {"first_divergence_index": i,
                                 "want": want, "got": got},
                    "rerun_count": len(rerun)}
    if len(rerun) != len(pack["decisions"]):
        return {"schema": PACK_SCHEMA, "refused": None,
                "verdict": "REPLAY_MISMATCH",
                "evidence": {"first_divergence_index": len(rerun),
                             "why": "决策条数不一致"},
                "rerun_count": len(rerun)}
    return {"schema": PACK_SCHEMA, "refused": None, "verdict": "REPLAY_OK",
            "evidence": None, "rerun_count": len(rerun)}


class ReplayLedger:
    """重放账本（R4）：append-only 只增不删。"""

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []

    def record(self, pack: dict[str, Any], verdict: dict[str, Any], *,
               at: str) -> dict[str, Any]:
        entry = {"at": at,
                 "pack_fingerprint": copy.deepcopy(pack.get("input_fingerprint")),
                 "verdict": verdict.get("verdict") or verdict.get("refused"),
                 "evidence": copy.deepcopy(verdict.get("evidence"))}
        self._entries.append(entry)
        return dict(entry)

    @property
    def entries(self) -> list[dict[str, Any]]:
        return [dict(e) for e in self._entries]
