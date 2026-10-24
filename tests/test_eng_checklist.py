"""PRD-147/T2：scripts/eng_checklist.py 的单元测试。

用临时目录搭最小仓库骨架，验证机检条目（打分、豁免、退出码、CI report-only）。
不依赖真实仓库状态；对真实仓库只做 report-only 冒烟（不判分）。
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "eng_checklist.py"
_spec = importlib.util.spec_from_file_location("eng_checklist", SCRIPT)
ec = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ec)

REAL_REPO = Path(__file__).resolve().parents[1]

SKILL_MD = """---
name: demo-skill
description: Use when a demo checklist fixture runs. 演示夹具运行时使用。
allowed-tools: Bash, Read
---

# 演示技能

**一句话：演示用。**

## 步骤

1. 跑示例命令。

## 命令

```bash
lp demo run   # 输出结论行，退出码 0
```
"""

PLUGIN_README = """# livepowers-demo

演示插件：用途简介在开篇。

## 安装

```
/plugin install livepowers-demo@livepowers-marketplace
```

## 快速上手

1. 装好后跑 `/lp-demo`，退出码 0 即成功。

## 配置项

| 配置 | 位置 | 说明 |
|---|---|---|
| `DEMO_HOME` | 环境变量 | 数据区位置 |
"""


def write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def build_fixture(root):
    root = Path(root)
    write(root / "skills" / "demo-skill" / "SKILL.md", SKILL_MD)
    write(root / "skills" / "using-livepowers" / "SKILL.md",
          "# 路由\n\n| 场景 | skill |\n|---|---|\n| 演示 | `demo-skill` |\n")
    write(root / "tests" / "demo-skill" / "test_examples.py",
          '"""demo-skill 测试。"""\n# 契约（L1）/ 示例（L2）/ 反例（L3）三层\n'
          '# skipIf 需真实环境\n')
    trig = root / "tests" / "triggers" / "demo-skill.jsonl"
    lines = [{'prompt': '正例%d' % i, 'expect': ['demo-skill'], 'reject': ['other']}
             for i in range(3)]
    lines += [{'prompt': '反例%d' % i, 'expect': ['other'], 'reject': ['demo-skill']}
              for i in range(2)]
    write(trig, "\n".join(json.dumps(x) for x in lines) + "\n")
    # 插件层：README 四节 + 逐字节拷贝 + manifest 路径
    write(root / "plugins" / "livepowers-demo" / "README.md", PLUGIN_README)
    write(root / "plugins" / "livepowers-demo" / "skills" / "demo-skill" / "SKILL.md", SKILL_MD)
    write(root / "plugins" / "livepowers-demo" / ".claude-plugin" / "plugin.json",
          json.dumps({"name": "livepowers-demo", "icon": "assets/icon.svg"}))
    write(root / "plugins" / "livepowers-demo" / "assets" / "icon.svg", "<svg/>")
    # 仓库级
    write(root / "README.md", "# demo\n\n| 场景 | skill |\n|---|---|\n| 演示 | `demo-skill` |\n")
    write(root / "CHANGELOG.md", "# Changelog\n\n## [Unreleased]\n\n- `demo-skill`\n")
    write(root / "tests" / "test_repo.py", "class TestNoIdentifyingInfo(unittest.TestCase):\n    pass\n")
    write(root / ".github" / "workflows" / "test.yml",
          'matrix:\n  python: ["3.9", "3.11", "3.13"]\n  LP_DENYLIST: ${{ vars.LP_DENYLIST }}\n'
          '        run: python -m unittest tests.test_repo.TestNoIdentifyingInfo -v\n')
    write(root / "examples" / "walkthrough.sh", "#!/usr/bin/env bash\nexit 0\n")
    (root / "skills" / "delivery-chain" / "examples" / "minimal-chain").mkdir(parents=True)
    write(root / "skills" / "delivery-chain" / "SKILL.md",
          "---\nname: delivery-chain\ndescription: Use when chain. 链演示。\nallowed-tools: Bash\n---\n\n链演示。\n")
    write(root / "templates" / "parallel-experts" / "README.md",
          "# 并行专家模板\n\n文件表：`agents/specialist.md`。\n")
    write(root / "templates" / "parallel-experts" / "agents" / "specialist.md", "# 专家\n")
    write(root / "hooks" / "keep.txt", "\n")
    # 根 manifests（E-S02 仓库层）
    write(root / ".claude-plugin" / "plugin.json",
          json.dumps({"icon": ".claude-plugin/assets/icon.svg"}))
    write(root / ".claude-plugin" / "assets" / "icon.svg", "<svg/>")
    write(root / ".claude-plugin" / "marketplace.json",
          json.dumps({"plugins": [{"source": "./plugins/livepowers-demo"}]}))
    write(root / ".cursor-plugin" / "marketplace.json",
          json.dumps({"plugins": [{"source": "plugins/livepowers-demo"}]}))
    write(root / ".cursor-plugin" / "plugin.json",
          json.dumps({"skills": "./skills/", "hooks": "./hooks/hooks-cursor.json"}))
    write(root / "hooks" / "hooks-cursor.json", "{}\n")
    return root


def by_item(results, item, obj=None):
    return [r for r in results if r.item == item and (obj is None or r.obj == obj)]


class TestPassFixture(unittest.TestCase):
    """全绿夹具：机检条目全部 2 分（人工项除外），判定 PASS。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = build_fixture(self._tmp.name)
        self.c = ec.Checker(repo=str(self.root))

    def tearDown(self):
        self._tmp.cleanup()

    def test_skill_items(self):
        res = self.c.run_skill("demo-skill")
        scores = {r.item: r.score for r in res}
        self.assertEqual(scores["E-T01"], 2)
        self.assertEqual(scores["E-T02"], 2)
        self.assertEqual(scores["E-D02"], 2)
        self.assertEqual(scores["E-D03"], 2)
        self.assertEqual(scores["E-D04"], 2)
        self.assertEqual(scores["E-D05"], 2)
        self.assertEqual(scores["E-X01"], 2)
        self.assertEqual(scores["E-S03"], 2)
        self.assertIsNone(scores["E-T03"])   # 人工
        self.assertIsNone(scores["E-S04"])   # 写操作类判定交人工

    def test_plugin_and_repo_items(self):
        res, skills = self.c.run_plugin("livepowers-demo")
        self.assertEqual(skills, ["demo-skill"])
        scores = {r.item: r.score for r in res if r.obj == "plugin:livepowers-demo"}
        self.assertEqual(scores["E-T04"], 2)
        self.assertEqual(scores["E-D01"], 2)
        self.assertEqual(scores["E-S01"], 2)
        self.assertEqual(scores["E-S02"], 2)
        self.assertEqual(scores["E-S05"], 2)
        repo_scores = {r.item: r.score for r in self.c.run_repo()}
        self.assertEqual(repo_scores["E-X02"], 2)
        self.assertEqual(repo_scores["E-X04"], 2)
        self.assertEqual(repo_scores["E-S01"], 2)
        self.assertEqual(repo_scores["E-S02"], 2)
        self.assertEqual(repo_scores["E-S05"], 2)

    def test_verdict_pass(self):
        res, _ = self.c.run_plugin("livepowers-demo")
        res += self.c.run_repo()
        v, ratio = ec.verdict(res)
        self.assertTrue(v.startswith("PASS"), v)
        self.assertGreaterEqual(ratio, 0.9)


class TestFailures(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = build_fixture(self._tmp.name)
        self.c = ec.Checker(repo=str(self.root))

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_trigger_file(self):
        os.remove(self.root / "tests" / "triggers" / "demo-skill.jsonl")
        r = by_item(self.c.run_skill("demo-skill"), "E-T02")[0]
        self.assertEqual((r.score, r.status), (0, "FAIL"))

    def test_thin_trigger_file(self):
        p = self.root / "tests" / "triggers" / "demo-skill.jsonl"
        p.write_text(json.dumps({"prompt": "x", "expect": ["demo-skill"], "reject": []}) + "\n",
                     encoding="utf-8")
        r = by_item(self.c.run_skill("demo-skill"), "E-T02")[0]
        self.assertEqual((r.score, r.status), (1, "PARTIAL"))

    def test_plugin_copy_drift(self):
        p = self.root / "plugins" / "livepowers-demo" / "skills" / "demo-skill" / "SKILL.md"
        p.write_text(SKILL_MD + "\n漂移\n", encoding="utf-8")
        r = by_item(self.c.run_plugin("livepowers-demo")[0], "E-T04")[0]
        self.assertEqual((r.score, r.status), (0, "FAIL"))

    def test_readme_missing_section(self):
        p = self.root / "plugins" / "livepowers-demo" / "README.md"
        p.write_text(p.read_text(encoding="utf-8").replace("## 配置项", "## 其它"),
                     encoding="utf-8")
        r = by_item(self.c.run_plugin("livepowers-demo")[0], "E-D01")[0]
        self.assertEqual((r.score, r.status), (1, "PARTIAL"))

    def test_missing_registration(self):
        (self.root / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
        r = by_item(self.c.run_skill("demo-skill"), "E-D04")[0]
        self.assertEqual((r.score, r.status), (0, "FAIL"))

    def test_no_command_example(self):
        p = self.root / "skills" / "demo-skill" / "SKILL.md"
        p.write_text(SKILL_MD.split("## 命令")[0] + "## 命令\n\n见正文。\n", encoding="utf-8")
        r = by_item(self.c.run_skill("demo-skill"), "E-X01")[0]
        self.assertEqual((r.score, r.status), (0, "FAIL"))

    def test_credential_literal_in_plugin(self):
        # 字面密钥（拼接构造，避免测试源码本身命中扫描模式）
        leak = "api" + "_key = '" + "abcdef0123456789" + "'\n"
        write(self.root / "plugins" / "livepowers-demo" / "leak.txt", leak)
        r = by_item(self.c.run_plugin("livepowers-demo")[0], "E-S01")[0]
        self.assertEqual((r.score, r.status), (0, "FAIL"))

    def test_private_ip_in_skill(self):
        write(self.root / "skills" / "demo-skill" / "notes.md",
              "内网地址 192.168.1.10 请脱敏\n")
        r = self.c.check_s05("skill:demo-skill", ["skills"])
        self.assertEqual((r.score, r.status), (0, "FAIL"))

    def test_manifest_escape_path(self):
        p = self.root / ".claude-plugin" / "marketplace.json"
        p.write_text(json.dumps({"plugins": [{"source": "../outside"}]}), encoding="utf-8")
        r = by_item(self.c.run_repo(), "E-S02")[0]
        self.assertEqual((r.score, r.status), (0, "FAIL"))

    def test_allowed_tools_missing(self):
        p = self.root / "skills" / "demo-skill" / "SKILL.md"
        p.write_text(SKILL_MD.replace("allowed-tools: Bash, Read\n", ""), encoding="utf-8")
        r = by_item(self.c.run_skill("demo-skill"), "E-S03")[0]
        self.assertEqual((r.score, r.status), (0, "FAIL"))

    def test_verdict_fail(self):
        os.remove(self.root / "tests" / "triggers" / "demo-skill.jsonl")
        res, _ = self.c.run_plugin("livepowers-demo")
        v, _ = ec.verdict(res + self.c.run_repo())
        self.assertEqual(v, "FAIL")


class TestExemptions(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = build_fixture(self._tmp.name)
        # 挖一个常规级缺口（E-X02：删掉 walkthrough.sh）
        os.remove(self.root / "examples" / "walkthrough.sh")

    def tearDown(self):
        self._tmp.cleanup()

    def test_exempt_regular_item(self):
        c = ec.Checker(repo=str(self.root),
                       exemptions={("repo", "E-X02"): "EX-20261023-99"})
        r = by_item(c.run_repo(), "E-X02")[0]
        self.assertEqual(r.status, "EXEMPT")
        v, ratio = ec.verdict(c.run_repo())
        self.assertTrue(v.startswith("PASS"), v)   # 豁免后不进分母，不挡判定
        self.assertGreaterEqual(ratio, 0.9)

    def test_blocking_item_not_exemptible(self):
        c = ec.Checker(repo=str(self.root),
                       exemptions={("skill:demo-skill", "E-T02"): "EX-20261023-98"})
        os.remove(self.root / "tests" / "triggers" / "demo-skill.jsonl")
        r = by_item(c.run_skill("demo-skill"), "E-T02")[0]
        self.assertEqual((r.score, r.status), (0, "FAIL"))   # 阻断级豁免不生效
        notes = " ".join(c.manual_notes)
        self.assertIn("台账违规", notes)


class TestCLIOnRealRepo(unittest.TestCase):
    """对真实仓库只做 report-only 冒烟：能出报告、退出码受 --report-only 控制。"""

    def test_report_only_exit_zero(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--plugin", "livepowers-night", "--report-only"],
            capture_output=True, text=True, cwd=str(REAL_REPO))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for token in ("night-loop-planning", "nightly-crystallization-review",
                      "E-T01", "E-S05", "判定"):
            self.assertIn(token, proc.stdout)

    def test_gating_exit_code_is_zero_or_one(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--plugin", "livepowers-night"],
            capture_output=True, text=True, cwd=str(REAL_REPO))
        self.assertIn(proc.returncode, (0, 1))   # FAIL=1、其余 0，不崩

    def test_unknown_skill_rejected(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--skill", "no-such-skill"],
            capture_output=True, text=True, cwd=str(REAL_REPO))
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
