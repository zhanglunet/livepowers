# -*- coding: utf-8 -*-
"""PRD-363/T2 测试（trend #1642 的 T2 环节）：上架审批收件箱。

运行：python3 -m unittest tests.test_prd363_t2_listing_inbox -v（仓库根执行）

覆盖（T1 §3.1/§3.2/§4 + R1–R4）：collect 三源只读汇聚（词表封闭+五件套缺一
INBOX_ITEM_INCOMPLETE 显形拒绝入箱+与 PRD-335 genui_gate dropped 产物直接
对接）；InboxLedger 状态机（approve/reject 人批留痕/重复裁决/未知 id/AUTO_EXEC
携带上架载荷拒绝——零上架零 skillpack 变更 R1）；append-only（events+裁决不
可改）；view kind 过滤；AST 零网络零子进程。零网络；全合成占位。
"""
import ast
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from genui_gate import tree_gate  # noqa: E402
from listing_inbox import (  # noqa: E402
    ERROR_CODES,
    ITEM_KINDS,
    InboxError,
    InboxLedger,
    collect,
)

NOW = "2026-11-11T09:00:00Z"
LEAKY = {"type": "分组框", "props": {"title": "配置页（占位）",
                                     "hack_attr": "越权属性（占位）"},
         "children": []}
SECURITY = [{"source_ref": "security-scan#plugin-7（占位）",
             "report_ref": "scan-report sha16:…（占位）",
             "diff_digest": "sha16:…（占位）",
             "reason": "依赖混淆疑似（占位）"}]
EDGE = [{"source_ref": "market#case-3（占位）",
         "report_ref": "review sha16:…（占位）", "reason": "边界案例（占位）"}]


class TestCollect(unittest.TestCase):
    def test_three_sources_closed_vocab(self):
        dropped = [{"index": 0, "prop": "hack_attr",
                    "report_ref": "genui-product/v1（占位）"}]
        items = collect(security_reviews=SECURITY, dropped_reviews=dropped,
                        edge_cases=EDGE, at=NOW)
        self.assertEqual([it["kind"] for it in items],
                         ["security_manual_review", "dropped_props_review",
                          "market_edge_case"])
        self.assertEqual(set(ITEM_KINDS),
                         {"security_manual_review", "dropped_props_review",
                          "market_edge_case"})

    def test_evidence_complete(self):
        """R3：五件套齐（diff_digest 可空但键须在位）。"""
        items = collect(security_reviews=SECURITY, at=NOW)
        it = items[0]
        for key in ("item_id", "kind", "source_ref", "report_ref", "reason",
                    "diff_digest"):
            self.assertIn(key, it)
        self.assertTrue(it["report_ref"])

    def test_dropped_from_real_genui_gate(self):
        """与 PRD-335/T3 串联：tree_gate dropped 产物直接入箱。"""
        out = tree_gate(LEAKY)
        self.assertEqual(out["gate"], "DROPPED_PROPS")
        dropped = [{"index": 0, "prop": d["prop"],
                    "report_ref": "genui-product/v1（占位）"}
                   for d in out["dropped"]]
        items = collect(dropped_reviews=dropped, at=NOW)
        self.assertEqual(items[0]["kind"], "dropped_props_review")
        self.assertEqual(items[0]["reason"].split(" ")[0], "白名单外属性")

    def test_incomplete_raises_visible(self):
        """R3：report_ref 缺失 → INBOX_ITEM_INCOMPLETE 显形拒绝入箱。"""
        with self.assertRaisesRegex(InboxError, "INBOX_ITEM_INCOMPLETE"):
            collect(security_reviews=[{"source_ref": "s"}], at=NOW)


class TestLedger(unittest.TestCase):
    def _ledger(self):
        led = InboxLedger()
        dropped = [{"index": 0, "prop": "hack_attr",
                    "report_ref": "genui-product/v1（占位）"}]
        led.add(collect(security_reviews=SECURITY, dropped_reviews=dropped,
                        edge_cases=EDGE, at=NOW))
        return led

    def test_approve_reject_state_machine(self):
        led = self._ledger()
        a = led.approve("item-001", by="reviewer（占位）", at=NOW)
        self.assertEqual(a["state"], "approved")
        r = led.reject("item-003", by="reviewer（占位）", at=NOW,
                       reason="退回重报（占位）")
        self.assertEqual(r["state"], "rejected")
        self.assertEqual(r["reject_reason"], "退回重报（占位）")

    def test_double_and_unknown_visible(self):
        led = self._ledger()
        led.approve("item-001", by="r（占位）", at=NOW)
        with self.assertRaisesRegex(InboxError, "INBOX_DOUBLE_DECIDE"):
            led.reject("item-001", by="r（占位）", at=NOW)
        with self.assertRaisesRegex(InboxError, "未知"):
            led.approve("item-999", by="r（占位）", at=NOW)

    def test_auto_exec_listing_payload_rejected(self):
        """R1：裁决携带上架/skillpack 写载荷 → AUTO_EXEC 显形拒绝。"""
        led = self._ledger()
        with self.assertRaisesRegex(InboxError, "INBOX_AUTO_EXEC_ATTEMPT"):
            led.approve("item-001", by="r（占位）", at=NOW,
                        payload={"publish": "plugin-7（占位）"})
        with self.assertRaisesRegex(InboxError, "INBOX_AUTO_EXEC_ATTEMPT"):
            led.reject("item-001", by="r（占位）", at=NOW,
                       payload={"install": "skillpack（占位）"})
        self.assertEqual(led.view()[0]["state"], "pending")   # 零状态变化

    def test_append_only_and_view_filter(self):
        led = self._ledger()
        led.approve("item-001", by="r（占位）", at=NOW)
        before = [dict(e) for e in led.events]
        led.reject("item-002", by="r（占位）", at=NOW, reason="r（占位）")
        self.assertEqual(led.events[:len(before)], before)
        self.assertEqual(len(led.events), len(before) + 1)
        self.assertEqual(len(led.view("security_manual_review")), 1)
        self.assertEqual(len(led.view()), 3)


class TestRedline(unittest.TestCase):
    def test_error_codes_closed(self):
        self.assertEqual(set(ERROR_CODES),
                         {"INBOX_ITEM_INCOMPLETE", "INBOX_DOUBLE_DECIDE",
                          "INBOX_AUTO_EXEC_ATTEMPT"})

    def test_ast_zero_network_zero_subprocess(self):
        banned = {"urllib", "requests", "socket", "http", "subprocess"}
        tree = ast.parse((REPO / "scripts" / "listing_inbox.py").read_text(
            encoding="utf-8"))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module.split(".")[0]]
            for mod in mods:
                self.assertNotIn(mod, banned)


if __name__ == "__main__":
    unittest.main()
