# -*- coding: utf-8 -*-
"""PRD-293/T3 测试（trend #1468）：失败报错闸门——引用方 fail-closed 装载。

运行：python3 -m unittest tests.test_prd293_t3_failclosed -v（仓库根执行）

覆盖（T1 设计 §5/§6，验收「解析不到报错不降级/失败闸门有测试」）：
  ① fail-closed 装载：引用缺失 → 引用方整体不可用（无半成品）；② 环 →
  装载失败显形；③ 全 resolved → 契约包齐备；④ x-references 双载体同源
  机判（漂移显形）；⑤ 错误码封闭穷举；⑥ 零正文通道复核。
零网络；全合成占位。
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from skill_load_gate import (  # noqa: E402
    ERROR_CODES,
    load_with_references,
    x_references_consistency,
)

REGISTRY = {
    "packs": [{
        "name": "livepowers-fixture",
        "skills": [
            {"name": "base-skill（占位）",
             "triggers": "Use when 基础流程（占位）。",
             "examples": ["产出：基础记录（占位）"],
             "x-references": ["@dep-skill（占位）"]},
            {"name": "dep-skill（占位）",
             "triggers": "Use when 依赖步骤（占位）。",
             "examples": ["产出：依赖记录（占位）"]},
            {"name": "broken-skill（占位）",
             "triggers": "Use when 坏引用（占位）。",
             "examples": [],
             "x-references": ["@不存在（占位）"]},
            {"name": "cyclic-skill（占位）",
             "triggers": "Use when 环（占位）。",
             "examples": [],
             "x-references": ["@base-skill（占位）"]},
            {"name": "selfref-skill（占位）",
             "triggers": "Use when 自引用（占位）。",
             "examples": [],
             "x-references": ["@selfref-skill（占位）"]},
            {"name": "loop-a（占位）",
             "triggers": "Use when 环A（占位）。",
             "examples": [],
             "x-references": ["@loop-b（占位）"]},
            {"name": "loop-b（占位）",
             "triggers": "Use when 环B（占位）。",
             "examples": [],
             "x-references": ["@loop-a（占位）"]},
        ],
    }],
}


class FailClosed装载Tests(unittest.TestCase):
    def test_all_resolved_contract_pack_complete(self):
        out = load_with_references("base-skill（占位）", REGISTRY)
        self.assertTrue(out["usable"])
        self.assertIn("base-skill（占位）", out["contracts"])
        self.assertIn("dep-skill（占位）", out["contracts"])
        self.assertTrue(out["contracts"]["dep-skill（占位）"]["trigger_conditions"])

    def test_missing_reference_whole_skill_unusable(self):
        """R2 fail-closed：坏引用 → 引用方整体不可用，无半成品。"""
        out = load_with_references("broken-skill（占位）", REGISTRY)
        self.assertFalse(out["usable"])
        self.assertEqual(out["failures"][0]["error_code"], "REF_NOT_FOUND")
        self.assertNotIn("contracts", out)                     # 不产出部分可用产物

    def test_cycle_fails_load_with_trace(self):
        """环：loop-a→loop-b→loop-a（声明图成环）→ 装载失败显形。"""
        out = load_with_references("loop-a（占位）", REGISTRY)
        self.assertFalse(out["usable"])
        self.assertEqual(out["failures"][0]["error_code"], "REF_CYCLE")

    def test_self_reference_unusable(self):
        out = load_with_references("selfref-skill（占位）", REGISTRY)
        self.assertFalse(out["usable"])
        self.assertEqual(out["failures"][0]["error_code"], "REF_CYCLE")


class 双载体同源Tests(unittest.TestCase):
    def test_consistent_declared_vs_resolved(self):
        records = [{"from_skill": "base-skill（占位）", "to_skill": "dep-skill（占位）",
                    "status": "resolved"}]
        entry = REGISTRY["packs"][0]["skills"][0]
        out = x_references_consistency(entry, records)
        self.assertTrue(out["consistent"])

    def test_drift_surfaces(self):
        records = []                                            # 声明了但没解析成功
        entry = REGISTRY["packs"][0]["skills"][0]
        out = x_references_consistency(entry, records)
        self.assertFalse(out["consistent"])
        self.assertEqual(out["declared_only"], ["dep-skill（占位）"])


class 词表封闭Tests(unittest.TestCase):
    def test_error_codes_exhaustive(self):
        self.assertEqual(sorted(ERROR_CODES),
                         ["REF_CYCLE", "REF_NOT_FOUND", "REF_REGISTRY_CORRUPT",
                          "REF_SELF_LOOP", "REF_SYNTAX_ERROR"])

    def test_zero_body_channel(self):
        """产物零正文通道复核（T4 断言面预演）。"""
        out = load_with_references("base-skill（占位）", REGISTRY)
        blob = str(out["contracts"])
        self.assertNotIn("正文", blob)


if __name__ == "__main__":
    unittest.main()
