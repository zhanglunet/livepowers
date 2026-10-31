# -*- coding: utf-8 -*-
"""PRD-199/T3 自测（trend #997）：agentskills 规范校验进发布门。

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


class PublishGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "skills"

    def test_compliant_passes(self):
        make_skills(self.root, ["demo-skill"])
        report = gate_mod.gate(self.root)
        self.assertTrue(report["ok"])
        self.assertEqual(report["errors"], [])

    def test_non_compliant_blocked_with_gaps(self):
        make_skills(self.root, ["bad-skill"],
                    fm="---\nname: bad-skill\ndescription: 缺规范四项\n---\n\n正文\n")
        report = gate_mod.gate(self.root)
        self.assertFalse(report["ok"])
        self.assertEqual(len(report["errors"]), 4)  # license + 3 metadata 项
        self.assertTrue(all("bad-skill" in e for e in report["errors"]))

    def test_cli_exit_1_when_non_compliant(self):
        make_skills(self.root, ["bad-skill"],
                    fm="---\nname: bad-skill\ndescription: 缺项\n---\n\n正文\n")
        proc = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "publish_gate_spec.py"),
             "--skills-root", str(self.root)],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("不合规", proc.stderr)

    def test_manifest_published_members_gated(self):
        make_skills(self.root, ["skill-a"])
        manifest = self.root.parent / "manifest.json"
        manifest.write_text(json.dumps({"packs": [
            {"name": "pack-1", "status": "published", "skills": ["skill-a"]},
            {"name": "pack-2", "status": "published", "skills": ["ghost-skill"]},
            {"name": "pack-3", "status": "draft", "skills": ["whatever"]},
        ]}, ensure_ascii=False), encoding="utf-8")
        report = gate_mod.gate_report_for(manifest, self.root)
        self.assertFalse(report["ok"])
        by_skill = {r["skill"]: r for r in report["results"]}
        self.assertTrue(by_skill["skill-a"]["ok"])
        self.assertFalse(by_skill["ghost-skill"]["ok"])   # 缺失即拒绝
        self.assertNotIn("whatever", by_skill)            # draft 包不进发布门


if __name__ == "__main__":
    unittest.main()
