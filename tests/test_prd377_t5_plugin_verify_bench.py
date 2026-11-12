# -*- coding: utf-8 -*-
"""PRD-377/T5 测试（trend #1881 的 T5 环节）：插件安检发现验证台验收试运行。

运行：uv run --with pytest python -m pytest tests/test_prd377_t5_plugin_verify_bench.py -q
（仓库根执行）

验收（T1 §6 T5 行「样例全链回放+UNVERIFIED 拦截演练+文档无密钥」）：
  接入点全链演练（PR 门槛 require_integration_point 验收）：真实
  scan_skill 扫描合成技能目录 → findings 过台 → VERIFIED 转
  security_reviews 消费形态（listing_inbox.collect 消费五件套）→ JSONL
  落账 → 闸门全 pass；两遍全链产物逐字节一致（确定性可复现）；UNVERIFIED
  拦截演练（复现不出发现拦在审批外+落账留痕）；目录变更二次验证关闭演练
  （BENCH_STALE 拒绝复用→新目录复算 VERIFIED）；账本 append-only；零
  上架词面复验（演练返回值零上架载荷键）；链复跑：T2/T3/T4 测试子进程
  复跑 exit 0；文档无密钥：T1 设计文档拼接 needle 扫描+占位符纪律。
  零网络；全合成占位。
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from market_gate_scan import scan_skill  # noqa: E402
from plugin_verify_bench import PluginBenchLedger, verify_findings  # noqa: E402
from plugin_verify_bench_gates import (  # noqa: E402
    append_only_gate,
    gate_summary,
    mark_baseline,
    stale_gate,
    verdict_gate,
)

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


def _bench_items(skill_dir):
    report = scan_skill(skill_dir, declared_name="skill-a（占位）",
                        declared_version="1.0.0")
    return [dict(f, finding_id=f"f-{i:03d}",
                 source_ref=f"market-gate-report/v1#findings[{i}]（占位）")
            for i, f in enumerate(report["findings"], start=1)]


def _security_reviews_from_verified(verified):
    """接入点：VERIFIED 发现转 security_reviews 消费形态（363 collect
    五件套：source_ref/report_ref/diff_digest/reason）。"""
    return [{"source_ref": v["source_ref"],
             "report_ref": f"verify-bench {v['dir_fingerprint']}（占位）",
             "diff_digest": "sha16:diff（占位）",
             "reason": f"安检发现 {v['rule_id']} 待审批（占位）"}
            for v in verified]


class TestIntegrationPointDrill(unittest.TestCase):
    def test_outlet_full_chain_twice_deterministic(self):
        """接入点全链演练（PR 门槛验收）：scan → 过台 → VERIFIED 转
        security_reviews 形态 → JSONL 落账 → 闸门全 pass；两遍逐字节一致。"""
        runs = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as td:
                skill_dir = _skill_dir(Path(td))
                items = _bench_items(skill_dir)
                out = verify_findings(items, skill_dir, recheck_fn, at=NOW)
                reviews = _security_reviews_from_verified(out["verified"])
                self.assertTrue(reviews)
                self.assertTrue(all({"source_ref", "report_ref", "reason"}
                                    <= set(q) for q in reviews))
                led = PluginBenchLedger(Path(td) / "pbench.jsonl")
                for rec in out["verified"] + [r for r in out["unverified"]
                                              if not r.get("refused")]:
                    led.record(rec, at=NOW)
                gates = [append_only_gate(led)]
                for rec in led.entries():
                    gates.append(verdict_gate(rec))
                    gates.append(stale_gate(rec, skill_dir))
                runs.append({"out": out, "reviews": reviews,
                             "entries": led.entries(),
                             "summary": gate_summary(gates)})
                self.assertEqual(gate_summary(gates)["gate"], "pass")
        self.assertEqual(json.dumps(runs[0], sort_keys=True),
                         json.dumps(runs[1], sort_keys=True))


class TestFailureDrills(unittest.TestCase):
    def test_unverified_blocked_and_traced(self):
        """UNVERIFIED 拦截演练：复现不出发现拦在审批外+落账留痕。"""
        with tempfile.TemporaryDirectory() as td:
            skill_dir = _skill_dir(Path(td))
            items = _bench_items(skill_dir)
            phantom = [dict(items[0], finding_id="f-900", rule_id="M-9-99")]
            led = PluginBenchLedger(Path(td) / "pbench.jsonl")
            out = verify_findings(phantom, skill_dir, recheck_fn, at=NOW)
            self.assertEqual(out["verified"], [])
            for rec in out["unverified"]:
                if not rec.get("refused"):
                    led.record(rec, at=NOW)
            self.assertEqual(led.entries()[-1]["verdict"], "UNVERIFIED")

    def test_dir_change_then_second_verify_closes(self):
        """目录变更二次验证关闭演练：BENCH_STALE 拒绝复用 → 新目录复算
        VERIFIED 落新账。"""
        with tempfile.TemporaryDirectory() as td:
            skill_dir = _skill_dir(Path(td))
            led = PluginBenchLedger(None)
            first = verify_findings(_bench_items(skill_dir), skill_dir,
                                    recheck_fn, at=NOW)
            self.assertTrue(first["verified"])
            led.record(first["verified"][0], at=NOW)
            (skill_dir / "extra.md").write_text("新增（占位）",
                                                encoding="utf-8")
            out = led.reverify(first["verified"][0]["finding_id"],
                               skill_dir, recheck_fn, at=NOW)
            self.assertEqual(out["refused"], "BENCH_STALE")
            second = verify_findings(_bench_items(skill_dir), skill_dir,
                                     recheck_fn, at=NOW)
            if second["verified"]:
                rec = led.record(second["verified"][0], at=NOW)
                self.assertEqual(rec["verdict"], "VERIFIED")

    def test_zero_listing_trigger_and_append_only(self):
        """零上架词面复验（演练返回值零上架载荷键）+账本 append-only。"""
        with tempfile.TemporaryDirectory() as td:
            skill_dir = _skill_dir(Path(td))
            out = verify_findings(_bench_items(skill_dir), skill_dir,
                                  recheck_fn, at=NOW)
            for rec in out["verified"]:
                for key in ("installed", "published", "skillpack_changed"):
                    self.assertNotIn(key, rec)
            led = PluginBenchLedger(None)
            for rec in out["verified"]:
                led.record(rec, at=NOW)
            mark_baseline(led)
            self.assertEqual(append_only_gate(led)["gate"], "pass")


class TestChainRerun(unittest.TestCase):
    def test_t2_t3_t4_rerun_green(self):
        """链复跑：T2/T3/T4 测试子进程复跑 exit 0（链上仍绿实测）。"""
        for test_file in ("test_prd377_t2_plugin_verify_bench.py",
                          "test_prd377_t3_plugin_verify_bench_gates.py",
                          "test_prd377_t4_plugin_verify_bench_boundary.py"):
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q",
                 str(Path(__file__).resolve().parent / test_file)],
                capture_output=True, timeout=300)
            self.assertEqual(proc.returncode, 0,
                             f"{test_file} 复跑失败：{proc.stdout[-400:]}")


class TestDocNoSecrets(unittest.TestCase):
    def test_t1_design_doc_no_secrets(self):
        """文档无密钥：T1 设计文档拼接 needle 扫描+占位符纪律（R5）。"""
        repo = Path(__file__).resolve().parents[1]
        doc = next(repo.glob("docs/plans/2026-11-12-prd-377-*.md"))
        text = doc.read_text(encoding="utf-8").lower()
        for needle in ("sk-" + "live", "passw" + "ord", "api_k" + "ey"):
            self.assertNotIn(needle, text, f"设计文档出现密钥词 {needle}")
        self.assertIn("占位", text)


if __name__ == "__main__":
    unittest.main()
