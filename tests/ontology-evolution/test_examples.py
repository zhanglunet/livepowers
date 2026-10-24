"""ontology-evolution 的独立验收测试。L1/L3 纯文本可跑；L2 需 lp 环境则跳过。"""
import re
import unittest
from pathlib import Path

from helpers import find_livepowers_lp, run_lp

SKILL = Path(__file__).resolve().parents[2] / "skills" / "ontology-evolution" / "SKILL.md"
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
    """L1：两层放置规则与四个状态存在。"""

    def test_frontmatter_name_matches_dir(self):
        self.assertEqual(_frontmatter(TEXT).get("name"), "ontology-evolution")

    def test_two_layers(self):
        self.assertIn("参考本体", TEXT)
        self.assertIn("本体孪生", TEXT)

    def test_four_states(self):
        for state in ["`candidate` 候选", "`validated` 已校验", "`confirmed` 已确认", "`published` 已发布"]:
            self.assertIn(state, TEXT, "四个状态缺：%s" % state)

    def test_only_published_referenceable(self):
        self.assertIn("只有 `published` 的定义可以被已注册能力引用", TEXT)


class Examples(unittest.TestCase):
    """L2：文档里的 Delta 模板例子可复现（纯文本）。"""

    def test_delta_template_ref(self):
        self.assertIn("templates/ontology-delta.yaml", TEXT)

    def test_version_bump_rule(self):
        self.assertIn("升 `ontology_version`", TEXT)

    @unittest.skipIf(LP is None, "需 lp 真实环境")
    def test_lp_help_exit_code(self):
        r = run_lp(LP, "--help")
        self.assertEqual(r.returncode, 0)


class Negative(unittest.TestCase):
    """L3：红线明确写出本体变更不能做的事。"""

    def test_no_quiet_drift(self):
        self.assertIn("不在会话里\"悄悄\"改口径", TEXT)

    def test_client_data_not_in_public_ontology(self):
        self.assertIn("客户数据、凭证、专有制度不进入公共参考本体", TEXT)


if __name__ == "__main__":
    unittest.main()
