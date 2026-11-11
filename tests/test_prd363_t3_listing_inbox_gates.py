# -*- coding: utf-8 -*-
"""PRD-363/T3 测试（trend #1642 的 T3 环节）：上架审批收件箱批阅闸门。

运行：python3 -m unittest tests.test_prd363_t3_listing_inbox_gates -v（仓库根执行）

覆盖（T1 §4 + R1/R4）：append_only_gate（无基线形态过/mark_baseline 后追加
pass/删除或首事件改写 LEDGER_DRIFT 显形/非账本对象显形）；state_gate 双向对账
（人批后一致 pass/条目被直接改写/events 有裁决条目回 pending/events 有裁决条
目被删——三种破坏全部 STATE_INCONSISTENT 显形）；gate_summary 一票否决；与 T2
串联（真实 add/approve/reject 产物过闸全 pass）；AST 零网络零子进程+闸门只读
（零裁决调用）。零网络；全合成占位。
"""
import ast
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from listing_inbox import InboxLedger, collect  # noqa: E402
from listing_inbox_gates import (  # noqa: E402
    ERROR_CODES,
    append_only_gate,
    gate_summary,
    mark_baseline,
    state_gate,
)

NOW = "2026-11-11T09:00:00Z"
SECURITY = [{"source_ref": "security-scan#plugin-7（占位）",
             "report_ref": "scan-report sha16:…（占位）",
             "diff_digest": "sha16:…（占位）",
             "reason": "依赖混淆疑似（占位）"}]
EDGE = [{"source_ref": "market#case-3（占位）",
         "report_ref": "review sha16:…（占位）", "reason": "边界案例（占位）"}]


class TestAppendOnlyGate(unittest.TestCase):
    def setUp(self):
        self.led = InboxLedger()
        self.led.add(collect(security_reviews=SECURITY, edge_cases=EDGE,
                             at=NOW))
        self.led.approve("item-001", by="r（占位）", at=NOW)

    def test_no_baseline_form_check_passes(self):
        self.assertEqual(append_only_gate(self.led)["gate"], "pass")

    def test_mark_baseline_then_append_passes(self):
        mark_baseline(self.led)
        self.led.reject("item-002", by="r（占位）", at=NOW, reason="r（占位）")
        self.assertEqual(append_only_gate(self.led)["gate"], "pass")

    def test_deletion_detected(self):
        mark_baseline(self.led)
        self.led._events.pop()
        self.assertEqual(append_only_gate(self.led)["gate"], "LEDGER_DRIFT")

    def test_first_event_rewrite_detected(self):
        mark_baseline(self.led)
        self.led._events[0]["op"] = "deleted（篡改）（占位）"
        self.assertEqual(append_only_gate(self.led)["gate"], "LEDGER_DRIFT")

    def test_non_ledger_object_visible(self):
        self.assertEqual(append_only_gate(object())["gate"], "LEDGER_DRIFT")


class TestStateGate(unittest.TestCase):
    def setUp(self):
        self.led = InboxLedger()
        self.led.add(collect(security_reviews=SECURITY, edge_cases=EDGE,
                             at=NOW))
        self.led.approve("item-001", by="r（占位）", at=NOW)

    def test_consistent_state_passes(self):
        self.assertEqual(state_gate(self.led)["gate"], "pass")

    def test_direct_item_rewrite_detected(self):
        """条目被直接改写（未经 _decide）→ STATE_INCONSISTENT。"""
        self.led.reject("item-002", by="r（占位）", at=NOW, reason="r（占位）")
        self.led._items["item-002"]["state"] = "pending"   # 直接改回
        out = state_gate(self.led)
        self.assertEqual(out["gate"], "STATE_INCONSISTENT")
        self.assertTrue(any("item-002" in r for r in out["reasons"]))

    def test_state_rollback_detected(self):
        """events 有裁决但条目回 pending → STATE_INCONSISTENT。"""
        self.led.reject("item-002", by="r（占位）", at=NOW, reason="r（占位）")
        self.led._items["item-002"]["state"] = "pending"
        out = state_gate(self.led)
        self.assertEqual(out["gate"], "STATE_INCONSISTENT")

    def test_item_deleted_detected(self):
        """events 有裁决但条目被删 → STATE_INCONSISTENT。"""
        self.led.reject("item-002", by="r（占位）", at=NOW, reason="r（占位）")
        del self.led._items["item-002"]
        out = state_gate(self.led)
        self.assertEqual(out["gate"], "STATE_INCONSISTENT")
        self.assertTrue(any("条目被删除" in r for r in out["reasons"]))


class TestSummaryAndChain(unittest.TestCase):
    def test_summary_one_block_votes_all(self):
        led = InboxLedger()
        led.add(collect(security_reviews=SECURITY, at=NOW))
        led.approve("item-001", by="r（占位）", at=NOW)
        led._items["item-001"]["state"] = "pending"
        out = gate_summary([append_only_gate(led), state_gate(led)])
        self.assertEqual(out["gate"], "block")
        self.assertEqual(out["gates_checked"], 2)

    def test_chain_with_real_t2_products(self):
        """与 T2 串联：真实 add/approve/reject 产物过闸全 pass。"""
        led = InboxLedger()
        led.add(collect(security_reviews=SECURITY, edge_cases=EDGE, at=NOW))
        led.approve("item-001", by="r（占位）", at=NOW)
        led.reject("item-002", by="r（占位）", at=NOW, reason="r（占位）")
        mark_baseline(led)
        results = [append_only_gate(led), state_gate(led)]
        self.assertTrue(all(r["gate"] == "pass" for r in results))
        self.assertEqual(gate_summary(results)["gate"], "pass")

    def test_gate_codes_closed(self):
        self.assertEqual(set(ERROR_CODES),
                         {"LEDGER_DRIFT", "STATE_INCONSISTENT",
                          "DECISION_MISSING"})


class TestRedline(unittest.TestCase):
    def test_ast_zero_network_zero_subprocess_readonly(self):
        """R1 AST：零网络零子进程+闸门只读（零裁决调用）。"""
        banned = {"urllib", "requests", "socket", "http", "subprocess"}
        src = (REPO / "scripts" / "listing_inbox_gates.py").read_text(
            encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module.split(".")[0]]
            for mod in mods:
                self.assertNotIn(mod, banned)
        for call in (".add(", ".approve(", ".reject("):
            self.assertNotIn(call, src, f"闸门出现裁决调用 {call}")


if __name__ == "__main__":
    unittest.main()
