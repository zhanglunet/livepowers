#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-307/T2 skill 调用重放包·replay-pack/v1 最小实现（trend issue #1547）。

设计依据 docs/plans/2026-11-07-prd-307-livepowers-skill-replay-pack-t1.md（T1，PR #146）：
实现其 §1 统一 schema（输入快照指纹 + 决策 + 输出 + 重放记录）、§3 重放校验判据
（原样重跑、逐字节一致为 MATCH）与 append-only 账本。纯加法：不改动
skill_registry / pack_installer / subpack_registry 的任何行为，调用方在 skill
调用（触发检索）出口自行落包。

核心纪律（T1 §1 字段纪律）：
- **append-only**：账本只追加，成败都记，不提供删除/截断面。
- **二值重放结论**：MATCH / MISMATCH；MISMATCH 不静默。
- **错误码封闭词表**：穷举于 ``ERROR_CODES``。
- **重放面只读**：零写盘、零网络；重放只跑注入的确定性检索。
- **零正文复制**（承 PRD-293 红线）：账本不存 SKILL.md 正文/产出正文——只存
  触发指令、登记册指纹与命中技能标识（pack/name）；重放包对 skill 目录零读取。
- **指纹算法版本化**：fpv1 = 规范化 JSON 的 SHA-256 前 16 位。

示例触发指令/技能名全为占位合成。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

#: 重放包 schema（T1 §1，固定）
REPLAY_PACK_SCHEMA_VERSION = "replay-pack/v1"

#: 指纹算法标识（版本化；算法变更即换新标识，历史账本不重算为一致）
FINGERPRINT_ALGO = "fpv1"

#: 重放期望与状态（封闭）
REPLAY_EXPECT_BYTE_IDENTICAL = "byte-identical"
REPLAY_MATCH = "MATCH"
REPLAY_MISMATCH = "MISMATCH"
REPLAY_NOT_RUN = "NOT_RUN"

#: 封闭错误码词表（穷举；新增必须改本表）
ERROR_CODES = (
    "REPLAY_INPUT_REQUIRED",
    "REPLAY_DECISION_FIELDS_REQUIRED",
    "REPLAY_OUTPUT_REQUIRED",
    "REPLAY_COMMAND_INVALID",
    "REPLAY_INPUT_MISMATCH",
    "REPLAY_MISMATCH",
    "REPLAY_LEDGER_NOT_APPENDABLE",
)


class ReplayPackError(ValueError):
    """replay-pack/v1 纪律错误；``code`` 必须取自封闭词表 ERROR_CODES。"""

    def __init__(self, code: str, message: str) -> None:
        if code not in ERROR_CODES:
            raise ValueError(f"未登记错误码：{code}（词表={ERROR_CODES}）")
        super().__init__(f"{code}: {message}")
        self.code = code


def canonical_bytes(payload: Any) -> bytes:
    """规范化 JSON 字节（sort_keys + 紧凑分隔符 + UTF-8）；指纹与逐字节比对都用它。"""
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def fingerprint(payload: Any) -> str:
    """fpv1 指纹：canonical_bytes 的 SHA-256 前 16 位，前缀带算法标识。"""
    return f"{FINGERPRINT_ALGO}:" + hashlib.sha256(canonical_bytes(payload)).hexdigest()[:16]


def build_replay_pack(
    *,
    action: str,
    inputs: dict[str, Any],
    decision: dict[str, Any],
    output: dict[str, Any],
    replay_command: str,
) -> dict[str, Any]:
    """组装 replay-pack/v1 包；字段纪律不满足即报错不猜（错误码封闭）。"""
    if not inputs:
        raise ReplayPackError("REPLAY_INPUT_REQUIRED", "inputs 为空，没有可指纹化的输入")
    missing = [
        k
        for k in ("chosen", "why", "rules_version")
        if k not in decision or decision[k] in (None, "")
    ]
    if missing:
        raise ReplayPackError(
            "REPLAY_DECISION_FIELDS_REQUIRED", f"decision 缺字段：{missing}"
        )
    if "result" not in output or "key_numbers" not in output:
        raise ReplayPackError("REPLAY_OUTPUT_REQUIRED", "output 需要 result 与 key_numbers")
    if not isinstance(replay_command, str) or not replay_command:
        raise ReplayPackError("REPLAY_COMMAND_INVALID", "replay.command 必须是非空字符串")
    return {
        "schema_version": REPLAY_PACK_SCHEMA_VERSION,
        "action": action,
        "input": {"snapshot_fingerprint": fingerprint(inputs), "inputs": inputs},
        "decision": dict(decision),
        "output": {"result": output["result"], "key_numbers": output["key_numbers"]},
        "replay": {
            "command": replay_command,
            "expect": REPLAY_EXPECT_BYTE_IDENTICAL,
            "status": REPLAY_NOT_RUN,
        },
    }


class ReplayLedger:
    """append-only 账本：JSONL 只追加，不提供修改/删除/截断面。"""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def append(self, pack: dict[str, Any]) -> None:
        """追加一包；成败都记。"""
        try:
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(canonical_bytes(pack).decode("utf-8") + "\n")
        except OSError as exc:
            raise ReplayPackError("REPLAY_LEDGER_NOT_APPENDABLE", str(exc)) from exc

    def read_all(self) -> list[dict[str, Any]]:
        """按追加序读全部包；文件不存在视为空账本。"""
        try:
            raw = self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return []
        return [json.loads(line) for line in raw.splitlines() if line]

    def bytes_now(self) -> bytes | None:
        """当前账本字节（供审计/测试断言 verify 零写盘）。"""
        try:
            return self._path.read_bytes()
        except FileNotFoundError:
            return None


def verify_replay(
    pack: dict[str, Any],
    rerun: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """原样重跑：``rerun(inputs, decision)`` 的输出视图与账本 output 逐字节比对。

    只读：不改 pack、不写任何文件。契约：``rerun`` 返回与账本 output 同形状的
    视图（{"result", "key_numbers"}）——动作出口用同一套 view 函数规范化
    （见 ``output_view_of_skill_invoke``），保证记录与重放同口径。
    """
    rerun_output = rerun(pack["input"]["inputs"], pack["decision"])
    expected = canonical_bytes(
        {"result": pack["output"]["result"], "key_numbers": pack["output"]["key_numbers"]}
    )
    actual = canonical_bytes(
        {"result": rerun_output.get("result"), "key_numbers": rerun_output.get("key_numbers")}
    )
    matched = expected == actual
    return {
        "action": pack["action"],
        "input_snapshot_fingerprint": pack["input"]["snapshot_fingerprint"],
        "status": REPLAY_MATCH if matched else REPLAY_MISMATCH,
        "expect": pack["replay"]["expect"],
        "fingerprint_algo": FINGERPRINT_ALGO,
        "evidence": None if matched else {"ledger": pack["output"], "rerun": rerun_output},
    }


def output_view_of_skill_invoke(matches: list[dict[str, Any]]) -> dict[str, Any]:
    """检索产出 → 重放包 output 视图；记录与重放共用同一规范化。

    只留 (pack, name) 技能标识——one_line/triggers 属登记资产，产出正文
    （SKILL.md）永不入账本（承 PRD-293 零正文复制线）。
    """
    return {
        "result": {
            "matches": [{"pack": m.get("pack"), "name": m.get("name")}
                        for m in matches],
        },
        "key_numbers": {"matches_total": len(matches)},
    }


def pack_from_skill_invoke(
    registry: dict[str, Any],
    query: str,
    matches: list[dict[str, Any]],
) -> dict[str, Any]:
    """把一次 ``search`` 的产出装订成重放包（PRD-307 关键动作接入）。

    input 存触发指令原文 + 登记册指纹；decision.chosen = 命中技能清单摘要；
    rules_version 取规范版本（skill-pack-layering-spec@x）。零改动
    skill_registry 模块本身；对 skills/ 目录零读取。
    """
    from skill_registry import SPEC_NAME, SPEC_VERSION

    if not query or not str(query).strip():
        raise ReplayPackError("REPLAY_INPUT_REQUIRED", "触发指令为空")
    view = output_view_of_skill_invoke(matches or [])
    return build_replay_pack(
        action="skill_invoke",
        inputs={"query": query, "registry_fingerprint": fingerprint(registry)},
        decision={
            "chosen": "; ".join(f"{m['pack']}/{m['name']}"
                                for m in view["result"]["matches"]) or "miss（无命中，不硬凑）",
            "why": "触发词检索（§4.2：triggers 子串 OR，大小写不敏感）；"
                   "账本零正文复制（不存 SKILL.md/产出正文——承 PRD-293）",
            "rules_version": f"{SPEC_NAME}@{SPEC_VERSION}",
        },
        output=view,
        replay_command="rerun: skill_registry.search(原登记册, 账本 query)——先验登记册指纹一致",
    )


def verify_skill_replay(
    pack: dict[str, Any],
    registry: dict[str, Any],
    search_fn: Callable[[dict[str, Any], str], list[dict[str, Any]]],
) -> dict[str, Any]:
    """skill 调用重放专用：先验登记册指纹一致，再原样重跑检索并逐字节比对。

    指纹不一致 → REPLAY_INPUT_MISMATCH 显形（重放的不是当时那本登记册）；
    一致 → search_fn(registry, 账本 query) 过同一视图规范化后与账本逐字节
    比对。全程只读、对 skills/ 目录零读取、零正文复制。
    """
    inputs = pack["input"]["inputs"]
    if inputs.get("registry_fingerprint") != fingerprint(registry):
        return {
            "action": pack["action"],
            "input_snapshot_fingerprint": pack["input"]["snapshot_fingerprint"],
            "status": REPLAY_MISMATCH,
            "expect": pack["replay"]["expect"],
            "fingerprint_algo": FINGERPRINT_ALGO,
            "evidence": {
                "reason": "REPLAY_INPUT_MISMATCH",
                "field": "registry_fingerprint",
                "ledger": inputs.get("registry_fingerprint"),
                "rerun": fingerprint(registry),
            },
        }
    matches = search_fn(registry, inputs["query"])
    view = output_view_of_skill_invoke(matches)
    return verify_replay(pack, lambda _i, _d: view)
