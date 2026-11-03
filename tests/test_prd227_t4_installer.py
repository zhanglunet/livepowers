# -*- coding: utf-8 -*-
"""PRD-227/T4 自测（trend #1138）：发布与安装路径适配——分包后安装不断链。

运行：uv run --no-project --with pytest python -m pytest tests/test_prd227_t4_installer.py -q

覆盖（T1 规范 §1.1/§3.3/§3.4）：按包安装（三类各一例安装后文件落位）、
旧安装方式不断链（目标既有文件原样保留=子集操作）、依赖缺失拒绝（不自动
补装）、幂等（重装 unchanged）、卸载只删成员+被依赖方提示、安装清单可落盘、
确定性。零网络；路径全部临时目录注入。
"""
import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from pack_installer import (  # noqa: E402
    InstallError,
    install_packs,
    uninstall_packs,
)
from skill_registry import build_registry, load_registry  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
PACKS = ["delivery", "governance", "methodology", "ops"]


def _source():
    return REPO


class TestInstall:
    def test_three_packs_install_to_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = install_packs(_source(), tmp, PACKS)
            assert manifest["schema"] == "pack-install-manifest/v1"
            assert manifest["total_skills"] == 21
            assert all(Path(i["path"]).is_dir() for i in manifest["installed"])

    def test_old_install_way_unaffected(self):
        """旧安装方式不断链：按包安装后目标里既有文件原样保留（子集操作）。"""
        with tempfile.TemporaryDirectory() as tmp:
            keep = Path(tmp) / "skills" / "my-own-skill"
            keep.mkdir(parents=True)
            (keep / "SKILL.md").write_text("自有内容（占位）", encoding="utf-8")
            install_packs(_source(), tmp, PACKS)
            assert (keep / "SKILL.md").read_text(encoding="utf-8") == "自有内容（占位）"

    def test_idempotent_reinstall_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            install_packs(_source(), tmp, PACKS)
            again = install_packs(_source(), tmp, PACKS)
            assert all(i["action"] == "unchanged" for i in again["installed"])

    def test_missing_dependency_rejected(self):
        """§3.3 禁止隐式依赖：depends_on 未覆盖且目标不存在 → 拒绝并列表。

        用合成源（登记册含 depends_on 声明 + 对应 skill 目录）驱动——真实
        登记册当前无跨包依赖声明（不虚构）。"""
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as tmp:
            registry = json.loads((_source() / "registry.json").read_text(encoding="utf-8"))
            dep_pack = registry["packs"][0]        # 被依赖方（不安装）
            dependent_pack = registry["packs"][1]  # 安装方（依赖被依赖方）
            dependent_pack["skills"][0]["depends_on"] = [dep_pack["skills"][0]["name"]]
            for pack in registry["packs"]:
                for skill in pack["skills"]:
                    d = Path(source) / skill["x-path"]
                    d.mkdir(parents=True, exist_ok=True)
                    (d / "SKILL.md").write_text("---\nname: x\n---\n占位", encoding="utf-8")
            (Path(source) / "registry.json").write_text(
                json.dumps(registry, ensure_ascii=False), encoding="utf-8")
            with pytest.raises(InstallError, match="依赖缺失"):
                install_packs(source, tmp, [dependent_pack["name"]])

    def test_unknown_pack_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with pytest.raises(InstallError, match="未在登记册"):
                install_packs(_source(), tmp, ["nonexistent"])

    def test_manifest_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            install_packs(_source(), tmp, ["delivery"])
            manifest = json.loads(
                (Path(tmp) / "install-manifest.json").read_text(encoding="utf-8"))
            assert manifest["packs"] == ["livepowers-delivery"]


class TestUninstall:
    def test_uninstall_removes_members_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            install_packs(_source(), tmp, PACKS)
            keep = Path(tmp) / "skills" / "my-own-skill"
            keep.mkdir(parents=True)
            registry = load_registry(_source() / "registry.json")
            result = uninstall_packs(tmp, registry, ["ops"])
            assert "night-loop-planning" in result["removed"]
            assert not (Path(tmp) / "skills" / "night-loop-planning").exists()
            assert keep.is_dir()  # 非成员文件不碰

    def test_uninstall_dependent_warns(self):
        """§3.4：卸载被依赖方时给出提示（合成 registry 声明依赖）。"""
        registry = {"schema": "x", "packs": [
            {"name": "livepowers-core", "positioning": "p", "version": "0.1.0",
             "spec_version": "1.0.0", "skills": [
                {"name": "base-skill", "triggers": ["base"], "x-path": "skills/base-skill",
                 "depends_on": ["leaf-skill"]}]},
            {"name": "livepowers-extra", "positioning": "p", "version": "0.1.0",
             "spec_version": "1.0.0", "skills": [
                {"name": "leaf-skill", "triggers": ["leaf"], "x-path": "skills/leaf-skill",
                 "depends_on": []}]},
        ]}
        with tempfile.TemporaryDirectory() as tmp:
            leaf = Path(tmp) / "skills" / "leaf-skill"
            leaf.mkdir(parents=True)
            result = uninstall_packs(tmp, registry, ["livepowers-extra"])
            assert result["removed"] == ["leaf-skill"]
            assert any("仍被依赖" in w for w in result["warnings"])
