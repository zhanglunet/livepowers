"""acceptance-gates 的独立验收测试。L1/L3 纯文本可跑；L2 需 lp 环境则跳过。"""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / "skills" / "acceptance-gates" / "SKILL.md"
TEXT = SKILL.read_text(encoding="utf-8")
LP = shutil.which("lp")


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
    """L1：四道门与关键主张存在。"""

    def test_frontmatter_name_matches_dir(self):
        self.assertEqual(_frontmatter(TEXT).get("name"), "acceptance-gates")

    def test_four_gates_present(self):
        for gate in ["形式检查", "契约测试", "独立对抗审查", "人工采纳"]:
            self.assertIn(gate, TEXT, "四道门缺：%s" % gate)

    def test_separation_of_duties(self):
        self.assertIn("验收标准和基准用例不能由生成方修改", TEXT)

    def test_five_roles_present(self):
        for role in ["派工者", "执行者", "验证者", "采纳人", "运营者"]:
            self.assertIn(role, TEXT, "五种职责缺：%s" % role)


class Examples(unittest.TestCase):
    """L2：文档里的操作示例可复现（纯文本）。"""

    def test_verify_then_register_flow(self):
        self.assertIn("lp task move <id> verify", TEXT)
        self.assertIn("lp task move <id> registered", TEXT)

    def test_outcome_accept_example(self):
        self.assertIn("lp outcome accept --scenario <场景> --task <id> --by <采纳人>", TEXT)

    @unittest.skipIf(LP is None, "需 lp 真实环境")
    def test_lp_help_exit_code(self):
        r = subprocess.run([LP, "--help"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)


class Negative(unittest.TestCase):
    """L3：测试通过不等于正确——反例边界写明。"""

    def test_passing_tests_not_proof(self):
        self.assertIn("并不证明所有情境下都正确", TEXT)

    def test_no_self_signoff(self):
        self.assertIn("不由生成者的自我声明决定", TEXT)


if __name__ == "__main__":
    unittest.main()
