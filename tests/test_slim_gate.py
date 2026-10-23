"""PRD-148/T2：scripts/slim_gate.py 的单元测试。

验收口径（trend #741）：无记录不可标 published；有记录→过、无记录→拒。
用临时目录搭最小仓库骨架（基线 skill + 三处登记锚点 + 决策记录目录），
另对真实仓库做全绿冒烟。
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "slim_gate.py"
_spec = importlib.util.spec_from_file_location("slim_gate", SCRIPT)
sg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sg)

REAL_REPO = Path(__file__).resolve().parents[1]

BASELINE_SKILL = "old-skill"
NEW_SKILL = "new-skill"

APPROVED_RECORD = """---
record: SG-20261023-01
skill: new-skill
proposer: alice
reviewer: bob
date: 2026-10-23
trigger: new-proposal
ladder:
  q1_exist: pass
  q2_merge: pass
  q3_boundary: pass
  q4_worth: pass
evidence:
  type: real-record
  link: docs/slim-gate/records/2026-10-23-new-skill.md
decision: approved
status: final
---

## 结论

approved。

## 五问判定

- Q1–Q4 全 pass。

## 跳过了什么、有什么风险

无（演示夹具）。
"""

REJECTED_RECORD = APPROVED_RECORD.replace("SG-20261023-01", "SG-20261023-02") \
    .replace("decision: approved", "decision: rejected")


def write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def build_fixture(root, with_new_skill=False):
    """最小仓库：1 个基线 skill（三处登记齐全）+ 锚点文件 + 空记录目录。"""
    root = Path(root)
    skills = [BASELINE_SKILL] + ([NEW_SKILL] if with_new_skill else [])
    for s in skills:
        write(root / "skills" / s / "SKILL.md",
              "---\nname: %s\ndescription: Use when demo. 演示用。\n---\n\n正文。\n" % s)
        write(root / "plugins" / "livepowers-demo" / "skills" / s / "SKILL.md",
              "---\nname: %s\ndescription: Use when demo. 演示用。\n---\n\n正文。\n" % s)
    router_rows = "\n".join("| 场景%d | `%s` |" % (i, s) for i, s in enumerate(skills))
    write(root / "skills" / "using-livepowers" / "SKILL.md",
          "# 路由\n\n| 场景 | skill |\n|---|---|\n%s\n" % router_rows)
    write(root / "README.md", "# demo\n\n| 场景 | skill |\n|---|---|\n%s\n" % router_rows)
    write(root / "docs" / "slim-gate" / "records" / "README.md", "# 记录目录\n")
    write(root / "docs" / "slim-gate" / "baseline-2026-10-23.md",
          "# 基线\n\n- `%s`\n" % BASELINE_SKILL)
    write(root / "templates" / "slim-gate-record.md",
          "# 模板\n---\nrecord: SG-x\nskill: x\ndecision: approved\n---\n")
    return root


class TestGateRules(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = build_fixture(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def add_record(self, text, name="2026-10-23-new-skill.md"):
        write(self.root / "docs" / "slim-gate" / "records" / name, text)

    def rebuild(self, with_new_skill):
        return build_fixture(self.root, with_new_skill=with_new_skill)

    def test_baseline_only_pass(self):
        violations, lines = sg.check(str(self.root))
        self.assertEqual(violations, [])
        self.assertTrue(any("PASS" in l for l in lines))

    def test_new_skill_without_record_rejected(self):
        self.rebuild(with_new_skill=True)
        violations, _ = sg.check(str(self.root))
        self.assertEqual(len(violations), 1)
        self.assertIn("缺瘦身门决策记录", violations[0])
        self.assertIn(NEW_SKILL, violations[0])

    def test_new_skill_with_approved_record_passes(self):
        self.rebuild(with_new_skill=True)
        self.add_record(APPROVED_RECORD)
        violations, lines = sg.check(str(self.root))
        self.assertEqual(violations, [])
        self.assertTrue(any("decision=approved" in l for l in lines))

    def test_new_skill_with_rejected_record_rejected(self):
        self.rebuild(with_new_skill=True)
        self.add_record(REJECTED_RECORD)
        violations, _ = sg.check(str(self.root))
        self.assertEqual(len(violations), 1)
        self.assertIn("不是 approved", violations[0])

    def test_unpublished_new_skill_needs_no_record(self):
        # new-skill 只在 skills/ 里，三处登记缺两处：不视为 published，不要求记录
        write(self.root / "skills" / NEW_SKILL / "SKILL.md",
              "---\nname: %s\ndescription: Use when demo. 演示用。\n---\n\n正文。\n" % NEW_SKILL)
        violations, lines = sg.check(str(self.root))
        self.assertEqual(violations, [])
        self.assertTrue(any("未发布" in l for l in lines))

    def test_proposer_equals_reviewer_invalid(self):
        self.rebuild(with_new_skill=True)
        self.add_record(APPROVED_RECORD.replace("reviewer: bob", "reviewer: alice"))
        violations, _ = sg.check(str(self.root))
        self.assertEqual(len(violations), 1)   # 记录无效 → 视同缺记录

    def test_bad_decision_enum_invalid(self):
        self.rebuild(with_new_skill=True)
        self.add_record(APPROVED_RECORD.replace("decision: approved", "decision: maybe"))
        violations, _ = sg.check(str(self.root))
        self.assertEqual(len(violations, ), 1)

    def test_latest_record_wins(self):
        self.rebuild(with_new_skill=True)
        self.add_record(APPROVED_RECORD, name="2026-10-20-new-skill.md")
        self.add_record(REJECTED_RECORD.replace("date: 2026-10-23", "date: 2026-10-25"),
                        name="2026-10-25-new-skill.md")
        violations, _ = sg.check(str(self.root))
        self.assertEqual(len(violations), 1)   # 最新记录是 rejected

    def test_records_readme_not_counted(self):
        self.rebuild(with_new_skill=True)
        violations, lines = sg.check(str(self.root))
        self.assertFalse(any("README.md 无效" in l for l in lines))


class TestTemplateAndRealRepo(unittest.TestCase):
    def test_template_has_required_frontmatter(self):
        t = (REAL_REPO / "templates" / "slim-gate-record.md").read_text(encoding="utf-8")
        for key in ("record:", "skill:", "proposer:", "reviewer:", "date:", "trigger:",
                    "ladder:", "q1_exist:", "q2_merge:", "q3_boundary:", "q4_worth:",
                    "evidence:", "decision:", "status:", "safety_exempt:"):
            self.assertIn(key, t)
        self.assertIn("跳过了什么、有什么风险", t)

    def test_real_repo_passes(self):
        proc = subprocess.run([sys.executable, str(SCRIPT)],
                              capture_output=True, text=True, cwd=str(REAL_REPO))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("PASS", proc.stdout)

    def test_real_repo_report_only_always_zero(self):
        proc = subprocess.run([sys.executable, str(SCRIPT), "--report-only"],
                              capture_output=True, text=True, cwd=str(REAL_REPO))
        self.assertEqual(proc.returncode, 0)

    def test_skill_template_mentions_gate(self):
        t = (REAL_REPO / "templates" / "skill.md").read_text(encoding="utf-8")
        self.assertIn("瘦身门", t)
        self.assertIn("docs/slim-gate/records/", t)


if __name__ == "__main__":
    unittest.main()
