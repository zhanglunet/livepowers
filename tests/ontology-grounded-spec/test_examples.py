"""ontology-grounded-spec 的独立验收测试。L1/L3 纯文本可跑；L2 需 lp 环境则跳过。"""
import re
import unittest
from pathlib import Path

from helpers import find_livepowers_lp, run_lp

SKILL = Path(__file__).resolve().parents[2] / "skills" / "ontology-grounded-spec" / "SKILL.md"
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
    """L1：四步流程与规格要素存在。"""

    def test_frontmatter_name_matches_dir(self):
        self.assertEqual(_frontmatter(TEXT).get("name"), "ontology-grounded-spec")

    def test_four_steps_present(self):
        for step in ["苏格拉底式澄清", "判断变化落在哪一层", "写规格", "自检"]:
            self.assertIn(step, TEXT, "四步缺：%s" % step)

    def test_acceptance_sample_quota(self):
        self.assertIn("验收样例", TEXT)
        self.assertIn("≥3 正常 + 2 边界 + 1 错误", TEXT)

    def test_principle(self):
        self.assertIn("先本体、后代码", TEXT)


class Examples(unittest.TestCase):
    """L2：文档里的规格模板例子可复现（纯文本）。"""

    def test_spec_template_ref(self):
        self.assertIn("templates/spec.md", TEXT)

    def test_business_invariant_example(self):
        self.assertIn("审批未完成的合同不得生效", TEXT)

    @unittest.skipIf(LP is None, "需 lp 真实环境")
    def test_lp_task_move_help_runs(self):
        r = run_lp(LP, "task", "move", "--help")
        self.assertEqual(r.returncode, 0)


class Negative(unittest.TestCase):
    """L3：模糊时不准先做一版看看——反例边界写明。"""

    def test_no_build_first_look_later(self):
        self.assertIn("不要\"先做一版看看\"", TEXT)

    def test_assumptions_are_not_orders(self):
        self.assertIn("不当作指令", TEXT)


if __name__ == "__main__":
    unittest.main()
