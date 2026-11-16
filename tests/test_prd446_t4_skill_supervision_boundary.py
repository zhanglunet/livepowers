# -*- coding: utf-8 -*-
"""PRD-446/T4 测试（trend #2153 的 T4 环节）：skill 生成监督台划界断言。
运行：uv run --with pytest python -m pytest tests/test_prd446_t4_skill_supervision_boundary.py -q
覆盖（T1 §3 非目标边界）：上架审批权零触碰（AST+源扫描钉值）+包成稿/安检验证/
收件箱零导入+借鉴词零出现+标准库-only+R1 出口拦截+R3 方法面封闭+AST 零网络。
零网络；全合成占位。
"""
import ast
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from skill_supervision_bench import (  # noqa: E402
    SkillSupervisionSession, SupervisionLedger)
from skill_supervision_gate import approve_via_gate  # noqa: E402

NOW = "2026-11-15T09:00:00Z"
MODULES = ["skill_supervision_bench.py", "skill_supervision_gate.py"]


def _imports_of(path: Path) -> set:
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    return imported


def _code_names(path: Path) -> set:
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


class TestBoundary(unittest.TestCase):
    def test_approval_authority_untouched(self):
        """上架审批权零触碰：监督台模块无上架裁决函数（AST 定义扫描）。"""
        scripts = Path(__file__).resolve().parents[1] / "scripts"
        for mod in MODULES:
            tree = ast.parse((scripts / mod).read_text(encoding="utf-8"))
            funcs = {n.name.lower() for n in ast.walk(tree)
                     if isinstance(node_funcs := n, (ast.FunctionDef,
                                                     ast.AsyncFunctionDef))}
            for banned in ("approve_package", "reject_package",
                           "approve_listing", "reject_listing"):
                self.assertNotIn(banned, funcs, f"{mod} 定义 {banned}")

    def test_no_downstream_imports(self):
        """包成稿（PRD-423 评审流水线）/安检验证（PRD-377）/收件箱（PRD-363）
        零导入——监督台只做生成过程监督。"""
        scripts = Path(__file__).resolve().parents[1] / "scripts"
        for mod in MODULES:
            imported = _imports_of(scripts / mod)
            for banned in ("skill_review_pipeline", "plugin_verify_bench",
                           "skill_inbox", "collab_session"):
                self.assertNotIn(banned, imported, f"{mod} 导入 {banned}")

    def test_borrowed_zero_symbols(self):
        """借鉴仓（plannotator/ag-ui，Apache-2.0/MIT 实测）零符号——只借形态。"""
        scripts = Path(__file__).resolve().parents[1] / "scripts"
        for mod in MODULES:
            names = {n.lower() for n in _code_names(scripts / mod)}
            for word in ("plannotator", "ag_ui"):
                self.assertNotIn(word, names, f"{mod} 出现 {word}")

    def test_stdlib_only_and_ast_redline(self):
        """标准库-only+零网络零子进程 AST。"""
        scripts = Path(__file__).resolve().parents[1] / "scripts"
        allowed = {"__future__", "copy", "json", "pathlib", "typing"}
        for mod in MODULES:
            imported = _imports_of(scripts / mod)
            self.assertLessEqual(imported - allowed, set(), mod)
            self.assertFalse(imported & {"urllib", "requests", "socket",
                                         "http", "subprocess"}, mod)


class TestBehaviorPins(unittest.TestCase):
    def test_r1_unapproved_blocked(self):
        s = SkillSupervisionSession(task_ref="t（占位）", created_at=NOW)
        s.add_step(seq=1, name="x（占位）", status="待复核")
        s.add_version(version="v1", package_ref="p（占位）")
        out = s.outlet([{"version": "v1"}])
        self.assertEqual(out["passed"], [])

    def test_gate_overrides_status_bit(self):
        """闸门不信手写 status 位：raw records 决定放行（T3 行为钉值）。"""
        s = SkillSupervisionSession(task_ref="t（占位）", created_at=NOW)
        s.add_step(seq=1, name="x（占位）", status="待复核")
        s.add_version(version="v1", package_ref="p（占位）")
        s.versions[0]["status"] = "已点头"   # 手写 status 位
        out = approve_via_gate(s, [{"version": "v1"}])
        self.assertEqual(out["passed"], [])

    def test_r3_ledger_surface_closed(self):
        led = SupervisionLedger(None)
        methods = {n for n in dir(led) if not n.startswith("_")}
        self.assertLessEqual(methods, {"record", "entries"}, methods)

    def test_attribution_required_everywhere(self):
        """留痕红线：批注/发回/裁决缺作者或时间一律拒绝。"""
        s = SkillSupervisionSession(task_ref="t（占位）", created_at=NOW)
        s.add_step(seq=1, name="x（占位）", status="待复核")
        s.add_version(version="v1", package_ref="p（占位）")
        from skill_supervision_bench import SupervisionError
        with self.assertRaisesRegex(SupervisionError, "SUPERVISION_INCOMPLETE"):
            s.annotate(author="甲（占位）", at="", seq=1, text="x（占位）")
        with self.assertRaisesRegex(SupervisionError, "SUPERVISION_INCOMPLETE"):
            s.approve(approver="乙（占位）", at="", version="v1")


if __name__ == "__main__":
    unittest.main()
