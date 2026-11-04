# -*- coding: utf-8 -*-
"""PRD-293/T2 测试（trend #1467）：skill 间 @引用解析最小实现。

运行：python3 -m unittest tests.test_prd293_t2_skill_ref -v（仓库根执行）

覆盖（T1 设计 §3/§4/§5/§6，验收「样例可解析到触发条件与输出契约，不复制
全文，解析不到报错，有测试」）：parse 单形态与禁止形态（节锚/版本后缀/
双写）；resolve 精确匹配→触发条件+输出契约（登记册形态=零正文读取的
结构保证）、NOT_FOUND fail-closed、SELF_LOOP、CYCLE 环检测、
REGISTRY_CORRUPT；二值返回；RefAudit 双侧留痕+依赖图重建。
零网络；全合成占位。
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from skill_ref_resolver import (  # noqa: E402
    ERROR_CODES,
    RefAudit,
    RefSyntaxError,
    parse,
    resolve,
)

REGISTRY = {
    "packs": [{
        "name": "livepowers-fixture",
        "skills": [
            {"name": "base-skill（占位）",
             "triggers": "Use when 基础流程需要执行（占位）。",
             "examples": ["产出：基础流程核对记录（占位）"],
             "x-references": ["@dep-skill（占位）"]},
            {"name": "dep-skill（占位）",
             "triggers": "Use when 依赖步骤需要执行（占位）。",
             "examples": ["产出：依赖步骤记录（占位）"]},
            {"name": "leaf-skill（占位）",
             "triggers": "Use when 叶子步骤需要执行（占位）。",
             "examples": ["产出：叶子记录（占位）"]},
        ],
    }],
}


class TestParse(unittest.TestCase):
    def test_simple_name(self):
        self.assertEqual(parse("@base-skill（占位）"), "base-skill（占位）")

    def test_prohibited_forms(self):
        for bad in ("@base-skill（占位）#正文", "@base（占位） v2",
                    "@@双写", "@base（占位） extra", "base-skill"):
            with self.assertRaises(RefSyntaxError):
                parse(bad)

    def test_error_codes_closed(self):
        self.assertEqual(set(ERROR_CODES),
                         {"REF_SYNTAX_ERROR", "REF_NOT_FOUND", "REF_SELF_LOOP",
                          "REF_CYCLE", "REF_REGISTRY_CORRUPT"})


class TestResolve(unittest.TestCase):
    def test_resolves_to_trigger_and_contract_zero_body(self):
        out = resolve("@dep-skill（占位）", REGISTRY, from_skill="base-skill（占位）")
        self.assertEqual(out["resolution"]["status"], "resolved")
        self.assertEqual(out["skill"], "dep-skill（占位）")
        self.assertEqual(out["trigger_conditions"],
                         "Use when 依赖步骤需要执行（占位）。")
        self.assertEqual(out["output_contract"], ["产出：依赖步骤记录（占位）"])
        blob = str(out)
        self.assertNotIn("正文", blob)                    # 零正文通道

    def test_not_found_fail_closed(self):
        out = resolve("@不存在（占位）", REGISTRY, from_skill="leaf-skill（占位）")
        self.assertEqual(out["resolution"]["error_code"], "REF_NOT_FOUND")
        self.assertIn("fail-closed", out["resolution"]["detail"])

    def test_self_loop(self):
        out = resolve("@base-skill（占位）", REGISTRY,
                      from_skill="base-skill（占位）")
        self.assertEqual(out["resolution"]["error_code"], "REF_SELF_LOOP")

    def test_cycle_detection(self):
        # 环：base→dep（既有 x-references）+ dep→base（拟新增）= 环
        out = resolve("@base-skill（占位）", REGISTRY,
                      from_skill="dep-skill（占位）")
        self.assertEqual(out["resolution"]["error_code"], "REF_CYCLE")
        self.assertIn("dep-skill（占位）", out["resolution"]["detail"])

    def test_registry_corrupt_on_duplicate(self):
        dup = {"packs": [{"skills": REGISTRY["packs"][0]["skills"] +
                          [{"name": "dep-skill（占位）", "triggers": "x（占位）",
                            "examples": []}]}]}
        out = resolve("@dep-skill（占位）", dup, from_skill="leaf-skill（占位）")
        self.assertEqual(out["resolution"]["error_code"], "REF_REGISTRY_CORRUPT")

    def test_binary_return(self):
        for raw in ("@dep-skill（占位）", "@不存在（占位）"):
            out = resolve(raw, REGISTRY, from_skill="leaf-skill（占位）")
            self.assertIn(out["resolution"]["status"], ("resolved", "refused"))


class TestRefAudit(unittest.TestCase):
    def test_logged_both_sides_and_graph(self):
        audit = RefAudit()
        audit.resolve_logged("@dep-skill（占位）", REGISTRY, at="2026-11-04T09:00:00Z",
                             from_skill="base-skill（占位）")
        audit.resolve_logged("@不存在（占位）", REGISTRY, at="2026-11-04T09:01:00Z",
                             from_skill="base-skill（占位）")
        graph = audit.dependency_graph()
        self.assertEqual(graph, {"base-skill（占位）": ["dep-skill（占位）"]})
        self.assertEqual(audit.records[1]["error_code"], "REF_NOT_FOUND")

    def test_append_only(self):
        audit = RefAudit()
        audit.resolve_logged("@dep-skill（占位）", REGISTRY, at="2026-11-04T09:00:00Z",
                             from_skill="base-skill（占位）")
        before = list(audit.records)
        audit.resolve_logged("@不存在（占位）", REGISTRY, at="2026-11-04T09:01:00Z")
        self.assertEqual(audit.records[:len(before)], before)


if __name__ == "__main__":
    unittest.main()
