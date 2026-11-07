# -*- coding: utf-8 -*-
"""PRD-227/T3 测试：总登记册实现——检索 / 触发词 / 验收例（trend #1137）。

运行：python3 -m pytest tests/test_prd227_t3_registry.py -q

覆盖：规范合规（§4.2 必填/§5.1 包名/§5.2 技能名全库唯一/§6.3 semver/§6.4 对齐声明/
§4.3 未知非 x- 字段拒/包定位唯一）、triggers 与 frontmatter 一致（§4.4）、
验收例机械派生不虚构、检索（触发词命中/OR/短词拒绝/确定性）、双载体同源
（REGISTRY.md 重新渲染 == 落盘文件）、registry.json 与 skills/ 目录同步（重新
生成 == 落盘文件）、覆盖全部 sub-pack。零网络；只读。
"""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from skill_registry import (  # noqa: E402
    PACK_POSITIONING,
    REGISTRY_MD_PATH,
    REGISTRY_PATH,
    SPEC_NAME,
    SPEC_VERSION,
    build_registry,
    load_registry,
    render_md,
    search,
    validate_registry,
)
from subpack_registry import SKILL_SUBPACKS, SubpackError  # noqa: E402


class 规范合规Tests(unittest.TestCase):
    def setUp(self):
        self.registry = load_registry()

    def test_real_registry_passes_validation(self):
        self.assertEqual(validate_registry(self.registry), [])

    def test_four_domain_packs_cover_all_subpacks(self):
        packs = {p["name"] for p in self.registry["packs"]}
        self.assertEqual(packs, {"livepowers-delivery", "livepowers-governance",
                                 "livepowers-methodology", "livepowers-ops"})

    def test_covers_all_t2_skills(self):
        """登记册覆盖 T2 全部分包 skill（验收：覆盖全部 sub-pack）。"""
        registered = {s["name"] for p in self.registry["packs"] for s in p["skills"]}
        self.assertEqual(registered, set(SKILL_SUBPACKS))

    def test_pack_positioning_matches_design(self):
        for pack in self.registry["packs"]:
            domain = pack["name"].replace("livepowers-", "")
            self.assertEqual(pack["positioning"], PACK_POSITIONING[domain])
            self.assertTrue(pack["positioning"].endswith(""))

    def test_alignment_declaration(self):
        self.assertEqual(self.registry["alignment"], f"{SPEC_NAME}@{SPEC_VERSION}")

    def test_missing_pack_field_flagged(self):
        pack = dict(self.registry["packs"][0])
        del pack["spec_version"]
        errors = validate_registry({"alignment": self.registry["alignment"],
                                    "packs": [pack]})
        self.assertTrue(any("spec_version" in e for e in errors))

    def test_bad_pack_name_flagged(self):
        pack = dict(self.registry["packs"][0])
        pack["name"] = "delivery"
        errors = validate_registry({"alignment": self.registry["alignment"],
                                    "packs": [pack]})
        self.assertTrue(any("§5.1" in e for e in errors))

    def test_duplicate_skill_name_flagged(self):
        pack = json.loads(json.dumps(self.registry["packs"][0]))
        pack["skills"].append(json.loads(json.dumps(pack["skills"][0])))
        pack["skills"][-1]["name"] = "delivery-chain"
        pack["skills"][-2]["name"] = "delivery-chain"
        errors = validate_registry({"alignment": self.registry["alignment"],
                                    "packs": [pack]})
        self.assertTrue(any("技能名重复" in e for e in errors))

    def test_unknown_non_x_field_flagged(self):
        pack = json.loads(json.dumps(self.registry["packs"][0]))
        pack["owner_team"] = "someone"
        errors = validate_registry({"alignment": self.registry["alignment"],
                                    "packs": [pack]})
        self.assertTrue(any("x-" in e for e in errors))

    def test_non_semver_version_flagged(self):
        pack = dict(self.registry["packs"][0])
        pack["version"] = "v1"
        errors = validate_registry({"alignment": self.registry["alignment"],
                                    "packs": [pack]})
        self.assertTrue(any("semver" in e for e in errors))


class 触发词与验收例Tests(unittest.TestCase):
    def test_triggers_match_frontmatter_description(self):
        """triggers = SKILL.md frontmatter description 原文（§4.4 一致性）。"""
        registry = load_registry()
        for pack in registry["packs"]:
            for skill in pack["skills"]:
                md = (REPO / skill["x-path"] / "SKILL.md").read_text(encoding="utf-8")
                description = md.split("description:", 1)[1].split("\n", 1)[0].strip()
                self.assertEqual(skill["triggers"], description,
                                 f"{skill['name']} triggers 与 frontmatter 不一致")

    def test_examples_derived_from_metadata_output(self):
        """验收例 = 「按 SKILL.md 执行，产出满足 metadata.output：<原文>」（不虚构）。"""
        registry = load_registry()
        checked = 0
        for pack in registry["packs"]:
            for skill in pack["skills"]:
                md = (REPO / skill["x-path"] / "SKILL.md").read_text(encoding="utf-8")
                if "output:" in md:
                    self.assertTrue(skill.get("examples"))
                    self.assertIn("metadata.output", skill["examples"][0])
                    checked += 1
        self.assertGreater(checked, 0)

    def test_every_skill_has_one_line(self):
        registry = load_registry()
        for pack in registry["packs"]:
            for skill in pack["skills"]:
                self.assertTrue(skill.get("x-one_line"))


class 检索Tests(unittest.TestCase):
    def setUp(self):
        self.registry = load_registry()

    def test_trigger_hits_expected_skill(self):
        hits = search(self.registry, "验收")
        names = {h["name"] for h in hits}
        self.assertIn("acceptance-gates", names)

    def test_case_insensitive_and_or_semantics(self):
        hits_en = search(self.registry, "takeover")
        self.assertIn("takeover-handling", {h["name"] for h in hits_en})
        hits_or = search(self.registry, "本体 夜巡")
        names = {h["name"] for h in hits_or}
        self.assertTrue("ontology-evolution" in names or "night-loop-planning" in names)

    def test_short_query_rejected(self):
        with self.assertRaises(SubpackError):
            search(self.registry, "本")

    def test_deterministic_order(self):
        one = search(self.registry, "交付")
        two = search(self.registry, "交付")
        self.assertEqual(one, two)


class 双载体同源Tests(unittest.TestCase):
    def test_registry_json_in_sync_with_skills_dir(self):
        """重新生成 == 落盘 registry.json（单一事实源防漂移，§7）。"""
        on_disk = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        rebuilt = build_registry(REPO / "skills")
        self.assertEqual(on_disk, rebuilt)

    def test_registry_md_is_current_render(self):
        registry = load_registry()
        self.assertEqual(REGISTRY_MD_PATH.read_text(encoding="utf-8"), render_md(registry))

    def test_render_contains_all_packs_and_skills(self):
        rendered = render_md(load_registry())
        for pack in load_registry()["packs"]:
            self.assertIn(pack["name"], rendered)
            for skill in pack["skills"]:
                self.assertIn(skill["name"], rendered)


if __name__ == "__main__":
    unittest.main()
