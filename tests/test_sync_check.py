# -*- coding: utf-8 -*-
"""PRD-200/T2 自测（trend #1001）：跨工具同步检查——四工具覆盖/状态准确/零写入。"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from sync_check import sync_check, status_table  # noqa: E402

EXPECTED = {"示例技能A": "abc123def4567890", "示例技能B": "def456abc7890123"}


class TestSyncCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for name, fp in EXPECTED.items():
            d = self.root / "expected" / name
            d.mkdir(parents=True, exist_ok=True)
            (d / "SKILL.md").write_text(f"# {name}\n示例内容", encoding="utf-8")
        self.expected_dir = self.root / "expected"

    def tearDown(self):
        self.tmp.cleanup()

    def _make_tool(self, tool, content_map):
        root = self.root / f"{tool}_skills"
        for name, content in content_map.items():
            d = root / name
            d.mkdir(parents=True, exist_ok=True)
            if content is not None:
                (d / "SKILL.md").write_text(content, encoding="utf-8")
        return str(root)

    def test_four_tools_covered(self):
        roots = {t: str(self.root / f"{t}_skills") for t in ("claude", "cursor", "codex", "pi")}
        r = sync_check(self.expected_dir, roots)
        tools = {i["tool"] for i in r["instances"]}
        self.assertEqual(tools, set(roots.keys()))

    def test_installed_match(self):
        root = self._make_tool("claude", {n: f"# {n}\n示例内容" for n in EXPECTED})
        r = sync_check(self.expected_dir, {"claude": root})
        for inst in r["instances"]:
            self.assertEqual(inst["status"], "installed")
            self.assertEqual(inst["fp_match"], "match")

    def test_missing_detected(self):
        roots = {t: str(self.root / f"{t}_skills") for t in ("claude", "cursor", "codex", "pi")}
        for t in roots:
            Path(t).mkdir(parents=True, exist_ok=True)
        r = sync_check(self.expected_dir, roots)
        missing = [i for i in r["instances"] if i["status"] == "missing"]
        self.assertGreater(len(missing), 0)

    def test_incomplete_detected(self):
        roots = {t: str(self.root / f"{t}_skills") for t in ("claude", "cursor", "codex", "pi")}
        for t in roots:
            (self.root / f"{t}_skills" / "示例技能A").mkdir(parents=True, exist_ok=True)
        r = sync_check(self.expected_dir, roots)
        incomplete = [i for i in r["instances"] if i["status"] == "incomplete"]
        self.assertGreater(len(incomplete), 0)

    def test_content_mismatch(self):
        root = self._make_tool("claude", {n: f"# {n}\n不同内容" for n in EXPECTED})
        r = sync_check(self.expected_dir, {"claude": root})
        mismatch = [i for i in r["instances"] if i.get("fp_match") == "content_mismatch"]
        self.assertGreater(len(mismatch), 0)

    def test_status_table_output(self):
        roots = {t: str(self.root / f"{t}_skills") for t in ("claude", "cursor", "codex", "pi")}
        r = sync_check(self.expected_dir, roots)
        table = status_table(r)
        self.assertIn("tool", table)
        self.assertIn("status", table)

    def test_zero_write(self):
        root = self._make_tool("claude", {n: f"# {n}\n示例内容" for n in EXPECTED})
        before = sorted((p.name, p.stat().st_mtime) for p in Path(root).rglob("*") if p.is_file())
        sync_check(self.expected_dir, {"claude": root})
        after = sorted((p.name, p.stat().st_mtime) for p in Path(root).rglob("*") if p.is_file())
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
