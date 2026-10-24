"""PRD-148/T3：scripts/skill_similarity.py 的单元测试。

用临时目录构造已知相似 / 不相似的 skill 对，验证：得分与阈值、四字段取最大、
英文/中文分开比对、触发词重叠、排序可复现、CLI（--top/--format/--out、退出码恒 0）。
对真实仓库只做只读冒烟（21 个 skill、输出格式），不绑定具体相似对（防内容漂移）。
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "skill_similarity.py"
_spec = importlib.util.spec_from_file_location("skill_similarity", SCRIPT)
ss = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ss)

REAL_REPO = Path(__file__).resolve().parents[1]


def skill_md(name, description, headings=("## 步骤", "## 简洁输出规范")):
    body = "\n\n".join(["# %s" % name, "一句话。"] + list(headings))
    return "---\nname: %s\ndescription: %s\nallowed-tools: Read\n---\n\n%s\n" % (
        name, description, body)


def build_fixture(root):
    root = Path(root) / "skills"
    cases = {
        # 已知相似对 A：英文触发段几乎相同。
        "alpha-report": skill_md(
            "alpha-report",
            "Use when writing a weekly delivery report for stakeholders. "
            "写周报给干系人时使用。"),
        "alpha-report-v2": skill_md(
            "alpha-report-v2",
            "Use when writing a weekly delivery report for stakeholders "
            "and managers. 写周报给干系人时使用。"),
        # 已知不相似对 B/C：触发场景、语言、结构都不同。
        "beta-invoice": skill_md(
            "beta-invoice",
            "Use when reconciling supplier invoices against purchase "
            "orders. 供应商对账时使用。",
            ("## 对账步骤", "## 差异表", "## 简洁输出规范")),
        "gamma-roster": skill_md(
            "gamma-roster",
            "Use when planning on-call duty rotations for the team. "
            "排值班表时使用。",
            ("## 排班模板", "## 交接清单", "## 简洁输出规范")),
    }
    for k, v in cases.items():
        p = root / k
        p.mkdir(parents=True, exist_ok=True)
        (p / "SKILL.md").write_text(v, encoding="utf-8")
    return root.parent


class TestSimilarityCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.skills_dir = build_fixture(cls.tmp.name)
        cls.skills = ss.load_skills(str(cls.skills_dir / "skills"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def by_name(self, name):
        return next(s for s in self.skills if s["name"] == name)

    def test_loads_all_and_splits_description(self):
        self.assertEqual(len(self.skills), 4)
        a = self.by_name("alpha-report")
        self.assertTrue(a["en"].startswith("Use when writing"))
        self.assertTrue(a["zh"].startswith("写周报"))
        self.assertIn("步骤", a["headings"])

    def test_known_similar_pair_hits_strong(self):
        a, b = self.by_name("alpha-report"), self.by_name("alpha-report-v2")
        score, field = ss.similarity(a, b)
        self.assertGreaterEqual(score, 0.80, "已知相似对应达强提示线")
        self.assertIn(field, ("en", "zh"))
        pairs, stats = ss.scan(self.skills)
        names = {frozenset((p["a"], p["b"])) for p in pairs}
        self.assertIn(frozenset(("alpha-report", "alpha-report-v2")), names)
        self.assertGreaterEqual(stats["pairs_hint"], 1)

    def test_dissimilar_pair_below_hint(self):
        b, c = self.by_name("beta-invoice"), self.by_name("gamma-roster")
        score, _ = ss.similarity(b, c)
        self.assertLess(score, 0.60, "已知不相似对应低于提示线")
        pairs, _ = ss.scan(self.skills)
        names = {frozenset((p["a"], p["b"])) for p in pairs}
        self.assertNotIn(frozenset(("beta-invoice", "gamma-roster")), names)

    def test_en_zh_compared_separately_max_wins(self):
        # 中文一句话完全相同、英文完全不同：zh 字段应驱动得分到高位。
        x = {"name": "x-one", "en": "totally unrelated english trigger",
             "zh": "完全相同的中文一句话", "headings": "", "tokens": set()}
        y = {"name": "y-two", "en": "nothing to do with the above at all",
             "zh": "完全相同的中文一句话", "headings": "", "tokens": set()}
        score, field = ss.similarity(x, y)
        self.assertEqual(field, "zh")
        self.assertGreater(score, 0.9)

    def test_empty_fields_do_not_score(self):
        # 空 × 空不得得 1.0（ratio 的护栏）。
        a = {"name": "", "en": "", "zh": "", "headings": "", "tokens": set()}
        self.assertEqual(ss.similarity(a, dict(a))[0], 0.0)

    def test_overlap_trigger_words_reported(self):
        a, b = self.by_name("alpha-report"), self.by_name("alpha-report-v2")
        self.assertIn("weekly", a["tokens"] & b["tokens"])

    def test_scan_ordering_reproducible(self):
        p1, _ = ss.scan(self.skills)
        p2, _ = ss.scan(self.skills)
        self.assertEqual(p1, p2)
        scores = [p["score"] for p in p1]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_top_limit(self):
        pairs, _ = ss.scan(self.skills, top=1)
        self.assertLessEqual(len(pairs), 1)

    def test_unparsable_skill_skipped(self):
        d = self.skills_dir / "skills" / "broken-skill"
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text("没有 frontmatter 的文件\n", encoding="utf-8")
        loaded = ss.load_skills(str(self.skills_dir / "skills"))
        self.assertEqual(len(loaded), 4)
        self.assertNotIn("broken-skill", [s["name"] for s in loaded])


class TestSimilarityCLI(unittest.TestCase):
    def run_cli(self, *args, cwd=None):
        out = subprocess.run(
            [sys.executable, str(SCRIPT)] + list(args),
            capture_output=True, text=True, timeout=60, cwd=cwd)
        return out.returncode, out.stdout + out.stderr

    def test_exit_code_always_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = build_fixture(tmp)
            # 有相似对、无相似对（阈值调到 1.1）都不得拦截。
            for extra in (["--skills-dir", str(root / "skills")],
                          ["--skills-dir", str(root / "skills"), "--hint", "1.1"]):
                code, out = self.run_cli(*extra)
                self.assertEqual(code, 0, out)

    def test_json_format_parses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = build_fixture(tmp)
            code, out = self.run_cli("--skills-dir", str(root / "skills"),
                                     "--format", "json")
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertIn("pairs", data)
            self.assertEqual(data["stats"]["skills"], 4)
            pair = next(p for p in data["pairs"]
                        if {p["a"], p["b"]} == {"alpha-report", "alpha-report-v2"})
            self.assertGreaterEqual(pair["score"], 0.8)

    def test_out_file_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = build_fixture(tmp)
            dest = os.path.join(tmp, "report.md")
            code, out = self.run_cli("--skills-dir", str(root / "skills"),
                                     "--format", "markdown", "--out", dest)
            self.assertEqual(code, 0)
            self.assertTrue(os.path.isfile(dest))
            self.assertIn("已写入", out)

    def test_real_repo_smoke(self):
        # 只读冒烟：21 个 skill、行格式、可复现；不绑定具体相似对（防内容漂移）。
        code1, out1 = self.run_cli("--top", "0")
        code2, out2 = self.run_cli("--top", "0")
        self.assertEqual(code1, 0)
        self.assertEqual(out1, out2)
        m = re.search(r"skills：(\d+) 个；两两 (\d+) 对", out1)
        self.assertIsNotNone(m, out1[:200])
        self.assertEqual(int(m.group(1)), 21)
        self.assertEqual(int(m.group(2)), 21 * 20 // 2)
        for line in out1.splitlines():
            if line.startswith(("○", "★★")):
                self.assertRegex(
                    line, r"相似对：[a-z0-9-]+ × [a-z0-9-]+（\d\.\d{2}）\[\w+\] \| 重叠触发词：")


if __name__ == "__main__":
    unittest.main()
