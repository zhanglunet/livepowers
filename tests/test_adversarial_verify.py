#!/usr/bin/env python3
"""PRD-171/T2：对抗式验收 verifier 机检测试。

被测：scripts/adversarial_verify.py（trend issue #856；规范
docs/plans/2026-10-25-adversarial-acceptance.md，PRD-171/T1）。

覆盖：
1. 入库的两份用例清单（system1-first / acceptance-gates）通过校验，
   锚点真实存在、数量下限达标（红线 skill ≥2 条 NEG-RED）；
2. 三态判据（T1 §5 写死）：confirmed 须 evidence + ≥1 条证伪尝试、
   needs_validation 须 unresolved_fact、rejected 须 disproved_by；
3. 独立性机检（T1 §6.1）：verifier == author 即 FAIL（作者会话不可自签）；
4. 豁免禁令：safety 用例不可豁免；exempt_ref 须在工程门豁免台账登记
   且对象为该 skill；
5. 门禁判定（T1 §5）：缺 findings.json = 未过门；core 全 confirmed 才过；
   needs_validation + 有效豁免可过（EXEMPT）；rejected 无豁免通道；
   extended 不阻塞；
6. CLI 退出码与 template 子命令输出可校验。

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
import adversarial_verify as av  # noqa: E402

SKILL_MD = ("---\nname: {name}\ndescription: Use when testing the verifier.\n"
            "allowed-tools: Bash, Read\n---\n\n# 测试用\n\n## 流程\n\n正文（构造）。\n")

CASE_A = {"case_id": "AC-skill-a-POS01", "skill": "skill-a", "type": "POS-EX",
          "claim": "示例命令重跑退出码 0（构造）", "claim_source": "skills/skill-a/SKILL.md#流程",
          "input": "lp registry find \"<意图占位>\"", "expected": ["退出码 0"],
          "safety": False, "priority": "core"}
CASE_TR = dict(CASE_A, case_id="AC-skill-a-TR01", type="POS-TR",
               claim="命中触发场景按流程走完（构造）")
CASE_NEG1 = dict(CASE_A, case_id="AC-skill-a-NEG01", type="NEG-TR",
                 claim="边界外场景不触发（构造）", priority="extended")
CASE_NEG2 = dict(CASE_A, case_id="AC-skill-a-NEG02", type="NEG-TR",
                 claim="边界外场景不触发 2（构造）", priority="extended")
CASE_RED = dict(CASE_A, case_id="AC-skill-a-RED01", type="NEG-RED",
                claim="严禁盲目调用写操作（构造）", expected=["不执行写操作"],
                safety=True)
# 触发反例锚点：指向真实存在的测试路径，验证路径型锚点。
CASE_NEG_PATH = dict(CASE_A, case_id="AC-skill-a-NEG03", type="NEG-TR",
                     claim="评测集反例不触发（构造）",
                     claim_source="tests/triggers/system1-first.jsonl")


def write_cases(root, skill, cases, na_reason=None):
    d = os.path.join(root, "tests", "adversarial", skill)
    os.makedirs(d, exist_ok=True)
    lines = [json.dumps(c, ensure_ascii=False) for c in cases]
    if na_reason:
        lines.append(json.dumps({"na": "NEG-RED", "reason": na_reason}, ensure_ascii=False))
    with open(os.path.join(d, "cases.jsonl"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def write_findings(root, skill, records):
    d = os.path.join(root, "tests", "adversarial", skill)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "findings.json"), "w", encoding="utf-8") as f:
        json.dump({"records": records}, f, ensure_ascii=False, indent=1)


def write_exemptions(root, rows=(("EX-20261025-01", "skill:skill-a"),)):
    p = os.path.join(root, "docs", "engineering-checklist")
    os.makedirs(p, exist_ok=True)
    with open(os.path.join(p, "exemptions.md"), "w", encoding="utf-8") as f:
        f.write("# 豁免台账（构造）\n\n| 豁免 ID | 对象 | 条目 |\n|---|---|---|\n")
        for ex_id, obj in rows:
            f.write("| %s | %s | E-X01 | 构造行，仅测试解析 |\n" % (ex_id, obj))


def make_record(case, verdict="confirmed", skill="skill-a", **kw):
    r = {"record_id": "AV-20261025-%s-01" % skill, "case_id": case["case_id"],
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


def make_root(tmp, skill="skill-a"):
    root = os.path.join(tmp, "repo")
    os.makedirs(os.path.join(root, "skills", skill))
    with open(os.path.join(root, "skills", skill, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(SKILL_MD.format(name=skill))
    return root


class TestLandedCases(unittest.TestCase):
    """入库的两份用例清单本身必须通过机检（T2 落文件质量）。"""

    def test_landed_cases_pass(self):
        for skill in ("system1-first", "acceptance-gates"):
            cases, na, errs = av.load_cases(REPO, skill)
            self.assertEqual(errs, [], "%s: %s" % (skill, errs))
            self.assertGreaterEqual(len(cases), 4)
            reds = [c for c in cases if c["type"] == "NEG-RED"]
            if skill in av.REDLINE_SKILLS:
                self.assertGreaterEqual(len(reds), 2, skill)
            else:
                self.assertGreaterEqual(len(reds), 1, skill)
            self.assertTrue(all(c["claim_source"] for c in cases))

    def test_case_ids_globally_unique(self):
        all_cases, errs = av.load_all_case_ids(REPO)
        self.assertEqual(errs, [], errs)
        ids = [c["case_id"] for cs in all_cases.values() for c in cs]
        self.assertEqual(len(set(ids)), len(ids))

    def test_redline_list_matches_spec(self):
        # T1 §3：红线名单沿用瘦身门红线，写死在脚本里。
        self.assertEqual(set(av.REDLINE_SKILLS),
                         {"oltp-action-safety", "acceptance-gates",
                          "auditable-agent-comms", "takeover-handling"})

    def test_findings_template_is_valid_empty(self):
        with open(os.path.join(REPO, "tests", "adversarial", "findings.template.json"),
                  encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data, {"records": []})


class TestCaseValidation(unittest.TestCase):
    def test_missing_anchor_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            bad = dict(CASE_A, claim_source="skills/skill-a/SKILL.md#不存在的节")
            write_cases(root, "skill-a", [bad, CASE_TR, CASE_NEG1, CASE_NEG2, CASE_RED])
            _, _, errs = av.load_cases(root, "skill-a")
            self.assertTrue(any("锚点不存在" in e for e in errs), errs)

    def test_negred_must_be_safety(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            bad = dict(CASE_RED, safety=False)
            write_cases(root, "skill-a", [CASE_A, CASE_TR, CASE_NEG1, CASE_NEG2, bad])
            _, _, errs = av.load_cases(root, "skill-a")
            self.assertTrue(any("NEG-RED" in e and "safety" in e for e in errs), errs)

    def test_non_negred_cannot_be_safety(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            bad = dict(CASE_A, safety=True)
            write_cases(root, "skill-a", [bad, CASE_TR, CASE_NEG1, CASE_NEG2, CASE_RED])
            _, _, errs = av.load_cases(root, "skill-a")
            self.assertTrue(any("仅 NEG-RED" in e for e in errs), errs)

    def test_minimum_counts_and_na_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            # 非红线 skill：无 NEG-RED 且未标 N/A → 报数量下限
            write_cases(root, "skill-a", [CASE_A, CASE_TR, CASE_NEG1, CASE_NEG2])
            _, _, errs = av.load_cases(root, "skill-a")
            self.assertTrue(any("NEG-RED" in e for e in errs), errs)
            # 标 N/A 并留理由 → 通过
            write_cases(root, "skill-a", [CASE_A, CASE_TR, CASE_NEG1, CASE_NEG2],
                        na_reason="正文确无严禁级主张（构造）")
            _, _, errs = av.load_cases(root, "skill-a")
            self.assertEqual(errs, [], errs)

    def test_redline_skill_cannot_na_and_needs_two_red(self):
        red_skill = "acceptance-gates"
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp, skill=red_skill)
            write_cases(root, red_skill, [CASE_A, CASE_TR, CASE_NEG1, CASE_NEG2],
                        na_reason="构造尝试")
            _, _, errs = av.load_cases(root, red_skill)
            self.assertTrue(any("红线 skill 不可对 NEG-RED 标 N/A" in e for e in errs), errs)
            write_cases(root, red_skill, [CASE_A, CASE_TR, CASE_NEG1, CASE_NEG2, CASE_RED])
            _, _, errs = av.load_cases(root, red_skill)
            self.assertTrue(any("NEG-RED ≥2" in e for e in errs), errs)

    def test_case_id_type_code_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            bad = dict(CASE_A, case_id="AC-skill-a-RED09")
            write_cases(root, "skill-a", [bad, CASE_TR, CASE_NEG1, CASE_NEG2, CASE_RED])
            _, _, errs = av.load_cases(root, "skill-a")
            self.assertTrue(any("类型短码" in e for e in errs), errs)

    def test_path_anchor_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            write_cases(root, "skill-a", [CASE_A, CASE_TR, CASE_NEG_PATH, CASE_NEG2, CASE_RED])
            _, _, errs = av.load_cases(root, "skill-a")
            # tests/triggers/system1-first.jsonl 在夹具根不存在 → 锚点错误；在真仓存在
            self.assertTrue(any("锚点不存在" in e for e in errs), errs)
            landed, _, errs2 = av.load_cases(REPO, "system1-first")
            self.assertEqual(errs2, [], errs2)
            self.assertTrue(any(c["claim_source"].startswith("tests/triggers/")
                                for c in landed))


class TestFindingsCheck(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = make_root(self._tmp.name)
        write_cases(self.root, "skill-a",
                    [CASE_A, CASE_TR, CASE_NEG1, CASE_NEG2, CASE_RED])
        write_exemptions(self.root)

    def test_valid_confirmed_passes(self):
        recs = [make_record(CASE_A)]
        write_findings(self.root, "skill-a", recs)
        errs = av.check_records(self.root, "skill-a",
                                {c["case_id"]: c for c in
                                 av.load_cases(self.root, "skill-a")[0]},
                                av.load_exempt_ledger(
                                    os.path.join(self.root, "docs",
                                                 "engineering-checklist", "exemptions.md")))
        self.assertEqual(errs, [], errs)

    def test_confirmed_requires_falsification(self):
        bad = make_record(CASE_A, falsification_attempts=[])
        write_findings(self.root, "skill-a", [bad])
        errs = av.check_records(self.root, "skill-a",
                                {c["case_id"]: c for c in
                                 av.load_cases(self.root, "skill-a")[0]}, {})
        self.assertTrue(any("证伪尝试" in e for e in errs), errs)

    def test_needs_validation_requires_unresolved_fact(self):
        bad = make_record(CASE_A, verdict="needs_validation", unresolved_fact=" ")
        write_findings(self.root, "skill-a", [bad])
        errs = av.check_records(self.root, "skill-a",
                                {c["case_id"]: c for c in
                                 av.load_cases(self.root, "skill-a")[0]}, {})
        self.assertTrue(any("unresolved_fact" in e for e in errs), errs)

    def test_rejected_requires_disproved_by(self):
        bad = make_record(CASE_A, verdict="rejected", disproved_by="")
        write_findings(self.root, "skill-a", [bad])
        errs = av.check_records(self.root, "skill-a",
                                {c["case_id"]: c for c in
                                 av.load_cases(self.root, "skill-a")[0]}, {})
        self.assertTrue(any("disproved_by" in e for e in errs), errs)

    def test_verifier_cannot_self_sign(self):
        bad = make_record(CASE_A, verifier="same-session", author="same-session")
        write_findings(self.root, "skill-a", [bad])
        errs = av.check_records(self.root, "skill-a",
                                {c["case_id"]: c for c in
                                 av.load_cases(self.root, "skill-a")[0]}, {})
        self.assertTrue(any("作者会话不可自签" in e for e in errs), errs)

    def test_safety_case_cannot_be_exempted(self):
        bad = make_record(CASE_RED, verdict="needs_validation",
                          unresolved_fact="构造：待补验", exempt_ref="EX-20261025-01")
        write_findings(self.root, "skill-a", [bad])
        ledger = av.load_exempt_ledger(
            os.path.join(self.root, "docs", "engineering-checklist", "exemptions.md"))
        errs = av.check_records(self.root, "skill-a",
                                {c["case_id"]: c for c in
                                 av.load_cases(self.root, "skill-a")[0]}, ledger)
        self.assertTrue(any("safety 用例不可豁免" in e for e in errs), errs)

    def test_exempt_ref_must_be_registered_for_this_skill(self):
        ledger = av.load_exempt_ledger(
            os.path.join(self.root, "docs", "engineering-checklist", "exemptions.md"))
        cases = {c["case_id"]: c for c in av.load_cases(self.root, "skill-a")[0]}
        # 未登记的 EX- ID → 拒绝
        bad = make_record(CASE_TR, verdict="needs_validation",
                          unresolved_fact="构造：待补验", exempt_ref="EX-20990101-99")
        write_findings(self.root, "skill-a", [bad])
        errs = av.check_records(self.root, "skill-a", cases, ledger)
        self.assertTrue(any("未在豁免台账登记" in e for e in errs), errs)
        # 已登记但台账对象不是本 skill → 无效豁免
        bad2 = make_record(CASE_TR, verdict="needs_validation",
                           unresolved_fact="构造：待补验", exempt_ref="EX-20261025-01")
        write_findings(self.root, "skill-a", [bad2])
        ledger2 = {"EX-20261025-01": "skill:other"}
        errs2 = av.check_records(self.root, "skill-a", cases, ledger2)
        self.assertTrue(any("台账对象" in e for e in errs2), errs2)

    def test_unknown_case_id_rejected(self):
        bad = make_record(CASE_A, case_id="AC-skill-a-POS99")
        write_findings(self.root, "skill-a", [bad])
        errs = av.check_records(self.root, "skill-a",
                                {c["case_id"]: c for c in
                                 av.load_cases(self.root, "skill-a")[0]}, {})
        self.assertTrue(any("不在冻结用例清单" in e for e in errs), errs)

    def test_missing_findings_reported(self):
        errs = av.check_records(self.root, "skill-a",
                                {c["case_id"]: c for c in
                                 av.load_cases(self.root, "skill-a")[0]}, {})
        self.assertTrue(any("缺" in e and "findings.json" in e for e in errs), errs)


class TestGate(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = make_root(self._tmp.name)
        write_cases(self.root, "skill-a",
                    [CASE_A, CASE_TR, CASE_NEG1, CASE_NEG2, CASE_RED])
        write_exemptions(self.root)
        self.ledger = av.load_exempt_ledger(
            os.path.join(self.root, "docs", "engineering-checklist", "exemptions.md"))

    def _gate(self):
        cases = {c["case_id"]: c for c in av.load_cases(self.root, "skill-a")[0]}
        errs = av.check_records(self.root, "skill-a", cases, self.ledger)
        if errs:
            return False, 0, 0, errs, [], []
        return av.gate_skill(self.root, "skill-a", cases, self.ledger)

    def test_gate_fails_without_findings(self):
        ok, _, _, blocking, _, _ = self._gate()
        self.assertFalse(ok)
        self.assertTrue(any("findings.json" in b for b in blocking), blocking)

    def test_gate_passes_when_all_core_confirmed(self):
        write_findings(self.root, "skill-a",
                       [make_record(CASE_A), make_record(CASE_TR),
                        make_record(CASE_RED)])
        ok, core_pass, core_total, blocking, exempted, notes = self._gate()
        self.assertTrue(ok, blocking)
        self.assertEqual((core_pass, core_total), (3, 3))

    def test_gate_needs_validation_with_valid_exemption(self):
        rec = make_record(CASE_A, verdict="needs_validation",
                          unresolved_fact="构造：待补验", exempt_ref="EX-20261025-01")
        write_findings(self.root, "skill-a",
                       [rec, make_record(CASE_TR), make_record(CASE_RED)])
        ok, _, _, blocking, exempted, _ = self._gate()
        self.assertTrue(ok, blocking)
        self.assertEqual(len(exempted), 1, exempted)

    def test_gate_blocked_without_exemption(self):
        rec = make_record(CASE_A, verdict="needs_validation",
                          unresolved_fact="构造：待补验")
        write_findings(self.root, "skill-a",
                       [rec, make_record(CASE_TR), make_record(CASE_RED)])
        ok, _, _, blocking, _, _ = self._gate()
        self.assertFalse(ok)
        self.assertTrue(any("无有效豁免" in b for b in blocking), blocking)

    def test_gate_rejected_has_no_exemption_path(self):
        rec = make_record(CASE_A, verdict="rejected",
                          disproved_by="构造：矛盾观察")
        write_findings(self.root, "skill-a",
                       [rec, make_record(CASE_TR), make_record(CASE_RED)])
        ok, _, _, blocking, _, _ = self._gate()
        self.assertFalse(ok)
        self.assertTrue(any("rejected" in b for b in blocking), blocking)

    def test_gate_safety_case_cannot_pass_by_exemption(self):
        rec = make_record(CASE_RED, verdict="needs_validation",
                          unresolved_fact="构造：待补验")
        write_findings(self.root, "skill-a",
                       [make_record(CASE_A), make_record(CASE_TR), rec])
        ok, _, _, blocking, _, _ = self._gate()
        self.assertFalse(ok)
        self.assertTrue(any("safety" in b for b in blocking), blocking)

    def test_extended_cases_do_not_block(self):
        rec = make_record(CASE_NEG1, verdict="rejected",
                          disproved_by="构造：矛盾观察")
        write_findings(self.root, "skill-a",
                       [make_record(CASE_A), make_record(CASE_TR),
                        make_record(CASE_RED), rec])
        ok, _, _, blocking, _, notes = self._gate()
        self.assertTrue(ok, blocking)
        self.assertTrue(any("extended" in n for n in notes), notes)


class TestCLI(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, os.path.join(REPO, "scripts", "adversarial_verify.py")] + list(args),
            capture_output=True, text=True, cwd=REPO)

    def test_cases_cli_on_landed_skills(self):
        p = self.run_cli("cases", "--all")
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        self.assertIn("PASS", p.stdout)

    def test_gate_cli_reports_not_passed_without_findings(self):
        p = self.run_cli("gate", "system1-first")
        self.assertEqual(p.returncode, 1)
        self.assertIn("FAIL", p.stdout)
        self.assertIn("findings.json", p.stdout)

    def test_gate_cli_json_output(self):
        p = self.run_cli("gate", "system1-first", "--json")
        self.assertEqual(p.returncode, 1)
        data = json.loads(p.stdout[p.stdout.index("{"):])
        self.assertFalse(data["ok"])
        self.assertEqual(data["skills"][0]["skill"], "system1-first")

    def test_template_cli_prints_valid_skeleton_and_example(self):
        p = self.run_cli("template", "system1-first", "--example")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('{"records": []}', p.stdout)
        lines = p.stdout.splitlines()
        start = next(i for i, ln in enumerate(lines) if "构造样例记录" in ln)
        data = json.loads("\n".join(lines[start + 1:]))
        self.assertEqual(data["records"][0]["verdict"], "confirmed")
        self.assertIn("构造", data["records"][0]["evidence"])


if __name__ == "__main__":
    unittest.main()
