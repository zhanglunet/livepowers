# -*- coding: utf-8 -*-
"""PRD-446/T2（trend issue #2151 的 T2 环节）：skill 生成监督台最小实现。

按 T1 设计（docs/plans/2026-11-15-prd-446-skill-supervision-bench-design.md）
§4 落地三构件与数据模型：
  - Progress：SupervisionSession + StepRecord 状态机（待开始/进行中/待复核/
    已发回；已点头按包版本给，不落在步骤上）；
  - Annotation：人批注，锚定步骤+字段/文件，状态 待处理/已采纳/已驳回；
  - FeedbackTicket：一点发回，状态 待处理/处理中/已回炉/已关闭，回炉出新
    PackageVersion 回监督台复核；
  - ApprovalGate：按包版本点头；未点头的 skill 包不上架审批（R1）；
  - 三件套（进度+批注+发回反馈）全程落 SupervisionLedger（JSONL append-only
    路径注入）；批注/发回/裁决都带作者与时间（留痕 R3）。
skill 生成不碰上架审批权：本模块无任何上架裁决路径（R2，T4 划界钉值）。
零 LLM 零网络零子进程；示例全虚构占位。
测试：tests/test_prd446_t2_skill_supervision_bench.py
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

BENCH_SCHEMA = "skill-supervision-bench/v1"
STEP_STATUS = ("待开始", "进行中", "待复核", "已发回")
ANNOTATION_STATUS = ("待处理", "已采纳", "已驳回")
TICKET_STATUS = ("待处理", "处理中", "已回炉", "已关闭")
VERSION_STATUS = ("生成中", "待复核", "已点头")
ERROR_CODES = ("SUPERVISION_INCOMPLETE", "SUPERVISION_STATE_CONFLICT",
               "SUPERVISION_NOT_APPROVED")


class SupervisionError(ValueError):
    """监督台违规——显形拒绝。"""


def _require(ok: bool, code: str, detail: str) -> None:
    if not ok:
        raise SupervisionError(f"{code}：{detail}")


def _author_at(**kw: Any) -> tuple[str, str]:
    actor, at = kw.get("author") or kw.get("approver"), kw.get("at")
    _require(bool(actor) and bool(at), "SUPERVISION_INCOMPLETE",
             "作者与时间缺一不可（留痕红线）")
    return str(actor), str(at)


class SkillSupervisionSession:
    """一次 skill 生成任务的监督会话（§4.2）。"""

    def __init__(self, *, task_ref: str, created_at: str) -> None:
        _require(bool(task_ref) and bool(created_at), "SUPERVISION_INCOMPLETE",
                 "task_ref/created_at 缺一")
        self.task_ref = str(task_ref)
        self.created_at = str(created_at)
        self.steps: list[dict[str, Any]] = []
        self.versions: list[dict[str, Any]] = []
        self.annotations: list[dict[str, Any]] = []
        self.tickets: list[dict[str, Any]] = []
        self.decisions: list[dict[str, Any]] = []

    # ---- Progress：步骤状态机 -------------------------------------------------
    def add_step(self, *, seq: int, name: str, status: str = "待复核",
                 input_summary: str = "", output_summary: str = "",
                 fields: list[str] | None = None) -> dict[str, Any]:
        _require(status in ("进行中", "待复核"), "SUPERVISION_STATE_CONFLICT",
                 f"新步骤状态 {status!r} 只允许 进行中/待复核")
        step = {"seq": seq, "name": name, "status": status,
                "input_summary": input_summary,
                "output_summary": output_summary,
                "fields": list(fields or [])}
        self.steps.append(step)
        return copy.deepcopy(step)

    def send_back_step(self, *, seq: int, at: str) -> dict[str, Any]:
        _require(any(s["seq"] == seq for s in self.steps),
                 "SUPERVISION_STATE_CONFLICT", f"步骤 {seq} 不存在")
        step = next(s for s in self.steps if s["seq"] == seq)
        _require(step["status"] == "待复核", "SUPERVISION_STATE_CONFLICT",
                 f"步骤 {seq} 当前 {step['status']!r} 不可发回")
        step["status"] = "已发回"
        return copy.deepcopy(step)

    # ---- PackageVersion -------------------------------------------------------
    def add_version(self, *, version: str, package_ref: str,
                    status: str = "待复核",
                    step_summary: str = "") -> dict[str, Any]:
        _require(status in ("生成中", "待复核"), "SUPERVISION_STATE_CONFLICT",
                 f"新版本状态 {status!r} 只允许 生成中/待复核")
        _require(all(v["version"] != version for v in self.versions),
                 "SUPERVISION_STATE_CONFLICT", f"版本 {version!r} 重复")
        v = {"version": version, "package_ref": package_ref,
             "status": status, "step_summary": step_summary}
        self.versions.append(v)
        return copy.deepcopy(v)

    # ---- Annotation（批注）----------------------------------------------------
    def annotate(self, *, author: str, at: str, seq: int, text: str,
                 field: str = "") -> dict[str, Any]:
        actor, ts = _author_at(author=author, at=at)
        _require(any(s["seq"] == seq for s in self.steps),
                 "SUPERVISION_STATE_CONFLICT", f"批注锚定步骤 {seq} 不存在")
        _require(bool(text), "SUPERVISION_INCOMPLETE", "批注文本不能为空")
        a = {"seq": len(self.annotations) + 1, "author": actor, "at": ts,
             "step": seq, "field": str(field), "text": str(text),
             "status": "待处理"}
        self.annotations.append(a)
        return copy.deepcopy(a)

    def resolve_annotation(self, *, seq: int, status: str,
                           by: str, at: str) -> dict[str, Any]:
        _author_at(author=by, at=at)
        _require(status in ANNOTATION_STATUS[1:], "SUPERVISION_STATE_CONFLICT",
                 f"批注状态 {status!r} 词表外")
        a = next((x for x in self.annotations if x["seq"] == seq), None)
        _require(a is not None, "SUPERVISION_STATE_CONFLICT",
                 f"批注 {seq} 不存在")
        _require(a["status"] == "待处理", "SUPERVISION_STATE_CONFLICT",
                 f"批注 {seq} 已是 {a['status']!r} 不可重复处理")
        a["status"] = status
        return copy.deepcopy(a)

    # ---- FeedbackTicket（发回）------------------------------------------------
    def send_back(self, *, author: str, at: str, seq: int, demand: str,
                  target_version: str) -> dict[str, Any]:
        """一点发回：生成 FeedbackTicket，目标步骤转已发回，版本转回炉中。"""
        actor, ts = _author_at(author=author, at=at)
        _require(bool(demand), "SUPERVISION_INCOMPLETE", "发回诉求不能为空")
        ann = next((x for x in self.annotations if x["seq"] == seq), None)
        _require(ann is not None, "SUPERVISION_STATE_CONFLICT",
                 f"发回来源批注 {seq} 不存在")
        ver = next((v for v in self.versions
                    if v["version"] == target_version), None)
        _require(ver is not None, "SUPERVISION_STATE_CONFLICT",
                 f"目标包版本 {target_version!r} 不存在")
        _require(ver["status"] == "待复核", "SUPERVISION_STATE_CONFLICT",
                 f"版本 {target_version!r} 当前 {ver['status']!r} 不可发回")
        t = {"seq": len(self.tickets) + 1, "author": actor, "at": ts,
             "source_annotation": seq, "demand": str(demand),
             "target_version": str(target_version), "status": "待处理",
             "returned_version": None}
        self.tickets.append(t)
        self.send_back_step(seq=next(
            s["seq"] for s in self.steps if s["seq"] == ann["step"]), at=ts)
        ver["status"] = "已发回"
        return copy.deepcopy(t)

    def return_new_version(self, *, ticket_seq: int, version: str,
                           package_ref: str) -> dict[str, Any]:
        """回炉出新版：票转已回炉并挂新版引用，新版回监督台复核。"""
        t = next((x for x in self.tickets if x["seq"] == ticket_seq), None)
        _require(t is not None, "SUPERVISION_STATE_CONFLICT",
                 f"发回单 {ticket_seq} 不存在")
        _require(t["status"] in ("待处理", "处理中"),
                 "SUPERVISION_STATE_CONFLICT",
                 f"发回单 {ticket_seq} 已是 {t['status']!r}")
        v = self.add_version(version=version, package_ref=package_ref,
                             status="待复核",
                             step_summary=f"回炉（票 {ticket_seq}）")
        t["status"] = "已回炉"
        t["returned_version"] = version
        return copy.deepcopy(v)

    def close_ticket(self, *, ticket_seq: int, by: str, at: str) -> dict[str, Any]:
        """人复核新版满意：关闭发回单。"""
        _author_at(author=by, at=at)
        t = next((x for x in self.tickets if x["seq"] == ticket_seq), None)
        _require(t is not None, "SUPERVISION_STATE_CONFLICT",
                 f"发回单 {ticket_seq} 不存在")
        _require(t["status"] == "已回炉", "SUPERVISION_STATE_CONFLICT",
                 f"发回单 {ticket_seq} 当前 {t['status']!r} 不可关闭——须先回炉出新版")
        t["status"] = "已关闭"
        return copy.deepcopy(t)

    # ---- ApprovalGate（点头，按包版本）----------------------------------------
    def approve(self, *, approver: str, at: str, version: str,
                note: str = "") -> dict[str, Any]:
        actor, ts = _author_at(approver=approver, at=at)
        ver = next((v for v in self.versions if v["version"] == version), None)
        _require(ver is not None, "SUPERVISION_STATE_CONFLICT",
                 f"包版本 {version!r} 不存在")
        _require(ver["status"] == "待复核", "SUPERVISION_STATE_CONFLICT",
                 f"版本 {version!r} 当前 {ver['status']!r} 不可点头")
        open_tickets = [t for t in self.tickets
                        if t["status"] in ("待处理", "处理中")
                        and t["target_version"] == version]
        _require(not open_tickets, "SUPERVISION_STATE_CONFLICT",
                 f"版本 {version!r} 名下有未闭环发回单 {len(open_tickets)} 条——先回炉闭环再点头")
        ver["status"] = "已点头"
        d = {"approver": actor, "at": ts, "version": version,
             "verdict": "点头", "note": str(note)}
        self.decisions.append(d)
        return copy.deepcopy(d)

    def approved_versions(self) -> list[str]:
        return [v["version"] for v in self.versions if v["status"] == "已点头"]

    def outlet(self, packages: list[dict[str, Any]]) -> dict[str, Any]:
        """上架审批队列入口（R1）：只放行已点头的包版本。"""
        approved = set(self.approved_versions())
        passed, blocked = [], []
        for p in packages or []:
            (passed if str(p.get("version")) in approved else blocked).append(
                copy.deepcopy(p))
        return {"schema": BENCH_SCHEMA, "passed": passed,
                "blocked": blocked, "blocked_count": len(blocked)}


class SupervisionLedger:
    """三件套全程留痕（R3）：JSONL append-only，路径注入。"""

    _KINDS = ("step", "version", "annotation", "ticket", "decision")

    def __init__(self, path: str | Path | None = None) -> None:
        self._entries: list[dict[str, Any]] = []
        self._path = Path(path) if path else None

    def record(self, *, kind: str, at: str, payload: dict[str, Any]) -> dict[str, Any]:
        _require(kind in self._KINDS, "SUPERVISION_INCOMPLETE",
                 f"kind {kind!r} 词表外")
        _require(bool(at), "SUPERVISION_INCOMPLETE", "留痕时间缺一")
        entry = {"schema": BENCH_SCHEMA, "kind": kind, "at": str(at),
                 "payload": copy.deepcopy(payload)}
        self._entries.append(entry)
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False,
                                    sort_keys=True) + "\n")
        return dict(entry)

    def entries(self) -> list[dict[str, Any]]:
        return [dict(e) for e in self._entries]
