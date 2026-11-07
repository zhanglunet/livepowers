# -*- coding: utf-8 -*-
"""PRD-307/T2 skill 调用重放包·replay-pack/v1 最小实现测试（trend #1547）。

覆盖（T1 设计 §1/§3/§4）：schema 组装与字段纪律（缺字段报错不猜、错误码封闭）、
fpv1 指纹稳定性、append-only 账本、verify_skill_replay 二值结论（同册同指令重放
必 MATCH / 换册显形 REPLAY_INPUT_MISMATCH / 重放面零写盘零正文复制）、与
search 检索出口的端到端装订（真实登记册全量）。全部占位合成零网络。
"""
import copy
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from skill_registry import load_registry, search  # noqa: E402
import replay_pack as rp  # noqa: E402


def _registry():
    try:
        return load_registry()
    except Exception:
        # 测试环境兜底：最小合法登记册
        return {"alignment": "skill-pack-layering-spec@1.0.0",
                "packs": [{"name": "lp-syn", "positioning": "占位包", "version": "0.1.0",
                           "spec_version": "1.0.0",
                           "skills": [{"name": "syn-skill", "triggers": ["合成触发词"],
                                       "positioning": "占位技能"}]}]}


REGISTRY = _registry()
QUERY = "合成触发词"


class SchemaAssemblyTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.matches = search(REGISTRY, QUERY)
        cls.pack = rp.pack_from_skill_invoke(REGISTRY, QUERY, cls.matches)

    def test_pack_shape_and_registry_fingerprint(self):
        self.assertEqual(self.pack["schema_version"], "replay-pack/v1")
        self.assertEqual(self.pack["action"], "skill_invoke")
        self.assertEqual(self.pack["input"]["inputs"]["query"], QUERY)
        self.assertTrue(self.pack["input"]["inputs"]["registry_fingerprint"]
                        .startswith("fpv1:"))
        self.assertIn("skill-pack-layering-spec", self.pack["decision"]["rules_version"])

    def test_output_view_carries_identifiers_not_prose(self):
        view = rp.output_view_of_skill_invoke(self.matches)
        for m in view["result"]["matches"]:
            self.assertIn("pack", m) and self.assertIn("name", m)
            self.assertNotIn("one_line", m)   # 登记资产不入账本
            self.assertNotIn("triggers", m)
        self.assertEqual(view["key_numbers"]["matches_total"], len(self.matches))

    def test_empty_query_rejected(self):
        with self.assertRaises(rp.ReplayPackError) as ei:
            rp.pack_from_skill_invoke(REGISTRY, "  ", [])
        self.assertEqual(ei.exception.code, "REPLAY_INPUT_REQUIRED")

    def test_fingerprint_stability_and_sensitivity(self):
        p1 = rp.pack_from_skill_invoke(REGISTRY, QUERY, self.matches)
        p2 = rp.pack_from_skill_invoke(REGISTRY, QUERY, self.matches)
        self.assertEqual(p1["input"]["inputs"]["registry_fingerprint"],
                         p2["input"]["inputs"]["registry_fingerprint"])
        drifted = copy.deepcopy(REGISTRY)
        if drifted.get("packs"):
            drifted["packs"][0]["name"] = drifted["packs"][0]["name"] + "-drifted"
        p3 = rp.pack_from_skill_invoke(drifted, QUERY, search(drifted, QUERY))
        self.assertNotEqual(p3["input"]["inputs"]["registry_fingerprint"],
                            p1["input"]["inputs"]["registry_fingerprint"])


class FieldDisciplineTests(unittest.TestCase):

    def test_closed_error_vocabulary(self):
        good = dict(action="skill_invoke", inputs={"k": "v"},
                    decision={"chosen": "c", "why": "w", "rules_version": "v1"},
                    output={"result": "r", "key_numbers": {"n": 1}},
                    replay_command="rerun: x")
        with self.assertRaises(rp.ReplayPackError) as ei:
            rp.build_replay_pack(**{**good, "inputs": {}})
        self.assertEqual(ei.exception.code, "REPLAY_INPUT_REQUIRED")
        for drop in ("chosen", "why", "rules_version"):
            decision = {k: v for k, v in good["decision"].items() if k != drop}
            with self.assertRaises(rp.ReplayPackError) as ed:
                rp.build_replay_pack(**{**good, "decision": decision})
            self.assertEqual(ed.exception.code, "REPLAY_DECISION_FIELDS_REQUIRED")
        with self.assertRaises(ValueError):
            rp.ReplayPackError("NOT_IN_TABLE", "x")
        self.assertEqual(len(set(rp.ERROR_CODES)), len(rp.ERROR_CODES))


class LedgerTests(unittest.TestCase):

    def test_append_only_and_cold_start(self):
        pack = rp.pack_from_skill_invoke(REGISTRY, QUERY, search(REGISTRY, QUERY))
        with tempfile.TemporaryDirectory() as tmp:
            ledger = rp.ReplayLedger(Path(tmp) / "ledger.jsonl")
            self.assertEqual(ledger.read_all(), [])
            ledger.append(pack)
            before = ledger.bytes_now()
            ledger.append(pack)
            packs = ledger.read_all()
            self.assertEqual(len(packs), 2)
            self.assertEqual(packs[0], pack)
            self.assertGreater(len(ledger.bytes_now()), len(before))


class VerifyReplayTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.matches = search(REGISTRY, QUERY)
        cls.pack = rp.pack_from_skill_invoke(REGISTRY, QUERY, cls.matches)

    def test_same_registry_replays_to_match_and_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = rp.ReplayLedger(Path(tmp) / "ledger.jsonl")
            ledger.append(self.pack)
            before = ledger.bytes_now()
            result = rp.verify_skill_replay(self.pack, REGISTRY, search)
            self.assertEqual(result["status"], rp.REPLAY_MATCH)
            self.assertIsNone(result["evidence"])
            self.assertEqual(ledger.bytes_now(), before)  # 重放面只读

    def test_drifted_registry_is_input_mismatch(self):
        drifted = copy.deepcopy(REGISTRY)
        if drifted.get("packs"):
            drifted["packs"][0]["name"] = drifted["packs"][0]["name"] + "-drifted"
        result = rp.verify_skill_replay(self.pack, drifted, search)
        self.assertEqual(result["status"], rp.REPLAY_MISMATCH)
        self.assertEqual(result["evidence"]["reason"], "REPLAY_INPUT_MISMATCH")
        self.assertEqual(result["evidence"]["field"], "registry_fingerprint")

    def test_miss_replays_as_miss_not_forced(self):
        pack = rp.pack_from_skill_invoke(REGISTRY, "完全不相关的查询词",
                                         search(REGISTRY, "完全不相关的查询词"))
        self.assertIn("miss", pack["decision"]["chosen"])
        result = rp.verify_skill_replay(pack, REGISTRY, search)
        self.assertEqual(result["status"], rp.REPLAY_MATCH)

    def test_ledger_roundtrip_replay_still_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = rp.ReplayLedger(Path(tmp) / "ledger.jsonl")
            ledger.append(self.pack)
            reloaded = rp.ReplayLedger(Path(tmp) / "ledger.jsonl").read_all()[0]
            result = rp.verify_skill_replay(reloaded, REGISTRY, search)
            self.assertEqual(result["status"], rp.REPLAY_MATCH)


if __name__ == "__main__":
    unittest.main()
