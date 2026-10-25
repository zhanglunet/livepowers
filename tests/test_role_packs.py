#!/usr/bin/env python3
"""PRD-172/T2：角色包发行清单机检（最小发行）。

被测对象：role-packs/（trend issue #861；分组与 schema 见
docs/plans/2026-10-25-role-skill-pack.md，PRD-172/T1）。

覆盖：
1. manifest.json 符合 T1 §4.2 schema（schema_version、packs、ungrouped、
   status / inclusion / acceptance.state 取值）；
2. 三包与根 skills/ 逐字节一致——把工程门 E-T04「插件拷贝逐字节一致」的
   机检模式扩展到 role-packs/（包内技能原样拷贝、不裁剪正文）；
3. 包构成与 T1 §3 一致：入口技能必含、销售/财务含写操作护栏、人力含
   两个 H 桶技能；writing-livepowers-skills 不进任何包；ungrouped 四技能；
4. manifest 与根 .claude-plugin/marketplace.json 一致：marketplace_entry
   的包都有条目，source / version / name 一致；
5. published 硬门禁的清单侧判定：status=published 的包，其 skills 的
   acceptance 必须全 confirmed 或有效豁免（当前三包为 draft，全部 pending，
   不得标 published——T4 #863 再接对抗验收门禁）。

夹具不涉及真实主机名 / 账号 / 密钥。Python 3.9 兼容。
"""
import json
import os
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROLE_PACKS = REPO / "role-packs"
MANIFEST = ROLE_PACKS / "manifest.json"
MARKETPLACE = REPO / ".claude-plugin" / "marketplace.json"
ROOT_SKILLS = REPO / "skills"

ENTRY_SKILL = "using-livepowers"
EXCLUDED_SKILLS = {ENTRY_SKILL, "writing-livepowers-skills"}  # T1 §2.1 口径
UNGROUPED = ["crystallize-to-system1", "agent-harness-for-tools",
             "generalizing-skills", "living-surface"]
STATUSES = ("planned", "draft", "published")
INCLUSIONS = ("required", "optional")
ACCEPTANCE_STATES = ("pending", "confirmed", "exempt", "blocked")
BUCKETS = ("G", "S", "F", "H", "entry")
PACK_COMPOSITION = {
    "livepowers-role-sales": {
        "entry": ENTRY_SKILL, "count": 10,
        "required_extra": ["oltp-action-safety", "fde-delivery",
                           "delivery-chain", "takeover-handling"],
    },
    "livepowers-role-finance": {
        "entry": ENTRY_SKILL, "count": 10,
        "required_extra": ["oltp-action-safety", "env-scan-ontology",
                           "ontology-evolution"],
    },
    "livepowers-role-hr": {
        "entry": ENTRY_SKILL, "count": 8,
        "required_extra": ["digital-role-spec", "auditable-agent-comms"],
    },
}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class TestManifestSchema(unittest.TestCase):
    def setUp(self):
        self.manifest = load_json(MANIFEST)

    def test_top_level(self):
        self.assertEqual(self.manifest.get("schema_version"), 1)
        self.assertRegex(self.manifest.get("updated", ""), r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(self.manifest.get("skill_source"), "../skills/")
        self.assertTrue((ROLE_PACKS / self.manifest["skill_source"]).resolve().is_dir())
        self.assertIsInstance(self.manifest.get("packs"), list)
        self.assertEqual(len(self.manifest["packs"]), 3)
        self.assertEqual(self.manifest.get("ungrouped"), UNGROUPED)

    def test_pack_fields(self):
        for pack in self.manifest["packs"]:
            with self.subTest(pack=pack.get("pack_id")):
                self.assertIn(pack.get("pack_id"), PACK_COMPOSITION)
                self.assertIn(pack.get("status"), STATUSES)
                self.assertEqual(pack.get("entry_skill"), ENTRY_SKILL)
                self.assertIsInstance(pack.get("skills"), list)
                self.assertIn("marketplace_entry", pack)

    def test_skill_entries(self):
        seen = set()
        for pack in self.manifest["packs"]:
            names = []
            for s in pack["skills"]:
                with self.subTest(pack=pack["pack_id"], skill=s.get("name")):
                    self.assertIn(s["name"], {d.name for d in ROOT_SKILLS.iterdir() if d.is_dir()},
                                  "manifest 引用了不存在的 skill")
                    self.assertIn(s["bucket"], BUCKETS)
                    self.assertIn(s["inclusion"], INCLUSIONS)
                    acc = s["acceptance"]
                    self.assertIn(acc["state"], ACCEPTANCE_STATES)
                    if acc["state"] == "exempt":
                        self.assertTrue(acc.get("exempt_ref"),
                                        "exempt 状态必须带 exempt_ref（EX- ID）")
                    else:
                        self.assertIsNone(acc.get("exempt_ref"))
                    ev = acc.get("evidence")
                    if acc["state"] != "pending":
                        self.assertTrue(ev, "非 pending 状态必须给 evidence 路径")
                    names.append(s["name"])
                    seen.add(s["name"])
            self.assertEqual(len(set(names)), len(names),
                             "%s 包内 skill 重复" % pack["pack_id"])

    def test_excluded_skills_never_packed(self):
        for pack in self.manifest["packs"]:
            names = {s["name"] for s in pack["skills"]}
            self.assertNotIn("writing-livepowers-skills", names,
                             "作者元技能不进任何角色包（T1 §2.1）")

    def test_ungrouped_skills_not_in_packs(self):
        for pack in self.manifest["packs"]:
            names = {s["name"] for s in pack["skills"]}
            self.assertEqual(names & set(UNGROUPED), set(),
                             "U 桶技能不应进角色包")


class TestPackComposition(unittest.TestCase):
    """包构成与 T1 §3 的三包构成表一致。"""

    def setUp(self):
        self.manifest = load_json(MANIFEST)

    def test_counts_and_required(self):
        for pack in self.manifest["packs"]:
            spec = PACK_COMPOSITION[pack["pack_id"]]
            names = {s["name"] for s in pack["skills"]}
            with self.subTest(pack=pack["pack_id"]):
                self.assertEqual(len(names), spec["count"],
                                 "%s 应含 %d 个 skill" % (pack["pack_id"], spec["count"]))
                self.assertIn(spec["entry"], names)
                for req in spec["required_extra"]:
                    self.assertIn(req, names, "%s 缺必含技能 %s" % (pack["pack_id"], req))
                inc = {s["name"]: s["inclusion"] for s in pack["skills"]}
                self.assertEqual(inc[spec["entry"]], "required")

    def test_safety_and_hr_buckets(self):
        by_pack = {p["pack_id"]: {s["name"] for s in p["skills"]}
                   for p in self.manifest["packs"]}
        # 写操作护栏：涉写角色包（销售 CRM / 财务凭证）必含
        self.assertIn("oltp-action-safety", by_pack["livepowers-role-sales"])
        self.assertIn("oltp-action-safety", by_pack["livepowers-role-finance"])
        # 红线护栏（acceptance-gates）三包全含；人力包含两个 H 桶技能
        for pack_id in by_pack:
            self.assertIn("acceptance-gates", by_pack[pack_id])
        self.assertIn("digital-role-spec", by_pack["livepowers-role-hr"])
        self.assertIn("auditable-agent-comms", by_pack["livepowers-role-hr"])

    def test_grouped_skills_reach_at_least_one_pack(self):
        """T1 §3 分组表 19 个（除 writing-livepowers-skills 外的根 skill 减 U 桶）
        至少进一个包；未进包的 grouped 技能（nightly-crystallization-review，
        财务·选含本期未选）须在 PR 说明留痕，不在此硬卡。"""
        packed = {s["name"] for p in self.manifest["packs"] for s in p["skills"]}
        root = {d.name for d in ROOT_SKILLS.iterdir() if d.is_dir()}
        accounted = packed | set(UNGROUPED) | EXCLUDED_SKILLS | {"nightly-crystallization-review"}
        self.assertEqual(root - accounted, set(),
                         "这些 skill 既未进包也未进 ungrouped/排除口径：%s" % (root - accounted))


class TestPackCopies(unittest.TestCase):
    """E-T04 机检模式扩展到 role-packs/：包内技能与根 skills/ 逐字节一致。"""

    def test_pack_skill_copies_byte_identical(self):
        mismatched, missing = [], []
        copies = sorted(pf for d in ROLE_PACKS.glob("*/skills/*")
                        for pf in d.rglob("*") if pf.is_file())
        self.assertGreater(len(copies), 0, "role-packs/*/skills/ 下没有拷贝文件")
        for pf in copies:
            # pf = role-packs/<pack>/skills/<skill>/<file...>
            parts = pf.relative_to(ROLE_PACKS).parts
            rel = Path(*parts[2:])
            root_f = ROOT_SKILLS / rel
            if not root_f.is_file():
                missing.append(str(pf))
            elif pf.read_bytes() != root_f.read_bytes():
                mismatched.append(str(pf))
        self.assertEqual(missing, [], "包内拷贝在根 skills/ 找不到对应文件：%s" % missing)
        self.assertEqual(mismatched, [], "包内拷贝与根 skills/ 漂移：%s" % mismatched)

    def test_manifest_skills_match_pack_dirs(self):
        manifest = load_json(MANIFEST)
        for pack in manifest["packs"]:
            pdir = ROLE_PACKS / pack["pack_id"]
            with self.subTest(pack=pack["pack_id"]):
                self.assertTrue(pdir.is_dir(), "缺包目录：%s" % pdir)
                actual = {d.name for d in (pdir / "skills").iterdir() if d.is_dir()}
                listed = {s["name"] for s in pack["skills"]}
                self.assertEqual(actual, listed,
                                 "%s 目录与 manifest 不一致：目录多 %s，manifest 多 %s"
                                 % (pack["pack_id"], sorted(actual - listed),
                                    sorted(listed - actual)))

    def test_pack_plugin_json(self):
        for pack in load_json(MANIFEST)["packs"]:
            pdir = ROLE_PACKS / pack["pack_id"]
            with self.subTest(pack=pack["pack_id"]):
                meta = load_json(pdir / ".claude-plugin" / "plugin.json")
                self.assertEqual(meta.get("name"), pack["pack_id"])
                self.assertEqual(meta.get("version"), pack["version"])
                self.assertEqual(meta.get("license"), "MIT")
                readme = pdir / "README.md"
                self.assertTrue(readme.is_file(), "缺包 README")
                text = readme.read_text(encoding="utf-8")
                for s in pack["skills"]:
                    self.assertIn("`%s`" % s["name"], text,
                                  "包 README 技能表缺 %s" % s["name"])
                self.assertIn("pending", text, "README 应含验收状态列")


class TestMarketplaceConsistency(unittest.TestCase):
    """marketplace_entry 的包必须在根 marketplace.json 有同构条目（清单是输入、市场清单是产物）。"""

    def test_packs_in_marketplace(self):
        entries = {e["name"]: e for e in load_json(MARKETPLACE)["plugins"]}
        for pack in load_json(MANIFEST)["packs"]:
            with self.subTest(pack=pack["pack_id"]):
                if not pack.get("marketplace_entry"):
                    continue
                self.assertIn(pack["pack_id"], entries,
                              "manifest 声明 marketplace_entry 但市场清单缺条目")
                entry = entries[pack["pack_id"]]
                self.assertEqual(entry["source"], "./role-packs/" + pack["pack_id"])
                self.assertEqual(entry["version"], pack["version"])
                self.assertTrue((REPO / entry["source"]).is_dir())

    def test_marketplace_role_pack_sources_declared(self):
        manifest_packs = {p["pack_id"] for p in load_json(MANIFEST)["packs"]}
        for entry in load_json(MARKETPLACE)["plugins"]:
            if entry["source"].startswith("./role-packs/"):
                self.assertIn(entry["name"], manifest_packs,
                              "市场清单里的角色包不在发行清单中（清单是输入，市场是产物）")


class TestPublishedGate(unittest.TestCase):
    """T1 §4.2 硬门禁（清单侧）：published 的包必须全 confirmed 或有效豁免。
    完整对抗验收门禁（联动 findings.json）由 T4（trend #863）接入。"""

    def test_draft_packs_not_marked_published(self):
        for pack in load_json(MANIFEST)["packs"]:
            with self.subTest(pack=pack["pack_id"]):
                if pack["status"] == "published":
                    unconfirmed = [s["name"] for s in pack["skills"]
                                   if s["acceptance"]["state"] not in ("confirmed", "exempt")]
                    self.assertEqual(unconfirmed, [],
                                     "存在 rejected/pending 的 skill 时包不得标 published")
                else:
                    self.assertIn(pack["status"], ("planned", "draft"))
                    states = {s["acceptance"]["state"] for s in pack["skills"]}
                    self.assertEqual(states, {"pending"},
                                     "T2 初值：三包验收状态全部 pending")


if __name__ == "__main__":
    unittest.main()
