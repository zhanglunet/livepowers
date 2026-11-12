# -*- coding: utf-8 -*-
"""PRD-377/T2（trend issue #1881 的 T2 环节）：插件安检发现验证台最小实现。

按 T1 设计（docs/plans/2026-11-12-prd-377-plugin-verification-bench-design.md）
§4 落地：

  - verify_finding(finding, skill_dir, recheck_fn)：逐条安检发现复现验证
    ——recheck_fn 注入式重跑同一扫描器（market_gate_scan.scan_skill，技能
    目录只读遍历，零新增检测规则 R2）；复现结果包含同 rule_id+location 的
    发现 → VERIFIED，否则 UNVERIFIED（词表封闭）；目录指纹复用
    install_snapshot.dir_fingerprint（PRD-279 同源 import）；
  - verify_findings(findings, skill_dir, recheck_fn)：收录审批来源包装
    （接入点：scan_skill findings 之后、listing_inbox.collect
    (security_reviews) 之前）——UNVERIFIED 拦下不上审批（R1）；
  - PluginBenchLedger：机器可读 JSONL 落账（路径注入，append-only R3/R4）；
    八件套缺一 BENCH_INCOMPLETE 拒绝入账；
  - reverify：技能目录变更二次验证——目录指纹与当前不符 → BENCH_STALE
    拒绝复用旧验证（R4 关闭以最新 VERIFIED 为准）。

零 LLM 零网络零子进程零安装词面；示例全虚构占位。
测试：tests/test_prd377_t2_plugin_verify_bench.py
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable

from install_snapshot import dir_fingerprint   # 指纹与 PRD-279 同源（T1 §0）

BENCH_SCHEMA = "plugin-verify-bench/v1"
VERDICTS = ("VERIFIED", "UNVERIFIED")
ERROR_CODES = ("BENCH_INCOMPLETE", "BENCH_REPRO_MISMATCH", "BENCH_STALE")


class PluginBenchError(ValueError):
    """验证台违规——显形拒绝。"""


def _recusal(code: str, detail: str) -> dict[str, Any]:
    return {"schema": BENCH_SCHEMA, "refused": code, "detail": detail,
            "verdict": None}


def _files_bytes(skill_dir: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for path in sorted(Path(skill_dir).rglob("*")):
        if path.is_file():
            try:
                files[str(path.relative_to(skill_dir))] = path.read_bytes()
            except OSError:
                continue
    return files


def _reproduced(finding: dict[str, Any],
                rerun: list[dict[str, Any]]) -> bool:
    """复现判定：重跑结果中存在同 rule_id+location 的发现。"""
    for r in rerun:
        if (r.get("rule_id") == finding.get("rule_id")
                and r.get("location") == finding.get("location")):
            return True
    return False


def verify_finding(finding: dict[str, Any], skill_dir: Path,
                   recheck_fn: Callable[[Path], list[dict[str, Any]]],
                   *, at: str = "") -> dict[str, Any]:
    """逐条安检发现复现验证（R1/R2）：重跑同一扫描器，复现 → VERIFIED。"""
    if not isinstance(finding, dict):
        return _recusal("BENCH_INCOMPLETE", "finding 非对象")
    missing = [k for k in ("finding_id", "rule_id", "location", "source_ref")
               if not finding.get(k)]
    if missing:
        return _recusal("BENCH_INCOMPLETE", f"八件套缺 {missing}")
    if not callable(recheck_fn):
        return _recusal("BENCH_INCOMPLETE", "recheck_fn 未注入")
    rerun = recheck_fn(Path(skill_dir)) or []
    match = _reproduced(finding, rerun)
    return {
        "schema": BENCH_SCHEMA,
        "finding_id": finding["finding_id"],
        "rule_id": finding["rule_id"],
        "location": finding["location"],
        "source_ref": finding["source_ref"],
        "dir_fingerprint": dir_fingerprint(_files_bytes(Path(skill_dir))),
        "finding": copy.deepcopy(finding),
        "reproduce": {"match": match,
                      "detail": f"重跑检出 {len(rerun)} 条（占位）"},
        "verdict": "VERIFIED" if match else "UNVERIFIED",
        "at": at,
    }


def verify_findings(findings: list[dict[str, Any]], skill_dir: Path,
                    recheck_fn: Callable[[Path], list[dict[str, Any]]],
                    *, at: str = "") -> dict[str, Any]:
    """收录审批来源包装（接入点）：UNVERIFIED 拦下不上审批（R1）。"""
    verified: list[dict[str, Any]] = []
    unverified: list[dict[str, Any]] = []
    for f in findings or []:
        out = verify_finding(f, skill_dir, recheck_fn, at=at)
        if out.get("refused") or out["verdict"] == "UNVERIFIED":
            unverified.append(out)
        else:
            verified.append(out)
    return {"schema": BENCH_SCHEMA, "verified": verified,
            "unverified": unverified, "unverified_count": len(unverified)}


class PluginBenchLedger:
    """验证账本（R3/R4）：JSONL append-only；八件套缺一拒绝入账。"""

    _REQUIRED = ("finding_id", "rule_id", "location", "source_ref",
                 "dir_fingerprint", "finding", "verdict")

    def __init__(self, path: str | Path | None = None) -> None:
        self._records: list[dict[str, Any]] = []
        self._path = Path(path) if path else None

    def record(self, out: dict[str, Any], *, at: str = "") -> dict[str, Any]:
        if out.get("refused"):
            raise PluginBenchError(f"{out['refused']}：{out['detail']}")
        rec = dict(out, at=at)
        missing = [k for k in self._REQUIRED if rec.get(k) in (None, "")]
        if missing:
            raise PluginBenchError(f"BENCH_INCOMPLETE：账目缺 {missing}")
        if rec["verdict"] not in VERDICTS:
            raise PluginBenchError(f"BENCH_INCOMPLETE：verdict 词表外 "
                                   f"{rec['verdict']!r}")
        if rec["verdict"] == "VERIFIED" and not rec["reproduce"]["match"]:
            raise PluginBenchError("BENCH_REPRO_MISMATCH：声称 VERIFIED 但"
                                   "复现 match=false——验证结论与复现证据"
                                   "不一致")
        self._records.append(copy.deepcopy(rec))
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False,
                                    sort_keys=True) + "\n")
        return dict(rec)

    def entries(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self._records]

    def latest_for(self, finding_id: str) -> dict[str, Any] | None:
        found = [r for r in self._records
                 if r["finding_id"] == finding_id]
        return dict(found[-1]) if found else None

    def reverify(self, finding_id: str, skill_dir: Path,
                 recheck_fn: Callable[[Path], list[dict[str, Any]]],
                 *, at: str = "") -> dict[str, Any]:
        """技能目录变更二次验证（R4）：目录指纹不符 → BENCH_STALE 拒绝
        复用。"""
        prior = self.latest_for(finding_id)
        fp_now = dir_fingerprint(_files_bytes(Path(skill_dir)))
        if prior and prior["dir_fingerprint"] != fp_now:
            return _recusal("BENCH_STALE",
                            f"{finding_id} 旧验证目录指纹与当前不符——目录"
                            "变更后须重新验证，旧 VERIFIED 不复用")
        base = {"finding_id": finding_id,
                "rule_id": (prior or {}).get("rule_id") or "",
                "location": (prior or {}).get("location") or "",
                "source_ref": (prior or {}).get("source_ref") or ""}
        return self.record(verify_finding(base, skill_dir, recheck_fn,
                                          at=at), at=at)
