"""PRD-148/T5 验收演示（trend #744）。

虚构新 skill 样例（测试夹具，不入 skills/ 正式目录）完整走一遍瘦身门：
  阶段① 未三处登记 → 不视为 published，不要求记录（exit 0）；
  阶段② 三处登记（published）无决策记录 → 拒（CI 口径 exit 1，违规文案指向补记录）；
  阶段③ 按 templates/slim-gate-record.md 补决策记录 → 过（exit 0，decision=approved）。
仓内留档一致性：docs/slim-gate/records/2026-10-23-slim-gate-demo-skill.md（示范记录，
虚构 skill）被 slim_gate 采信为有效记录且不破坏真实仓库的门禁判定；
另断言相似检测（T3）对近重复虚构提案给出 ≥0.60 提示（Q2 的输入，merged 变体）。
"""
import contextlib
import importlib.util
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

_sg = importlib.util.spec_from_file_location("slim_gate", REPO / "scripts" / "slim_gate.py")
sg = importlib.util.module_from_spec(_sg)
_sg.loader.exec_module(sg)
_ss = importlib.util.spec_from_file_location("skill_similarity",
                                             REPO / "scripts" / "skill_similarity.py")
ss = importlib.util.module_from_spec(_ss)
_ss.loader.exec_module(ss)

DEMO_SKILL = "slim-gate-demo-skill"
BASELINE_SKILL = "old-skill"
DEMO_RECORD = REPO / "docs" / "slim-gate" / "records" / "2026-10-23-slim-gate-demo-skill.md"
DEMO_DOC = REPO / "docs" / "slim-gate" / "demo-2026-10-23.md"

SKILL_MD = """---
name: slim-gate-demo-skill
description: Use when demoing the slim gate walkthrough on a fixture. 夹具演示走门用（虚构）。
allowed-tools: Bash, Read
---

# 瘦身门演示 skill（虚构提案）

**一句话：只存在于测试夹具，演示瘦身门三阶段，不入正式 skills/。**

## 步骤

1. 三处登记后跑发布检查；
2. 按模板补决策记录后复检。

## 命令

```bash
python3 scripts/slim_gate.py   # 退出码：0=过，1=拒（CI 口径）
```
"""


def write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def build_fixture(root):
    """最小仓库骨架：1 个基线 skill（三处登记齐全）+ 记录目录 + 模板占位。"""
    root = Path(root)
    for s in (BASELINE_SKILL,):
        write(root / "skills" / s / "SKILL.md",
              "---\nname: %s\ndescription: Use when demo baseline. 基线演示。\n---\n\n正文。\n" % s)
        write(root / "plugins" / "livepowers-demo" / "skills" / s / "SKILL.md",
              "---\nname: %s\ndescription: Use when demo baseline. 基线演示。\n---\n\n正文。\n" % s)
    router_rows = "| 场景0 | `%s` |" % BASELINE_SKILL
    write(root / "skills" / "using-livepowers" / "SKILL.md",
          "# 路由\n\n| 场景 | skill |\n|---|---|\n%s\n" % router_rows)
    write(root / "README.md", "# demo\n\n| 场景 | skill |\n|---|---|\n%s\n" % router_rows)
    write(root / "docs" / "slim-gate" / "records" / "README.md", "# 记录目录\n")
    write(root / "docs" / "slim-gate" / "baseline-fixture.md",
          "# 基线\n\n- `%s`\n" % BASELINE_SKILL)
    write(root / "templates" / "slim-gate-record.md",
          "# 模板\n---\nrecord: SG-x\nskill: x\ndecision: approved\n---\n")
    return root


def register_three_anchors(root):
    """把虚构 skill 补齐三处登记（①路由表 ②根 README 技能表 ③插件拷贝）= published。"""
    write(root / "skills" / DEMO_SKILL / "SKILL.md", SKILL_MD)
    write(root / "plugins" / "livepowers-demo" / "skills" / DEMO_SKILL / "SKILL.md", SKILL_MD)
    row = "| 场景1 | `%s` |" % DEMO_SKILL
    for rel in ("skills/using-livepowers/SKILL.md", "README.md"):
        p = root / rel
        p.write_text(p.read_text(encoding="utf-8").rstrip("\n") + "\n" + row + "\n",
                     encoding="utf-8")


def run_gate(root):
    """CI 口径：对夹具仓库执行 slim_gate 的 CLI 判定路径，返回退出码（0=过 / 1=拒）。"""
    old = sg.REPO
    sg.REPO = str(root)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return sg.main([])
    finally:
        sg.REPO = old


class TestWalkthrough(unittest.TestCase):
    """三阶段走门：未登记不拦 → published 无记录拒（exit 1）→ 补记录过（exit 0）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = build_fixture(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stage1_unpublished_needs_no_record(self):
        write(self.root / "skills" / DEMO_SKILL / "SKILL.md", SKILL_MD)   # 只起草，未登记
        self.assertEqual(run_gate(self.root), 0)
        _, lines = sg.check(str(self.root))
        self.assertTrue(any("未发布" in l and DEMO_SKILL in l for l in lines))

    def test_stage2_published_without_record_rejected(self):
        register_three_anchors(self.root)
        self.assertEqual(run_gate(self.root), 1)                          # CI 口径：拒
        violations, _ = sg.check(str(self.root))
        self.assertEqual(len(violations), 1)
        self.assertIn(DEMO_SKILL, violations[0])
        self.assertIn("缺瘦身门决策记录", violations[0])
        self.assertIn("templates/slim-gate-record.md", violations[0])

    def test_stage3_record_added_passes(self):
        register_three_anchors(self.root)
        shutil.copyfile(DEMO_RECORD,
                        self.root / "docs" / "slim-gate" / "records"
                        / "2026-10-23-slim-gate-demo-skill.md")
        self.assertEqual(run_gate(self.root), 0)                          # CI 口径：过
        _, lines = sg.check(str(self.root))
        self.assertTrue(any(DEMO_SKILL in l and "decision=approved" in l for l in lines))
        self.assertTrue(any("PASS" in l for l in lines))

    def test_stage3_negative_rejected_record_still_fails(self):
        # 反向对照：补的是 rejected 记录（终态）→ 依旧 exit 1
        register_three_anchors(self.root)
        text = DEMO_RECORD.read_text(encoding="utf-8") \
            .replace("decision: approved", "decision: rejected")
        write(self.root / "docs" / "slim-gate" / "records"
              / "2026-10-23-slim-gate-demo-skill.md", text)
        self.assertEqual(run_gate(self.root), 1)


class TestRepoRecordArchive(unittest.TestCase):
    """仓内留档：示范记录有效、skill 虚构不在 skills/，真实仓库门禁不被破坏。"""

    def test_sample_record_valid_and_fictional(self):
        latest, invalid = sg.load_records(str(REPO))
        self.assertEqual(invalid, [])
        rec = latest.get(DEMO_SKILL)
        self.assertIsNotNone(rec, "示范记录未被 slim_gate 采信")
        self.assertEqual(rec["decision"], "approved")
        self.assertEqual(rec["status"], "provisional")          # 构造证据 → provisional
        self.assertEqual(rec["_file"], "2026-10-23-slim-gate-demo-skill.md")
        self.assertNotEqual(rec.get("proposer"), rec.get("reviewer"))
        self.assertFalse((REPO / "skills" / DEMO_SKILL).exists(),
                         "虚构 skill 不得进入 skills/ 正式目录")
        self.assertNotIn(DEMO_SKILL, sg.load_baseline(str(REPO)))

    def test_real_repo_gate_still_passes_with_sample_record(self):
        proc = subprocess.run([sys.executable, str(REPO / "scripts" / "slim_gate.py")],
                              capture_output=True, text=True, cwd=str(REPO))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("PASS", proc.stdout)
        self.assertIn("决策记录：1 条", proc.stdout)             # 样例记录计入但不违规

    def test_docs_link_archive(self):
        self.assertTrue(DEMO_DOC.is_file(), "缺案例留档文档 demo-2026-10-23.md")
        demo = DEMO_DOC.read_text(encoding="utf-8")
        for token in ("exit 1", "exit 0", "缺瘦身门决策记录", "decision=approved",
                      "rejected", "merged", "provisional"):
            self.assertIn(token, demo)
        records_readme = (REPO / "docs" / "slim-gate" / "records" / "README.md") \
            .read_text(encoding="utf-8")
        self.assertIn("2026-10-23-slim-gate-demo-skill.md", records_readme)
        gate_readme = (REPO / "docs" / "slim-gate" / "README.md").read_text(encoding="utf-8")
        self.assertIn("demo-2026-10-23.md", gate_readme)


class TestSimilarityHintVariant(unittest.TestCase):
    """变体：近重复虚构提案 → 相似检测提示（Q2 输入，merged 处置的依据）。"""

    def test_near_duplicate_gets_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            desc = ("Use when planning overnight batch loops with stop-loss "
                    "and handover budgets. 夜间批处理规划演示（虚构）。")
            for name in ("demo-night-planning-twin", "demo-night-planning"):
                write(Path(tmp) / name / "SKILL.md",
                      "---\nname: %s\ndescription: %s\n---\n\n# 演示\n\n## 步骤\n\n1. 走门。\n"
                      % (name, desc))
            skills = ss.load_skills(tmp)
            self.assertEqual(len(skills), 2)
            pairs, stats = ss.scan(skills)
            self.assertGreaterEqual(stats["pairs_hint"], 1)     # 重复度指标 ≥1 对提示
            self.assertEqual(len(pairs), 1)
            pair = pairs[0]
            self.assertGreaterEqual(pair["score"], 0.60)
            self.assertEqual({pair["a"], pair["b"]},
                             {"demo-night-planning-twin", "demo-night-planning"})
            self.assertIn(pair["field"], ("name", "en", "zh", "headings"))
            # 提示只作 Q2 输入：处置走决策记录（merged 括注目标）；脚本自身不判定、不拦截
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ss.main(["--skills-dir", tmp, "--top", "5"]), 0)


if __name__ == "__main__":
    unittest.main()
