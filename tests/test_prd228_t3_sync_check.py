# -*- coding: utf-8 -*-
"""PRD-228/T3 测试：配置同步检查——检出漂移并提示（trend #1142）。

运行：uv run --with pytest python -m pytest tests/test_prd228_t3_sync_check.py -q

覆盖（验收「人为制造的漂移可被检出并提示」）：全 match 幂等基线、手改生成文件
检出（含差异行 note）、文件缺失检出、源配置变更检出（指纹变更）、PRD-200 清单
衔接（技能漂移并入同一报告、status 词表一致）、prompts 有漂移才非空、确定性。
零网络；路径全部临时目录注入。
"""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from config_sync_check import config_sync_check, source_fingerprint  # noqa: E402
from tool_config_gen import generate_tool_configs  # noqa: E402

import tempfile  # noqa: E402

SOURCE = {
    "skills_root": "~/skills/livepowers",
    "model": "glm-5.3-flash",
    "allowed_commands": ["lp hook watch", "lp evidence add"],
    "telemetry_enabled": False,
}


def _distribute(tmp: str, source=None):
    out = Path(tmp) / "dist"
    generate_tool_configs(source or SOURCE, out)
    return out


class 漂移检出Tests(unittest.TestCase):
    def test_fresh_distribution_all_match(self):
        """T2 刚分发完 → 四工具全 match（幂等基线）。"""
        with tempfile.TemporaryDirectory() as tmp:
            out = _distribute(tmp)
            report = config_sync_check(SOURCE, out)
            self.assertEqual(report["schema"], "config-sync-check/v1")
            self.assertEqual(report["summary"]["drift"], 0)
            self.assertEqual(report["summary"]["match"], 4)
            self.assertEqual(report["prompts"], [])

    def test_manual_edit_detected_with_field_hint(self):
        """人为手改生成文件 → content_mismatch + 差异行 note（验收核心）。"""
        with tempfile.TemporaryDirectory() as tmp:
            out = _distribute(tmp)
            claude = out / "claude" / "settings.json"
            edited = json.loads(claude.read_text(encoding="utf-8"))
            edited["model"] = "手改的模型"
            claude.write_text(json.dumps(edited, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
            report = config_sync_check(SOURCE, out)
            bad = [i for i in report["instances"] if i["tool"] == "claude"]
            self.assertEqual(len(bad), 1)
            self.assertEqual(bad[0]["status"], "content_mismatch")
            self.assertEqual(bad[0]["fp_match"], "content_mismatch")
            self.assertIn("不一致", bad[0]["note"])
            self.assertEqual(report["summary"]["config_drift"], 1)
            self.assertTrue(any("重新分发" in p for p in report["prompts"]))

    def test_missing_file_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = _distribute(tmp)
            (out / "pi" / "agent.toml").unlink()
            report = config_sync_check(SOURCE, out)
            pi = [i for i in report["instances"] if i["tool"] == "pi"][0]
            self.assertEqual(pi["status"], "missing")
            self.assertIn("不存在", pi["note"])

    def test_source_change_changes_fingerprint_and_drift(self):
        """源配置变更 → 指纹变化 + 全部配置漂移（改源后须重发的提示）。"""
        with tempfile.TemporaryDirectory() as tmp:
            out = _distribute(tmp)
            changed = dict(SOURCE, model="另一个模型")
            report = config_sync_check(changed, out)
            self.assertNotEqual(report["source_fingerprint"], source_fingerprint(SOURCE))
            self.assertEqual(report["summary"]["config_drift"], 4)


class PRD200衔接Tests(unittest.TestCase):
    def test_skills_drift_merged_into_same_report(self):
        """传 expected_skills_dir + skills_roots：技能装机现状并入同一清单。"""
        with tempfile.TemporaryDirectory() as tmp:
            out = _distribute(tmp)
            skills = Path(tmp) / "skills" / "demo-skill"
            skills.mkdir(parents=True)
            (skills / "SKILL.md").write_text("---\nname: demo-skill\n---\n占位", encoding="utf-8")
            tool_root = Path(tmp) / "toolroot" / "demo-skill"
            tool_root.mkdir(parents=True)
            (tool_root / "SKILL.md").write_text("被改过的内容", encoding="utf-8")
            report = config_sync_check(
                SOURCE, out,
                expected_skills_dir=Path(tmp) / "skills",
                skills_roots={"claude": str(Path(tmp) / "toolroot")})
            scopes = {i.get("scope") for i in report["instances"]}
            self.assertIn("skills", scopes)
            skill_instances = [i for i in report["instances"] if i.get("scope") == "skills"]
            self.assertEqual(skill_instances[0]["status"], "installed")  # PRD-200 口径
            self.assertEqual(skill_instances[0]["fp_match"], "content_mismatch")
            self.assertEqual(report["summary"]["skills_drift"], 1)
            self.assertTrue(any("PRD-200" in p for p in report["prompts"]))
            # status 词表与 PRD-200 sync-check-v1 同族
            self.assertTrue(all(i["status"] in ("match", "content_mismatch", "missing",
                                                "installed", "incomplete")
                                for i in report["instances"]))


class 纪律Tests(unittest.TestCase):
    def test_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = _distribute(tmp)
            (out / "cursor" / "rules.md").write_text("手改\n", encoding="utf-8")
            one = config_sync_check(SOURCE, out)
            two = config_sync_check(SOURCE, out)
            self.assertEqual(json.dumps(one, ensure_ascii=False, sort_keys=True),
                             json.dumps(two, ensure_ascii=False, sort_keys=True))

    def test_missing_source_field_rejected(self):
        with self.assertRaises(Exception):
            config_sync_check({"model": "x"}, ".")

    def test_fingerprint_stable(self):
        self.assertEqual(source_fingerprint(SOURCE), source_fingerprint(dict(SOURCE)))
        self.assertNotEqual(source_fingerprint(SOURCE), source_fingerprint(dict(SOURCE, model="y")))


if __name__ == "__main__":
    unittest.main()
