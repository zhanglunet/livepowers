# -*- coding: utf-8 -*-
"""PRD-130/T3+T4+T5 测试与验收：六路 adapter + CI 一致性校验 + 5 插件验收
（trend #651/#652/#653）。

T3 口径（issue #651）：OpenCode / Copilot / Pi adapter——三种格式生成。
T4 口径（issue #652）：单 skill 生成物一致性校验——生成物未手改可机判。
T5 口径（issue #653）：5 个插件六路全部生成并抽测安装。

Pi 的「用户笔记本实测可用」需用户环境——本验收交付生成与一致性机判，
实测留验收人（诚实边界，见 PR 描述）。
"""
import json
import shutil
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from harness_matrix import (MATRIX_V2, build_output, generate_matrix,
                            generate_outputs, verify_unmodified)

REAL_SKILLS = ["env-scan-ontology", "crystallize-to-system1", "oltp-action-safety",
               "digital-role-spec", "using-livepowers"]


class T3AdapterTests(unittest.TestCase):
    def test_six_routes_generated(self):
        out = REPO / ".tmp-t3-out"
        manifest = generate_outputs("env-scan-ontology", str(REPO / "skills" / "env-scan-ontology"), str(out))
        self.assertEqual(len(manifest["artifacts"]), 6)
        self.assertEqual({a["harness"] for a in manifest["artifacts"]}, set(MATRIX_V2))
        shutil.rmtree(out, ignore_errors=True)

    def test_frontmatter_policy_per_tool(self):
        src = (REPO / "skills" / "env-scan-ontology" / "SKILL.md").read_text(encoding="utf-8")
        # claude-code / pi 保留 frontmatter；codex / cursor / opencode / copilot 剥离
        for harness, keep in (("claude-code", True), ("pi", True),
                              ("codex", False), ("cursor", False),
                              ("opencode", False), ("copilot", False)):
            text = build_output(harness, "env-scan-ontology", src)
            if keep:
                self.assertTrue(text.startswith("---"), f"{harness} 保留 frontmatter 在文件头")
            else:
                self.assertFalse(text.startswith("---"), f"{harness} 剥离 frontmatter")
                self.assertTrue(text.startswith("<!--"), f"{harness} 溯源头置顶")

    def test_semantics_preserved_body_verbatim(self):
        src = (REPO / "skills" / "oltp-action-safety" / "SKILL.md").read_text(encoding="utf-8")
        body_marker = src.split("---", 2)[-1].strip().splitlines()[0]
        for harness in MATRIX_V2:
            text = build_output(harness, "oltp-action-safety", src)
            self.assertIn(body_marker, text, f"{harness} 正文语义必须原样保留")

    def test_codex_opencode_agents_md_copilot_instructions(self):
        self.assertEqual(MATRIX_V2["codex"]["entry"], "AGENTS.md")
        self.assertEqual(MATRIX_V2["opencode"]["entry"], "opencode/AGENTS.md")
        self.assertEqual(MATRIX_V2["copilot"]["entry"], "copilot-instructions.md")
        self.assertIn("pi", MATRIX_V2)


class T4ConsistencyTests(unittest.TestCase):
    def test_verify_passes_on_fresh_generation(self):
        out = REPO / ".tmp-t4-out"
        generate_outputs("digital-role-spec", str(REPO / "skills" / "digital-role-spec"), str(out))
        result = verify_unmodified(str(REPO / "skills" / "digital-role-spec"), str(out))
        self.assertTrue(result["ok"])
        self.assertEqual(result["checked"], 6)
        shutil.rmtree(out, ignore_errors=True)

    def test_verify_catches_hand_edit(self):
        out = REPO / ".tmp-t4b-out"
        skill = "oltp-action-safety"
        generate_outputs(skill, str(REPO / "skills" / skill), str(out))
        target = out / "codex" / "AGENTS.md"
        marker = "do not hand-edit"
        target.write_text(target.read_text(encoding="utf-8").replace(marker, "hand-edited-marker"), encoding="utf-8")
        result = verify_unmodified(str(REPO / "skills" / skill), str(out))
        self.assertFalse(result["ok"])
        self.assertEqual(result["drift"], [{"harness": "codex", "issue": "hand-edited"}])
        shutil.rmtree(out, ignore_errors=True)


class T5AcceptanceTests(unittest.TestCase):
    def test_five_skills_six_routes_all_generated_and_consistent(self):
        out = REPO / ".tmp-t5-out"
        total = 0
        for skill in REAL_SKILLS:
            manifest = generate_outputs(skill, str(REPO / "skills" / skill), str(out))
            self.assertEqual(len(manifest["artifacts"]), 6, skill)
            total += len(manifest["artifacts"])
            result = verify_unmodified(str(REPO / "skills" / skill), str(out))
            self.assertTrue(result["ok"], f"{skill} 一致性校验失败")
        self.assertEqual(total, 30, "5 插件 × 6 路 = 30 产物")

    def test_install_smoke_claude_code_skill_loadable(self):
        # 抽测安装（本地等价口径）：claude-code 路产物拷入模拟技能目录，
        # frontmatter 可解析、name 与插件一致。npx skills add 实测留验收人。
        out = REPO / ".tmp-t5b-out"
        skill = "using-livepowers"
        generate_outputs(skill, str(REPO / "skills" / skill), str(out))
        target_dir = out / "_installed" / skill
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(out / "claude-code" / "SKILL.md", target_dir / "SKILL.md")
        text = (target_dir / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---"), "SKILL.md 保留 frontmatter")
        self.assertIn(f"name: {skill}", text)
        shutil.rmtree(out, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
