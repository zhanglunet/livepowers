#!/usr/bin/env python3
"""PRD-171/T3：scripts/adversarial_gate.py（对抗验收发布门禁）单元测试。

验收口径（trend #857）：门禁脚本/CI 可测——非 confirmed 不可 published，
缺 findings 即拒。规则（T1 §5 写死 + 瘦身门口径）：
1. 基线外 published skill：缺用例清单即拒；缺 findings.json 即拒；
2. core 全 confirmed 才过；needs_validation + 有效豁免（EX- ID 对象为该
   skill）可过；无豁免即拒；safety 用例不可豁免；rejected 无豁免通道；
3. 基线存量（docs/adversarial-gate/baseline-*.md）不要求；未三处登记的
   skill 不视为 published、不要求；
4. published 锚点沿用瘦身门 published_map（三处登记）；
5. 真实仓库全绿冒烟：存量全在基线内，门禁通过。

夹具一律构造数据（占位符），不含真实主机名 / 账号 / 密钥。Python 3.9 兼容。
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
import adversarial_gate as ag  # noqa: E402
import adversarial_verify as av  # noqa: E402
import slim_gate as sg  # noqa: E402

SCRIPT = os.path.join(REPO, "scripts", "adversarial_gate.py")

SKILL_MD = ("---\nname: {name}\ndescription: Use when testing the gate.\n"
            "allowed-tools: Bash, Read\n---\n\n# 测试用\n\n## 流程\n\n正文（构造）。\n")
ROUTER_MD = "---\nname: using-livepowers\ndescription: router.\n---\n\n# 路由\n\n- `skill-a`\n"


def write_skill(root, name, body=None):
    d = os.path.join(root, "skills", name)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(SKILL_MD.format(name=name) if body is None else body)


def make_published(root, skill="skill-a"):
    """三处登记：①路由表 ②根 README 技能表 ③插件拷贝。"""
    write_skill(root, "using-livepowers", ROUTER_MD)
    write_skill(root, skill)
    with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as f:
        f.write("# repo\n\n技能表：`%s`\n" % skill)
    os.makedirs(os.path.join(root, "plugins", "p1", "skills", skill), exist_ok=True)


def write_baseline(root, names):
    d = os.path.join(root, "docs", "adversarial-gate")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "baseline-2026-10-25.md"), "w", encoding="utf-8") as f:
        f.write("# 基线（构造）\n\n")
        for n in names:
            f.write("- `%s`\n" % n)


def write_exemptions(root, rows=(("EX-20261025-01", "skill:skill-a"),)):
    p = os.path.join(root, "docs", "engineering-checklist")
    os.makedirs(p, exist_ok=True)
    with open(os.path.join(p, "exemptions.md"), "w", encoding="utf-8") as f:
        f.write("# 豁免台账（构造）\n\n| 豁免 ID | 对象 | 条目 |\n|---|---|---|\n")
        for ex_id, obj in rows:
            f.write("| %s | %s | E-X01 | 构造行，仅测试解析 |\n" % (ex_id, obj))


def full_cases(skill="skill-a"):
    """满足 T1 §3 数量下限的一组构造用例（POS-EX/POS-TR/NEG-TR×2/NEG-RED）。"""
    base = {"skill": skill, "claim_source": "skills/%s/SKILL.md#流程" % skill,
            "input": "lp registry find \"<意图占位>\"", "expected": ["退出码 0"]}
    return [
        dict(base, case_id="AC-%s-POS01" % skill, type="POS-EX",
             claim="示例命令重跑退出码 0（构造）", safety=False, priority="core"),
        dict(base, case_id="AC-%s-TR01" % skill, type="POS-TR",
             claim="命中触发场景按流程走完（构造）", safety=False, priority="core"),
        dict(base, case_id="AC-%s-NEG01" % skill, type="NEG-TR",
             claim="边界外场景不触发 1（构造）", safety=False, priority="extended"),
        dict(base, case_id="AC-%s-NEG02" % skill, type="NEG-TR",
             claim="边界外场景不触发 2（构造）", safety=False, priority="extended"),
        dict(base, case_id="AC-%s-RED01" % skill, type="NEG-RED",
             claim="严禁盲目调用写操作（构造）", expected=["不执行写操作"],
             safety=True, priority="core"),
    ]


def write_cases(root, skill, cases):
    d = os.path.join(root, "tests", "adversarial", skill)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "cases.jsonl"), "w", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(c, ensure_ascii=False) for c in cases) + "\n")


def make_record(case, skill="skill-a", seq=1, verdict="confirmed", **kw):
    r = {"record_id": "AV-20261025-%s-%02d" % (skill, seq), "case_id": case["case_id"],
         "verdict": verdict,
         "evidence": "重跑示例命令退出码 0，输出含命中条目（构造）" if verdict == "confirmed" else "",
         "falsification_attempts": (["尝试 A：换输入变体重跑，观察与主张一致，未推翻（构造）"]
                                    if verdict == "confirmed" else []),
         "unresolved_fact": "缺 <环境数据>，无法落定；补验动作：待数据到位后重跑（构造）"
                            if verdict == "needs_validation" else "",
         "disproved_by": "输入 X → 观察 Y，与主张矛盾（构造）" if verdict == "rejected" else "",
         "verifier": "verifier-session-a", "verifier_model": "model-x",
         "author": "author-session-b", "date": "2026-10-25"}
    r.update(kw)
    return r


def write_findings(root, skill, records):
    d = os.path.join(root, "tests", "adversarial", skill)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "findings.json"), "w", encoding="utf-8") as f:
        json.dump({"records": records}, f, ensure_ascii=False, indent=1)


def confirmed_findings(root, skill="skill-a"):
    cases = full_cases(skill)
    write_cases(root, skill, cases)
    write_findings(root, skill,
                   [make_record(c, skill, i + 1) for i, c in enumerate(cases)])
    return cases


def make_root(tmp, published=True, baseline=()):
    root = os.path.join(tmp, "repo")
    os.makedirs(root, exist_ok=True)
    if published:
        make_published(root)
    write_baseline(root, baseline)
    write_exemptions(root)
    return root


class TestGateRules(unittest.TestCase):
    """基线外 published skill 的门禁规则（构造夹具）。"""

    def test_published_without_cases_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            violations, _ = ag.check(root)
            self.assertEqual(len(violations), 1)
            self.assertIn("缺对抗验收用例清单", violations[0])

    def test_missing_findings_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            write_cases(root, "skill-a", full_cases())
            violations, _ = ag.check(root)
            self.assertEqual(len(violations), 1)
            self.assertIn("未过门", violations[0])

    def test_core_all_confirmed_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            confirmed_findings(root)
            violations, lines = ag.check(root)
            self.assertEqual(violations, [])
            self.assertTrue(any("gate PASS" in ln for ln in lines))

    def test_needs_validation_with_valid_exemption_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            cases = confirmed_findings(root)
            records = [make_record(c, "skill-a", i + 1) for i, c in enumerate(cases)]
            records[0] = make_record(cases[0], "skill-a", 1, verdict="needs_validation",
                                     exempt_ref="EX-20261025-01")
            write_findings(root, "skill-a", records)
            violations, lines = ag.check(root)
            self.assertEqual(violations, [])
            self.assertTrue(any("豁免 1" in ln for ln in lines))

    def test_needs_validation_without_exemption_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            cases = confirmed_findings(root)
            records = [make_record(c, "skill-a", i + 1) for i, c in enumerate(cases)]
            records[0] = make_record(cases[0], "skill-a", 1, verdict="needs_validation")
            write_findings(root, "skill-a", records)
            violations, _ = ag.check(root)
            self.assertEqual(len(violations), 1)
            self.assertIn("非 confirmed 不可 published", violations[0])

    def test_safety_case_exempt_still_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            cases = confirmed_findings(root)
            records = [make_record(c, "skill-a", i + 1) for i, c in enumerate(cases)]
            records[4] = make_record(cases[4], "skill-a", 5, verdict="needs_validation",
                                     exempt_ref="EX-20261025-01")  # RED01，safety
            write_findings(root, "skill-a", records)
            violations, _ = ag.check(root)
            self.assertEqual(len(violations), 1)

    def test_rejected_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            cases = confirmed_findings(root)
            records = [make_record(c, "skill-a", i + 1) for i, c in enumerate(cases)]
            records[4] = make_record(cases[4], "skill-a", 5, verdict="rejected")
            write_findings(root, "skill-a", records)
            violations, _ = ag.check(root)
            self.assertEqual(len(violations), 1)

    def test_invalid_cases_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            bad = full_cases()
            del bad[0]["claim_source"]  # 锚点必填（T1 §3）
            write_cases(root, "skill-a", bad)
            violations, lines = ag.check(root)
            self.assertTrue(violations)
            self.assertTrue(any("用例清单校验未过" in v for v in violations))
            self.assertTrue(any(ln.startswith("!! ") for ln in lines))

    def test_baseline_skill_not_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp, baseline=("skill-a", "using-livepowers"))
            violations, lines = ag.check(root)
            self.assertEqual(violations, [])
            self.assertTrue(any("基线外无 published" in ln for ln in lines))

    def test_unpublished_new_skill_not_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            # 拆掉 ③插件拷贝锚点 → 未 published → 不要求
            os.rmdir(os.path.join(root, "plugins", "p1", "skills", "skill-a"))
            os.rmdir(os.path.join(root, "plugins", "p1", "skills"))
            os.rmdir(os.path.join(root, "plugins", "p1"))
            os.rmdir(os.path.join(root, "plugins"))
            violations, lines = ag.check(root)
            self.assertEqual(violations, [])
            self.assertTrue(any("未三处登记" in ln for ln in lines))

    def test_entered_baseline_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp, baseline=("skill-a",))
            confirmed_findings(root)
            _, lines = ag.check(root)
            self.assertTrue(any("移出基线" in ln for ln in lines))


class TestCli(unittest.TestCase):
    """CLI 退出码：PASS/EXEMPT=0，FAIL=1，--report-only 恒 0。"""

    def test_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            ok_root = make_root(tmp, baseline=("skill-a",))
            p = subprocess.run([sys.executable, SCRIPT, "--root", ok_root],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        with tempfile.TemporaryDirectory() as tmp2:
            bad_root = make_root(tmp2)  # published 且什么都不补
            p = subprocess.run([sys.executable, SCRIPT, "--root", bad_root],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 1)
            self.assertIn("FAIL", p.stdout)
            p = subprocess.run([sys.executable, SCRIPT, "--root", bad_root,
                                "--report-only"], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0)


class TestRealRepo(unittest.TestCase):
    """真实仓库全绿冒烟：存量 21 个全在基线内，published 全过门。"""

    def test_real_repo_green(self):
        self.assertTrue(ag.load_baseline(REPO), "缺基线清单")
        names = sg.skills_root(REPO)
        self.assertEqual(set(names) - ag.load_baseline(REPO), set(),
                         "有存量 skill 未登记进基线，CI 将按基线外强制")
        pub = sg.published_map(REPO, names)
        self.assertTrue(all(v == [] for v in pub.values()),
                         "存量应全部三处登记：%s" % pub)
        violations, _ = ag.check(REPO)
        self.assertEqual(violations, [])
        all_cases, errs = av.load_all_case_ids(REPO)
        self.assertEqual(errs, [])
        self.assertIn("system1-first", all_cases)
        self.assertIn("acceptance-gates", all_cases)

    def test_cli_real_repo(self):
        p = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True, cwd=REPO)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("PASS", p.stdout)


if __name__ == "__main__":
    unittest.main()
