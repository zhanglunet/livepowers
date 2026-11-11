# -*- coding: utf-8 -*-
"""PRD-363/T5 测试（trend #1642 的 T5 环节）：上架收件箱验收试运行。

运行：uv run --with pytest python -m pytest tests/test_prd363_t5_listing_inbox.py -q
（仓库根执行）

验收（T1 §5 T5 行「样例回放+文档无密钥」）：
  全链周期演练：三源只读汇聚 → 入箱 → 人批 → 人拒留痕 → 重复裁决演练
  （INBOX_DOUBLE_DECIDE 显形）→ AUTO_EXEC 演练（install/publish 载荷
  INBOX_AUTO_EXEC_ATTEMPT 显形拒绝——零上架写零 skillpack 变更）；两遍
  全链周期产物逐字节一致（确定性可复现）；账本 append-only；零上架行为
  复验（批/拒返回值零上架/skillpack 变更载荷键）；链复跑：T2/T3/T4
  测试子进程复跑 exit 0（链上仍绿实测）；文档无密钥：T1 设计文档拼接
  needle 扫描+占位符纪律。零网络；全合成占位。
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from listing_inbox import InboxError, InboxLedger, collect  # noqa: E402

NOW = "2026-11-11T09:00:00Z"
SECURITY = [{"source_ref": "security-scan#plugin-7（占位）",
             "report_ref": "scan-report sha16:…（占位）",
             "diff_digest": "sha16:…（占位）",
             "reason": "依赖混淆疑似（占位）"}]
EDGE = [{"source_ref": "market#case-3（占位）",
         "report_ref": "review sha16:…（占位）", "reason": "边界案例（占位）"}]


def _fresh_cycle():
    items = collect(security_reviews=SECURITY, edge_cases=EDGE, at=NOW)
    led = InboxLedger()
    led.add(items)
    led.approve(items[0]["item_id"], by="reviewer（占位）", at=NOW)
    led.reject(items[1]["item_id"], by="reviewer（占位）", at=NOW,
               reason="不收（占位）")
    return items, led


class TestFullCycleDrill(unittest.TestCase):
    def test_cycle_deterministic_twice(self):
        """全链周期（收→批→拒）两遍：条目/events/状态逐字节一致。"""
        items1, led1 = _fresh_cycle()
        items2, led2 = _fresh_cycle()
        self.assertEqual(json.dumps(items1, sort_keys=True),
                         json.dumps(items2, sort_keys=True))
        self.assertEqual(json.dumps(led1.events, sort_keys=True),
                         json.dumps(led2.events, sort_keys=True))
        states = [it["state"] for it in led1.view()]
        self.assertEqual(sorted(states), ["approved", "rejected"])

    def test_reject_trace_and_zero_listing_keys(self):
        """拒也留痕；批/拒返回值零上架/skillpack 变更键（R1 行为复验）。"""
        items, led = _fresh_cycle()
        rejected = next(it for it in led.view()
                        if it["item_id"] == items[1]["item_id"])
        self.assertEqual(rejected["reject_reason"], "不收（占位）")
        fresh = InboxLedger()
        fresh.add(collect(security_reviews=SECURITY, edge_cases=EDGE,
                          at=NOW))
        approved = fresh.approve(items[0]["item_id"], by="reviewer（占位）",
                                 at=NOW)
        for key in ("installed", "published", "skillpack_changed"):
            self.assertNotIn(key, approved)


class TestFailureDrills(unittest.TestCase):
    def test_double_decide_visible(self):
        """重复裁决演练：INBOX_DOUBLE_DECIDE 显形拒绝。"""
        items, led = _fresh_cycle()
        with self.assertRaisesRegex(InboxError, "INBOX_DOUBLE_DECIDE"):
            led.approve(items[0]["item_id"], by="reviewer（占位）", at=NOW)

    def test_auto_exec_payload_rejected(self):
        """AUTO_EXEC 演练：install 载荷 → INBOX_AUTO_EXEC_ATTEMPT 显形
        拒绝（零上架写——上架动作走既有发布流程）。"""
        items, led = _fresh_cycle()
        with self.assertRaisesRegex(InboxError, "INBOX_AUTO_EXEC_ATTEMPT"):
            led.approve(items[1]["item_id"], by="reviewer（占位）", at=NOW,
                        payload={"install": True})

    def test_ledger_append_only_through_drills(self):
        """账本 append-only：全演练流程后 events 只增不删。"""
        _, led1 = _fresh_cycle()
        n0 = len(led1.events)
        items2, led2 = _fresh_cycle()
        try:
            led2.approve(items2[0]["item_id"], by="reviewer（占位）", at=NOW)
        except InboxError:
            pass   # 重复裁决被拒——events 不增
        self.assertEqual(len(led2.events), n0)


class TestChainRerun(unittest.TestCase):
    def test_t2_t3_t4_rerun_green(self):
        """链复跑：T2/T3/T4 测试子进程复跑 exit 0（链上仍绿实测）。"""
        for test_file in ("test_prd363_t2_listing_inbox.py",
                          "test_prd363_t3_listing_inbox_gates.py",
                          "test_prd363_t4_listing_inbox_boundary.py"):
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q",
                 str(Path(__file__).resolve().parent / test_file)],
                capture_output=True, timeout=300)
            self.assertEqual(proc.returncode, 0,
                             f"{test_file} 复跑失败：{proc.stdout[-400:]}")


class TestDocNoSecrets(unittest.TestCase):
    def test_t1_design_doc_no_secrets(self):
        """文档无密钥：T1 设计文档拼接 needle 扫描+占位符纪律。"""
        repo = Path(__file__).resolve().parents[1]
        doc = next(repo.glob("docs/plans/2026-11-11-prd-363-*.md"))
        text = doc.read_text(encoding="utf-8").lower()
        for needle in ("sk-" + "live", "passw" + "ord", "api_k" + "ey"):
            self.assertNotIn(needle, text, f"设计文档出现密钥词 {needle}")
        self.assertIn("占位", text)


if __name__ == "__main__":
    unittest.main()
