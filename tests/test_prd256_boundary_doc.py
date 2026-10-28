# -*- coding: utf-8 -*-
"""PRD-256/T4 自测（trend #1283）：与 PRD-112 边界说明与选用指引。

运行：python3 -m unittest test_prd256_boundary_doc -v（在 tests/ 目录执行）

覆盖（issue #1283 验收标准：文档划清会话内分工 vs 专家编排）：
  boundary-vs-112.md 在位且被 README 引用
  含 112 划界小节（边界表覆盖 112/256 两侧、关键差异维度齐全）
  含选用指引（112 场景 / 256 场景 / 两者组合）
  含常见误用纠正 ≥2 例

虚构纪律：文档不含真实主机名、账号、密钥（CI 另有 TestNoIdentifyingInfo 全仓扫描）。
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "pi-subagents"
DOC = TEMPLATE / "boundary-vs-112.md"
README = TEMPLATE / "README.md"


class TestBoundaryDoc(unittest.TestCase):
    def setUp(self):
        self.assertTrue(DOC.is_file(), f"缺少边界文档: {DOC}")
        self.text = DOC.read_text(encoding="utf-8")

    def test_doc_exists_and_referenced_from_readme(self):
        """文档存在，且模板包 README 指向它（入口可发现）。"""
        self.assertIn("boundary-vs-112.md", README.read_text(encoding="utf-8"))

    def test_boundary_table_draws_112_line(self):
        """含 112 划界小节：两侧对照 + 关键差异维度（并行范围/编排主体/基础设施）。"""
        self.assertIn("PRD-112", self.text)
        self.assertIn("边界表", self.text)
        for dim in ("并行范围", "编排主体", "基础设施"):
            self.assertIn(dim, self.text, dim)
        # 划清两侧：跨会话（112）vs 单会话内（256）
        self.assertIn("跨会话", self.text)
        self.assertIn("单会话内", self.text)
        self.assertIn("orchestra.yaml", self.text)          # 112 侧实物
        self.assertIn("handoff.schema.json", self.text)     # 256 侧实物
        # 表格至少 4 行（表头 + 三个以上维度）
        table_rows = [ln for ln in self.text.splitlines() if ln.strip().startswith("|")]
        self.assertGreaterEqual(len(table_rows), 6)

    def test_selection_guide_and_misuse_corrections(self):
        """含选用指引（112/256/组合）与常见误用纠正 ≥2 例。"""
        self.assertIn("选用指引", self.text)
        self.assertIn("组合", self.text)  # 两者可组合：implement 角色可由 112 专家承担
        self.assertIn("implement", self.text)
        misuse_count = self.text.count("误用")
        self.assertGreaterEqual(misuse_count, 3)  # 两例标题 + 小节名（≥2 例纠正）
        self.assertIn("症状", self.text)
        self.assertIn("纠正", self.text)


if __name__ == "__main__":
    unittest.main()
