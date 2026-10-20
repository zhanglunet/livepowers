"""generalizing-skills 的独立验收测试。L1/L3 纯文本可跑；L2 需 lp 环境则跳过。"""
import re
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / "skills" / "generalizing-skills" / "SKILL.md"
TEXT = SKILL.read_text(encoding="utf-8")


def _frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "缺 frontmatter"
    fm = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if line and ":" in line and not line.startswith("#"):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm


class Contract(unittest.TestCase):
    """L1：三层拆分、本体契约、四组角色、规则模式与取值分开。"""

    def test_frontmatter_name_matches_dir(self):
        self.assertEqual(_frontmatter(TEXT).get("name"), "generalizing-skills")

    def test_three_layers(self):
        for layer in ["业务本体", "方法", "环境实例"]:
            self.assertIn(layer, TEXT)

    def test_rule_pattern_vs_value(self):
        self.assertIn("规则模式与规则取值必须分开", TEXT)

    def test_ontology_contract_references_not_copies(self):
        self.assertIn("ontology_contract:", TEXT)
        self.assertIn("ontology-evolution", TEXT)
        self.assertIn("只引用 + 摘要", TEXT)

    def test_four_role_groups(self):
        for group in ["**结构**", "**本体规则**", "**实例参数**", "**产物**"]:
            self.assertIn(group, TEXT)


class Examples(unittest.TestCase):
    """L2：初始化写绑定、复用前比对指纹、验收三条证据（纯文本）。"""

    def test_binding_has_fingerprint_and_confirmation(self):
        self.assertIn(".livepowers/bindings/<skill-name>.yaml", TEXT)
        for key in ["fingerprint:", "confirmed_by:", "confirmed_at:", "ontology: {name:"]:
            self.assertIn(key, TEXT)

    def test_reuse_compares_fingerprint(self):
        self.assertIn("--diff .livepowers/env/<skill-name>-fp.json", TEXT)
        self.assertIn("关键列出现新的取值", TEXT)

    def test_acceptance_needs_second_workspace(self):
        self.assertIn("第二个 workspace 跑通", TEXT)
        self.assertIn("acceptance-gates", TEXT)

    def test_should_we_generalize_gate(self):
        self.assertIn("第 0 步：值不值得泛化", TEXT)


class Negative(unittest.TestCase):
    """L3：反模式与红线写明不能做的事。"""

    def test_no_rules_in_binding(self):
        self.assertIn("把业务规则写进每个项目的配置", TEXT)

    def test_no_silent_inherit(self):
        self.assertIn("新项目默认继承上一个项目的阈值和状态映射", TEXT)

    def test_no_stale_binding_after_drift(self):
        self.assertIn("指纹漂移或本体版本越界时，不用旧绑定继续跑", TEXT)

    def test_description_has_no_project_nouns(self):
        desc = _frontmatter(TEXT).get("description", "")
        for word in ["华东", "订单月报", "D:\\"]:
            self.assertNotIn(word, desc)


if __name__ == "__main__":
    unittest.main()
