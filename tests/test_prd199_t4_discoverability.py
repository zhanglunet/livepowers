# -*- coding: utf-8 -*-
"""PRD-199/T4 自测（trend #998）：跨工具可发现性验证（四工具均可发现并触发）。

运行：uv run --with pytest python -m pytest tests/test_prd199_t4_discoverability.py -q

覆盖（验收「四工具均可发现并触发」）：
  四工具全装齐 + 触发词在 → all_ok=True
  某工具缺 SKILL.md → 该工具 discoverable=False + 理由
  name 与目录不一致 → 不可发现
  description 缺触发关键词 → 不可发现
  可发现但 invoke_fn 不命中 → triggered=False + 理由（可发现≠可触发）
  零写入断言（验证过程不改工具目录）

虚构纪律：全虚构；零网络。
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from discoverability_check import verify_discoverability  # noqa: E402

GOOD_SKILL = """---
name: demo-skill
description: 演示技能：当用户说「按 demo-skill 的说明来一份示例输出」时使用（虚构）。
license: MIT
metadata:
  when_not_to_use: 不适用于真实场景（虚构）
  output: 演示输出（虚构）
  compatibility: claude/cursor/codex/pi（虚构）
---

# 演示
"""

TOOLS = {
    "claude": "claude/skills",
    "cursor": "cursor/skills",
    "codex": "codex/skills",
    "pi": "pi/skills",
}


def install_all(root: Path, fm=GOOD_SKILL):
    for tool_root in TOOLS.values():
        d = root / tool_root / "demo-skill"
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(fm, encoding="utf-8")
    src = root / "src" / "demo-skill"
    src.mkdir(parents=True)
    (src / "SKILL.md").write_text(fm, encoding="utf-8")
    return root / "src"


def always_trigger(tool, skill_id, utterance):
    return True


class DiscoverabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_all_four_tools_discover_and_trigger(self):
        src = install_all(self.root)
        report = verify_discoverability(
            src, {t: self.root / p for t, p in TOOLS.items()}, always_trigger)
        self.assertTrue(report["all_ok"])
        for tool, t in report["skills"]["demo-skill"]["tools"].items():
            self.assertTrue(t["discoverable"], tool)
            self.assertTrue(t["triggered"], tool)

    def test_missing_skill_in_one_tool_fails(self):
        src = install_all(self.root)
        (self.root / "cursor" / "skills" / "demo-skill" / "SKILL.md").unlink()
        report = verify_discoverability(
            src, {t: self.root / p for t, p in TOOLS.items()}, always_trigger)
        cursor = report["skills"]["demo-skill"]["tools"]["cursor"]
        self.assertFalse(cursor["discoverable"])
        self.assertIn("缺失", cursor["reasons"][0])
        self.assertFalse(report["all_ok"])

    def test_name_mismatch_not_discoverable(self):
        src = install_all(self.root, fm=GOOD_SKILL.replace(
            "name: demo-skill", "name: wrong-name"))
        report = verify_discoverability(
            src, {t: self.root / p for t, p in TOOLS.items()}, always_trigger)
        self.assertFalse(report["skills"]["demo-skill"]["all_ok"])
        cursor = report["skills"]["demo-skill"]["tools"]["cursor"]
        self.assertTrue(any("不一致" in r for r in cursor["reasons"]))

    def test_description_without_keywords_not_discoverable(self):
        bad = GOOD_SKILL.replace("demo-skill", "无关词").replace("演示技能：当用户说", "无关描述（虚构）：")
        src = install_all(self.root, fm=bad)
        report = verify_discoverability(
            src, {t: self.root / p for t, p in TOOLS.items()}, always_trigger)
        self.assertFalse(report["skills"]["demo-skill"]["all_ok"])

    def test_discoverable_but_not_triggered(self):
        src = install_all(self.root)

        def never(tool, skill_id, utterance):
            return False

        report = verify_discoverability(src, {t: self.root / p for t, p in TOOLS.items()},
                                        never)
        for tool, t in report["skills"]["demo-skill"]["tools"].items():
            self.assertTrue(t["discoverable"])                 # 可发现
            self.assertFalse(t["triggered"])                   # 但触发不命中 → 如实报
            self.assertIn("唤起未命中", t["reasons"][0])
        self.assertFalse(report["all_ok"])

    def test_zero_write(self):
        src = install_all(self.root)
        before = sorted(str(p) for p in self.root.rglob("*"))
        verify_discoverability(src, {t: self.root / p for t, p in TOOLS.items()},
                               always_trigger)
        after = sorted(str(p) for p in self.root.rglob("*"))
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
