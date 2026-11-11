# -*- coding: utf-8 -*-
"""PRD-349/T4 测试（trend #1628 的 T4 环节）：中文触发调用重放划界断言。

运行：python3 -m pytest tests/test_prd349_t4_skill_call_replay_boundary.py -q
（仓库根执行；与 349/T2 同目录惯例）

覆盖（T1 §0/§2，验收「划界断言通过」）：
  ① 模块隔离双向：skill_call_replay/gates 零导入 install_snapshot（PRD-279
    安装可逆）/eng_checklist（PRD-341 生产化机检）+ 借鉴词零出现（AiSOC/
    OpenBot MIT 只借形态）；install_snapshot 零导入 skill_call_replay*；
  ② 唯一耦合钉值：skill_call_replay 静态导入全标准库——解析层经
    resolve_fn 注入（PRD-227 登记册形态注入，零 import 耦合钉值）；零网络
    零子进程零 skill 执行词面 AST（R2）；
  ③ R1 行为钉值：决策缺 utterance/resolved_skill 任一或空 calls →
    refused=PACK_INCOMPLETE；
  ④ R2 零执行行为钉值：resolve_fn 收到深拷贝（registry 零污染）；
  ⑤ R3 零静默钉值：mismatch 键面封闭 {schema,refused,verdict,evidence,
    rerun_count}——零回退新结果载荷键；
  ⑥ R4：ReplayLedger 方法面封闭（零删除方法）；
  ⑦ §2 划界钉值：install_snapshot 快照面（install-snapshot-v1 +
    FingerprintMismatch）符号不变——PRD-279 管安装可逆，本条管调用可重放，
    互不越界。
零网络；全合成占位。
"""
import ast
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from install_snapshot import SCHEMA as INSTALL_SCHEMA  # noqa: E402
from skill_call_replay import (  # noqa: E402
    ReplayLedger,
    make_pack,
    replay,
)

REGISTRY = {"packs": [{"skills": [
    {"name": "weekly-report（占位）", "triggers": ["写周报（占位）"],
     "examples": "输出周报 markdown（占位）"}]}]}
UTTERANCES = ["@weekly-report（占位）"]
CALLS = [{"utterance": UTTERANCES[0], "resolved_skill": "weekly-report（占位）",
          "trigger_conditions": ["写周报（占位）"], "refusal_code": None}]

REPLAY_MODULES = ["skill_call_replay.py", "skill_call_replay_gates.py"]
SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def resolve_fn(raw, registry):
    return {"skill": "weekly-report（占位）",
            "trigger_conditions": ["写周报（占位）"], "resolution": {}}


def _imports_of(path: Path) -> set:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    return imported


class TestModuleIsolation(unittest.TestCase):
    def test_replay_never_imports_snapshot_or_checklist(self):
        """重放面零触碰安装快照/生产化机检（可重放不感知安装可逆）。"""
        for mod in REPLAY_MODULES:
            imported = _imports_of(SCRIPTS / mod)
            for banned in ("install_snapshot", "eng_checklist",
                           "skill_ref_resolver"):
                self.assertNotIn(banned, imported, f"{mod} 导入 {banned}")
            blob = ast.dump(ast.parse(
                (SCRIPTS / mod).read_text(encoding="utf-8")))
            for symbol in ("FingerprintMismatch", "run_checklist"):
                self.assertNotIn(symbol, blob, f"{mod} 引用 {symbol}")

    def test_snapshot_never_imports_replay(self):
        """快照面零导入重放（PRD-279 不感知本条——双向隔离）。"""
        imported = _imports_of(SCRIPTS / "install_snapshot.py")
        for mod in ("skill_call_replay", "skill_call_replay_gates"):
            self.assertNotIn(mod, imported)

    def test_no_aisoc_openbot_symbols(self):
        """借鉴仓（AiSOC/OpenBot，MIT 实测）零符号——只借形态。"""
        for mod in REPLAY_MODULES:
            blob = ast.dump(ast.parse(
                (SCRIPTS / mod).read_text("utf-8"))).lower()
            for word in ("aisoc", "openbot"):
                self.assertNotIn(word, blob, f"{mod} 出现 {word}")

    def test_only_coupling_is_injected_resolve_fn(self):
        """§2 钉值：skill_call_replay 静态导入全标准库——解析层经 resolve_fn
        注入（零 import 耦合）。"""
        imported = _imports_of(SCRIPTS / "skill_call_replay.py")
        self.assertLessEqual(imported,
                             {"__future__", "copy", "hashlib", "json",
                              "typing"})
        src = (SCRIPTS / "skill_call_replay.py").read_text("utf-8")
        self.assertIn("resolve_fn", src)


class TestRedLinePins(unittest.TestCase):
    def test_r1_pack_incomplete_refusal_pinned(self):
        """R1 行为钉值：决策缺 utterance/resolved_skill 或空 calls →
        refused=PACK_INCOMPLETE。"""
        out = make_pack([{"resolved_skill": "x"}], REGISTRY,
                        rules_version="v1")
        self.assertEqual(out["refused"], "PACK_INCOMPLETE")
        out2 = make_pack([], REGISTRY, rules_version="v1")
        self.assertEqual(out2["refused"], "PACK_INCOMPLETE")

    def test_r2_zero_execution_ast_and_deepcopy(self):
        """R2 AST+行为：零网络零子进程零 skill 执行词面；resolve_fn 收到
        深拷贝 registry 零污染。"""
        banned = {"urllib", "requests", "socket", "http", "subprocess",
                  "pack_installer", "install_flow"}
        for mod in REPLAY_MODULES:
            imported = _imports_of(SCRIPTS / mod)
            self.assertFalse(imported & banned,
                             f"{mod} 导入 {imported & banned}")
            src = (SCRIPTS / mod).read_text(encoding="utf-8").lower()
            for word in ("run_skill", "execute_skill", "install("):
                self.assertNotIn(word, src, f"{mod} 出现 {word}")
        pack = make_pack(CALLS, REGISTRY, rules_version="v1")
        seen = {}

        def mutating_resolve(raw, registry):
            seen["raw"] = raw
            registry["packs"] = []   # 就地改写仅副本
            return {"skill": "weekly-report（占位）",
                    "trigger_conditions": ["写周报（占位）"],
                    "resolution": {}}

        replay(pack, UTTERANCES, REGISTRY, mutating_resolve,
               rules_version="v1")
        self.assertEqual(seen["raw"], UTTERANCES[0])
        self.assertEqual(len(REGISTRY["packs"]), 1, "调用方 registry 零污染")

    def test_r3_mismatch_returns_closed_keys_no_new_result(self):
        """R3 零静默钉值：mismatch 键面封闭——零回退新结果载荷键。"""
        pack = make_pack(CALLS, REGISTRY, rules_version="v1")
        out = replay(pack, UTTERANCES, REGISTRY,
                     lambda raw, reg: {"skill": "改写（占位）",
                                       "trigger_conditions": [],
                                       "resolution": {}},
                     rules_version="v1")
        self.assertEqual(out["verdict"], "REPLAY_MISMATCH")
        self.assertEqual(out["evidence"]["first_divergence_index"], 0)
        self.assertEqual(set(out), {"schema", "refused", "verdict",
                                    "evidence", "rerun_count"})

    def test_r4_ledger_method_surface_closed(self):
        """R4：ReplayLedger 方法面封闭——零删除方法。"""
        led = ReplayLedger()
        methods = {n for n in dir(led) if not n.startswith("_")}
        self.assertLessEqual(methods, {"record", "entries"}, methods)
        pack = make_pack(CALLS, REGISTRY, rules_version="v1")
        led.record(pack, {"verdict": "REPLAY_OK", "evidence": None},
                   at="2026-11-11T09:00:00Z")
        self.assertEqual(len(led.entries), 1)


class TestDemarcationPins(unittest.TestCase):
    def test_install_snapshot_surface_unchanged(self):
        """§2 划界钉值：install_snapshot 快照面（install-snapshot-v1 +
        FingerprintMismatch）符号不变——PRD-279 管安装可逆，本条管调用
        可重放，互不越界。"""
        import install_snapshot as inst
        self.assertEqual(INSTALL_SCHEMA, "install-snapshot-v1")
        self.assertTrue(hasattr(inst, "FingerprintMismatch"))
        self.assertFalse(hasattr(inst, "replay"),
                         "快照面不应出现重放符号")


if __name__ == "__main__":
    unittest.main()
