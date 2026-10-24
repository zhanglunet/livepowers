"""using-livepowers 的独立验收测试。L1/L3 纯文本可跑；L2 需 lp 环境则跳过。"""
import re
import unittest
from pathlib import Path

from helpers import find_livepowers_lp, run_lp

SKILL = Path(__file__).resolve().parents[2] / "skills" / "using-livepowers" / "SKILL.md"
TEXT = SKILL.read_text(encoding="utf-8")
LP = find_livepowers_lp()


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
    """L1：范式公式、七条铁律与路由表存在。"""

    def test_frontmatter_name_matches_dir(self):
        self.assertEqual(_frontmatter(TEXT).get("name"), "using-livepowers")

    def test_paradigm_formula(self):
        self.assertIn("Agentic AI = Agent + Ontology + Harness", TEXT)

    def test_seven_iron_rules(self):
        for rule in ["先检查技能", "先 System 1，后 System 2",
                     "没有证据的探索等于没发生", "不在本体之外操作",
                     "写操作必过安全门禁", "生成者不评审自己",
                     "没有基线的价值不算价值"]:
            self.assertIn(rule, TEXT, "七条铁律缺：%s" % rule)

    def test_routing_table_covers_all_skills(self):
        skills_root = Path(__file__).resolve().parents[2] / "skills"
        known = {p.name for p in skills_root.iterdir() if p.is_dir()}
        known.discard("using-livepowers")
        missing = [s for s in known if ("`%s`" % s) not in TEXT]
        self.assertEqual(missing, [], "路由表缺 skill：%s" % missing)


class Examples(unittest.TestCase):
    """L2：文档里的标准工作循环例子可复现（纯文本）。"""

    def test_standard_loop(self):
        self.assertIn("lp registry find", TEXT)
        self.assertIn("lp evidence add --system S1", TEXT)

    def test_cold_start_draft_version(self):
        self.assertIn("0.1.0-draft", TEXT)

    @unittest.skipIf(LP is None, "需 lp 真实环境")
    def test_registry_find_exit_codes(self):
        # 契约：退出码只能是 0=HIT / 2=MISS / 3=MAYBE HIT
        r = run_lp(LP, "registry", "find", "ci-smoke-nonexistent-intent-xyz")
        self.assertIn(r.returncode, (0, 2, 3))


class Negative(unittest.TestCase):
    """L3：反模式明确写出不能跳过技能的情形。"""

    def test_assumptions_are_not_orders(self):
        self.assertIn("不确定的想法是**假设**，不是指令", TEXT)

    def test_no_skip_for_simple(self):
        self.assertIn("不能用\"这次很简单\"跳过", TEXT)


if __name__ == "__main__":
    unittest.main()
