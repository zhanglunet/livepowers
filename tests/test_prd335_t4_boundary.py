# -*- coding: utf-8 -*-
"""PRD-335/T4 测试（trend #1614 的 T4 环节）：生成式 UI 同库+零执行断言。

运行：python3 -m unittest tests.test_prd335_t4_boundary -v（仓库根执行）

覆盖（T1 §0 R3/R4 + §2 划界）：R4 零执行语义（COMPONENT_VOCAB 全组件属性
白名单零事件属性 onclick/on* 零 URL 属性 src/href；渲染产物零 <script/
onclick/javascript:/eval 符号；模块 AST 零网络零子进程零 eval/exec）；R3
同库断言（genui_gate 渲染入口 is genui.render 同一函数对象——预览与最终
唯一入口；产物确定性复钉）；词表钉值（五类组件封闭 + 枚举钉值）；模块隔
离（genui 对零 genui_gate 反向依赖——闸门单向消费）。零网络；全合成占位。
"""
import ast
import copy
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import genui  # noqa: E402
import genui_gate  # noqa: E402
from genui import COMPONENT_VOCAB, render, validate_tree  # noqa: E402

TREE = {"type": "分组框", "props": {"title": "配置页（占位）"}, "children": [
    {"type": "字段行", "props": {"label": "名称", "value": "示例（占位）"},
     "children": []}]}


class TestZeroExecutionSemantics(unittest.TestCase):
    def test_vocab_no_event_no_url_props(self):
        """R4：全组件属性白名单零事件属性零 URL 属性。"""
        event_prefixes = ("on", "bind")
        url_props = {"src", "href", "action", "url", "link"}
        for comp, spec in COMPONENT_VOCAB.items():
            keys = set(spec["required"]) | set(spec["optional"])
            for key in keys:
                self.assertFalse(key.lower().startswith(event_prefixes),
                                 f"{comp} 属性 {key} 疑似事件属性")
                self.assertNotIn(key.lower(), url_props,
                                 f"{comp} 属性 {key} 是 URL 属性")

    def test_render_output_zero_scripts_zero_urls(self):
        """R4：渲染产物零 <script/onclick/javascript:。"""
        lines = render(validate_tree(TREE)["clean_tree"])
        blob = "\n".join(lines).lower()
        for token in ("<script", "onclick", "javascript:", "eval(", "http://",
                      "https://"):
            self.assertNotIn(token, blob)

    def test_modules_zero_network_zero_eval(self):
        """两模块 AST 零网络/零子进程/零 eval/exec（零执行语义）。"""
        banned = {"urllib", "requests", "socket", "http", "subprocess"}
        for name in ("genui.py", "genui_gate.py"):
            src = (REPO / "scripts" / name).read_text(encoding="utf-8")
            tree = ast.parse(src)
            for node in ast.walk(tree):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    mods = [node.module.split(".")[0]]
                for mod in mods:
                    self.assertNotIn(mod, banned, f"{name} 导入了 {mod}")
            low = src.lower()
            self.assertNotIn("eval(", low, name)
            self.assertNotIn("exec(", low, name)


class TestSameFunctionNail(unittest.TestCase):
    def test_gate_renders_via_same_function_object(self):
        """R3：genui_gate 的渲染入口 is genui.render——同一函数对象唯一入口。"""
        self.assertIs(genui_gate.render, genui.render)

    def test_preview_equals_final_deterministic(self):
        """R3 行为复钉：预览与最终同函数——同树同输出逐字节一致。"""
        clean = validate_tree(TREE)["clean_tree"]
        self.assertEqual(render(clean), render(clean))
        product = genui_gate.tree_gate(TREE)
        self.assertEqual(product["lines"], render(clean))


class TestVocabNailAndIsolation(unittest.TestCase):
    def test_component_vocab_closed_five(self):
        """词表钉值：五类组件封闭（T1 §3.1）。"""
        self.assertEqual(set(COMPONENT_VOCAB),
                         {"文本标签", "字段行", "分组框", "分隔线", "提示条"})
        self.assertEqual(COMPONENT_VOCAB["文本标签"]["enums"]["size"],
                         ["标准", "大", "小"])
        self.assertEqual(COMPONENT_VOCAB["提示条"]["enums"]["tone"],
                         ["提示", "警告"])

    def test_genui_module_no_gate_dependency(self):
        """模块隔离：genui 零反向依赖 genui_gate（闸门单向消费）。"""
        src = (REPO / "scripts" / "genui.py").read_text(encoding="utf-8")
        self.assertNotIn("genui_gate", src)

    def test_tree_gate_readonly(self):
        """闸门只读：前后树原样（零变更）。"""
        before = copy.deepcopy(TREE)
        genui_gate.tree_gate(TREE)
        self.assertEqual(TREE, before)


if __name__ == "__main__":
    unittest.main()
