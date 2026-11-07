# -*- coding: utf-8 -*-
"""PRD-227/T5 测试：验收试运行 + 规范外发（trend #1139）。

运行：python3 -m unittest tests.test_prd227_t5_replay -v（仓库根执行）
或：python3 -m unittest discover -s tests -p "test_prd227_t5_replay.py" -v

验收标准（trend #1139）：**试运行通过，规范文档已发布且带版本号**。

试运行（真实登记册 registry.json 4 包 21 技能 + pack_installer 全链）：
  1. 按包安装 livepowers-delivery → install-manifest 计数/动作可复核；
  2. 重装幂等（同包重装零 diff 全 unchanged）；
  3. 双包安装后卸载其一 → 只删成员目录，非成员文件不碰；
  4. 依赖门（合成 fixture 登记册走真实代码路径）：缺失依赖拒装列清单（§3.3），
     被依赖方先卸 → §3.4 提示；
  5. 前置：validate_registry 全绿。
规范外发：spec 文档 v1.0.0 已发布（外发状态行 + §8 变更记录 + §9 外发适配
列 PRD-220/233/239/243 适配要点）。
零网络；tmp 沙盘；fixture 全合成占位。
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from pack_installer import InstallError, install_packs, uninstall_packs  # noqa: E402
from skill_registry import load_registry, validate_registry  # noqa: E402

SPEC = REPO / "docs" / "plans" / "2026-10-26-skill-pack-layering-spec.md"


def _fixture_source(tmp: Path) -> Path:
    """合成 fixture 登记册：pack-a(base) ← pack-b(depends_on base-skill)。"""
    src = tmp / "fixture-src"
    (src / "skills" / "base-skill").mkdir(parents=True)
    (src / "skills" / "base-skill" / "SKILL.md").write_text(
        "---\nname: base-skill\ndescription: 基础技能（占位）\n---\n\n正文（占位）\n",
        encoding="utf-8")
    (src / "skills" / "dep-skill").mkdir(parents=True)
    (src / "skills" / "dep-skill" / "SKILL.md").write_text(
        "---\nname: dep-skill\ndescription: 依赖基础技能（占位）\n---\n\n正文（占位）\n",
        encoding="utf-8")
    registry = {
        "schema_version": "1.0",
        "spec_version": "1.0.0",
        "library": "livepowers-fixture",
        "version": "0.1.0",
        "alignment": "skill-pack-layering-spec@1.0.0",
        "packs": [
            {"name": "livepowers-pack-a",
             "positioning": "基础能力包（占位一句话定位）", "description": "基础包（占位）",
             "version": "0.1.0",
             "spec_version": "1.0.0",
             "skills": [{"name": "base-skill", "x-path": "skills/base-skill",
                         "description": "基础技能（占位）",
                         "triggers": ["用基础技能（占位）"]}]},
            {"name": "livepowers-pack-b",
             "positioning": "依赖基础包的进阶包（占位一句话定位）", "description": "依赖包（占位）",
             "version": "0.1.0",
             "spec_version": "1.0.0",
             "skills": [{"name": "dep-skill", "x-path": "skills/dep-skill",
                         "description": "依赖基础技能（占位）",
                         "triggers": ["用进阶技能（占位）"],
                         "depends_on": ["base-skill"]}]},
        ],
    }
    (src / "registry.json").write_text(json.dumps(registry, ensure_ascii=False),
                                       encoding="utf-8")
    return src


class 试运行Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="lp227-t5-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.registry = load_registry(REPO / "registry.json")

    def test_registry_validate_green_prerequisite(self):
        """前置：真实登记册 validate_registry 零错误（试运行基线合规）。"""
        self.assertEqual(validate_registry(self.registry), [])

    def test_trial_install_delivery_pack(self):
        """① 按包安装 delivery：3 技能落位，清单计数/动作可复核。"""
        target = self.tmp / "ws-a"
        manifest = install_packs(REPO, target, ["delivery"])
        self.assertEqual(manifest["packs"], ["livepowers-delivery"])
        actions = {s["action"] for s in manifest["installed"]}
        self.assertEqual(actions, {"copied"})
        self.assertEqual(manifest["total_skills"], 3)
        self.assertEqual(len(manifest["installed"]), 3)
        for skill in manifest["installed"]:
            self.assertTrue((target / Path(skill["path"]).relative_to(target)
                             / "SKILL.md").is_file(), skill["path"])

    def test_trial_reinstall_idempotent(self):
        """② 重装幂等：同包重装零 diff（全 unchanged）。"""
        target = self.tmp / "ws-b"
        install_packs(REPO, target, ["delivery"])
        again = install_packs(REPO, target, ["delivery"])
        self.assertEqual({s["action"] for s in again["installed"]}, {"unchanged"})
        self.assertEqual(again["total_skills"], 3)

    def test_trial_uninstall_keeps_non_members(self):
        """③ 卸载只删成员：另一包成员与非成员文件原样保留。"""
        target = self.tmp / "ws-c"
        install_packs(REPO, target, ["delivery", "governance"])
        sentinel = target / "skills" / "delivery-chain" / "sentinel.txt"
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_text("非成员哨兵（占位）", encoding="utf-8")
        result = uninstall_packs(target, self.registry, ["delivery"])
        self.assertEqual(len(result["removed"]), 3)
        gov_paths = [s["x-path"] for p in self.registry["packs"]
                     if p["name"] == "livepowers-governance" for s in p["skills"]]
        for rel in gov_paths:
            self.assertTrue((target / rel).is_dir(), rel)
        self.assertFalse((target / "skills" / "delivery-chain").exists())

    def test_dependency_gate_and_uninstall_hint(self):
        """④ 依赖门与卸载提示（fixture 登记册走真实代码路径）：
        缺失依赖拒装列清单（§3.3）；先卸被依赖方 → §3.4 提示。"""
        src = _fixture_source(self.tmp)
        target = self.tmp / "ws-d"
        with self.assertRaises(InstallError) as ctx:
            install_packs(src, target, ["pack-b"])
        self.assertIn("依赖缺失", str(ctx.exception))
        self.assertIn("base-skill", str(ctx.exception))
        install_packs(src, target, ["pack-a", "pack-b"])
        fixture_registry = load_registry(src / "registry.json")
        result = uninstall_packs(target, fixture_registry, ["pack-a"])
        self.assertTrue(any("仍被依赖" in w for w in result["warnings"]))


class 规范外发Tests(unittest.TestCase):
    def test_spec_published_with_version(self):
        """⑤ 规范文档已发布且带版本号：外发状态行 + 变更记录 + 适配仓清单。"""
        content = SPEC.read_text(encoding="utf-8")
        self.assertIn("skill-pack-layering-spec", content)
        self.assertIn("v1.0.0", content)
        self.assertIn("已发布", content)                 # 状态：草案 → 已发布
        self.assertIn("v1.0.0（外发）", content)         # §8 变更记录
        for prd in ("PRD-220", "PRD-233", "PRD-239", "PRD-243"):
            self.assertIn(prd, content)                  # §9 外发适配四仓
        self.assertIn("spec_version", content)


if __name__ == "__main__":
    unittest.main()
