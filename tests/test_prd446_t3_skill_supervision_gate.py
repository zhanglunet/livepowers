# -*- coding: utf-8 -*-
"""PRD-446/T3 测试（trend #2152 的 T3 环节）：监督回路闸门。
运行：uv run --with pytest python -m pytest tests/test_prd446_t3_skill_supervision_gate.py -q
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from skill_supervision_gate import (  # noqa: E402
    GATE_REASONS, approve_via_gate, evaluate)
from skill_supervision_bench import SkillSupervisionSession  # noqa: E402

NOW = "2026-11-15T09:00:00Z"
T1 = "2026-11-15T10:00:00Z"
T2 = "2026-11-15T11:00:00Z"


def ok_session():
    s = SkillSupervisionSession(task_ref="t（占位）", created_at=NOW)
    s.add_step(seq=1, name="模板选取（占位）", status="待复核")
    s.add_version(version="v1", package_ref="p（占位）")
    s.approve(approver="乙（占位）", at=T1, version="v1")
    return s


class TestGate(unittest.TestCase):
    def test_clean_approve_allowed(self):
        s = ok_session()
        out = evaluate("v1", s.decisions, s.tickets)
        self.assertEqual((out["allowed"], out["reason"]),
                         (True, "GATE_ALLOWED"))

    def test_no_decision(self):
        out = evaluate("v1", [], [])
        self.assertEqual(out["reason"], "GATE_NO_DECISION")

    def test_not_latest_approve(self):
        decisions = [{"verdict": "点头", "version": "v1", "at": T1,
                      "approver": "乙（占位）"},
                     {"verdict": "发回", "version": "v1", "at": T2,
                      "approver": "乙（占位）"}]
        out = evaluate("v1", decisions, [])
        self.assertEqual(out["reason"], "GATE_NOT_LATEST_APPROVE")

    def test_ticket_open(self):
        # status 位被手写为已点头（闸门必须不信 status，只看原始记录）
        decisions = [{"verdict": "点头", "version": "v1", "at": T1,
                      "approver": "乙（占位）"}]
        tickets = [{"target_version": "v1", "status": "待处理", "at": T2}]
        out = evaluate("v1", decisions, tickets)
        self.assertEqual(out["reason"], "GATE_TICKET_OPEN")

    def test_superseded(self):
        decisions = [{"verdict": "点头", "version": "v1", "at": T1,
                      "approver": "乙（占位）"}]
        tickets = [{"target_version": "v1", "status": "已回炉",
                    "returned_version": "v2", "at": T2}]
        out = evaluate("v1", decisions, tickets)
        self.assertEqual(out["reason"], "GATE_SUPERSEDED")

    def test_stale_approval(self):
        decisions = [{"verdict": "点头", "version": "v1", "at": T2,
                      "approver": "乙（占位）"}]
        tickets = [{"target_version": "v1", "status": "已关闭", "at": T2}]
        out = evaluate("v1", decisions, tickets)
        self.assertEqual(out["reason"], "GATE_STALE_APPROVAL")

    def test_fresh_approval_after_closed_ticket_allowed(self):
        decisions = [{"verdict": "点头", "version": "v1", "at": "2026-11-15T12:00:00Z",
                      "approver": "乙（占位）"}]
        tickets = [{"target_version": "v1", "status": "已关闭", "at": T2}]
        out = evaluate("v1", decisions, tickets)
        self.assertEqual((out["allowed"], out["reason"]),
                         (True, "GATE_ALLOWED"))

    def test_unknown_version(self):
        out = evaluate("v9", [], [])
        self.assertEqual(out["reason"], "GATE_NO_DECISION")

    def test_gate_outlet_blocks_unapproved(self):
        class FakeSession:
            decisions = [{"verdict": "点头", "version": "v2", "at": T1,
                          "approver": "乙（占位）"}]
            tickets: list = []
        out = approve_via_gate(FakeSession(),
                               [{"version": "v1"}, {"version": "v2"}])
        self.assertEqual(out["blocked_count"], 1)
        self.assertEqual(out["blocked"][0]["gate"], "GATE_NO_DECISION")
        self.assertEqual(out["passed"][0]["version"], "v2")

    def test_gate_reasons_closed(self):
        self.assertEqual(len(GATE_REASONS), 7)


if __name__ == "__main__":
    unittest.main()
