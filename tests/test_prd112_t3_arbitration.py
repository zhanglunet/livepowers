# -*- coding: utf-8 -*-
"""PRD-112/T3 汇总仲裁规则测试（trend #561）。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from parallel_arbitration import arbitrate, validate_expert_list, ERROR_CODES  # noqa: E402

EXPERTS = [
    {"id": "content", "when": "always", "modules": ["headings", "links"]},
    {"id": "meta", "when": "always", "modules": ["title"]},
    {"id": "media", "when": "{has_images}", "modules": ["images"]},
]
OUTPUTS = {
    "content": [{"module": "headings", "verdict": "ok"}, {"module": "links", "verdict": "warn"}],
    "meta": [{"module": "title", "verdict": "ok"}],
    "media": [{"module": "images", "verdict": "ok"}],
}


class ArbitrationTests(unittest.TestCase):

    def test_always_experts_adopted(self):
        result = arbitrate(EXPERTS[:2], {"content": OUTPUTS["content"],
                                         "meta": OUTPUTS["meta"]})
        self.assertEqual(len(result["adopted"]), 3)
        self.assertFalse(result["no_input"])
        self.assertEqual(len(result["suppressed"]), 0)

    def test_conditional_false_skipped_not_conflict(self):
        result = arbitrate(EXPERTS, OUTPUTS, conditions={"media": False})
        modules = [a["module"] for a in result["adopted"]]
        self.assertNotIn("images", modules)
        self.assertEqual(len(result["suppressed"]), 0)  # skipped ≠ conflict

    def test_conditional_true_adopted(self):
        result = arbitrate(EXPERTS, OUTPUTS, conditions={"media": True})
        modules = [a["module"] for a in result["adopted"]]
        self.assertIn("images", modules)

    def test_module_overlap_first_alphabetical_wins_rest_suppressed(self):
        experts = [
            {"id": "b-team", "when": "always", "modules": ["headings"]},
            {"id": "a-team", "when": "always", "modules": ["headings"]},
        ]
        outputs = {"b-team": [{"module": "headings", "verdict": "b"}],
                   "a-team": [{"module": "headings", "verdict": "a"}]}
        result = arbitrate(experts, outputs)
        self.assertEqual(len(result["adopted"]), 1)
        self.assertEqual(result["adopted"][0]["expert_id"], "b-team")  # 首个（遍历序）
        self.assertEqual(len(result["suppressed"]), 1)
        self.assertEqual(result["suppressed"][0]["suppressed"][0] if "suppressed" in result["suppressed"][0] else result["suppressed"][0]["expert_id"], "a-team")

    def test_empty_output_no_input_flag(self):
        result = arbitrate(EXPERTS, {})
        self.assertTrue(result["no_input"])
        self.assertEqual(len(result["adopted"]), 0)

    def test_validate_expert_list(self):
        self.assertEqual(validate_expert_list(EXPERTS), [])
        bad = [{"id": "", "when": "sometimes", "modules": []}]
        errors = validate_expert_list(bad)
        self.assertEqual(len(errors), 3)  # 缺 id + when 非法 + modules 空

    def test_closed_error_codes(self):
        self.assertEqual(len(set(ERROR_CODES)), len(ERROR_CODES))


if __name__ == "__main__":
    unittest.main()
