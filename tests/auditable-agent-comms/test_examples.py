"""auditable-agent-comms 的独立验收测试。L1/L3 纯文本可跑；L2 需真实环境则跳过。"""
import re
import shutil
import unittest
from pathlib import Path

from helpers import find_livepowers_lp

SKILL = Path(__file__).resolve().parents[2] / "skills" / "auditable-agent-comms" / "SKILL.md"
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
    """L1：无暗流通道原则与消息信封存在。"""

    def test_frontmatter_name_matches_dir(self):
        self.assertEqual(_frontmatter(TEXT).get("name"), "auditable-agent-comms")

    def test_no_dark_channel_principle(self):
        self.assertIn("智能体之间没有暗流通道", TEXT)

    def test_envelope_fields(self):
        for field in ["trace_id", "task_id", "contract_version", "from", "to", "type", "body"]:
            self.assertIn(field, TEXT, "消息信封缺字段：%s" % field)

    def test_three_trust_domains(self):
        for dom in ["可信沙箱内", "组织内跨团队", "跨组织"]:
            self.assertIn(dom, TEXT, "信任域缺：%s" % dom)


class Examples(unittest.TestCase):
    """L2：文档里的交换机用法可复现（纯文本）。"""

    def test_switch_serve_example(self):
        self.assertIn("agent_switch.py serve --port 7070", TEXT)

    def test_replay_and_verify(self):
        self.assertIn("agent_switch.py replay --trace t1", TEXT)
        self.assertIn("agent_switch.py verify", TEXT)

    @unittest.skipIf(shutil.which("python3") is None, "需 python3 环境")
    def test_switch_script_exists_in_repo(self):
        script = Path(__file__).resolve().parents[2] / "scripts" / "agent_switch.py"
        self.assertTrue(script.is_file(), "仓库应自带 scripts/agent_switch.py")


class Negative(unittest.TestCase):
    """L3：超长/拦截消息必须被拒绝，不能悄悄通过。"""

    def test_oversize_rejected_not_silent(self):
        self.assertIn("交换机会拒绝超过", TEXT)

    def test_rejected_messages_still_logged(self):
        self.assertIn("被拒消息同样落盘", TEXT)


if __name__ == "__main__":
    unittest.main()
