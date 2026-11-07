# -*- coding: utf-8 -*-
"""PRD-293/T5 测试（trend #1470）：验收试运行——样例全流程回放 + 歧义/失败
演练 + 文档无密钥。

运行：python3 -m unittest tests.test_prd293_t5_acceptance -v（仓库根执行）

验收标准（trend #1470）：**引用解析全链通过；红线断言全过；文档无密钥**。

回放：base-skill 装载（自身+dep 引用契约齐备）→ 审计依赖图 → 歧义/失败
演练（NOT_FOUND fail-closed/SELF_LOOP/CYCLE/CORRUPT 全触发且不降级）→
文档无密钥。
零网络；全合成占位。
"""
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from skill_load_gate import load_with_references, x_references_consistency  # noqa: E402
from skill_ref_resolver import RefAudit, resolve  # noqa: E402

REGISTRY = {
    "packs": [{
        "name": "livepowers-fixture",
        "skills": [
            {"name": "base-skill（占位）",
             "triggers": "Use when 基础流程（占位）。",
             "examples": ["产出：基础记录（占位）"],
             "x-references": ["@dep-skill（占位）"]},
            {"name": "dep-skill（占位）",
             "triggers": "Use when 依赖步骤（占位）。",
             "examples": ["产出：依赖记录（占位）"]},
        ],
    }],
}


class 全链回放Tests(unittest.TestCase):
    def test_full_chain_replay_load_and_audit(self):
        """样例全流程：解析+留痕 → 装载闸契约包齐备 → 依赖图可重建。"""
        audit = RefAudit()
        for i, raw in enumerate(("@dep-skill（占位）",)):
            out = audit.resolve_logged(raw, REGISTRY, at=f"2026-11-04T09:0{i}:00Z",
                                       from_skill="base-skill（占位）")
            self.assertFalse(out["refused"], raw)
        loaded = load_with_references("base-skill（占位）", REGISTRY)
        self.assertTrue(loaded["usable"])
        self.assertEqual(set(loaded["contracts"]),
                         {"base-skill（占位）", "dep-skill（占位）"})
        graph = audit.dependency_graph()
        self.assertEqual(graph.get("base-skill（占位）"), ["dep-skill（占位）"])
        # 双载体同源：声明集 == 审计解析集
        entry = REGISTRY["packs"][0]["skills"][0]
        self.assertTrue(x_references_consistency(entry, audit.records)["consistent"])

    def test_replay_deterministic(self):
        def run():
            audit = RefAudit()
            audit.resolve_logged("@dep-skill（占位）", REGISTRY,
                                 at="2026-11-04T09:00:00Z",
                                 from_skill="base-skill（占位）")
            return str(audit.records)
        self.assertEqual(run(), run())


class 歧义失败演练Tests(unittest.TestCase):
    def test_all_failures_no_degrade(self):
        """四路全触发且不降级（NOT_FOUND/SELF_LOOP/CYCLE/CORRUPT）。"""
        broken = {"packs": [{"skills": [
            {"name": "坏引用（占位）", "triggers": "x（占位）", "examples": [],
             "x-references": ["@不存在（占位）"]},
            {"name": "自引（占位）", "triggers": "x（占位）", "examples": [],
             "x-references": ["@自引（占位）"]},
            {"name": "环A（占位）", "triggers": "x（占位）", "examples": [],
             "x-references": ["@环B（占位）"]},
            {"name": "环B（占位）", "triggers": "x（占位）", "examples": [],
             "x-references": ["@环A（占位）"]}]}]}
        for skill, want in (("坏引用（占位）", "REF_NOT_FOUND"),
                            ("自引（占位）", "REF_CYCLE"),
                            ("环A（占位）", "REF_CYCLE")):
            out = load_with_references(skill, broken)
            self.assertFalse(out["usable"], skill)
            self.assertEqual(out["failures"][0]["error_code"], want, skill)
        dup = {"packs": [{"skills": [
            {"name": "dup（占位）", "triggers": "x", "examples": []},
            {"name": "dup（占位）", "triggers": "y", "examples": []},
            {"name": "caller（占位）", "triggers": "x", "examples": []}]}]}
        audit = RefAudit()
        out = audit.resolve_logged("@dup（占位）", dup, at="2026-11-04T09:00:00Z",
                                   from_skill="caller（占位）")
        self.assertEqual(out["error_code"], "REF_REGISTRY_CORRUPT")


class 文档无密钥Tests(unittest.TestCase):
    def test_design_doc_no_secrets(self):
        secret_re = re.compile(r"(sk-[A-Za-z0-9]{8,}|ghp_[A-Za-z0-9]{8,}|"
                               r"AKIA[0-9A-Z]{16}|password\s*[:=]\s*['\"][^'\"]{4,})",
                               re.IGNORECASE)
        docs = list((REPO / "docs" / "plans").glob("2026-11-04-prd-293-*.md"))
        self.assertTrue(docs, "T1 设计文档在位")
        for doc in docs:
            blob = doc.read_text(encoding="utf-8")
            self.assertFalse(secret_re.findall(blob), doc.name)
            for host in re.findall(r"https?://([a-z0-9.-]+)", blob, re.IGNORECASE):
                self.assertTrue(host.endswith(("github.com", "example.com",
                                               "example.invalid", "synthetic",
                                               "local")), f"{doc.name} {host}")


if __name__ == "__main__":
    unittest.main()
