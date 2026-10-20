"""takeover-handling 的独立验收测试。L1/L3 纯文本可跑；L2 需 lp 环境则跳过。"""
import re
import unittest
from pathlib import Path

from helpers import find_livepowers_lp, run_lp

SKILL = Path(__file__).resolve().parents[2] / "skills" / "takeover-handling" / "SKILL.md"
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
    """L1：止损转接管条件与归因表存在。"""

    def test_frontmatter_name_matches_dir(self):
        self.assertEqual(_frontmatter(TEXT).get("name"), "takeover-handling")

    def test_stop_retry_on_takeover(self):
        self.assertIn("执行 Agent 停止一切重试", TEXT)

    def test_attribution_table(self):
        for cause in ["规格不清", "本体缺口", "环境漂移", "已固化能力失效",
                      "预算定得太低", "工具 / 权限故障", "任务本身不该做"]:
            self.assertIn(cause, TEXT, "归因表缺主因：%s" % cause)

    def test_takeover_cost_booked(self):
        self.assertIn("lp outcome cost --scenario <场景> --kind takeover", TEXT)


class Examples(unittest.TestCase):
    """L2：文档里的接管三选一例子可复现（纯文本）。"""

    def test_three_options(self):
        self.assertIn("--reset-loops", TEXT)
        self.assertIn("--extend-budget", TEXT)
        self.assertIn("lp task move <id> closed", TEXT)

    def test_takeover_when_condition(self):
        self.assertIn("takeover_when", TEXT)

    @unittest.skipIf(LP is None, "需 lp 真实环境")
    def test_lp_task_show_help_runs(self):
        r = run_lp(LP, "task", "show", "--help")
        self.assertEqual(r.returncode, 0)


class Negative(unittest.TestCase):
    """L3：反模式明确写出接管中不能做的事。"""

    def test_taker_is_not_executor(self):
        self.assertIn("接管人就是原执行者", TEXT)

    def test_no_direct_to_production(self):
        self.assertIn("从接管直接进入生产运行", TEXT)


if __name__ == "__main__":
    unittest.main()
