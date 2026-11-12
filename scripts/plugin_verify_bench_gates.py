# -*- coding: utf-8 -*-
"""PRD-377/T3（trend issue #1881 的 T3 环节）：插件安检发现验证台闸门。

按 T1 设计 §5 落地，消费 T2 plugin_verify_bench 产物（注入式只读）：

  - mark_baseline + append_only_gate：账本 records 只增不删复核（基线锚
    单调不减 + 首条原样），破坏 LEDGER_DRIFT 显形；
  - verdict_gate：验证结论与复现证据双向对账——VERIFIED 但 match=false、
    UNVERIFIED 但 match=true（BENCH_REPRO_MISMATCH）、八件套缺一/词表外
    （BENCH_INCOMPLETE）显形；
  - stale_gate：目录指纹与当前技能目录不符 BENCH_STALE 显形；
  - gate_summary 多闸一票否决合并显形。

ERROR_CODES 随模块导出（348 教训）；零 LLM 零网络零安装词面；闸门只读。
测试：tests/test_prd377_t3_plugin_verify_bench_gates.py
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from install_snapshot import dir_fingerprint   # 指纹同源（T1 §0）

GATE_SCHEMA = "plugin-verify-bench-gate/v1"
GATE_CODES = ("LEDGER_DRIFT", "BENCH_INCOMPLETE", "BENCH_REPRO_MISMATCH",
              "BENCH_STALE")
ERROR_CODES = GATE_CODES   # 错误码词表（与闸门同源，随模块导出——348 教训）


def _fail(gate: str, reasons: list[str]) -> dict[str, Any]:
    return {"schema": GATE_SCHEMA, "gate": gate, "reasons": reasons}


def _files_bytes(skill_dir: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for path in sorted(Path(skill_dir).rglob("*")):
        if path.is_file():
            try:
                files[str(path.relative_to(skill_dir))] = path.read_bytes()
            except OSError:
                continue
    return files


def mark_baseline(ledger: Any) -> None:
    """打基线锚：记录当前 records 长度与首条（只挂只读锚属性）。"""
    entries = getattr(ledger, "entries", None)
    if not callable(entries):
        raise ValueError("账本无 entries 方法——非 PluginBenchLedger")
    rows = entries()
    ledger._gate_baseline_len = len(rows)
    ledger._gate_baseline_first = dict(rows[0]) if rows else None


def append_only_gate(ledger: Any) -> dict[str, Any]:
    """账本只增不删复核（R4 落地）。"""
    entries = getattr(ledger, "entries", None)
    if not callable(entries):
        return _fail("LEDGER_DRIFT",
                     ["账本无 entries 方法——非 PluginBenchLedger"])
    rows = entries()
    if getattr(ledger, "_gate_baseline_len", None) is not None:
        if len(rows) < ledger._gate_baseline_len:
            return _fail("LEDGER_DRIFT",
                         [f"records 长度 {len(rows)} < 基线 "
                          f"{ledger._gate_baseline_len}——发生删除"])
    first = getattr(ledger, "_gate_baseline_first", None)
    if first is not None and rows and rows[0] != first:
        return _fail("LEDGER_DRIFT", ["首条账目被改写——append-only 破坏"])
    return _fail("pass", [])


def verdict_gate(record: dict[str, Any]) -> dict[str, Any]:
    """验证结论与复现证据双向对账（R1/R3 落地）。"""
    reasons: list[str] = []
    missing = [k for k in ("finding_id", "rule_id", "location", "source_ref",
                           "dir_fingerprint", "finding", "verdict")
               if record.get(k) in (None, "")]
    if missing:
        reasons = reasons + [f"账目缺 {missing}（BENCH_INCOMPLETE）"]
    verdict = record.get("verdict")
    if verdict is not None and verdict not in ("VERIFIED", "UNVERIFIED"):
        reasons = reasons + [f"verdict {verdict!r} 词表外"
                             "（BENCH_INCOMPLETE）"]
    rep = record.get("reproduce") or {}
    if verdict == "VERIFIED" and rep.get("match") is not True:
        reasons = reasons + ["声称 VERIFIED 但复现 match!=true——验证结论与"
                             "复现证据不一致（BENCH_REPRO_MISMATCH）"]
    if verdict == "UNVERIFIED" and rep.get("match") is True:
        reasons = reasons + ["复现 match=true 但声称 UNVERIFIED——验证结论与"
                             "复现证据不一致（BENCH_REPRO_MISMATCH）"]
    if not reasons:
        return _fail("pass", [])
    code = "BENCH_INCOMPLETE" if any("INCOMPLETE" in r for r in reasons) \
        else "BENCH_REPRO_MISMATCH"
    return _fail(code, reasons)


def stale_gate(record: dict[str, Any], skill_dir: Path) -> dict[str, Any]:
    """复用旧验证复核：目录指纹与当前技能目录不符 BENCH_STALE 显形。"""
    fp = record.get("dir_fingerprint")
    if fp and fp != dir_fingerprint(_files_bytes(Path(skill_dir))):
        return _fail("BENCH_STALE",
                     [f"账目目录指纹 {fp} 与当前技能目录不符——目录变更后旧"
                      "验证不复用（BENCH_STALE）"])
    return _fail("pass", [])


def gate_summary(gates: list[dict[str, Any]]) -> dict[str, Any]:
    """多闸一票否决合并显形。"""
    reasons = [r for g in gates for r in g.get("reasons", [])]
    return {"schema": GATE_SCHEMA,
            "gate": "pass" if not reasons else "block",
            "gates_checked": len(gates), "reasons": reasons}
