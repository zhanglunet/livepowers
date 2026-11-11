# -*- coding: utf-8 -*-
"""PRD-349/T2 测试（trend #1628 的 T2 环节）：skill 调用重放包。

运行：python3 -m unittest tests.test_prd349_t2_skill_call_replay -v（仓库根执行）

覆盖（T1 §3.1/§3.2/§4 + R1–R4）：三件套构建（缺 utterance/空入参
PACK_INCOMPLETE）；重放三步（同输入同登记册 REPLAY_OK/登记册或版本漂移
INPUT_DRIFT 拒绝防冒充/决策漂移 MISMATCH 首分歧条显形）；R2 重放零执行
（与 skill_ref_resolver.resolve 真实串联——解析层复算，零 skill 执行）；R4
账本 append-only；AST 零网络零子进程。零网络；全合成占位。
"""
import ast
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from skill_call_replay import (  # noqa: E402
    ERROR_CODES,
    ReplayLedger,
    make_pack,
    replay,
)
from skill_ref_resolver import resolve  # noqa: E402

NOW = "2026-11-11T09:00:00Z"
REGISTRY = {"packs": [{"skills": [
    {"name": "weekly-report（占位）", "triggers": ["写周报（占位）"],
     "examples": "输出周报 markdown（占位）"}]}]}
UTTERANCES = ["@weekly-report（占位）"]
CALLS = [{"utterance": UTTERANCES[0], "resolved_skill": "weekly-report（占位）",
          "trigger_conditions": ["写周报（占位）"], "refusal_code": None}]


class TestPackBuild(unittest.TestCase):
    def test_pack_three_parts_complete(self):
        pack = make_pack(CALLS, REGISTRY, rules_version="v1")
        self.assertEqual(pack["schema"], "skill-call-replay-pack/v1")
        fp = pack["input_fingerprint"]
        self.assertTrue(fp["registry_digest"].startswith("sha16:"))
        self.assertEqual(fp["rules_version"], "v1")
        self.assertEqual(pack["output"]["resolved"], ["weekly-report（占位）"])

    def test_incomplete_refused(self):
        out = make_pack([{"resolved_skill": "x"}], REGISTRY, rules_version="v1")
        self.assertEqual(out["refused"], "PACK_INCOMPLETE")
        out2 = make_pack([], REGISTRY, rules_version="v1")
        self.assertEqual(out2["refused"], "PACK_INCOMPLETE")
        out3 = make_pack(CALLS, REGISTRY, rules_version="")
        self.assertEqual(out3["refused"], "PACK_INCOMPLETE")


class TestReplay(unittest.TestCase):
    def _pack(self):
        return make_pack(CALLS, REGISTRY, rules_version="v1")

    def test_same_inputs_replay_ok_with_real_resolver(self):
        """R2 正路：同登记册重放 resolve → REPLAY_OK（解析层复算零执行）。"""
        out = replay(self._pack(), UTTERANCES, REGISTRY, resolve,
                     rules_version="v1")
        self.assertEqual(out["verdict"], "REPLAY_OK")

    def test_input_drift_refused(self):
        mutated = {"packs": [{"skills": []}]}
        out = replay(self._pack(), UTTERANCES, mutated, resolve,
                     rules_version="v1")
        self.assertEqual(out["refused"], "REPLAY_INPUT_DRIFT")
        out2 = replay(self._pack(), UTTERANCES, REGISTRY, resolve,
                      rules_version="v2")
        self.assertEqual(out2["refused"], "REPLAY_INPUT_DRIFT")

    def test_mismatch_first_divergence_visible(self):
        """R3：解析漂移 → MISMATCH 首分歧条显形，零静默。

        登记册内容漂移属于 INPUT_DRIFT（指纹复核先拒）；决策漂移用同登记册
        的漂移 resolver（stub 返回 REF_NOT_FOUND）触发。
        """
        mutated = {"packs": [{"skills": []}]}
        out = replay(self._pack(), UTTERANCES, mutated, resolve,
                     rules_version="v1")
        self.assertEqual(out["refused"], "REPLAY_INPUT_DRIFT")

        def drift_resolve(utt, reg):
            return {"skill": None, "trigger_conditions": None,
                    "resolution": {"status": "refused",
                                   "error_code": "REF_NOT_FOUND"}}
        out2 = replay(self._pack(), UTTERANCES, REGISTRY, drift_resolve,
                      rules_version="v1")
        self.assertEqual(out2["verdict"], "REPLAY_MISMATCH")
        self.assertEqual(out2["evidence"]["first_divergence_index"], 0)
        self.assertEqual(out2["evidence"]["got"]["refusal_code"], "REF_NOT_FOUND")

    def test_incomplete_pack_refused(self):
        out = replay({"schema": "skill-call-replay-pack/v1"}, UTTERANCES,
                     REGISTRY, resolve, rules_version="v1")
        self.assertEqual(out["refused"], "PACK_INCOMPLETE")


class TestLedgerAndRedline(unittest.TestCase):
    def test_ledger_append_only(self):
        led = ReplayLedger()
        pack = make_pack(CALLS, REGISTRY, rules_version="v1")
        led.record(pack, {"verdict": "REPLAY_OK", "evidence": None}, at=NOW)
        before = [dict(x) for x in led.entries]
        led.record(pack, {"refused": "REPLAY_INPUT_DRIFT", "evidence": None},
                   at=NOW)
        self.assertEqual(led.entries[0], before[0])
        self.assertEqual(len(led.entries), 2)

    def test_error_codes_closed(self):
        self.assertEqual(set(ERROR_CODES),
                         {"REPLAY_INPUT_DRIFT", "REPLAY_MISMATCH",
                          "PACK_INCOMPLETE"})

    def test_ast_zero_network_zero_subprocess(self):
        """R2 AST：解析层复算——零网络零子进程。"""
        banned = {"urllib", "requests", "socket", "http", "subprocess"}
        tree = ast.parse((REPO / "scripts" / "skill_call_replay.py").read_text(
            encoding="utf-8"))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module.split(".")[0]]
            for mod in mods:
                self.assertNotIn(mod, banned)


if __name__ == "__main__":
    unittest.main()
