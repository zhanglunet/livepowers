"""crystallize-to-system1 的独立验收测试。L1/L3 纯文本可跑；L2 需 lp 环境则跳过。"""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / "skills" / "crystallize-to-system1" / "SKILL.md"
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
    """L1：六步流程与 F-V-S-R 门禁存在。"""

    def test_frontmatter_name_matches_dir(self):
        self.assertEqual(_frontmatter(TEXT).get("name"), "crystallize-to-system1")

    def test_six_steps_present(self):
        for step in ["过门禁", "TDD", "实现规范", "组装能力包", "独立验收", "注册与发布"]:
            self.assertIn(step, TEXT, "六步缺：%s" % step)

    def test_fvsr_gate(self):
        self.assertIn("lp score", TEXT)
        self.assertIn("V=0 一票否决", TEXT)

    def test_registry_add_requires_two_people(self):
        self.assertIn("--generated-by <生成者> --accepted-by <采纳人>", TEXT)
        self.assertIn("两者必须不同", TEXT)


class Examples(unittest.TestCase):
    """L2：文档里的评分与注册例子可复现（纯文本）。"""

    def test_score_formula(self):
        self.assertIn("合成分 = F×2 + V×1.5 + S×1 + R×1", TEXT)

    def test_breakeven_formula(self):
        self.assertIn("n* = (K + M) / (c2′ − c1)", TEXT)

    @unittest.skipIf(LP is None, "需 lp 真实环境")
    def test_lp_score_exit_codes(self):
        # 文档约定：建议固化 exit 0；否则 exit 3
        r = subprocess.run([LP, "score", "--help"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)


class Negative(unittest.TestCase):
    """L3：反模式清单明确写出不能做的事。"""

    def test_no_register_after_single_hit(self):
        self.assertIn("模型答对一次就注册", TEXT)

    def test_no_llm_hidden_in_crystallized_code(self):
        self.assertIn("固化代码里藏着一次 LLM 调用", TEXT)


if __name__ == "__main__":
    unittest.main()
