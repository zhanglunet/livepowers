# -*- coding: utf-8 -*-
"""PRD-377/T3 测试（trend #1881 的 T3 环节）：插件安检发现验证台闸门。

运行：uv run --with pytest python -m pytest tests/test_prd377_t3_plugin_verify_bench_gates.py -q
（仓库根执行）

覆盖（T1 §5 + R1/R3/R4）：append_only_gate（无基线形态过/mark_baseline 后
追加 pass/删除或首条改写 LEDGER_DRIFT 显形/非账本对象显形）；verdict_gate
（一致 pass/双向不一致 BENCH_REPRO_MISMATCH/缺件词表外 BENCH_INCOMPLETE
显形）；stale_gate（指纹一致 pass/不符 BENCH_STALE 显形）；gate_summary
一票否决；与 T2 串联（真实 scan_skill+PluginBenchLedger 产物过闸全 pass）；
ERROR_CODES 随模块导出；AST 零 LLM 零网络零安装词面+闸门只读。零网络；
全合成占位。
"""
import ast
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from plugin_verify_bench import PluginBenchLedger, verify_finding  # noqa: E402
from plugin_verify_bench_gates import (  # noqa: E402
    ERROR_CODES,
    append_only_gate,
    gate_summary,
    mark_baseline,
    stale_gate,
    verdict_gate,
)
from market_gate_scan import scan_skill  # noqa: E402

NOW = "2026-11-13T09:00:00Z"


def _skill_dir(tmp: Path) -> Path:
    d = tmp / "skill-a（占位）"
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        "---\nname: skill-a（占位）\nversion: 1.0.0\n---\n\n# 正文（占位）\n"
        "subprocess.call（占位文本触发 M-2-02 扫描）\n",
        encoding="utf-8")
    return d


def recheck_fn(skill_dir):
    return scan_skill(skill_dir, declared_name="skill-a（占位）",
                      declared_version="1.0.0").get("findings", [])


FINDING = {"finding_id": "f-001", "rule_id": "M-2-02",
           "location": "SKILL.md",
           "source_ref": "market-gate-report/v1#findings[0]（占位）"}


def _ledger(skill_dir):
    led = PluginBenchLedger(None)
    led.record(verify_finding(dict(FINDING, finding_id="f-001"), skill_dir,
                              recheck_fn, at=NOW), at=NOW)
    led.record(verify_finding(dict(FINDING, finding_id="f-002"), skill_dir,
                              recheck_fn, at=NOW), at=NOW)
    return led


class TestAppendOnlyGate(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.skill_dir = _skill_dir(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_baseline_form_check_passes(self):
        self.assertEqual(append_only_gate(_ledger(self.skill_dir))["gate"],
                         "pass")

    def test_mark_baseline_then_append_passes(self):
        led = _ledger(self.skill_dir)
        mark_baseline(led)
        led.record(verify_finding(dict(FINDING, finding_id="f-003"),
                                  self.skill_dir, recheck_fn, at=NOW),
                   at=NOW)
        self.assertEqual(append_only_gate(led)["gate"], "pass")

    def test_deletion_detected(self):
        led = _ledger(self.skill_dir)
        mark_baseline(led)
        led._records.pop()
        self.assertEqual(append_only_gate(led)["gate"], "LEDGER_DRIFT")

    def test_first_record_rewrite_detected(self):
        led = _ledger(self.skill_dir)
        mark_baseline(led)
        led._records[0]["verdict"] = "UNVERIFIED"
        self.assertEqual(append_only_gate(led)["gate"], "LEDGER_DRIFT")

    def test_non_ledger_object_visible(self):
        self.assertEqual(append_only_gate(object())["gate"], "LEDGER_DRIFT")


class TestVerdictGate(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.skill_dir = _skill_dir(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_consistent_record_passes(self):
        rec = verify_finding(dict(FINDING, finding_id="f-001"),
                             self.skill_dir, recheck_fn, at=NOW)
        self.assertEqual(verdict_gate(rec)["gate"], "pass")

    def test_verified_but_no_match_mismatch(self):
        rec = verify_finding(dict(FINDING, finding_id="f-001"),
                             self.skill_dir, recheck_fn, at=NOW)
        rec["reproduce"]["match"] = False
        self.assertEqual(verdict_gate(rec)["gate"], "BENCH_REPRO_MISMATCH")

    def test_unverified_but_match_mismatch(self):
        rec = verify_finding(dict(FINDING, finding_id="f-001"),
                             self.skill_dir, recheck_fn, at=NOW)
        rec["verdict"] = "UNVERIFIED"   # 词表内但与 match=true 不一致
        self.assertEqual(verdict_gate(rec)["gate"], "BENCH_REPRO_MISMATCH")

    def test_vocab_out_and_missing_visible(self):
        rec = dict(verify_finding(dict(FINDING, finding_id="f-001"),
                                  self.skill_dir, recheck_fn, at=NOW),
                   verdict="MAYBE（占位）")
        self.assertEqual(verdict_gate(rec)["gate"], "BENCH_INCOMPLETE")
        out = verdict_gate({"finding_id": "x"})
        self.assertEqual(out["gate"], "BENCH_INCOMPLETE")
        self.assertTrue(any("缺" in r for r in out["reasons"]))


class TestStaleGate(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.skill_dir = _skill_dir(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_matching_fingerprint_passes(self):
        rec = verify_finding(dict(FINDING, finding_id="f-001"),
                             self.skill_dir, recheck_fn, at=NOW)
        self.assertEqual(stale_gate(rec, self.skill_dir)["gate"], "pass")

    def test_stale_fingerprint_visible(self):
        rec = verify_finding(dict(FINDING, finding_id="f-001"),
                             self.skill_dir, recheck_fn, at=NOW)
        with tempfile.TemporaryDirectory() as td:
            other = _skill_dir(Path(td))
            (other / "extra.md").write_text("新增（占位）", encoding="utf-8")
            self.assertEqual(stale_gate(rec, other)["gate"], "BENCH_STALE")


class TestSummaryAndChain(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.skill_dir = _skill_dir(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_summary_one_block_votes_all(self):
        led = _ledger(self.skill_dir)
        led.record(verify_finding(dict(FINDING, finding_id="f-003"),
                                  self.skill_dir, recheck_fn, at=NOW),
                   at=NOW)
        rec = verify_finding(dict(FINDING, finding_id="f-001"),
                             self.skill_dir, recheck_fn, at=NOW)
        rec["reproduce"]["match"] = False
        out = gate_summary([append_only_gate(led), verdict_gate(rec)])
        self.assertEqual(out["gate"], "block")
        self.assertEqual(out["gates_checked"], 2)

    def test_chain_with_real_t2_products(self):
        """与 T2 串联：真实 scan_skill+PluginBenchLedger 产物过闸全 pass。"""
        led = _ledger(self.skill_dir)
        mark_baseline(led)
        rec = verify_finding(dict(FINDING, finding_id="f-001"),
                             self.skill_dir, recheck_fn, at=NOW)
        results = [append_only_gate(led), verdict_gate(rec),
                   stale_gate(rec, self.skill_dir)]
        self.assertTrue(all(r["gate"] == "pass" for r in results))
        self.assertEqual(gate_summary(results)["gate"], "pass")

    def test_error_codes_closed_and_exported(self):
        import plugin_verify_bench_gates as g
        self.assertEqual(set(g.ERROR_CODES),
                         {"LEDGER_DRIFT", "BENCH_INCOMPLETE",
                          "BENCH_REPRO_MISMATCH", "BENCH_STALE"})


class TestRedline(unittest.TestCase):
    def test_ast_zero_llm_zero_network_zero_install_readonly(self):
        banned = {"urllib", "requests", "socket", "http", "subprocess",
                  "openai", "anthropic", "pack_installer", "install_flow"}
        src = SCRIPTS / "plugin_verify_bench_gates.py"
        tree = ast.parse(src.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertFalse(imported & banned, imported & banned)
        text = src.read_text(encoding="utf-8")
        for call in (".record(", ".append("):
            self.assertNotIn(call, text, f"闸门出现账本写调用 {call}")


if __name__ == "__main__":
    unittest.main()
