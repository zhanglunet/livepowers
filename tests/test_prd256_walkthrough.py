# -*- coding: utf-8 -*-
"""PRD-256/T3 自测（trend #1282）：example-walkthrough.md 三角色编排示范可校验。

运行：python3 -m unittest test_prd256_walkthrough -v（在 tests/ 目录执行）

覆盖：
  从 walkthrough 提取全部内联合同（json 围栏块）逐个过 handoff.schema.json 校验
  三角色派发齐全，最终 result 全部 done（示范可跑通）
  含一次 rejected 流转（verify 打回）且闭环（重派后复验 done）
  重派合同新 task_id 引用原 task_id（retries 字段 + notes 均留痕，原 task_id 在示范内）
  主会话汇总节存在且对照三份合同 result

虚构纪律：示范内容全虚构；不含真实主机名、账号、密钥。
"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_handoff as vh  # noqa: E402

TEMPLATE = ROOT / "templates" / "pi-subagents"
WALKTHROUGH = TEMPLATE / "example-walkthrough.md"
SCHEMA = TEMPLATE / "handoff.schema.json"


def load_contracts():
    """从 walkthrough.md 提取全部内联合同（json 围栏块，按文档顺序）。"""
    text = WALKTHROUGH.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)```", text, re.S)
    return text, [json.loads(b) for b in blocks]


class TestWalkthroughContracts(unittest.TestCase):
    def setUp(self):
        self.text, self.contracts = load_contracts()
        self.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def test_all_inline_contracts_pass_schema(self):
        """全部内联合同（json 围栏块）逐个过 handoff.schema.json 校验。"""
        self.assertGreaterEqual(len(self.contracts), 5,
                                "示范内联合同应至少 5 份（探索/实现×2/验证×2）")
        for i, c in enumerate(self.contracts):
            self.assertEqual(c.get("schema"), "handoff-v1", f"合同 #{i} schema 头")
            self.assertEqual(vh.builtin_validate(c, self.schema), [],
                             f"合同 #{i} {c.get('task_id')} 未过 schema")

    def test_three_roles_covered_and_final_done(self):
        """三角色派发齐全；每角色最终合同 result 均为 done（示范可跑通）。"""
        finals = {}
        for c in self.contracts:
            finals[c["to"]] = c  # 文档顺序在后即最终
        for role in ("explore", "implement", "verify"):
            self.assertIn(role, finals, f"缺 {role} 派发合同")
            self.assertEqual(finals[role].get("result", {}).get("status"), "done",
                             f"{role} 最终合同未 done")

    def test_rejected_flow_present_and_closed(self):
        """含一次 verify 打回（rejected），且重派复验后闭环 done。"""
        rejected = [c for c in self.contracts
                    if c.get("result", {}).get("status") == "rejected"]
        self.assertGreaterEqual(len(rejected), 1, "示范应含至少一次 rejected 流转")
        r = rejected[0]
        self.assertEqual(r["to"], "verify", "打回应由 verify 角色给出")
        # 闭环：打回之后（文档顺序）存在同角色复验合同且 done
        idx = self.contracts.index(r)
        later_verify_done = [c for c in self.contracts[idx + 1:]
                             if c["to"] == "verify"
                             and c.get("result", {}).get("status") == "done"]
        self.assertTrue(later_verify_done, "verify 打回后应存在复验 done 的闭环")

    def test_retry_contract_references_original_task_id(self):
        """重派合同新 task_id 引用原 task_id：retries 字段留痕且原 task_id 在示范内。"""
        ids = {c["task_id"] for c in self.contracts}
        retries = [c for c in self.contracts if c.get("retries")]
        self.assertGreaterEqual(len(retries), 1, "应存在引用原 task_id 的重派合同")
        for c in retries:
            self.assertNotEqual(c["task_id"], c["retries"][0], "重派须为新 task_id")
            self.assertIn(c["retries"][0], ids,
                          f"{c['task_id']} 引用的原 task_id {c['retries'][0]} 不在示范内")
            self.assertIn(c["retries"][0], c.get("result", {}).get("notes", ""),
                          f"{c['task_id']} 的 notes 也应引用原 task_id")
        impl_retries = [c for c in retries if c["to"] == "implement"]
        self.assertTrue(impl_retries, "打回修复的重派应落在 implement（verify 不修代码）")

    def test_summary_section_exists_with_three_results(self):
        """主会话汇总节存在，且对照三份最终合同 result。"""
        self.assertIn("主会话汇总", self.text)
        section = self.text.split("主会话汇总", 1)[1]
        for tid in ("hb_explore_101", "hb_impl_102", "hb_verify_102"):
            self.assertIn(tid, section, f"汇总节应对照合同 {tid} 的 result")


if __name__ == "__main__":
    unittest.main()
