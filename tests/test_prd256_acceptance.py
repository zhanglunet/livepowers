# -*- coding: utf-8 -*-
"""PRD-256/T5 验收试运行（trend #1284）：样例任务走三角色——端到端验收回放。

运行：python3 -m unittest test_prd256_acceptance -v（在 tests/ 目录执行）

按 T1 设计（docs/plans/2026-10-28-prd-256-pi-subagents-template.md §6 T5 验收标准）
对 T1–T4 全链交付做端到端验收（全部走查内容全虚构、零网络、零 mock）：

  §6.1 示范任务三角色走通，全部交接合同过 handoff.schema.json 校验（T3 走查回放）
  §6.2 合同三要素（input/expect/result）齐全；acceptance 逐条有 evidence
  §6.3 含一次 verify 打回 → implement 修复 → 重新派发的完整流转（rejected 留痕闭环）
  §6.4 主会话汇总由合同 result 对照呈现（无需额外报告文件）
  §6.5 模板包与示范零密钥；与上游 pi-subagents 逐段比对确认零文案拷贝
       ——关键短语抽样比对：抽样自上游 main 分支（2026-10-23 实测取样，
       GitHub raw README.md / agents/scout.md / agents/worker.md / agents/reviewer.md），
       固化为离线夹具，断言这些上游原文短语零命中本模板包；
       上游角色体系（scout/worker/reviewer/…）不被复用为本包角色页。
  模板包结构完整：README/三角色页/schema/走查/边界文档/机器校验入口在位。

红线：只借"三角色 + 交接合同"形态（上游实测 MIT），角色定义、handoff-v1 字段、
示范走查全部本仓原创。本文件不含真实主机名、账号、密钥。
"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_handoff as vh  # noqa: E402

TEMPLATE = ROOT / "templates" / "pi-subagents"
WALKTHROUGH = TEMPLATE / "example-walkthrough.md"
SCHEMA = TEMPLATE / "handoff.schema.json"
VALIDATOR = ROOT / "scripts" / "validate_handoff.py"

SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{16,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)

# 上游关键短语抽样（nicobailon/pi-subagents main 分支，2026-10-23 实测取样；
# 仅作零拷贝比对的离线夹具，逐条为上游原文 verbatim 片段）：
UPSTREAM_SAMPLED_PHRASES = {
    "README.md": [
        "lets Pi delegate work to focused child agents",
        "A subagent is a focused child Pi session",
        "Complexity alone does not authorize delegation",
        "clarify → scout → worker → fresh reviewers → worker",
        "Fast local codebase recon",
    ],
    "agents/scout.md": [
        "You are a scouting subagent running inside pi",
        "compressed context for handoff",
        "Reserve unscoped `grep` for exhaustive exact-literal verification",
    ],
    "agents/worker.md": [
        "Implementation agent for normal tasks and approved oracle handoffs",
        "You are the single writer thread",
        "pause and escalate instead of deciding it yourself",
    ],
    "agents/reviewer.md": [
        "Versatile review specialist for code diffs, plans, proposed solutions",
        "You are a disciplined review subagent",
        "Inspect, evaluate, and report findings with evidence",
    ],
}

UPSTREAM_ROLE_WORDS = ("scout", "worker", "reviewer", "oracle",
                       "researcher", "delegate", "evidence-auditor")


def load_contracts():
    """从 walkthrough.md 提取全部内联合同（json 围栏块，按文档顺序）。"""
    text = WALKTHROUGH.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)```", text, re.S)
    return text, [json.loads(b) for b in blocks]


class TestThreeRoleFullFlow(unittest.TestCase):
    """§6.1/§6.2 样例任务三角色全流程：合同齐全且全过 schema。"""

    def setUp(self):
        self.text, self.contracts = load_contracts()
        self.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def test_all_inline_contracts_pass_schema_with_three_elements(self):
        """全部内联合同过 handoff.schema.json；三要素 input/expect/result 齐全。"""
        self.assertGreaterEqual(len(self.contracts), 5,
                                "示范内联合同应至少 5 份（探索/实现×2/验证×2）")
        for i, c in enumerate(self.contracts):
            self.assertEqual(c.get("schema"), "handoff-v1", f"合同 #{i} schema 头")
            self.assertEqual(vh.builtin_validate(c, self.schema), [],
                             f"合同 #{i} {c.get('task_id')} 未过 schema")
            for part in ("input", "expect", "result"):
                self.assertIn(part, c, f"合同 {c['task_id']} 缺三要素之一: {part}")
            self.assertTrue(c["input"].get("constraints"),
                            f"合同 {c['task_id']} 派发未带 constraints 红线")
            self.assertTrue(c["expect"].get("acceptance"),
                            f"合同 {c['task_id']} 缺 acceptance 清单")

    def test_acceptance_items_backed_by_evidence(self):
        """acceptance 逐条有可判定证据：终态合同 result.evidence 非空。"""
        for c in self.contracts:
            if c["result"]["status"] in ("done", "rejected"):
                self.assertTrue(c["expect"].get("acceptance"),
                                f"合同 {c['task_id']} acceptance 清单为空")
                self.assertTrue(c["result"].get("evidence"),
                                f"合同 {c['task_id']} 终态缺 evidence")


class TestClosedLoop(unittest.TestCase):
    """§6.3 打回流转闭环：三角色最终 done，verify rejected 打回后修复复验闭环。"""

    def setUp(self):
        _, self.contracts = load_contracts()

    def test_three_roles_final_done(self):
        finals = {}
        for c in self.contracts:
            finals[c["to"]] = c  # 文档顺序在后即最终
        for role in ("explore", "implement", "verify"):
            self.assertIn(role, finals, f"缺 {role} 派发合同")
            self.assertEqual(finals[role]["result"]["status"], "done",
                             f"{role} 最终合同未 done")

    def test_rejected_flow_closed_loop(self):
        """verify rejected 打回 → 重派 implement 修复 → verify 复验 done 闭环。"""
        rejected = [c for c in self.contracts
                    if c["result"]["status"] == "rejected"]
        self.assertGreaterEqual(len(rejected), 1, "示范应含至少一次 rejected 打回")
        r = rejected[0]
        self.assertEqual(r["to"], "verify", "打回应由 verify 独立复验给出")
        idx = self.contracts.index(r)
        later = self.contracts[idx + 1:]
        impl_fixed = [c for c in later if c["to"] == "implement"
                      and c["result"]["status"] == "done"]
        verify_re = [c for c in later if c["to"] == "verify"
                     and c["result"]["status"] == "done"]
        self.assertTrue(impl_fixed, "打回后应有 implement 修复合同且 done")
        self.assertTrue(verify_re, "打回后应有 verify 复验合同且 done（闭环）")
        # 打回证据指明失败条目
        self.assertTrue(any("失败" in e for e in r["result"]["evidence"]),
                        "rejected 合同应留失败条目证据")


class TestRetryTrace(unittest.TestCase):
    """§6.3 重派留痕：新 task_id 引用原 task_id，修复落在 implement。"""

    def test_retry_contracts_reference_original_task_ids(self):
        _, contracts = load_contracts()
        ids = {c["task_id"] for c in contracts}
        retries = [c for c in contracts if c.get("retries")]
        self.assertGreaterEqual(len(retries), 1, "应存在重派合同")
        for c in retries:
            self.assertNotEqual(c["task_id"], c["retries"][0], "重派须为新 task_id")
            self.assertIn(c["retries"][0], ids,
                          f"{c['task_id']} 引用的原 task_id 不在示范内")
        impl_retries = [c for c in retries if c["to"] == "implement"]
        self.assertTrue(impl_retries, "打回修复的重派应落在 implement（verify 不修代码）")


class TestSummaryPresentation(unittest.TestCase):
    """§6.4 主会话汇总由合同 result 对照呈现。"""

    def test_summary_section_compares_three_results(self):
        text, contracts = load_contracts()
        marker = "## 6."
        self.assertIn(marker, text, "缺主会话汇总节")
        summary = text.split(marker, 1)[1]
        finals = {}
        for c in contracts:
            finals[c["to"]] = c
        for role, c in finals.items():
            self.assertIn(c["task_id"], summary,
                          f"汇总未对照 {role} 最终合同 {c['task_id']}")
        self.assertIn("done", summary, "汇总应呈现各合同 result.status")
        self.assertTrue(re.search(r"不写额外报告|无需额外报告", text),
                        "汇总应为合同 result 对照呈现（无额外报告文件）")


class TestZeroCopyFromUpstream(unittest.TestCase):
    """§6.5 只借形态无违规拷贝：上游关键短语抽样零命中；角色体系不复用。"""

    def test_upstream_key_phrases_absent_from_pack(self):
        """上游抽样关键短语在本模板包任一文件零命中（含示范与边界文档）。"""
        pack_files = sorted(p for p in TEMPLATE.rglob("*") if p.is_file())
        self.assertGreaterEqual(len(pack_files), 7, "模板包文件数异常")
        for src, phrases in UPSTREAM_SAMPLED_PHRASES.items():
            for phrase in phrases:
                for p in pack_files:
                    blob = p.read_text(encoding="utf-8", errors="replace")
                    self.assertNotIn(phrase, blob,
                                     f"模板包 {p.name} 命中上游 {src} 原文短语：{phrase!r}")

    def test_upstream_role_system_not_reused(self):
        """上游角色体系（scout/worker/reviewer/…）不复用：角色页仅本仓原创三角色。"""
        roles = {p.name for p in (TEMPLATE / "roles").glob("*.md")}
        self.assertEqual(roles, {"explore.md", "implement.md", "verify.md"},
                         "角色页应为本仓原创 explore/implement/verify 三角色")
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        enum = schema["properties"]["to"]["enum"]
        self.assertEqual(set(enum), {"main", "explore", "implement", "verify"})
        for word in UPSTREAM_ROLE_WORDS:
            self.assertNotIn(word, enum, f"合同 to 枚举不应复用上游角色名 {word}")


class TestNoSecrets(unittest.TestCase):
    """§6.5 零密钥：模板包（含示范、schema、边界文档）密钥扫描 0 命中。"""

    def test_no_secret_hits_in_template_pack(self):
        for p in sorted(TEMPLATE.rglob("*")):
            if not p.is_file():
                continue
            blob = p.read_text(encoding="utf-8", errors="replace")
            for pat in SECRET_PATTERNS:
                self.assertIsNone(pat.search(blob),
                                  f"{p.relative_to(ROOT)} 命中密钥模式 {pat.pattern}")


class TestTemplatePackStructure(unittest.TestCase):
    """模板包结构完整：全链交付物在位，机器校验入口可用。"""

    def test_all_deliverables_in_place(self):
        for rel in ("README.md", "handoff.schema.json", "example-walkthrough.md",
                    "boundary-vs-112.md",
                    "roles/explore.md", "roles/implement.md", "roles/verify.md"):
            self.assertTrue((TEMPLATE / rel).exists(), f"模板包缺 {rel}")
        self.assertTrue(VALIDATOR.exists(), "缺机器校验入口 scripts/validate_handoff.py")

    def test_validator_cli_accepts_walkthrough_contract(self):
        """机器校验入口对走查内联合同判 0（valid handoff-v1）。"""
        _, contracts = load_contracts()
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                         encoding="utf-8") as f:
            json.dump(contracts[0], f, ensure_ascii=False)
            path = f.name
        try:
            out = subprocess.run(
                [sys.executable, str(VALIDATOR), path],
                capture_output=True, text=True, timeout=60)
            self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
            self.assertIn("valid handoff-v1", out.stdout)
        finally:
            Path(path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
