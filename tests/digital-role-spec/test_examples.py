"""digital-role-spec 的独立验收测试。L1/L3 纯文本可跑；L2 需 lp 环境则跳过。"""
import re
import unittest
from pathlib import Path

from helpers import find_livepowers_lp, run_lp

SKILL = Path(__file__).resolve().parents[2] / "skills" / "digital-role-spec" / "SKILL.md"
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
    """L1：任务归属四类与模板存在。"""

    def test_frontmatter_name_matches_dir(self):
        self.assertEqual(_frontmatter(TEXT).get("name"), "digital-role-spec")

    def test_four_attributions(self):
        for attr in ["`auto`", "`agent`", "`human`", "`handoff`"]:
            self.assertIn(attr, TEXT, "归属分类缺：%s" % attr)

    def test_role_template_ref(self):
        self.assertIn("templates/digital-role.yaml", TEXT)

    def test_role_formula(self):
        self.assertIn("岗位 = 角色 + 职责 + 智能体团队", TEXT)


class Examples(unittest.TestCase):
    """L2：文档里的岗位经济账例子可复现（纯文本）。"""

    def test_attribution_examples(self):
        self.assertIn("由已固化能力（System 1）完成", TEXT)
        self.assertIn("必须人做（授权、裁定、对外承诺、无法验证的判断）", TEXT)

    def test_upgrade_path(self):
        self.assertIn("`agent` 任务被反复成功执行 → 进入固化候选", TEXT)

    @unittest.skipIf(LP is None, "需 lp 真实环境")
    def test_lp_help_exit_code(self):
        r = run_lp(LP, "--help")
        self.assertEqual(r.returncode, 0)


class Negative(unittest.TestCase):
    """L3：红线明确写出岗位不能做的事。"""

    def test_no_extra_privilege(self):
        self.assertIn("数字岗位不拥有超出岗位定义的权限", TEXT)

    def test_external_commitment_stays_human(self):
        self.assertIn("对外承诺、不可逆动作、法律与合规裁定保留给人", TEXT)


if __name__ == "__main__":
    unittest.main()
