"""night-loop-planning 的独立验收测试。L1/L3 纯文本可跑；L2 需 lp 环境则跳过。"""
import re
import unittest
from pathlib import Path

from helpers import find_livepowers_lp, run_lp

SKILL = Path(__file__).resolve().parents[2] / "skills" / "night-loop-planning" / "SKILL.md"
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
    """L1：节律、切段与交接契约存在。"""

    def test_frontmatter_name_matches_dir(self):
        self.assertEqual(_frontmatter(TEXT).get("name"), "night-loop-planning")

    def test_rhythm(self):
        self.assertIn("白天提需求、定规格、交互探索；夜间跑可延后的长程任务与固化；早晨交付可审核的成果", TEXT)

    def test_model_horizon(self):
        self.assertIn("model_horizon_minutes", TEXT)
        self.assertIn("lp job validate", TEXT)

    def test_handoff_contract(self):
        self.assertIn("actual_end_state", TEXT)
        self.assertIn("checker", TEXT)


class Examples(unittest.TestCase):
    """L2：文档里的作业契约例子可复现（纯文本）。"""

    def test_job_contract_template(self):
        self.assertIn("templates/job-contract.json", TEXT)

    def test_job_validate_example(self):
        self.assertIn("lp job validate jobs.json", TEXT)

    @unittest.skipIf(LP is None, "需 lp 真实环境")
    def test_lp_job_validate_help_runs(self):
        r = run_lp(LP, "job", "validate", "--help")
        self.assertEqual(r.returncode, 0)


class Negative(unittest.TestCase):
    """L3：反模式明确写出夜间作业不能做的事。"""

    def test_no_brakeless_loop(self):
        self.assertIn("没有止损条件的循环", TEXT)

    def test_handoff_no_wishful_thinking(self):
        self.assertIn("交接里写\"上一步应该已经完成\"", TEXT)


if __name__ == "__main__":
    unittest.main()
