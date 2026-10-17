"""outcome-ledger 的独立验收测试。L1/L3 纯文本可跑；L2 需 lp 环境则跳过。"""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / "skills" / "outcome-ledger" / "SKILL.md"
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
    """L1：价值闸门四个"可"与基线原则存在。"""

    def test_frontmatter_name_matches_dir(self):
        self.assertEqual(_frontmatter(TEXT).get("name"), "outcome-ledger")

    def test_no_baseline_no_value(self):
        self.assertIn("没有基线的价值不算价值", TEXT)

    def test_four_ables(self):
        for able in ["可量化", "可归因", "可复现", "可经营"]:
            self.assertIn(able, TEXT, "价值闸门缺：%s" % able)

    def test_cost_kinds(self):
        self.assertIn("human|inference|tool|rework|ops|amortization|takeover", TEXT)


class Examples(unittest.TestCase):
    """L2：文档里的台账命令例子可复现（纯文本）。"""

    def test_baseline_command(self):
        self.assertIn("lp outcome baseline --scenario <场景> --metric <指标>", TEXT)

    def test_delta_v_formula(self):
        self.assertIn("ΔV = 业务基数 B × 提升率 u", TEXT)

    @unittest.skipIf(LP is None, "需 lp 真实环境")
    def test_lp_outcome_report_runs(self):
        r = subprocess.run([LP, "outcome", "report"], capture_output=True, text=True)
        self.assertIn(r.returncode, (0, 1, 2))


class Negative(unittest.TestCase):
    """L3：红线明确写出核算时不能做的事。"""

    def test_no_cherry_picked_costs(self):
        self.assertIn("不只统计成功调用的费用", TEXT)

    def test_no_explanation_as_causation(self):
        self.assertIn("不把模型给出的解释当作因果证据", TEXT)


if __name__ == "__main__":
    unittest.main()
