"""agent-harness-for-tools 的独立验收测试。L1/L3 纯文本可跑；L2 需 lp 环境则跳过。"""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / "skills" / "agent-harness-for-tools" / "SKILL.md"
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
    """L1：三产出与硬约束主张存在。"""

    def test_frontmatter_name_matches_dir(self):
        self.assertEqual(_frontmatter(TEXT).get("name"), "agent-harness-for-tools")

    def test_three_outputs_present(self):
        for out in ["工具卡", "业务剧本", "硬约束"]:
            self.assertIn(out, TEXT, "三产出缺：%s" % out)

    def test_tool_card_template_ref(self):
        self.assertIn("templates/tool-card.md", TEXT)

    def test_validation_bar(self):
        self.assertIn("成功率应 ≥95%", TEXT)


class Examples(unittest.TestCase):
    """L2：文档里的剧本与验证例子可复现（纯文本）。"""

    def test_playbook_example(self):
        self.assertIn("剧本：转交逾期重点商机", TEXT)
        self.assertIn('crm opp list --filter "key=true,last_followup_days>30"', TEXT)

    def test_postcondition_check(self):
        self.assertIn("核对后置条件", TEXT)
        self.assertIn("排查禁止动作", TEXT)

    @unittest.skipIf(LP is None, "需 lp 真实环境")
    def test_lp_canary_record_runs(self):
        r = subprocess.run(
            [LP, "canary", "record", "--name", "ci-smoke",
             "--model", "ci", "--pass", "1", "--total", "1", "--tokens", "1"],
            capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)


class Negative(unittest.TestCase):
    """L3：约束不一刀切——反例边界写明。"""

    def test_no_one_size_fits_all(self):
        self.assertIn("不要一刀切", TEXT)

    def test_constraints_scale_with_risk(self):
        self.assertIn("约束力度与动作风险成正比", TEXT)


if __name__ == "__main__":
    unittest.main()
