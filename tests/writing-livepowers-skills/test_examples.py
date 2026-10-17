"""writing-livepowers-skills 的独立验收测试。L1/L3 纯文本可跑；L2 需真实环境则跳过。"""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / "skills" / "writing-livepowers-skills" / "SKILL.md"
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
    """L1：TDD 写技能流程与格式要求存在。"""

    def test_frontmatter_name_matches_dir(self):
        self.assertEqual(_frontmatter(TEXT).get("name"), "writing-livepowers-skills")

    def test_red_green_refactor(self):
        self.assertIn("RED", TEXT)
        self.assertIn("GREEN", TEXT)
        self.assertIn("REFACTOR", TEXT)

    def test_format_requirement(self):
        self.assertIn("skills/<kebab-case-name>/SKILL.md", TEXT)
        self.assertIn("name: <与目录名一致>", TEXT)

    def test_description_rule(self):
        self.assertIn("description", TEXT)
        self.assertIn("只写**何时使用**", TEXT)


class Examples(unittest.TestCase):
    """L2：文档里的触发集例子可复现（纯文本）。"""

    def test_trigger_set_quota(self):
        self.assertIn("tests/triggers/<name>.jsonl", TEXT)
        self.assertIn("至少 3 条正例与 2 条反例", TEXT)

    def test_trigger_set_exists_in_repo(self):
        triggers = Path(__file__).resolve().parents[2] / "tests" / "triggers"
        self.assertTrue(triggers.is_dir(), "仓库应有 tests/triggers/ 目录")

    @unittest.skipIf(LP is None, "需 lp 真实环境")
    def test_lp_help_exit_code(self):
        r = subprocess.run([LP, "--help"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)


class Negative(unittest.TestCase):
    """L3：明确写出不值得写成技能的情形。"""

    def test_no_one_off_skills(self):
        self.assertIn("**不写**：一次性解法", TEXT)

    def test_no_project_private_conventions(self):
        self.assertIn("项目私有约定（放项目的 AGENTS.md / CLAUDE.md）", TEXT)


if __name__ == "__main__":
    unittest.main()
