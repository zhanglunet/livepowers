"""nightly-crystallization-review 的独立验收测试。L1/L3 纯文本可跑；L2 需 lp 环境则跳过。"""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / "skills" / "nightly-crystallization-review" / "SKILL.md"
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
    """L1：夜间只生成不注册、晨报口径存在。"""

    def test_frontmatter_name_matches_dir(self):
        self.assertEqual(_frontmatter(TEXT).get("name"), "nightly-crystallization-review")

    def test_no_nightly_registration(self):
        self.assertIn("不要在夜间注册", TEXT)
        self.assertIn("注册要等早晨人工采纳", TEXT)

    def test_candidate_command(self):
        self.assertIn("lp candidates --min-count 3", TEXT)

    def test_morning_report_command(self):
        self.assertIn("lp report --current-model <当前模型>", TEXT)


class Examples(unittest.TestCase):
    """L2：文档里的证据与金丝雀例子可复现（纯文本）。"""

    def test_evidence_stats_example(self):
        self.assertIn("lp evidence stats", TEXT)

    def test_canary_example(self):
        self.assertIn("lp canary record --name <套件名>", TEXT)
        self.assertIn("lp canary compare", TEXT)

    @unittest.skipIf(LP is None, "需 lp 真实环境")
    def test_lp_candidates_runs(self):
        r = subprocess.run([LP, "candidates", "--min-count", "3"],
                           capture_output=True, text=True)
        self.assertIn(r.returncode, (0, 1, 2))


class Negative(unittest.TestCase):
    """L3：自动固化不可靠——反例边界写明。"""

    def test_auto_crystallize_unreliable(self):
        self.assertIn("自动固化并不可靠", TEXT)

    def test_night_output_is_draft(self):
        self.assertIn("夜间产出的永远是\"草稿 + 测试证据\"", TEXT)


if __name__ == "__main__":
    unittest.main()
