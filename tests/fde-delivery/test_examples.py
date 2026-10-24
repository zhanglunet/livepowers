"""fde-delivery 的独立验收测试。L1/L3 纯文本可跑；L2 需 lp 环境则跳过。"""
import re
import unittest
from pathlib import Path

from helpers import find_livepowers_lp, run_lp

SKILL = Path(__file__).resolve().parents[2] / "skills" / "fde-delivery" / "SKILL.md"
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
    """L1：两种产出与落地三步存在。"""

    def test_frontmatter_name_matches_dir(self):
        self.assertEqual(_frontmatter(TEXT).get("name"), "fde-delivery")

    def test_two_outputs(self):
        self.assertIn("交付给客户的**功能**", TEXT)
        self.assertIn("回流给产品的**资产**", TEXT)

    def test_three_steps(self):
        self.assertIn("先白盒", TEXT)
        self.assertIn("再契约", TEXT)
        self.assertIn("后证据闭环", TEXT)

    def test_five_base_assets(self):
        self.assertIn("五类底座资产", TEXT)


class Examples(unittest.TestCase):
    """L2：文档里的资产回流例子可复现（纯文本）。"""

    def test_asset_gates(self):
        self.assertIn("lp asset add --name", TEXT)
        self.assertIn("lp asset gate <id> abstractable", TEXT)

    def test_asset_reflow_rate(self):
        self.assertIn("资产回流率 = 入库现场创新 / 现场创新总数", TEXT)

    @unittest.skipIf(LP is None, "需 lp 真实环境")
    def test_lp_asset_list_runs(self):
        r = run_lp(LP, "asset", "list")
        self.assertEqual(r.returncode, 0)


class Negative(unittest.TestCase):
    """L3：客户资产永不入库——反例边界写明。"""

    def test_client_assets_never_enter_library(self):
        self.assertIn("客户数据、凭证、专有制度永远不入库", TEXT)

    def test_outsourcing_is_not_fde(self):
        self.assertIn("只留一套系统是外包", TEXT)


if __name__ == "__main__":
    unittest.main()
