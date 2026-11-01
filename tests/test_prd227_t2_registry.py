# -*- coding: utf-8 -*-
"""PRD-227/T2 自测（trend #1136）：分包落地——每包一句话定位齐全。

运行：uv run --with pytest python -m pytest tests/test_prd227_t2_registry.py -q

覆盖（验收「全部分包完成，每包定位齐全」）：
  真实 skills/ 目录 20 个 skill 全部登记、无遗漏无多余；
  四领域 sub-pack 覆盖；每 skill 一句话定位非空；
  登记未覆盖的 skill 名 → 报错（ok=False）；
  登记表 JSON 可序列化。
零网络。
"""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from subpack_registry import SubpackError, build_registry  # noqa: E402


class RegistryTests(unittest.TestCase):
    def test_all_real_skills_registered(self):
        registry = build_registry(REPO / "skills")
        self.assertTrue(registry["ok"], registry["errors"])
        self.assertEqual(len(registry["skills"]), 21)

    def test_four_subpacks_covered(self):
        registry = build_registry(REPO / "skills")
        packs = {s["subpack"] for s in registry["skills"].values()}
        self.assertEqual(packs, {"delivery", "governance", "methodology", "ops"})

    def test_every_skill_has_one_line(self):
        registry = build_registry(REPO / "skills")
        for name, info in registry["skills"].items():
            self.assertTrue(info["one_line"].strip(), f"{name} 缺一句话定位")

    def test_unregistered_skill_reports_error(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "ghost-skill"
            d.mkdir()
            (d / "SKILL.md").write_text("---\nname: ghost\n---\nx", encoding="utf-8")
            registry = build_registry(td)
            self.assertFalse(registry["ok"])
            self.assertTrue(any("ghost-skill" in e for e in registry["errors"]))

    def test_registry_serializable(self):
        registry = build_registry(REPO / "skills")
        text = json.dumps(registry, ensure_ascii=False)
        self.assertIn("subpack-registry/v1", text)


if __name__ == "__main__":
    unittest.main()
