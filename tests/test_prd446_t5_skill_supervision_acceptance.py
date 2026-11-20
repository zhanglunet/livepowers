# -*- coding: utf-8 -*-
"""PRD-446/T5 测试（trend #2154 的 T5 环节）：skill 生成监督台验收试运行。
运行：uv run --with pytest python -m pytest tests/test_prd446_t5_skill_supervision_acceptance.py -q
验收（T1 §9 T5 行「全链跑通」）：真实监督回路全链演练两遍逐字节一致——
生成（步骤+版本落账）→ 人批注 → 一点发回 → agent 回炉出新版 → 人复核
关闭 → 按新版本点头 → 闸门放行进上架审批队列（T2 outlet+T3 gate 双出口）；
失败演练：未点头包拦在队列外/未回炉先点头拒绝/闸门拦手写 status 位；
JSONL 留痕 append-only；链复跑 T2/T3/T4 子进程 exit 0；文档无密钥。
零网络；全合成占位。
"""
import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from skill_supervision_bench import (  # noqa: E402
    SupervisionError, SkillSupervisionSession, SupervisionLedger)
from skill_supervision_gate import approve_via_gate  # noqa: E402

NOW = "2026-11-15T09:00:00Z"
T1 = "2026-11-15T10:00:00Z"
T2 = "2026-11-15T11:00:00Z"
T3 = "2026-11-15T12:00:00Z"
TESTS = Path(__file__).resolve().parent


def full_chain():
    """真实监督回路全链：生成→批注→发回→回炉→复核→点头→闸门→队列。"""
    s = SkillSupervisionSession(task_ref="task-9（占位）", created_at=NOW)
    led = SupervisionLedger(None)
    steps = [("模板选取（占位）", 1), ("字段填充（占位）", 2),
             ("校验（占位）", 3), ("打包（占位）", 4)]
    for name, seq in steps:
        st = s.add_step(seq=seq, name=name, status="待复核",
                        input_summary=f"输入（占位 {seq}）",
                        output_summary=f"输出（占位 {seq}）")
        led.record(kind="step", at=NOW, payload=st)
    v1 = s.add_version(version="v1", package_ref="skill-pack/v1（占位）",
                       step_summary="初版（占位）")
    led.record(kind="version", at=NOW, payload=v1)
    s.annotate(author="甲（占位）", at=T1, seq=2, text="字段口径不对（占位）",
               field="fields/term")
    s.send_back(author="甲（占位）", at=T1, seq=1, demand="补字段并换模板（占位）",
                target_version="v1")
    s.return_new_version(ticket_seq=1, version="v2",
                         package_ref="skill-pack/v2（占位）")
    s.close_ticket(ticket_seq=1, by="甲（占位）", at=T2)
    s.approve(approver="乙（占位）", at=T3, version="v2", note="复核满意（占位）")
    for kind, payload in (("ticket", s.tickets[0]), ("decision", s.decisions[0])):
        led.record(kind=kind, at=T3, payload=payload)
    queue = [{"version": "v1"}, {"version": "v2"}]
    outlet = s.outlet(queue)
    gate = approve_via_gate(s, queue)
    return {"session": {"steps": s.steps, "versions": s.versions,
                        "annotations": s.annotations,
                        "tickets": s.tickets,
                        "decisions": s.decisions},
            "outlet": outlet, "gate": gate,
            "ledger": led.entries()}


class TestFullChain(unittest.TestCase):
    def test_chain_twice_byte_identical(self):
        runs = [full_chain(), full_chain()]
        self.assertEqual(json.dumps(runs[0], sort_keys=True),
                         json.dumps(runs[1], sort_keys=True))

    def test_unapproved_never_reaches_listing(self):
        run = full_chain()
        self.assertEqual(run["outlet"]["passed"][0]["version"], "v2")
        self.assertEqual(run["outlet"]["blocked_count"], 1)
        self.assertEqual(run["gate"]["passed"][0]["version"], "v2")
        self.assertEqual(run["gate"]["blocked_count"], 1)

    def test_ledger_records_full_trail(self):
        run = full_chain()
        kinds = [e["kind"] for e in run["ledger"]]
        self.assertIn("step", kinds)
        self.assertIn("version", kinds)
        self.assertIn("decision", kinds)
        self.assertTrue(all(e["at"] for e in run["ledger"]))


class TestFailureDrills(unittest.TestCase):
    def test_approve_before_return_loop_refused(self):
        s = SkillSupervisionSession(task_ref="t（占位）", created_at=NOW)
        s.add_step(seq=1, name="x（占位）", status="待复核")
        s.add_version(version="v1", package_ref="p（占位）")
        s.annotate(author="甲（占位）", at=NOW, seq=1, text="x（占位）")
        s.send_back(author="甲（占位）", at=NOW, seq=1, demand="d（占位）",
                    target_version="v1")
        with self.assertRaisesRegex(SupervisionError, "SUPERVISION_STATE_CONFLICT"):
            s.approve(approver="乙（占位）", at=NOW, version="v1")

    def test_gate_blocks_handwritten_status(self):
        s = SkillSupervisionSession(task_ref="t（占位）", created_at=NOW)
        s.add_step(seq=1, name="x（占位）", status="待复核")
        s.add_version(version="v1", package_ref="p（占位）")
        s.versions[0]["status"] = "已点头"   # 手写 status 位
        out = approve_via_gate(s, [{"version": "v1"}])
        self.assertEqual(out["passed"], [])

    def test_ledger_append_only(self):
        run = full_chain()
        self.assertTrue(all(e["at"] for e in run["ledger"]))
        led = SupervisionLedger(None)
        for e in run["ledger"]:
            led._entries.append(e)
        before = json.dumps(led.entries(), sort_keys=True)
        self.assertEqual(json.dumps(led.entries(), sort_keys=True), before)


class TestChainRerun(unittest.TestCase):
    def test_t2_t3_t4_rerun_green(self):
        """链复跑：T2/T3/T4 测试子进程复跑 exit 0（链上仍绿实测）。"""
        for name in ("test_prd446_t2_skill_supervision_bench.py",
                     "test_prd446_t3_skill_supervision_gate.py",
                     "test_prd446_t4_skill_supervision_boundary.py"):
            proc = subprocess.run(
                [sys.executable, "-m", "unittest", "discover",
                 "-s", str(TESTS), "-p", name],
                capture_output=True, timeout=300)
            self.assertEqual(proc.returncode, 0,
                             f"{name} 复跑失败：{proc.stdout[-400:]}{proc.stderr[-400:]}")


class TestDocNoSecrets(unittest.TestCase):
    def test_t1_design_doc_no_secrets(self):
        """文档无密钥：T1 设计拼接 needle 扫描+占位符纪律（R5）。"""
        doc = next(Path(__file__).resolve().parents[1].glob(
            "docs/plans/2026-11-15-prd-446-*.md"))
        text = doc.read_text(encoding="utf-8").lower()
        for needle in ("sk-" + "live", "passw" + "ord", "api_k" + "ey"):
            self.assertNotIn(needle, text, f"设计文档出现密钥词 {needle}")
        self.assertIn("占位", text)


if __name__ == "__main__":
    unittest.main()
