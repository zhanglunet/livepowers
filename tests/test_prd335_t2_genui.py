# -*- coding: utf-8 -*-
"""PRD-335/T2 测试（trend #1614 的 T2 环节）：生成式 UI 最小实现。

运行：python3 -m unittest tests.test_prd335_t2_genui -v（仓库根执行）

覆盖（T1 设计 §3.1/§3.2/§3.3/§4）：validate_tree 类型词表外整节点拒（R2）/
白名单外属性丢弃 dropped[] 显形 R1/必填缺失整节点拒/枚举越界回退默认/
深度与节点数上限整树拒/零执行语义（AST 红线：白名单不含事件脚本 URL）/
render 确定性同树同输出逐字节一致 R3/流式逐根拼接前缀不变。
零网络；全合成占位。
"""
import ast
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from genui import (  # noqa: E402
    COMPONENT_VOCAB,
    MAX_DEPTH,
    TreeRejected,
    render,
    render_roots,
    validate_tree,
)


def node(ntype, props=None, children=None):
    return {"type": ntype, "props": props or {}, "children": children or []}


class TestValidateTree(unittest.TestCase):
    def test_type_outside_vocab_whole_node_rejected(self):
        """R2：类型词表外整节点拒绝（模型不能发明组件）。"""
        out = validate_tree(node("超级图表（占位）", {"data": [1, 2]}))
        self.assertEqual(len(out["rejected_nodes"]), 1)
        self.assertIn("类型词表外", out["rejected_nodes"][0]["reason"])

    def test_unknown_prop_dropped_visible(self):
        """R1：白名单外属性丢弃+dropped[] 显形（不静默吞）。"""
        tree = node("字段行", {"label": "备注（占位）", "value": "v（占位）",
                               "onclick": "alert(1)"})
        out = validate_tree(tree)
        self.assertTrue(any(d["prop"] == "onclick" for d in out["dropped"]))
        # 丢弃后节点仍渲染（label/value 在）
        self.assertEqual(out["clean_tree"]["props"]["label"], "备注（占位）")

    def test_missing_required_whole_node_rejected(self):
        """必填属性被丢/缺失 → 整节点拒。"""
        out = validate_tree(node("字段行", {"label": "只有 label（占位）"}))
        self.assertEqual(len(out["rejected_nodes"]), 1)
        self.assertIn("必填", out["rejected_nodes"][0]["reason"])

    def test_enum_fallback_to_default(self):
        """枚举越界 → 回退默认+dropped 记录。"""
        out = validate_tree(node("文本标签", {"text": "t（占位）", "size": "巨大"}))
        self.assertEqual(out["clean_tree"]["props"]["size"], "标准")
        self.assertTrue(any(d["prop"] == "size" for d in out["dropped"]))

    def test_depth_and_node_limit_whole_tree_rejected(self):
        """超深/超节点数 → 整树拒绝（TreeRejected）。"""
        deep = node("分组框", {"title": "t（占位）"})
        cur = deep
        for _ in range(8):
            nxt = node("分组框", {"title": "t（占位）"})
            nxt["children"] = [cur]
            cur = nxt
        with self.assertRaises(TreeRejected):
            validate_tree(cur)


class TestRenderSameLibrary(unittest.TestCase):
    def test_preview_and_final_same_render(self):
        """R3：预览与最终同一渲染函数——同树同输出（逐字节一致）。"""
        tree = node("文本标签", {"text": "标题（占位）", "size": "大"})
        preview = render(tree)
        final = render(tree)
        self.assertEqual(preview, final)

    def test_streaming_prefix_stable(self):
        """流式喂入：逐子树渲染拼接，前缀不变。"""
        root = node("分组框", {"title": "组（占位）"},
                    [node("文本标签", {"text": "a（占位）"}),
                     node("文本标签", {"text": "b（占位）"})])
        full = render(root)
        root2 = node("分组框", {"title": "组（占位）"},
                     [node("文本标签", {"text": "a（占位）"})])
        prefix = render(root2)
        self.assertEqual(full[:len(prefix)], prefix)


class TestZeroExecution(unittest.TestCase):
    def test_ast_no_event_script_url_in_vocab(self):
        """R4：属性白名单零事件/脚本/URL（模型产出声明不产出代码）。"""
        src = ast.dump(ast.parse((REPO / "scripts" / "genui.py")
                                 .read_text(encoding="utf-8")))
        for token in ("onclick", "onsubmit", "<script", "javascript:", "href"):
            self.assertNotIn(token, src, f"词表含执行语义 {token}")

    def test_vocab_is_closed_five_types(self):
        self.assertEqual(set(COMPONENT_VOCAB),
                         {"文本标签", "字段行", "分组框", "分隔线", "提示条"})


if __name__ == "__main__":
    unittest.main()
