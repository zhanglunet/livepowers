"""oltp-action-safety 的独立验收测试。L1/L3 纯文本可跑；L2 需 lp 环境则跳过。"""
import re
import unittest
from pathlib import Path

from helpers import find_livepowers_lp, run_lp

SKILL = Path(__file__).resolve().parents[2] / "skills" / "oltp-action-safety" / "SKILL.md"
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
    """L1：八项检查与高风险闭环顺序存在。"""

    def test_frontmatter_name_matches_dir(self):
        self.assertEqual(_frontmatter(TEXT).get("name"), "oltp-action-safety")

    def test_eight_checks_present(self):
        for check in ["状态前提", "权限", "事务", "幂等", "并发", "审批", "审计", "补偿"]:
            self.assertIn(check, TEXT, "八项检查缺：%s" % check)

    def test_closed_loop_order(self):
        self.assertIn("发现 → 诊断 → 仿真", TEXT)
        self.assertIn("审批 → 执行 → 核验 → 补偿 / 回撤", TEXT)

    def test_idempotency_key_rule(self):
        self.assertIn("幂等键 = 业务动作 + 对象 ID + 业务日期", TEXT)


class Examples(unittest.TestCase):
    """L2：文档里的实现模式例子可复现（纯文本）。"""

    def test_read_check_write_pattern(self):
        self.assertIn("读—校验—写", TEXT)

    def test_outbox_pattern(self):
        self.assertIn("outbox 事件表", TEXT)

    @unittest.skipIf(LP is None, "需 lp 真实环境")
    def test_lp_help_exit_code(self):
        r = run_lp(LP, "--help")
        self.assertEqual(r.returncode, 0)


class Negative(unittest.TestCase):
    """L3：禁止拼接任意 UPDATE、回撤边界写明。"""

    def test_no_arbitrary_update(self):
        self.assertIn("禁止 Agent 拼接任意 UPDATE", TEXT)

    def test_rollback_boundary(self):
        self.assertIn("代码回退只控制**后续**执行", TEXT)


if __name__ == "__main__":
    unittest.main()
