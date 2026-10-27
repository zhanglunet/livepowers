#!/usr/bin/env python3
"""PRD-171/T5 验收演示（trend #859）。

虚构新 skill 样例（测试夹具，不入 skills/ 正式目录）完整走一遍对抗式验收
全流程（T2 verifier 机检 + T3 发布门禁，规范 docs/plans/2026-10-25-adversarial-
acceptance.md）：

  阶段① 用例清单入库（冻结）→ published 且无 findings.json → 门禁拒（exit 1）；
  阶段② 独立 verifier 真实执行用例：一条误报主张（示例命令输出 sum=9，实际
        输出 sum=7）被证伪 → verdict=rejected → 门禁仍拒（rejected 无豁免通道）；
  阶段③ 修复回 skill（脚本缺陷修正）→ 重验新开 record（旧 rejected 留痕）→
        门禁过（exit 0，core 3/3 confirmed）。

另覆盖（验收标准「故意失败用例被拦」的反向对照与误杀保护）：
  - verifier == author 自签 → 机检 FAIL（T1 §6.1）；
  - safety 用例 needs_validation + 豁免 → 仍拒（T1 §5 禁令）；
  - needs_validation + 有效豁免（EX- ID 台账登记且对象为该 skill）→ 放行留痕。

仓内留档：docs/adversarial-gate/demo-2026-10-27.md（走查记录 + 机读 findings
原文 + 三条验收标准逐条结论），测试抽取留档 JSON 复检并断言真实仓库门禁
不被夹具破坏；全文与夹具无真实主机名 / IP / 账号 / 密钥。Python 3.9 兼容。
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import adversarial_gate as ag  # noqa: E402
import adversarial_verify as av  # noqa: E402
import slim_gate as sg  # noqa: E402

SCRIPT_VERIFY = REPO / "scripts" / "adversarial_verify.py"
SCRIPT_GATE = REPO / "scripts" / "adversarial_gate.py"

DEMO_SKILL = "adversarial-demo-skill"
DEMO_DOC = REPO / "docs" / "adversarial-gate" / "demo-2026-10-27.md"
DAY = "20261027"
VERIFIER = "verifier-session-t5"
AUTHOR = "author-session-t5"

SKILL_MD = """---
name: adversarial-demo-skill
description: Use when demoing the adversarial acceptance walkthrough on a fixture. 对抗验收走查演示用（虚构）。
allowed-tools: Bash, Read
---

# 对抗验收演示 skill（虚构）

**一句话：只存在于测试夹具，演示 PRD-171 对抗式验收全流程，不入正式 skills/。**

## 流程

1. 读输入：把请求里的数字序列整理成待汇总清单；
2. 分批：超过 <批上限> 条先分批，避免一次全量；
3. 汇总：调用示例命令产出合计，回写结果。

## 示例

```bash
python3 tools/demo_digest.py --sum 2 3 4   # 退出码 0，输出含 sum=9
```

## 红线

- 严禁对空输入执行 `--sum`：无输入必须拒绝执行并提示缺输入，禁止默认按 0 处理。
"""

DIGEST_BUGGY = """#!/usr/bin/env python3
\"\"\"演示用汇总脚本（夹具构造）。\"\"\"
import sys


def main(argv):
    if len(argv) < 2 or argv[0] != "--sum":
        print("缺输入：用法 demo_digest.py --sum <数字...>", file=sys.stderr)
        return 2
    nums = [int(x) for x in argv[1:]]
    print("sum=%d" % sum(nums[1:]))  # 夹具构造的缺陷：漏加第一个输入
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
"""

DIGEST_FIXED = DIGEST_BUGGY.replace(
    'print("sum=%d" % sum(nums[1:]))  # 夹具构造的缺陷：漏加第一个输入',
    'print("sum=%d" % sum(nums))')

CASES = [
    {"case_id": "AC-%s-POS01" % DEMO_SKILL, "skill": DEMO_SKILL, "type": "POS-EX",
     "claim": "示例命令重跑退出码 0 且输出含 sum=9", "claim_source":
     "skills/%s/SKILL.md#示例" % DEMO_SKILL,
     "input": "python3 tools/demo_digest.py --sum 2 3 4",
     "expected": ["退出码 0", "输出含 sum=9"], "safety": False, "priority": "core"},
    {"case_id": "AC-%s-TR01" % DEMO_SKILL, "skill": DEMO_SKILL, "type": "POS-TR",
     "claim": "收到汇总请求按流程节三步执行：读输入 → 分批 → 汇总",
     "claim_source": "skills/%s/SKILL.md#流程" % DEMO_SKILL,
     "input": "构造输入 <数字序列占位>，按流程节三步执行",
     "expected": ["按步骤顺序执行并产出汇总结果", "流程可复现"],
     "safety": False, "priority": "core"},
    {"case_id": "AC-%s-NEG01" % DEMO_SKILL, "skill": DEMO_SKILL, "type": "NEG-TR",
     "claim": "非数字输入不进入汇总流程，提示输入须为数字",
     "claim_source": "skills/%s/SKILL.md#流程" % DEMO_SKILL,
     "input": "构造非数字输入 <文本占位>",
     "expected": ["不进入汇总，提示输入须为数字"], "safety": False, "priority": "extended"},
    {"case_id": "AC-%s-NEG02" % DEMO_SKILL, "skill": DEMO_SKILL, "type": "NEG-TR",
     "claim": "非汇总类请求（如 <其他任务占位>）不触发本技能",
     "claim_source": "skills/%s/SKILL.md#流程" % DEMO_SKILL,
     "input": "构造非汇总类请求 <其他任务占位>",
     "expected": ["不命中本技能"], "safety": False, "priority": "extended"},
    {"case_id": "AC-%s-RED01" % DEMO_SKILL, "skill": DEMO_SKILL, "type": "NEG-RED",
     "claim": "严禁对空输入执行 --sum：无输入必须拒绝执行并提示",
     "claim_source": "skills/%s/SKILL.md#红线" % DEMO_SKILL,
     "input": "构造空输入调用（仅 --sum，不带数字）",
     "expected": ["拒绝执行（退出码 2）", "输出提示缺输入", "不产生汇总输出"],
     "safety": True, "priority": "core"},
]


def record(seq, case_id, verdict, **kw):
    r = {"record_id": "AV-%s-%s-%02d" % (DAY, DEMO_SKILL, seq),
         "case_id": case_id, "verdict": verdict,
         "evidence": "", "falsification_attempts": [],
         "unresolved_fact": "", "disproved_by": "",
         "verifier": VERIFIER, "verifier_model": "model-x",
         "author": AUTHOR, "date": "2026-10-27"}
    r.update(kw)
    return r


def run_cli(script, *args):
    return subprocess.run([sys.executable, str(script)] + list(args),
                          capture_output=True, text=True, cwd=str(REPO))


def write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def run_digest(root, *args):
    """verifier 真实执行夹具脚本（证伪的观察来自真实运行，非编造字符串）。"""
    return subprocess.run([sys.executable, "tools/demo_digest.py"] + list(args),
                          capture_output=True, text=True, cwd=str(root))


def build_fixture(tmp):
    """最小仓库骨架：演示 skill 三处登记（published）+ 豁免台账 + 冻结用例。"""
    root = Path(tmp) / "repo"
    write(root / "skills" / "using-livepowers" / "SKILL.md",
          "# 路由\n\n| 场景 | skill |\n|---|---|\n| 场景1 | `%s` |\n" % DEMO_SKILL)
    write(root / "README.md",
          "# demo\n\n| 场景 | skill |\n|---|---|\n| 场景1 | `%s` |\n" % DEMO_SKILL)
    write(root / "plugins" / "p1" / "skills" / DEMO_SKILL / "SKILL.md", SKILL_MD)
    write(root / "skills" / DEMO_SKILL / "SKILL.md", SKILL_MD)
    write(root / "tools" / "demo_digest.py", DIGEST_BUGGY)
    write(root / "docs" / "adversarial-gate" / "baseline-2026-10-27.md",
          "# 基线（构造）\n\n- `using-livepowers`\n")
    write(root / "docs" / "engineering-checklist" / "exemptions.md",
          "# 豁免台账（构造）\n\n| 豁免 ID | 对象 | 条目 |\n|---|---|---|\n"
          "| EX-%s-01 | skill:%s | E-X01 | 构造行，仅测试解析 |\n" % (DAY, DEMO_SKILL))
    write(root / "tests" / "adversarial" / DEMO_SKILL / "cases.jsonl",
          "\n".join(json.dumps(c, ensure_ascii=False) for c in CASES) + "\n")
    return root


def write_findings(root, records):
    write(Path(root) / "tests" / "adversarial" / DEMO_SKILL / "findings.json",
          json.dumps({"records": records}, ensure_ascii=False, indent=1) + "\n")


# 阶段② findings：误报被驳回（POS01 rejected），红线 confirmed，NEG01 extended
# needs_validation（三态齐全）；NEG02 extended 无记录（演示 extended 不阻塞）。
STAGE2_RECORDS = [
    record(1, "AC-%s-POS01" % DEMO_SKILL, "rejected",
           disproved_by="运行 `python3 tools/demo_digest.py --sum 2 3 4`：退出码 0 "
                        "但输出 `sum=7`，与主张 `sum=9` 矛盾（脚本漏加第一个输入）——最小复现。"),
    record(2, "AC-%s-TR01" % DEMO_SKILL, "confirmed",
           evidence="按流程节三步执行构造输入 <数字序列占位>：产出汇总输出，"
                    "夹具真实执行摘录见 docs/adversarial-gate/demo-2026-10-27.md",
           falsification_attempts=[
               "尝试 A：打乱输入顺序重跑，汇总结果与主张一致，未推翻",
               "尝试 B：重复执行两次，输出可复现，未推翻"]),
    record(3, "AC-%s-RED01" % DEMO_SKILL, "confirmed",
           evidence="构造空输入执行：退出码 2，stderr 提示缺输入，无汇总输出"
                    "（摘录见 docs/adversarial-gate/demo-2026-10-27.md）",
           falsification_attempts=[
               "尝试 A：构造空输入与仅 --sum 两种越权调用，均被拒绝，未推翻红线"]),
    record(4, "AC-%s-NEG01" % DEMO_SKILL, "needs_validation",
           unresolved_fact="夹具未接入触发评测集，非数字输入行为缺构造数据；"
                           "补验动作：评测集接入后补跑（构造）"),
]

# 阶段③ findings：修复回 skill 后重验新开 record（旧 rejected 留痕，追加不改写）。
STAGE3_RECORDS = STAGE2_RECORDS + [
    record(5, "AC-%s-POS01" % DEMO_SKILL, "confirmed",
           evidence="修复后重跑 `python3 tools/demo_digest.py --sum 2 3 4`："
                    "退出码 0，输出 `sum=9`（摘录见 docs/adversarial-gate/"
                    "demo-2026-10-27.md）；本 record 为 AV-%s-%s-01（rejected）"
                    "的修复重验，旧 record 保留不改写" % (DAY, DEMO_SKILL),
           falsification_attempts=[
               "尝试 A：换输入 5 6 重跑得 sum=11，与主张一致，未推翻"]),
]

CORE_TOTAL = 3  # POS01 / TR01 / RED01 为 core


class TestWalkthrough(unittest.TestCase):
    """三阶段走全流程：缺 findings 拒 → 误报驳回仍拒 → 修复重验过。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = build_fixture(self._tmp.name)

    def stage2(self):
        """verifier 真实执行用例并写三态记录（含误报驳回）。"""
        # 红线反例：真实执行空输入 → 拒绝（confirmed 的证据来自真实观察）
        red = run_digest(self.root, "--sum")
        self.assertEqual(red.returncode, 2)
        self.assertIn("缺输入", red.stderr)
        # 示例正例：真实执行 → 观察与主张矛盾（误报）
        pos = run_digest(self.root, "--sum", "2", "3", "4")
        self.assertEqual(pos.returncode, 0)
        self.assertEqual(pos.stdout.strip(), "sum=7")  # 主张 sum=9 被证伪
        write_findings(self.root, STAGE2_RECORDS)
        return pos

    def test_stage1_cases_frozen_then_missing_findings_blocked(self):
        p = run_cli(SCRIPT_VERIFY, "--root", str(self.root),
                    "cases", DEMO_SKILL)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("PASS", p.stdout)
        # 用例冻结：文件只读，5 条构造用例齐四类（POS-EX/POS-TR/NEG-TR×2/NEG-RED）
        cases, _, errs = av.load_cases(str(self.root), DEMO_SKILL)
        self.assertEqual(errs, [], errs)
        self.assertEqual(len(cases), 5)
        # 故意失败场景 ①：published 且无 findings.json → 门禁拒
        g = run_cli(SCRIPT_GATE, "--root", str(self.root))
        self.assertEqual(g.returncode, 1)
        self.assertIn("缺 findings.json", g.stdout)
        self.assertIn("FAIL", g.stdout)

    def test_stage2_false_positive_rejected_and_still_blocked(self):
        pos = self.stage2()
        # 机检：三态记录本身合法（rejected 带 disproved_by；三态齐全）
        c = run_cli(SCRIPT_VERIFY, "--root", str(self.root), "check", DEMO_SKILL)
        self.assertEqual(c.returncode, 0, c.stdout + c.stderr)
        self.assertIn("PASS", c.stdout)
        # 误报落 findings：verdict=rejected + 最小复现（观察来自上方真实执行）
        recs = json.loads((Path(self.root) / "tests" / "adversarial" / DEMO_SKILL
                           / "findings.json").read_text(encoding="utf-8"))["records"]
        rej = [r for r in recs if r["verdict"] == "rejected"]
        self.assertEqual(len(rej), 1)
        self.assertEqual(rej[0]["case_id"], "AC-%s-POS01" % DEMO_SKILL)
        self.assertIn("sum=7", rej[0]["disproved_by"])
        # 故意失败场景 ②：误报驳回后不可发布（rejected 无豁免通道）
        g = run_cli(SCRIPT_VERIFY, "--root", str(self.root), "gate", DEMO_SKILL)
        self.assertEqual(g.returncode, 1)
        self.assertIn("rejected 为终态，无豁免通道", g.stdout)
        G = run_cli(SCRIPT_GATE, "--root", str(self.root))
        self.assertEqual(G.returncode, 1)
        self.assertIn("rejected 为终态，无豁免通道", G.stdout)
        self.assertIn("非 confirmed 不可 published", G.stdout)

    def test_stage3_fix_rerecord_passes(self):
        self.stage2()
        # 修复回 skill：脚本缺陷修正（verifier 不代改代码，作者修复后重验）
        write(Path(self.root) / "tools" / "demo_digest.py", DIGEST_FIXED)
        fixed = run_digest(self.root, "--sum", "2", "3", "4")
        self.assertEqual(fixed.returncode, 0)
        self.assertEqual(fixed.stdout.strip(), "sum=9")
        # 重验新开 record：追加不改写，旧 rejected 留痕
        write_findings(self.root, STAGE3_RECORDS)
        c = run_cli(SCRIPT_VERIFY, "--root", str(self.root), "check", "--all")
        self.assertEqual(c.returncode, 0, c.stdout + c.stderr)
        g = run_cli(SCRIPT_VERIFY, "--root", str(self.root), "gate", DEMO_SKILL)
        self.assertEqual(g.returncode, 0, g.stdout + g.stderr)
        self.assertIn("core %d/%d confirmed" % (CORE_TOTAL, CORE_TOTAL), g.stdout)
        # 发布面（T3）过门：三处登记的 skill 全过对抗验收门
        G = run_cli(SCRIPT_GATE, "--root", str(self.root))
        self.assertEqual(G.returncode, 0, G.stdout + G.stderr)
        self.assertIn("PASS", G.stdout)
        self.assertIn("gate PASS", G.stdout)
        # 机读 findings 齐全：三态齐备、追加式历史完整（rejected 不被改写）
        data = json.loads((Path(self.root) / "tests" / "adversarial" / DEMO_SKILL
                           / "findings.json").read_text(encoding="utf-8"))
        verdicts = {r["verdict"] for r in data["records"]}
        self.assertEqual(verdicts, {"confirmed", "needs_validation", "rejected"})
        self.assertEqual(len(data["records"]), 5)
        for r in data["records"]:
            for k in av.RECORD_FIELDS:
                self.assertIn(k, r)

    def test_stage3_exempt_variant_needs_validation_with_ledger(self):
        """误杀保护：core needs_validation + 有效豁免 → 放行且留痕（豁免 1）。"""
        recs = [
            record(1, "AC-%s-POS01" % DEMO_SKILL, "confirmed",
                   evidence="退出码 0，输出 sum=9（构造，演示豁免通道）",
                   falsification_attempts=["尝试 A：换输入重跑一致，未推翻"]),
            record(2, "AC-%s-TR01" % DEMO_SKILL, "needs_validation",
                   unresolved_fact="缺 <环境数据>，无法落定；补验动作：数据到位后重跑（构造）",
                   exempt_ref="EX-%s-01" % DAY),
            record(3, "AC-%s-RED01" % DEMO_SKILL, "confirmed",
                   evidence="空输入被拒，退出码 2（构造）",
                   falsification_attempts=["尝试 A：越权调用均被拒，未推翻"]),
        ]
        write_findings(self.root, recs)
        g = run_cli(SCRIPT_VERIFY, "--root", str(self.root), "gate", DEMO_SKILL)
        self.assertEqual(g.returncode, 0, g.stdout + g.stderr)
        self.assertIn("豁免 1", g.stdout)


class TestInterceptionVariants(unittest.TestCase):
    """「故意失败用例被拦」的反向对照（独立夹具，互不污染）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = build_fixture(self._tmp.name)

    def test_self_signing_rejected(self):
        """作者会话不可自签（T1 §6.1）：verifier == author → 机检 FAIL。"""
        bad = [dict(r, verifier=AUTHOR) for r in STAGE2_RECORDS]
        write_findings(self.root, bad)
        errs = av.check_records(
            str(self.root), DEMO_SKILL,
            {c["case_id"]: c for c in CASES},
            av.load_exempt_ledger(str(self.root / "docs" / "engineering-checklist"
                                      / "exemptions.md")))
        self.assertTrue(any("作者会话不可自签" in e for e in errs), errs)
        c = run_cli(SCRIPT_VERIFY, "--root", str(self.root), "check", DEMO_SKILL)
        self.assertEqual(c.returncode, 1)
        self.assertIn("FAIL", c.stdout)

    def test_safety_case_cannot_be_exempted(self):
        """safety 用例一律不可豁免（T1 §5 禁令）→ 门禁拒。"""
        recs = [dict(r) for r in STAGE2_RECORDS]
        recs[2] = record(3, "AC-%s-RED01" % DEMO_SKILL, "needs_validation",
                         unresolved_fact="构造：待补验",
                         exempt_ref="EX-%s-01" % DAY)
        write_findings(self.root, recs)
        g = run_cli(SCRIPT_VERIFY, "--root", str(self.root), "gate", DEMO_SKILL)
        self.assertEqual(g.returncode, 1)
        self.assertIn("safety", g.stdout)

    def test_rejected_has_no_exemption_path(self):
        """给 rejected 挂 exempt_ref：机检直接拒（exempt_ref 仅 needs_validation 可填）。"""
        recs = [dict(r) for r in STAGE2_RECORDS]
        recs[0]["exempt_ref"] = "EX-%s-01" % DAY
        write_findings(self.root, recs)
        c = run_cli(SCRIPT_VERIFY, "--root", str(self.root), "check", DEMO_SKILL)
        self.assertEqual(c.returncode, 1)
        self.assertIn("exempt_ref 仅 needs_validation 可填", c.stdout)

    def test_unregistered_exempt_ref_rejected(self):
        recs = [dict(r) for r in STAGE2_RECORDS]
        recs[3]["exempt_ref"] = "EX-20990101-99"  # 未在台账登记
        write_findings(self.root, recs)
        c = run_cli(SCRIPT_VERIFY, "--root", str(self.root), "check", DEMO_SKILL)
        self.assertEqual(c.returncode, 1)
        self.assertIn("未在豁免台账登记", c.stdout)

    def test_draft_skill_not_required(self):
        """未三处登记 → 不视为 published，不要求记录（门禁不拦）。"""
        shutil.rmtree(self.root / "plugins")  # 拆掉 ③插件拷贝锚点
        G = run_cli(SCRIPT_GATE, "--root", str(self.root))
        self.assertEqual(G.returncode, 0, G.stdout + G.stderr)
        self.assertIn("未三处登记", G.stdout)


class TestRepoArchive(unittest.TestCase):
    """仓内留档一致性与真实仓库门禁不被破坏。"""

    def test_demo_doc_exists_and_tells_same_story(self):
        self.assertTrue(DEMO_DOC.is_file(), "缺走查记录 docs/adversarial-gate/demo-2026-10-27.md")
        doc = DEMO_DOC.read_text(encoding="utf-8")
        for token in ("exit 1", "exit 0", "sum=7", "sum=9", "rejected",
                      "缺 findings.json", "rejected 为终态，无豁免通道",
                      "core %d/%d confirmed" % (CORE_TOTAL, CORE_TOTAL),
                      "作者会话不可自签", "AV-%s-%s-01" % (DAY, DEMO_SKILL)):
            self.assertIn(token, doc, token)

    def test_doc_embedded_findings_machine_readable_and_valid(self):
        """抽取留档 JSON 复检：与走查终态逐字一致、机检通过、可过门。"""
        doc = DEMO_DOC.read_text(encoding="utf-8")
        blocks = re.findall(r"```json\n(.*?)```", doc, re.S)
        findings_blocks = [b for b in blocks if '"records"' in b]
        cases_blocks = [b for b in blocks if '"case_id"' in b and '"records"' not in b]
        self.assertEqual(len(findings_blocks), 1, "留档应嵌一份 findings.json")
        self.assertEqual(len(cases_blocks), 1, "留档应嵌一份 cases.jsonl")
        embedded = json.loads(findings_blocks[0])
        self.assertEqual(embedded, {"records": STAGE3_RECORDS},
                         "留档 findings 与走查终态不一致")
        with tempfile.TemporaryDirectory() as tmp:
            root = build_fixture(tmp)
            write(root / "tools" / "demo_digest.py", DIGEST_FIXED)
            write(root / "tests" / "adversarial" / DEMO_SKILL / "cases.jsonl",
                  cases_blocks[0])
            write_findings(root, embedded["records"])
            ledger = av.load_exempt_ledger(str(root / "docs" / "engineering-checklist"
                                               / "exemptions.md"))
            errs = av.check_records(str(root), DEMO_SKILL,
                                    {c["case_id"]: c for c in CASES}, ledger)
            self.assertEqual(errs, [], errs)
            ok, core_pass, core_total, blocking, _, _ = av.gate_skill(
                str(root), DEMO_SKILL, {c["case_id"]: c for c in CASES}, ledger)
            self.assertTrue(ok, blocking)
            self.assertEqual((core_pass, core_total), (CORE_TOTAL, CORE_TOTAL))

    def test_fictional_skill_never_landed(self):
        self.assertFalse((REPO / "skills" / DEMO_SKILL).exists(),
                         "虚构 skill 不得进入 skills/ 正式目录")
        self.assertNotIn(DEMO_SKILL, ag.load_baseline(str(REPO)))
        all_cases, errs = av.load_all_case_ids(str(REPO))
        self.assertEqual(errs, [], errs)
        self.assertNotIn(DEMO_SKILL, all_cases)

    def test_real_repo_gates_still_green(self):
        p = run_cli(SCRIPT_GATE)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("PASS", p.stdout)
        c = run_cli(SCRIPT_VERIFY, "cases", "--all")
        self.assertEqual(c.returncode, 0, c.stdout + c.stderr)


SECRET_PATTERNS = (
    ("aws_key", r"AKIA[0-9A-Z]{16}"),
    ("api_key", r"sk-[A-Za-z0-9]{16,}"),
    ("bearer", r"Authorization:\s*Bearer\s+[A-Za-z0-9._-]{8,}"),
    ("password", r"(?i)(password|passwd)\s*[:=]\s*\S+"),
    ("token_assign", r"(?i)(token|secret)\s*[:=]\s*['\"]?[A-Za-z0-9/+]{16,}"),
    ("private_key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("ipv4", r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    ("ssh_target", r"\b(?:ssh|scp)\s+\S+@"),
)


class TestNoSecrets(unittest.TestCase):
    """验收标准「无密钥」：留档文档与本测试全文扫描 0 命中，带阳性对照。"""

    def test_scanner_has_positive_control(self):
        planted = "AKIA" + "IOSFODNN7EXAMPLE"  # 拼接构造，避免源码自身命中扫描
        hits = scan_secrets(planted)
        self.assertEqual([h[0] for h in hits], ["aws_key"])

    def test_demo_doc_and_test_clean(self):
        for f in (DEMO_DOC, Path(__file__)):
            text = f.read_text(encoding="utf-8")
            hits = scan_secrets(text)
            self.assertEqual(hits, [], "%s 含疑似密钥/内网信息：%s" % (f, hits))


def scan_secrets(text):
    hits = []
    for name, pat in SECRET_PATTERNS:
        for m in re.finditer(pat, text):
            line = text.count("\n", 0, m.start()) + 1
            hits.append((name, line, m.group(0)[:24]))
    return hits


if __name__ == "__main__":
    unittest.main()
