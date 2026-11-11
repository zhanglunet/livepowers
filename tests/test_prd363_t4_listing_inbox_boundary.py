# -*- coding: utf-8 -*-
"""PRD-363/T4 测试（trend #1642 的 T4 环节）：上架收件箱划界断言。

运行：uv run --with pytest python -m pytest tests/test_prd363_t4_listing_inbox_boundary.py -q
（仓库根执行）

覆盖（T1 §0/§2，验收「划界断言通过」）：
  ① 模块隔离双向：listing_inbox/listing_inbox_gates 零导入 genui_gate
    （PRD-335 渲染判定——被消费零 import）/market_gate_scan+market_whitelist
    （安检线——进池先扫继续）/pack_installer+install_flow（上架动作走
    既有发布流程）+ 借鉴词零出现（plannotator/t3code 只借控制面形态）；
    genui_gate 零导入 listing_inbox*（仅代码标识符扫描，docstring 提及
    不算）；
  ② 零网络零子进程零上架词面 AST（R1）；
  ③ R1 零自动执行 AST+行为：approve 携带 closed 词表动作载荷
    （publish/install）→ INBOX_AUTO_EXEC_ATTEMPT 显形拒绝；裁决返回值
    零上架/skillpack 变更载荷键；
  ④ R2 只读汇聚行为钉值：collect 注入式三源齐收（security_reviews/
    dropped_reviews/edge_cases 词表封闭），零内核调用面；
  ⑤ R3 每项带证据钉值：安检项缺 report_ref/reason 任一 →
    INBOX_ITEM_INCOMPLETE 显形拒绝入箱；
  ⑥ R4：InboxLedger 方法面封闭（零删除方法）+reject 留痕钉值；
  ⑦ §2 划界钉值：genui_gate 面（tree_gate 判定）符号不变——渲染判定
    归 335、收件箱零自动，互不越界。
零网络；全合成占位。
"""
import ast
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from listing_inbox import (  # noqa: E402
    InboxError,
    InboxLedger,
    ITEM_KINDS,
    collect,
)

NOW = "2026-11-11T09:00:00Z"
SECURITY = [{"source_ref": "security-scan#plugin-7（占位）",
             "report_ref": "scan-report sha16:…（占位）",
             "diff_digest": "sha16:…（占位）",
             "reason": "依赖混淆疑似（占位）"}]
EDGE = [{"source_ref": "market#case-3（占位）",
         "report_ref": "review sha16:…（占位）", "reason": "边界案例（占位）"}]

INBOX_MODULES = ["listing_inbox.py", "listing_inbox_gates.py"]


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
    def test_inbox_never_imports_gate_market_or_installer(self):
        """收件箱面零触碰渲染判定/安检扫描/安装器（只读消费=注入式；安检
        线继续进池先扫；上架走既有发布流程）。"""
        for mod in INBOX_MODULES:
            imported = _imports_of(SCRIPTS / mod)
            for banned in ("genui_gate", "market_gate_scan",
                           "market_whitelist", "pack_installer",
                           "install_flow", "skill_ref_resolver"):
                self.assertNotIn(banned, imported, f"{mod} 导入 {banned}")
            names = _code_names(SCRIPTS / mod)
            for symbol in ("tree_gate", "scan_plugin"):
                self.assertNotIn(symbol, names, f"{mod} 引用 {symbol}")

    def test_genui_gate_never_imports_inbox(self):
        """渲染判定面零导入收件箱（PRD-335 不感知本条——双向隔离）。"""
        imported = _imports_of(SCRIPTS / "genui_gate.py")
        for mod in ("listing_inbox", "listing_inbox_gates"):
            self.assertNotIn(mod, imported)

    def test_no_plannotator_t3code_symbols(self):
        """借鉴仓（plannotator Apache-2.0/t3code MIT 实测）零符号——只借
        控制面形态。"""
        for mod in INBOX_MODULES:
            blob = ast.dump(ast.parse(
                (SCRIPTS / mod).read_text("utf-8"))).lower()
            for word in ("plannotator", "t3code"):
                self.assertNotIn(word, blob, f"{mod} 出现 {word}")


class TestRedLinePins(unittest.TestCase):
    def test_r1_zero_listing_ast_and_payload_rejected(self):
        """R1 AST+行为：收件箱两模块零网络零子进程；上架词面零出现；
        approve 携带 closed 词表载荷（publish/install）→
        INBOX_AUTO_EXEC_ATTEMPT 显形拒绝；裁决返回值零上架/skillpack
        变更载荷键。"""
        banned = {"urllib", "requests", "socket", "http", "subprocess"}
        for mod in INBOX_MODULES:
            imported = _imports_of(SCRIPTS / mod)
            self.assertFalse(imported & banned,
                             f"{mod} 导入 {imported & banned}")
            names = {n.lower() for n in _code_names(SCRIPTS / mod)}
            for word in ("install_pack", "publish_pack", "mutate_skillpack"):
                self.assertNotIn(word, names, f"{mod} 出现 {word}")
        items = collect(security_reviews=SECURITY, edge_cases=EDGE, at=NOW)
        led = InboxLedger()
        led.add(items)
        iid = items[0]["item_id"]
        with self.assertRaisesRegex(InboxError, "INBOX_AUTO_EXEC_ATTEMPT"):
            led.approve(iid, by="reviewer（占位）", at=NOW,
                        payload={"install": True})
        out = led.approve(iid, by="reviewer（占位）", at=NOW)
        for key in ("installed", "published", "skillpack_changed"):
            self.assertNotIn(key, out)

    def test_r2_collect_injected_three_sources(self):
        """R2 只读汇聚行为钉值：collect 注入式三源齐收（词表封闭），零
        内核调用面。"""
        items = collect(security_reviews=SECURITY, edge_cases=EDGE, at=NOW)
        self.assertEqual([it["kind"] for it in items],
                         ["security_manual_review", "market_edge_case"])
        self.assertEqual(set(ITEM_KINDS),
                         {"security_manual_review", "dropped_props_review",
                          "market_edge_case"})

    def test_r3_incomplete_item_refused_pinned(self):
        """R3 行为钉值：安检项缺 report_ref/reason 任一 →
        INBOX_ITEM_INCOMPLETE 显形拒绝入箱。"""
        with self.assertRaisesRegex(InboxError, "INBOX_ITEM_INCOMPLETE"):
            collect(security_reviews=[{"source_ref": "s（占位）"}], at=NOW)

    def test_r4_ledger_surface_closed_and_reject_trace(self):
        """R4：InboxLedger 方法面封闭（零删除方法）+reject 留痕钉值。"""
        led = InboxLedger()
        methods = {n for n in dir(led) if not n.startswith("_")}
        self.assertLessEqual(methods, {"add", "approve", "reject", "view",
                                       "events"}, methods)
        items = collect(security_reviews=SECURITY, at=NOW)
        led.add(items)
        iid = items[0]["item_id"]
        out = led.reject(iid, by="reviewer（占位）", at=NOW,
                         reason="不收（占位）")
        self.assertEqual(out["reject_reason"], "不收（占位）")
        self.assertEqual(len(led.events), 2)   # add + rejected（只增）


class TestDemarcationPins(unittest.TestCase):
    def test_genui_gate_surface_unchanged(self):
        """§2 划界钉值：genui_gate 面（tree_gate 判定）符号不变——渲染
        判定归 335、收件箱零自动，互不越界。"""
        import genui_gate as gg
        self.assertTrue(callable(gg.tree_gate))
        self.assertFalse(hasattr(gg, "collect_inbox"),
                         "渲染判定面不应出现收件箱符号")


if __name__ == "__main__":
    unittest.main()
