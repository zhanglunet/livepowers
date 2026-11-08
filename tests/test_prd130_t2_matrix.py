# -*- coding: utf-8 -*-
"""PRD-130/T2 多 harness 矩阵测试（trend #650）。"""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from harness_matrix import generate_matrix

class MatrixTests(unittest.TestCase):
    def test_generate_for_all_harnesses(self):
        result = generate_matrix("test-skill", "skills/using-livepowers")
        self.assertEqual(len(result["targets"]), 4)

if __name__ == "__main__":
    unittest.main()
