# -*- coding: utf-8 -*-
"""PRD-335/T3 测试（trend #1614 的 T3 环节）：生成式 UI 丢弃闸门。

运行：python3 -m unittest tests.test_prd335_t3_genui_gate -v（仓库根执行）

覆盖（T1 设计 §3.3/R1）：GATE_CODES 词表封闭；干净树 OK 零丢弃；白名单外
属性 → DROPPED_PROPS 且 dropped[] 随产物输出（R1 丢弃显形不静默）；类型词
表外/必填缺失 → REJECTED_NODES 剔除占位显形；深度越限 TreeRejected →
TREE_REJECTED 整树拒绝零渲染；review_digest 逐行显形（零静默）；与 T2 串联
（render 同一函数预览即最终/确定性）；AST 零网络零事件脚本继承。零网络；
全合成占位。
"""
import ast
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from genui import render, validate_tree  # noqa: E402
from genui_gate import (  # noqa: E402
    GATE_CODES,
    review_digest,
    tree_gate,
)

CLEAN = {"type": "分组框", "props": {"title": "配置页（占位）"}, "children": [
    {"type": "字段行", "props": {"label": "名称", "value": "示例（占位）"},
     "children": []},
    {"type": "提示条", "props": {"tone": "提示", "text": "只读预览（占位）"},
     "children": []},
]}
LEAKY = {"type": "分组框", "props": {"title": "配置页（占位）",
                                     "hack_attr": "越权属性（占位）"}, "children": []}
BADTYPE = {"type": "月球控件", "props": {}, "children": []}
MISSING = {"type": "字段行", "props": {"value": "无标签（占位）"}, "children": []}


class TestGateCodes(unittest.TestCase):
    def test_closed_vocabulary(self):
        self.assertEqual(set(GATE_CODES),
                         {"OK", "DROPPED_PROPS", "REJECTED_NODES",
                          "TREE_REJECTED"})

    def test_clean_tree_ok(self):
        out = tree_gate(CLEAN)
        self.assertEqual(out["gate"], "OK")
        self.assertFalse(out["needs_review"])
        self.assertEqual(out["dropped"], [])
        self.assertTrue(out["lines"])          # 渲染产物非空
        self.assertEqual(out["schema"], "genui-product/v1")


class TestDroppedVisible(unittest.TestCase):
    def test_extra_prop_dropped_and_manifest_emitted(self):
        """R1：白名单外属性丢弃且 dropped[] 随产物输出——不静默。"""
        out = tree_gate(LEAKY)
        self.assertEqual(out["gate"], "DROPPED_PROPS")
        self.assertTrue(out["needs_review"])
        self.assertEqual(out["dropped"][0]["prop"], "hack_attr")
        self.assertNotIn("越权属性", "\n".join(out["lines"]))   # 产物无该属性
        self.assertTrue(any("hack_attr" in l for l in review_digest(out)))

    def test_rejected_node_replaced_and_visible(self):
        out = tree_gate(BADTYPE)
        self.assertEqual(out["gate"], "REJECTED_NODES")
        self.assertTrue(out["needs_review"])
        self.assertEqual(out["rejected_nodes"][0]["reason"], "类型词表外：'月球控件'（R2 封闭词表）")
        self.assertIn("[未知类型已剔除]", "\n".join(out["lines"]))

    def test_missing_required_rejected(self):
        out = tree_gate(MISSING)
        self.assertEqual(out["gate"], "REJECTED_NODES")
        self.assertTrue(any("必填属性 label 缺失" in r["reason"]
                            for r in out["rejected_nodes"]))

    def test_mixed_drop_and_reject_prefers_reject(self):
        tree = dict(LEAKY, children=[BADTYPE])
        out = tree_gate(tree)
        self.assertEqual(out["gate"], "REJECTED_NODES")
        self.assertTrue(out["dropped"])        # 两者都显形，判定取更重者


class TestTreeRejected(unittest.TestCase):
    def test_depth_overflow_blocked_zero_render(self):
        node = {"type": "文本标签", "props": {"text": "x"}, "children": []}
        deep = node
        for _ in range(8):
            deep = {"type": "分组框", "props": {"title": "层（占位）"},
                    "children": [deep]}
        out = tree_gate(deep)
        self.assertEqual(out["gate"], "TREE_REJECTED")
        self.assertEqual(out["lines"], [])     # 整树拒绝零渲染
        self.assertTrue(out["code_detail"]["code"] in ("DEPTH_LIMIT",
                                                       "NODE_LIMIT"))
        self.assertTrue(any("整树拒绝" in l for l in review_digest(out)))


class TestChainWithT2(unittest.TestCase):
    def test_render_is_same_function_as_t2(self):
        """与 T2 串联：闸门渲染 = validate_tree + render 同一函数（R3）。"""
        out = tree_gate(CLEAN)
        expect = render(validate_tree(CLEAN)["clean_tree"])
        self.assertEqual(out["lines"], expect)

    def test_deterministic_product(self):
        self.assertEqual(tree_gate(LEAKY), tree_gate(LEAKY))


class TestRedline(unittest.TestCase):
    def test_gate_module_zero_network_zero_events(self):
        banned = {"urllib", "requests", "socket", "http", "subprocess"}
        src = (REPO / "scripts" / "genui_gate.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module.split(".")[0]]
            for mod in mods:
                self.assertNotIn(mod, banned)
        for token in ("onclick", "<script", "javascript:", "eval("):
            self.assertNotIn(token, src)


if __name__ == "__main__":
    unittest.main()
