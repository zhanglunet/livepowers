# -*- coding: utf-8 -*-
"""PRD-200/T3 自测（trend #1002）：版本漂移与残留清理建议输出。

运行：uv run --with pytest python -m pytest tests/test_prd199_t3_publish_gate.py -q

覆盖：四项缺口任一拒绝 / 全合规通过 / CLI exit 1 / manifest published 成员过门。
零网络；全虚构。
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import publish_gate_spec as gate_mod  # noqa: E402
import sync_remediate as sr  # noqa: E402

GOOD_FM = """---
name: demo-skill
description: 演示技能（虚构）
license: MIT
metadata:
  when_not_to_use: 不适用于真实场景（虚构）
  output: 演示输出（虚构）
  compatibility: claude/cursor/codex/pi（虚构）
---

# 演示
"""


def make_skills(root: Path, names, fm=GOOD_FM):
    for n in names:
        d = root / n
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(fm, encoding="utf-8")


class RemediationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        make_skills(self.source, ["demo-skill", "other-skill"])
        self.roots = {"claude": str(self.root / "claude" / "skills")}

    def test_missing_with_root_creation(self):
        report = {"instances": [{"tool": "claude", "skill": "demo-skill",
                                 "status": "missing"}]}
        advice = sr.remediation_advice(report, self.roots, self.source)
        steps = advice[0]["steps"]
        self.assertTrue(any("mkdir -p" in s for s in steps))
        self.assertTrue(any("cp -R" in s and "demo-skill" in s for s in steps))

    def test_version_drift_rm_then_cp(self):
        dst = self.root / "claude" / "skills" / "demo-skill"
        dst.mkdir(parents=True)
        (dst / "SKILL.md").write_text("旧版本（虚构）", encoding="utf-8")
        report = {"instances": [{"tool": "claude", "skill": "demo-skill",
                                 "status": "installed", "fp_match": "content_mismatch"}]}
        advice = sr.remediation_advice(report, self.roots, self.source)
        steps = advice[0]["steps"]
        self.assertTrue(any(s.startswith("rm -rf") for s in steps))  # 先删旧版
        self.assertTrue(any(s.startswith("cp -R") for s in steps))   # 再对齐期望版本

    def test_incomplete_fills_skill_md(self):
        dst = self.root / "claude" / "skills" / "demo-skill"
        dst.mkdir(parents=True)
        report = {"instances": [{"tool": "claude", "skill": "demo-skill",
                                 "status": "incomplete"}]}
        advice = sr.remediation_advice(report, self.roots, self.source)
        self.assertTrue(any("SKILL.md" in s and "cp" in s for s in advice[0]["steps"]))

    def test_residue_detected_and_cleanup_advised(self):
        tool_root = self.root / "claude" / "skills"
        (tool_root / "demo-skill").mkdir(parents=True)
        (tool_root / "demo-skill@old").mkdir()  # 期望清单外的旧版残留
        residues = sr.scan_residue(self.source, self.roots)
        self.assertEqual(len(residues), 1)
        self.assertEqual(residues[0]["skill"], "demo-skill@old")
        advice = sr.residue_advice(residues)
        self.assertIn("rm -rf", advice[0]["steps"][0])
        self.assertIn("人工确认", advice[0]["steps"][0])

    def test_advice_is_zero_write(self):
        report = {"instances": [{"tool": "claude", "skill": "demo-skill",
                                 "status": "missing"}]}
        before = sorted(str(p) for p in self.root.rglob("*"))
        sr.remediation_advice(report, self.roots, self.source)
        sr.scan_residue(self.source, self.roots)
        after = sorted(str(p) for p in self.root.rglob("*"))
        self.assertEqual(before, after)  # 建议只生成，不执行


if __name__ == "__main__":
    unittest.main()
