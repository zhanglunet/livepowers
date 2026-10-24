"""living-surface 的独立验收测试。L1/L3 纯文本可跑；L2 需 lp 环境则跳过。"""
import re
import unittest
from pathlib import Path

from helpers import find_livepowers_lp, run_lp

SKILL = Path(__file__).resolve().parents[2] / "skills" / "living-surface" / "SKILL.md"
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
    """L1：三类需求与数字来源铁律存在。"""

    def test_frontmatter_name_matches_dir(self):
        self.assertEqual(_frontmatter(TEXT).get("name"), "living-surface")

    def test_three_demands(self):
        for d in ["存量固化", "新增固化", "次抛"]:
            self.assertIn(d, TEXT, "三类需求缺：%s" % d)

    def test_numbers_from_deterministic_query(self):
        self.assertIn("数字必须来自确定性查询", TEXT)

    def test_ephemeral_tier(self):
        self.assertIn("tier: ephemeral", TEXT)


class Examples(unittest.TestCase):
    """L2：文档里的次抛与生长例子可复现（纯文本）。"""

    def test_surface_validate_example(self):
        self.assertIn("lp surface validate <surface.json>", TEXT)

    def test_promote_flow(self):
        self.assertIn("lp surface promote <记录文件> --by <申请人>", TEXT)

    @unittest.skipIf(LP is None, "需 lp 真实环境")
    def test_lp_pages_list_runs(self):
        r = run_lp(LP, "pages", "list")
        self.assertEqual(r.returncode, 0)


class Negative(unittest.TestCase):
    """L3：红线明确写出展示面不能做的事。"""

    def test_detail_rows_not_in_git(self):
        self.assertIn("明细行不进 git", TEXT)

    def test_no_write_via_surface(self):
        self.assertIn("写操作不经过展示面", TEXT)


if __name__ == "__main__":
    unittest.main()
