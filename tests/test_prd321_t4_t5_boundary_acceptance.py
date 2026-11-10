# -*- coding: utf-8 -*-
"""PRD-321/T4+T5：叙事闸门划界断言 + 验收试运行（trend #650 区段）。

T4 划界：battle_narrative/battle_narrative_gate 零网络形态（无 requests/
urllib/socket/http）+ 零写盘调用形态（AST import 白名单）+ 闸门拒绝零副作用
（入参 deepcopy 不变）。
T5 验收：真实 T2 生成 → 闸门三场景（正常叙事/无证据拒/install 形态改写拒）
各两遍逐字段一致（可重放口径）。
"""
from __future__ import annotations
import ast
import copy
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from battle_narrative import generate_narrative
from battle_narrative_gate import narrative_gate, verify_narrative


class T4BoundaryTests(unittest.TestCase):
    def test_ast_import_stdlib_only(self):
        for mod in ("battle_narrative.py", "battle_narrative_gate.py"):
            tree = ast.parse((REPO / "scripts" / mod).read_text(encoding="utf-8"))
            roots = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    roots |= {a.name.split(".")[0] for a in node.names}
                elif isinstance(node, ast.ImportFrom) and node.module:
                    roots.add(node.module.split(".")[0])
            for bad in ("requests", "urllib", "socket", "http"):
                self.assertNotIn(bad, roots, f"{mod} 越界网络导入：{bad}")

    def test_gate_refusal_zero_side_effect(self):
        n = generate_narrative("s", "sc", [])
        frozen = copy.deepcopy(n)
        out = narrative_gate(n)
        self.assertFalse(out["allow"])
        self.assertEqual(n, frozen, "拒绝路径不得改入参")


class T5AcceptanceTests(unittest.TestCase):
    def _chain(self, skill, scenario, evidence):
        n = generate_narrative(skill, scenario, evidence)
        return {"narrative": n, "gate": narrative_gate(n)}

    def test_normal_narrative_replay_identical(self):
        out1 = self._chain("livepowers-core", "六仓实测（占位场景）",
                           ["tests/test_a.py", "tests/test_b.py"])
        out2 = self._chain("livepowers-core", "六仓实测（占位场景）",
                           ["tests/test_a.py", "tests/test_b.py"])
        self.assertEqual(out1, out2)
        self.assertTrue(out1["gate"]["allow"])

    def test_no_evidence_refused_replay_identical(self):
        def run():
            return self._chain("s", "sc", [])
        self.assertEqual(run(), run())
        self.assertFalse(run()["gate"]["allow"])
        self.assertTrue(any("无证据不发布" in e for e in run()["gate"]["evidence"]))

    def test_install_tampered_refused_replay_identical(self):
        def run():
            n = generate_narrative("s", "sc", ["tests/x.py"])
            n["install_command"] = "pip install s"
            return narrative_gate(n)
        self.assertEqual(run(), run())
        self.assertFalse(run()["allow"])
        self.assertTrue(any("install_command" in e for e in run()["evidence"]))


if __name__ == "__main__":
    unittest.main()
