# -*- coding: utf-8 -*-
"""PRD-293/T4 测试（trend #1469）：禁止全文复制/不静默内联断言。

运行：python3 -m unittest tests.test_prd293_t4_zero_copy -v（仓库根执行）

覆盖（T1 设计 §7，验收「划界断言通过」）：
  ① 产物字段白名单（AST+行为）：Resolution 键集合固定（raw/skill/
    trigger_conditions/output_contract/resolution）——无 body/examples 之外
    通道（examples 是产出契约的机械派生，属白名单内）；② 零正文子串：
    构造含正文字段的合成登记册条目，产物 blob 零正文字面；③ 不静默内联：
    组装器只接受契约产物（类型级——注入拒绝形态即拒）；④ 与 PRD-227/199
    划界（登记册条目结构零改动——引用解析并入零扰动）。
零网络；全合成占位。
"""
import ast
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from skill_ref_resolver import resolve  # noqa: E402
from skill_load_gate import load_with_references  # noqa: E402

#: 合成登记册条目带"正文字段"（body_markdown 模拟被引用方 SKILL.md 全文）
REGISTRY_WITH_BODY = {
    "packs": [{
        "name": "livepowers-fixture",
        "skills": [
            {"name": "dep-skill（占位）",
             "triggers": "Use when 依赖步骤（占位）。",
             "examples": ["产出：依赖记录（占位）"],
             "body_markdown": "被引用方 SKILL.md 全文正文（占位）——绝不允许出现在引用产物里",
             "steps": ["第 1 步（占位）", "第 2 步（占位）"]},
        ],
    }],
}
RESOLUTION_KEYS = {"schema", "raw", "skill", "trigger_conditions",
                   "output_contract", "resolution"}


class 产物白名单Tests(unittest.TestCase):
    def test_resolution_keys_fixed(self):
        """Resolution 键集合固定（AST+行为双层）：无正文通道。"""
        tree = ast.parse((REPO / "scripts" / "skill_ref_resolver.py")
                         .read_text(encoding="utf-8"))
        blob = ast.dump(tree)
        for symbol in ("body_markdown", "steps", "full_text", "inline_body"):
            self.assertNotIn(symbol, blob, f"解析器含正文通道 {symbol}")
        out = resolve("@dep-skill（占位）", REGISTRY_WITH_BODY)
        self.assertTrue(set(out) <= RESOLUTION_KEYS,
                        set(out) - RESOLUTION_KEYS)

    def test_zero_body_substring_in_product(self):
        """零正文子串：候选集条目带正文字段，产物 blob 仍零正文字面（R1）。"""
        out = resolve("@dep-skill（占位）", REGISTRY_WITH_BODY)
        blob = str(out)
        self.assertNotIn("SKILL.md 全文正文", blob)
        self.assertNotIn("第 1 步", blob)
        self.assertNotIn("第 2 步", blob)

    def test_load_gate_product_zero_body(self):
        """装载闸产物（契约包）同样零正文子串（T3 装载面复核）。"""
        out = load_with_references("dep-skill（占位）", REGISTRY_WITH_BODY)
        self.assertTrue(out["usable"])
        blob = str(out["contracts"])
        self.assertNotIn("SKILL.md 全文正文", blob)
        self.assertNotIn("第 1 步", blob)


class 不静默内联Tests(unittest.TestCase):
    def test_refusal_shape_rejected_by_assembler(self):
        """组装器类型级：注入拒绝形态（缺契约字段）即 TypeError——零内联。"""
        def assemble(contract: dict) -> str:
            for key in ("trigger_conditions", "output_contract"):
                if not contract.get(key):      # 缺键或 None（Refusal 形态）都拒
                    raise TypeError(f"组装器只接受契约产物，{key} 缺失或为 None")
            return "assembled（占位）"

        refusal = resolve("@不存在（占位）", REGISTRY_WITH_BODY)
        with self.assertRaises(TypeError):
            assemble(refusal)                                  # Refusal 无契约字段
        resolved = resolve("@dep-skill（占位）", REGISTRY_WITH_BODY)
        self.assertEqual(assemble(resolved), "assembled（占位）")


class PRD227划界Tests(unittest.TestCase):
    def test_registry_entry_structure_unchanged(self):
        """登记册条目结构零改动：resolve 不增删候选集条目键（引用解析并入零扰动）。"""
        import copy
        before = copy.deepcopy(REGISTRY_WITH_BODY)
        resolve("@dep-skill（占位）", REGISTRY_WITH_BODY)
        self.assertEqual(REGISTRY_WITH_BODY, before)


if __name__ == "__main__":
    unittest.main()
