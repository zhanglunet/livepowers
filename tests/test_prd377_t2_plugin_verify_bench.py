# -*- coding: utf-8 -*-
"""PRD-377/T2 测试（trend #1881 的 T2 环节）：插件安检发现验证台。

运行：uv run --with pytest python -m pytest tests/test_prd377_t2_plugin_verify_bench.py -q
（仓库根执行）

覆盖（T1 §4 + R1~R4）：verify_finding 八件套校验（缺一 BENCH_INCOMPLETE）；
真实扫描器串联（market_gate_scan.scan_skill 重跑复现 → VERIFIED；复现不出
→ UNVERIFIED 词表封闭）；verify_findings 收录审批来源包装（UNVERIFIED 拦
下）；PluginBenchLedger JSONL 真实落库+八件套缺一/词表外/REPRO_MISMATCH
声称拒绝；reverify 目录变更二次验证（指纹不符 BENCH_STALE 拒绝复用/一致
正常复验）；AST 零 LLM 零网络零子进程零安装词面+目录指纹与 PRD-279
install_snapshot.dir_fingerprint 同源。零网络；全合成占位。
"""
import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from install_snapshot import dir_fingerprint  # noqa: E402
from plugin_verify_bench import (  # noqa: E402
    BENCH_SCHEMA,
    ERROR_CODES,
    PluginBenchError,
    PluginBenchLedger,
    VERDICTS,
    verify_finding,
    verify_findings,
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


class TestVerifyFinding(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.skill_dir = _skill_dir(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_verified_with_real_scanner_rerun(self):
        """真实扫描器串联：M-2-02 发现与重跑结果一致 → VERIFIED；目录指纹
        与 PRD-279 dir_fingerprint 同源。"""
        report = scan_skill(self.skill_dir, declared_name="skill-a（占位）",
                            declared_version="1.0.0")
        hit = next(f for f in report["findings"]
                   if f["rule_id"] == "M-2-02")
        finding = dict(FINDING, location=hit["location"])
        out = verify_finding(finding, self.skill_dir, recheck_fn, at=NOW)
        self.assertEqual(out["verdict"], "VERIFIED")
        self.assertEqual(out["schema"], BENCH_SCHEMA)
        files_bytes = {str(p.relative_to(self.skill_dir)): p.read_bytes()
                       for p in self.skill_dir.rglob("*") if p.is_file()}
        self.assertEqual(out["dir_fingerprint"],
                         dir_fingerprint(files_bytes))

    def test_unverified_when_not_reproduced(self):
        out = verify_finding(dict(FINDING, rule_id="M-9-99"), self.skill_dir,
                             recheck_fn, at=NOW)
        self.assertEqual(out["verdict"], "UNVERIFIED")
        self.assertFalse(out["reproduce"]["match"])

    def test_incomplete_refused(self):
        bad = dict(FINDING)
        del bad["location"]
        out = verify_finding(bad, self.skill_dir, recheck_fn, at=NOW)
        self.assertEqual(out["refused"], "BENCH_INCOMPLETE")
        out2 = verify_finding(FINDING, self.skill_dir, None, at=NOW)
        self.assertEqual(out2["refused"], "BENCH_INCOMPLETE")

    def test_verdict_vocab_closed(self):
        self.assertEqual(set(VERDICTS), {"VERIFIED", "UNVERIFIED"})


class TestVerifyFindings(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.skill_dir = _skill_dir(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_outlet_blocks_unverified(self):
        """收录审批来源包装：UNVERIFIED 拦下不上审批（R1）。"""
        findings = [dict(FINDING, finding_id="f-001"),
                    dict(FINDING, finding_id="f-002", rule_id="M-9-99")]
        out = verify_findings(findings, self.skill_dir, recheck_fn, at=NOW)
        self.assertEqual(len(out["verified"]), 1)
        self.assertEqual(out["unverified_count"], 1)
        self.assertEqual(out["unverified"][0]["finding_id"], "f-002")


class TestPluginBenchLedger(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.skill_dir = _skill_dir(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_jsonl_persistence_append_only(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "pbench" / "ledger.jsonl"
            led = PluginBenchLedger(path)
            led.record(verify_finding(dict(FINDING, finding_id="f-001"),
                                      self.skill_dir, recheck_fn, at=NOW),
                       at=NOW)
            led.record(verify_finding(dict(FINDING, finding_id="f-002"),
                                      self.skill_dir, recheck_fn, at=NOW),
                       at=NOW)
            self.assertEqual(len(led.entries()), 2)
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0])["finding_id"], "f-001")

    def test_record_refusals(self):
        led = PluginBenchLedger(None)
        with self.assertRaisesRegex(PluginBenchError, "BENCH_INCOMPLETE"):
            led.record({"schema": BENCH_SCHEMA}, at=NOW)
        with self.assertRaisesRegex(PluginBenchError, "BENCH_REPRO_MISMATCH"):
            bad = verify_finding(dict(FINDING, finding_id="f-003"),
                                 self.skill_dir, recheck_fn, at=NOW)
            bad = dict(bad, verdict="VERIFIED",
                       reproduce={"match": False, "detail": "改（占位）"})
            led.record(bad, at=NOW)


class TestReverify(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.skill_dir = _skill_dir(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_stale_refuses_reuse(self):
        """技能目录变更 → BENCH_STALE 拒绝复用旧 VERIFIED。"""
        led = PluginBenchLedger(None)
        led.record(verify_finding(dict(FINDING, finding_id="f-001"),
                                  self.skill_dir, recheck_fn, at=NOW),
                   at=NOW)
        (self.skill_dir / "extra.md").write_text("新增文件（占位）",
                                                 encoding="utf-8")
        out = led.reverify("f-001", self.skill_dir, recheck_fn, at=NOW)
        self.assertEqual(out["refused"], "BENCH_STALE")

    def test_same_dir_reverify_ok(self):
        led = PluginBenchLedger(None)
        led.record(verify_finding(dict(FINDING, finding_id="f-001"),
                                  self.skill_dir, recheck_fn, at=NOW),
                   at=NOW)
        out = led.reverify("f-001", self.skill_dir, recheck_fn, at=NOW)
        self.assertEqual(out["verdict"], "VERIFIED")


class TestRedline(unittest.TestCase):
    def test_dir_fingerprint_same_source_as_install_snapshot(self):
        """目录指纹与 PRD-279 install_snapshot.dir_fingerprint 同源
        （import 复用）。"""
        import plugin_verify_bench as pb
        import install_snapshot as inst
        self.assertIs(pb.dir_fingerprint, inst.dir_fingerprint)

    def test_ast_zero_llm_zero_network_zero_install(self):
        banned = {"urllib", "requests", "socket", "http", "subprocess",
                  "openai", "anthropic", "pack_installer", "install_flow"}
        src = SCRIPTS / "plugin_verify_bench.py"
        tree = ast.parse(src.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertFalse(imported & banned, imported & banned)

    def test_error_codes_closed(self):
        self.assertEqual(set(ERROR_CODES),
                         {"BENCH_INCOMPLETE", "BENCH_REPRO_MISMATCH",
                          "BENCH_STALE"})


if __name__ == "__main__":
    unittest.main()
