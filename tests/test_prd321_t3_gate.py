# -*- coding: utf-8 -*-
"""PRD-321/T3 实战验证叙事闸门测试（trend #650 区段）。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from battle_narrative import generate_narrative
from battle_narrative_gate import narrative_gate, verify_narrative


class GateTests(unittest.TestCase):
    def test_real_t2_output_passes(self):
        n = generate_narrative("livepowers-core", "六仓实测（占位场景）", ["tests/test_a.py", "tests/test_b.py"])
        out = narrative_gate(n)
        self.assertTrue(out["allow"], str(out))

    def test_no_evidence_refused(self):
        n = generate_narrative("s", "sc", [])
        out = narrative_gate(n)
        self.assertFalse(out["allow"])
        self.assertTrue(any("无证据不发布" in e for e in out["evidence"]))

    def test_bad_install_refused(self):
        n = generate_narrative("s", "sc", ["tests/x.py"])
        n["install_command"] = "pip install s"
        out = narrative_gate(n)
        self.assertFalse(out["allow"])
        self.assertTrue(any("install_command" in e for e in out["evidence"]))

    def test_verification_not_tests_refused(self):
        n = generate_narrative("s", "sc", ["tests/x.py"])
        n["verification"] = "口头验证"
        out = narrative_gate(n)
        self.assertFalse(out["allow"])
        self.assertTrue(any("tests/" in e for e in out["evidence"]))

    def test_empty_fields_refused(self):
        n = generate_narrative("", "", [])
        out = narrative_gate(n)
        self.assertFalse(out["allow"])
        self.assertGreaterEqual(len(out["evidence"]), 2)

    def test_gate_pure_deterministic(self):
        n = generate_narrative("k", "s", ["tests/t.py"])
        self.assertEqual(narrative_gate(n), narrative_gate(n))


if __name__ == "__main__":
    unittest.main()
