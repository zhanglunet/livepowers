# -*- coding: utf-8 -*-
"""PRD-377/T4 测试（trend #1881 的 T4 环节）：插件安检发现验证台划界断言。

运行：uv run --with pytest python -m pytest tests/test_prd377_t4_plugin_verify_bench_boundary.py -q
（仓库根执行）

覆盖（T1 §0/§3，验收「划界断言通过」）：
  ① 模块隔离双向：plugin_verify_bench/gates 零导入 listing_inbox（363
    收件箱——下游零感知）/market_gate_scan（扫描器——被消费零 import，
    经 recheck_fn 注入重跑）/market_whitelist/market_gate_flow/genui_gate
    （335 渲染判定）/pack_installer+install_flow（安装面）/skill_call_
    replay*（349 重放）+ 借鉴词零出现（codex/security-audit，仅代码标识符
    扫描 docstring 提及不算）；
  ② 唯一耦合钉值：plugin_verify_bench 对仓内模块唯一耦合=install_snapshot
    （dir_fingerprint 与 279 同源 import 细节钉值）；零 LLM 零网络零子进程
    零安装词面 AST（R1）；
  ③ R2 零新增发现 AST+行为：bench 零扫描词面（scan_skill/_finding 不在
    标识符面）——复算只经注入 fn；同一输入 verify_finding 两遍逐字节一致
    （确定性复现）；
  ④ R1 拦截行为钉值：UNVERIFIED 不进 verified 分组（不上收录审批）；
  ⑤ R3 八件套封闭钉值：缺件 BENCH_INCOMPLETE+verdict 词表封闭；
  ⑥ R4：PluginBenchLedger 公开方法面封闭+reverify BENCH_STALE；
  ⑦ §3 划界钉值：market_gate_scan 面（scan_skill+RULES 词表）与
    listing_inbox 面（ITEM_KINDS 词表）符号不变——扫描归扫描器、验证台
    零新增发现，互不越界。
零网络；全合成占位。
"""
import ast
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from listing_inbox import ITEM_KINDS  # noqa: E402
from market_gate_scan import scan_skill  # noqa: E402
from plugin_verify_bench import (  # noqa: E402
    BENCH_SCHEMA,
    ERROR_CODES,
    PluginBenchError,
    PluginBenchLedger,
    VERDICTS,
    verify_finding,
    verify_findings,
)

NOW = "2026-11-13T09:00:00Z"

BENCH_MODULES = ["plugin_verify_bench.py", "plugin_verify_bench_gates.py"]


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


def _finding_hit(skill_dir):
    report = scan_skill(skill_dir, declared_name="skill-a（占位）",
                        declared_version="1.0.0")
    hit = next(f for f in report["findings"] if f["rule_id"] == "M-2-02")
    return {"finding_id": "f-001", "rule_id": hit["rule_id"],
            "location": hit["location"],
            "source_ref": "market-gate-report/v1#findings[0]（占位）"}


def _imports_of(path: Path) -> set:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    return imported


def _code_names(path: Path) -> set:
    """仅代码标识符（ast.Name/Attribute）——docstring 提及不算引用。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


class TestModuleIsolation(unittest.TestCase):
    def test_bench_never_imports_inbox_scanner_gate_or_installer(self):
        """验证台面零触碰收件箱/扫描器/白名单/渲染判定/安装器/重放（扫描器
        经注入重跑零 import；收件箱是下游零感知）。"""
        for mod in BENCH_MODULES:
            imported = _imports_of(SCRIPTS / mod)
            for banned in ("listing_inbox", "market_gate_scan",
                           "market_whitelist", "market_gate_flow",
                           "genui_gate", "pack_installer", "install_flow",
                           "skill_call_replay", "skill_call_replay_gates"):
                self.assertNotIn(banned, imported, f"{mod} 导入 {banned}")
            names = _code_names(SCRIPTS / mod)
            for symbol in ("InboxLedger", "scan_skill", "tree_gate"):
                self.assertNotIn(symbol, names, f"{mod} 引用 {symbol}")

    def test_inbox_never_imports_bench(self):
        """收件箱面零导入验证台（363 不感知本条——双向隔离）。"""
        imported = _imports_of(SCRIPTS / "listing_inbox.py")
        for mod in ("plugin_verify_bench", "plugin_verify_bench_gates"):
            self.assertNotIn(mod, imported)

    def test_upstream_zero_symbols(self):
        """借鉴仓（codex-security Apache-2.0/security-audit-skill MIT 实测）
        零符号——只借控制面形态（仅代码标识符扫描）。"""
        for mod in BENCH_MODULES:
            names = {n.lower() for n in _code_names(SCRIPTS / mod)}
            for word in ("codex", "audit_skill"):
                self.assertNotIn(word, names, f"{mod} 出现 {word}")

    def test_only_coupling_is_install_snapshot(self):
        """§0 唯一耦合钉值：plugin_verify_bench 对仓内模块唯一耦合=
        install_snapshot（dir_fingerprint 与 279 同源 import 细节钉值）。"""
        imported = _imports_of(SCRIPTS / "plugin_verify_bench.py")
        internal = imported - {"__future__", "copy", "json", "pathlib",
                               "typing", "install_snapshot"}
        self.assertEqual(internal, set(), internal)
        tree = ast.parse((SCRIPTS / "plugin_verify_bench.py")
                         .read_text(encoding="utf-8"))
        from_mods = {n.module for n in ast.walk(tree)
                     if isinstance(n, ast.ImportFrom) and n.module}
        self.assertIn("install_snapshot", from_mods, from_mods)


class TestRedLinePins(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.skill_dir = _skill_dir(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_r2_no_new_finding_ast_and_deterministic(self):
        """R2 AST+行为：bench 零扫描词面（复算只经注入 fn）；同一输入
        verify_finding 两遍逐字节一致（确定性复现）。"""
        for mod in BENCH_MODULES:
            names = {n.lower() for n in _code_names(SCRIPTS / mod)}
            for word in ("scan_skill", "_finding"):
                self.assertNotIn(word, names, f"{mod} 出现 {word}")
        finding = _finding_hit(self.skill_dir)
        a = verify_finding(finding, self.skill_dir, recheck_fn, at=NOW)
        b = verify_finding(finding, self.skill_dir, recheck_fn, at=NOW)
        self.assertEqual(a, b)

    def test_r1_unverified_blocked_at_outlet(self):
        """R1 拦截钉值：UNVERIFIED 不进 verified 分组（不上收录审批）。"""
        out = verify_findings([dict(FINDING := _finding_hit(self.skill_dir),
                                    rule_id="M-9-99")], self.skill_dir,
                              recheck_fn, at=NOW)
        self.assertEqual(out["verified"], [])
        self.assertEqual(out["unverified_count"], 1)

    def test_r3_eight_piece_closed_and_vocab(self):
        """R3 钉值：账目缺件 BENCH_INCOMPLETE；verdict 词表封闭两值。"""
        led = PluginBenchLedger(None)
        with self.assertRaisesRegex(PluginBenchError, "BENCH_INCOMPLETE"):
            led.record({"schema": BENCH_SCHEMA}, at=NOW)
        self.assertEqual(set(VERDICTS), {"VERIFIED", "UNVERIFIED"})

    def test_r4_ledger_surface_closed_and_stale(self):
        """R4：PluginBenchLedger 公开方法面封闭（零删除方法）+reverify
        目录变更 BENCH_STALE 拒绝复用。"""
        led = PluginBenchLedger(None)
        methods = {n for n in dir(led) if not n.startswith("_")}
        self.assertLessEqual(methods, {"record", "entries", "latest_for",
                                       "reverify"}, methods)
        finding = _finding_hit(self.skill_dir)
        led.record(verify_finding(finding, self.skill_dir, recheck_fn,
                                  at=NOW), at=NOW)
        (self.skill_dir / "extra.md").write_text("新增（占位）",
                                                 encoding="utf-8")
        out = led.reverify("f-001", self.skill_dir, recheck_fn, at=NOW)
        self.assertEqual(out["refused"], "BENCH_STALE")


class TestDemarcationPins(unittest.TestCase):
    def test_scanner_and_inbox_surfaces_unchanged(self):
        """§3 划界钉值：market_gate_scan 面（scan_skill+RULES 词表）与
        listing_inbox 面（ITEM_KINDS 三词表）符号不变——扫描归扫描器、
        验证台零新增发现，互不越界。"""
        import market_gate_scan as mgs
        import listing_inbox as li
        self.assertTrue(callable(mgs.scan_skill))
        self.assertTrue(mgs.RULES, "扫描规则词表为空")
        self.assertEqual(set(ITEM_KINDS),
                         {"security_manual_review", "dropped_props_review",
                          "market_edge_case"})
        self.assertFalse(hasattr(mgs, "verify_finding"),
                         "扫描器面不应出现验证台符号")
        self.assertFalse(hasattr(li, "reverify"),
                         "收件箱面不应出现复验符号")


if __name__ == "__main__":
    unittest.main()
