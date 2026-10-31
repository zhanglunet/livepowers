# -*- coding: utf-8 -*-
"""PRD-200/T4 自测（trend #1003）：与发布流水线对接（新版发布后提示同步）。

运行：uv run --with pytest python -m pytest tests/test_prd200_t4_release_prompt.py -q

覆盖（验收「提示链路跑通」）：
  新版发布 + 本机旧版（指纹不符）→ 提示「建议同步」+ 可执行步骤
  新版发布 + 本机缺失 → 提示安装
  新版发布 + 本机已新版（指纹一致）→ 不打扰（零提示噪音）
  提示链路：expected_dir 更新（发布产物）→ 提示生成，全离线确定性
  release 缺字段拒绝；本函数零写入

虚构纪律：全虚构；零网络。
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from release_sync_prompt import release_sync_prompt  # noqa: E402

OLD_FM = """---
name: zh-demo
description: 演示技能（旧版，虚构）。
license: MIT
metadata:
  when_not_to_use: x（虚构）
  output: y（虚构）
  compatibility: z（虚构）
---

# 演示（旧）
"""
NEW_FM = OLD_FM.replace("旧版", "新版")

TOOLS = {"claude": "claude/skills"}


def setup(root: Path, *, installed_fm=OLD_FM, with_expected="1.0.0"):
    """expected_dir=发布流水线产物（新版）；工具目录=本机装机（可旧可新）。"""
    expected = root / "expected" / "zh-demo"
    expected.mkdir(parents=True)
    (expected / "SKILL.md").write_text(NEW_FM, encoding="utf-8")  # 新版
    (expected.parent / "version.txt").write_text(with_expected + "\n", encoding="utf-8")
    tool_root = root / TOOLS["claude"]
    d = tool_root / "zh-demo"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(installed_fm, encoding="utf-8")   # 本机
    return root / "expected", {t: str(root / p) for t, p in TOOLS.items()}, root / "expected"

RELEASE = {"skill_id": "zh-demo", "version": "2.0.0"}


class ReleasePromptTests(unittest.TestCase):
    def test_old_installed_gets_sync_prompt_with_steps(self):
        with tempfile.TemporaryDirectory() as td:
            expected, roots, src = setup(Path(td), installed_fm=OLD_FM)
            out = release_sync_prompt(expected, roots, RELEASE, source_dir=src)
            self.assertEqual(len(out["prompts"]), 1)
            p = out["prompts"][0]
            self.assertIn("建议同步", p["message"])
            self.assertIn("2.0.0", p["message"])
            self.assertTrue(any(s.startswith(("rm -rf", "cp -R")) for s in p["steps"]))

    def test_missing_install_prompt(self):
        with tempfile.TemporaryDirectory() as td:
            expected, roots, src = setup(Path(td))
            import shutil
            shutil.rmtree(Path(roots["claude"]) / "zh-demo")
            out = release_sync_prompt(expected, roots, RELEASE, source_dir=src)
            self.assertEqual(out["prompts"][0]["status"], "missing")

    def test_up_to_date_silent(self):
        with tempfile.TemporaryDirectory() as td:
            expected, roots, _ = setup(Path(td), installed_fm=NEW_FM)  # 本机已是新版
            out = release_sync_prompt(expected, roots, RELEASE, source_dir=Path(td) / "expected")
            self.assertEqual(out["prompts"], [])               # 不打扰

    def test_zero_write_and_validation(self):
        with tempfile.TemporaryDirectory() as td:
            expected, roots, src = setup(Path(td))
            before = sorted(str(p) for p in Path(td).rglob("*"))
            release_sync_prompt(expected, roots, RELEASE, source_dir=src)
            self.assertEqual(before, sorted(str(p) for p in Path(td).rglob("*")))
            with self.assertRaises(ValueError):
                release_sync_prompt(expected, roots, {"skill_id": "x"})


if __name__ == "__main__":
    unittest.main()
