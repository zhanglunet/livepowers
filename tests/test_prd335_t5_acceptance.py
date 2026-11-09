# -*- coding: utf-8 -*-
"""PRD-335/T5 测试（trend #1614 的 T5 环节）：生成式 UI 验收试运行。

运行：python3 -m unittest tests.test_prd335_t5_acceptance -v（仓库根执行）

覆盖（T1 §5 验收「样例树全链回放（含非法属性演练）+ 文档无密钥」）：
① 样例树全链回放——配置页样例树（五类组件全覆盖）→ tree_gate → 产物
  渲染（预览即最终同一函数）；回放可复现逐字节一致；
② 非法属性演练——白名单外属性丢弃 dropped[] 显形 / 类型词表外整节点剔除
  占位显形 / 枚举越界回退默认 / 深度越限整树拒绝零渲染——四路演练全显形；
③ 文档无密钥——T1 设计文档（T1 分支）零密钥/零 IP/外链仅 github 与
  example 域。
零网络；全合成占位。
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from genui import render, validate_tree  # noqa: E402
from genui_gate import review_digest, tree_gate  # noqa: E402

CLEAN = {"type": "分组框", "props": {"title": "配置页（占位）"}, "children": [
    {"type": "文本标签", "props": {"text": "标题（占位）", "size": "大"},
     "children": []},
    {"type": "字段行", "props": {"label": "名称", "value": "示例（占位）"},
     "children": []},
    {"type": "分隔线", "props": {}, "children": []},
    {"type": "提示条", "props": {"tone": "警告", "text": "只读预览（占位）"},
     "children": []},
]}
_FIELD = CLEAN["children"][1]
LEAKY = dict(CLEAN, children=[dict(_FIELD, props=dict(_FIELD["props"],
                                                      hack_attr="越权属性（占位）"))])
BADTYPE = {"type": "月球控件", "props": {}, "children": []}


class TestFullReplay(unittest.TestCase):
    def test_five_component_kinds_full_chain(self):
        """① 样例树（五类组件全覆盖）全链回放 OK，预览即最终。"""
        out = tree_gate(CLEAN)
        self.assertEqual(out["gate"], "OK")
        blob = "\n".join(out["lines"])
        for token in ("配置页（占位）", "标题（占位）", "名称：示例（占位）",
                      "-", "⚠ 只读预览（占位）"):
            self.assertIn(token, blob)
        self.assertEqual(out["lines"], render(validate_tree(CLEAN)["clean_tree"]))

    def test_replay_reproducible(self):
        """① 回放可复现：同树重放逐字节一致。"""
        self.assertEqual(tree_gate(CLEAN), tree_gate(CLEAN))


class TestIllegalPropDrill(unittest.TestCase):
    def test_extra_prop_dropped_visible(self):
        """② 白名单外属性 → 丢弃 + dropped[] 显形 + 产物无该值（零静默）。"""
        out = tree_gate(LEAKY)
        self.assertEqual(out["gate"], "DROPPED_PROPS")
        self.assertTrue(out["needs_review"])
        self.assertNotIn("越权属性", "\n".join(out["lines"]))
        self.assertTrue(any("hack_attr" in l for l in review_digest(out)))

    def test_unknown_type_rejected_with_placeholder(self):
        """② 类型词表外 → 整节点剔除占位显形。"""
        tree = dict(CLEAN, children=[BADTYPE])
        out = tree_gate(tree)
        self.assertEqual(out["gate"], "REJECTED_NODES")
        self.assertIn("[未知类型已剔除]", "\n".join(out["lines"]))

    def test_enum_overflow_falls_back(self):
        """② 枚举越界 → 回退默认 + dropped 记录显形。"""
        tree = {"type": "文本标签", "props": {"text": "x（占位）",
                                             "size": "巨大"}, "children": []}
        out = tree_gate(tree)
        self.assertEqual(out["dropped"][0]["reason"], "枚举越界回退默认：'巨大'")
        self.assertIn("x（占位）", "\n".join(out["lines"]))

    def test_depth_overflow_tree_rejected_zero_render(self):
        """② 深度越限 → TreeRejected 整树拒绝零渲染（演练第 4 路）。"""
        node = {"type": "文本标签", "props": {"text": "x"}, "children": []}
        deep = node
        for _ in range(8):
            deep = {"type": "分组框", "props": {"title": "层（占位）"},
                    "children": [deep]}
        out = tree_gate(deep)
        self.assertEqual(out["gate"], "TREE_REJECTED")
        self.assertEqual(out["lines"], [])


class TestDocNoSecrets(unittest.TestCase):
    def test_design_doc_no_secrets(self):
        """③ 文档无密钥：T1 设计文档（T1 分支）零密钥/零 IP/外链仅
        github 与 example 域。"""
        doc = subprocess.run(
            ["git", "show", "trend/prd-335-t1-genui-design:docs/plans/"
             "2026-11-09-prd-335-genui-design.md"],
            capture_output=True, text=True, check=True).stdout
        for token in ("password", "secret", "api_key", "AKIA", "Bearer ",
                      "BEGIN RSA"):
            self.assertNotIn(token.lower(), doc.lower(), token)
        self.assertEqual(re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", doc), [])
        for m in re.findall(r"https?://[^\s）)】]+", doc):
            self.assertTrue(any(ok in m for ok in
                                ("github.com", "example.invalid",
                                 "example.com")), m)


if __name__ == "__main__":
    unittest.main()
