# -*- coding: utf-8 -*-
"""PRD-446/T2 测试（trend issue #2151 的 T2 环节）：skill 生成监督台。
运行：uv run --with pytest python -m pytest tests/test_prd446_t2_skill_supervision_bench.py -q
覆盖（T1 §4 + R1~R3）：步骤状态机/批注留痕/发回回炉闭环/点头按版本/
未点头不外流/JSONL 落库/词表封闭/AST 零网络。零网络；全合成占位。
"""
import ast
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from skill_supervision_bench import (  # noqa: E402
    ANNOTATION_STATUS, BENCH_SCHEMA, ERROR_CODES, SupervisionError,
    SkillSupervisionSession, SupervisionLedger, TICKET_STATUS,
)

NOW = "2026-11-15T09:00:00Z"


def mk_session():
    s = SkillSupervisionSession(task_ref="task-1（占位）", created_at=NOW)
    s.add_step(seq=1, name="模板选取（占位）", status="待复核")
    s.add_step(seq=2, name="字段填充（占位）", status="待复核")
    s.add_version(version="v1", package_ref="skill-pack/v1（占位）")
    return s


class TestProgress(unittest.TestCase):
    def test_step_lifecycle(self):
        s = mk_session()
        self.assertEqual(s.steps[0]["status"], "待复核")
        s.send_back_step(seq=1, at=NOW)
        self.assertEqual(s.steps[0]["status"], "已发回")

    def test_step_state_conflict(self):
        s = mk_session()
        s.send_back_step(seq=1, at=NOW)
        with self.assertRaisesRegex(SupervisionError, "SUPERVISION_STATE_CONFLICT"):
            s.send_back_step(seq=1, at=NOW)

    def test_duplicate_version_conflict(self):
        s = mk_session()
        with self.assertRaisesRegex(SupervisionError, "SUPERVISION_STATE_CONFLICT"):
            s.add_version(version="v1", package_ref="x（占位）")


class TestAnnotationTicket(unittest.TestCase):
    def test_annotate_and_send_back(self):
        s = mk_session()
        s.annotate(author="甲（占位）", at=NOW, seq=1, text="模板不对（占位）",
                   field="template")
        t = s.send_back(author="甲（占位）", at=NOW, seq=1,
                        demand="换模板（占位）", target_version="v1")
        self.assertEqual(t["status"], "待处理")
        self.assertEqual(s.steps[0]["status"], "已发回")
        self.assertEqual(s.versions[0]["status"], "已发回")

    def test_annotation_requires_author_at(self):
        s = mk_session()
        with self.assertRaisesRegex(SupervisionError, "SUPERVISION_INCOMPLETE"):
            s.annotate(author="", at=NOW, seq=1, text="x（占位）")

    def test_return_new_version_and_close(self):
        s = mk_session()
        s.annotate(author="甲（占位）", at=NOW, seq=1, text="模板不对（占位）")
        s.send_back(author="甲（占位）", at=NOW, seq=1, demand="换模板（占位）",
                    target_version="v1")
        s.return_new_version(ticket_seq=1, version="v2",
                             package_ref="skill-pack/v2（占位）")
        s.close_ticket(ticket_seq=1, by="甲（占位）", at=NOW)
        self.assertEqual(s.tickets[0]["status"], "已关闭")
        self.assertEqual(s.versions[1]["version"], "v2")

    def test_close_before_return_refused(self):
        s = mk_session()
        s.annotate(author="甲（占位）", at=NOW, seq=1, text="x（占位）")
        s.send_back(author="甲（占位）", at=NOW, seq=1, demand="d（占位）",
                    target_version="v1")
        with self.assertRaisesRegex(SupervisionError, "SUPERVISION_STATE_CONFLICT"):
            s.close_ticket(ticket_seq=1, by="甲（占位）", at=NOW)


class TestApprovalGate(unittest.TestCase):
    def test_approve_requires_closed_tickets(self):
        s = mk_session()
        s.annotate(author="甲（占位）", at=NOW, seq=1, text="x（占位）")
        s.send_back(author="甲（占位）", at=NOW, seq=1, demand="d（占位）",
                    target_version="v1")
        with self.assertRaisesRegex(SupervisionError, "SUPERVISION_STATE_CONFLICT"):
            s.approve(approver="乙（占位）", at=NOW, version="v1")

    def test_approve_then_outlet(self):
        s = mk_session()
        s.approve(approver="乙（占位）", at=NOW, version="v1", note="ok（占位）")
        out = s.outlet([{"version": "v1"}, {"version": "v2"}])
        self.assertEqual([p["version"] for p in out["passed"]], ["v1"])
        self.assertEqual(out["blocked_count"], 1)

    def test_unapproved_never_outlet(self):
        s = mk_session()
        out = s.outlet([{"version": "v1"}])
        self.assertEqual(out["passed"], [])
        self.assertEqual(out["blocked"][0]["version"], "v1")


class TestLedgerRedline(unittest.TestCase):
    def test_ledger_jsonl_append_only(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sup" / "log.jsonl"
            led = SupervisionLedger(path)
            led.record(kind="decision", at=NOW,
                       payload={"verdict": "点头（占位）"})
            led.record(kind="annotation", at=NOW, payload={"text": "x（占位）"})
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[1])["kind"], "annotation")

    def test_ledger_kind_vocab(self):
        led = SupervisionLedger(None)
        with self.assertRaisesRegex(SupervisionError, "SUPERVISION_INCOMPLETE"):
            led.record(kind="ghost", at=NOW, payload={})

    def test_no_approval_path_in_module(self):
        """R2 预检：模块源码不含审批通过/驳回路径词。"""
        src = (Path(__file__).resolve().parents[1] / "scripts"
               / "skill_supervision_bench.py").read_text(encoding="utf-8")
        for word in ("approve_package", "reject_package", "审批通过",
                     "审批驳回"):
            self.assertNotIn(word, src, word)

    def test_ast_zero_network(self):
        banned = {"urllib", "requests", "socket", "http", "subprocess"}
        src = (Path(__file__).resolve().parents[1] / "scripts"
               / "skill_supervision_bench.py").read_text(encoding="utf-8")
        imported = set()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertFalse(imported & banned, imported & banned)

    def test_vocab_closed(self):
        self.assertEqual(set(ANNOTATION_STATUS),
                         {"待处理", "已采纳", "已驳回"})
        self.assertEqual(set(TICKET_STATUS),
                         {"待处理", "处理中", "已回炉", "已关闭"})


if __name__ == "__main__":
    unittest.main()
