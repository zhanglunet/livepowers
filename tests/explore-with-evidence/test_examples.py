"""explore-with-evidence 的独立验收测试。L1/L3 纯文本可跑；L2 需 lp 环境则跳过。"""
import re
import unittest
from pathlib import Path

from helpers import find_livepowers_lp, run_lp

SKILL = Path(__file__).resolve().parents[2] / "skills" / "explore-with-evidence" / "SKILL.md"
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
    """L1：边界/预算/刹车三件事存在。"""

    def test_frontmatter_name_matches_dir(self):
        self.assertEqual(_frontmatter(TEXT).get("name"), "explore-with-evidence")

    def test_boundary_budget_brake(self):
        self.assertIn("定边界、定预算、定刹车", TEXT)

    def test_evidence_is_mandatory(self):
        self.assertIn("lp evidence add", TEXT)
        self.assertIn("记录证据", TEXT)

    def test_olap_oltp_split(self):
        self.assertIn("OLAP（只读）", TEXT)
        self.assertIn("OLTP（写入）", TEXT)


class Examples(unittest.TestCase):
    """L2：文档里的意图命名例子可复现（纯文本）。"""

    def test_intent_naming_examples(self):
        self.assertIn("weekly revenue by region", TEXT)
        self.assertIn("转交逾期商机", TEXT)

    def test_evidence_command_shape(self):
        self.assertIn("--system S2 --outcome success|fail|partial", TEXT)

    @unittest.skipIf(LP is None, "需 lp 真实环境")
    def test_lp_evidence_add_runs(self):
        r = run_lp(LP, "evidence", "add", "--intent", "ci-smoke-explore",
                   "--system", "S2", "--outcome", "success")
        self.assertEqual(r.returncode, 0)


class Negative(unittest.TestCase):
    """L3：反模式明确写出探索中不能做的事。"""

    def test_no_evidence_no_done(self):
        self.assertIn("不记证据就结束", TEXT)

    def test_no_endless_retry(self):
        self.assertIn("预算用完还在\"再试一次\"", TEXT)


if __name__ == "__main__":
    unittest.main()
