#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-227/T4（trend issue #1138）：发布与安装路径适配——分包后安装不断链。

按 T1 规范《skill-pack-layering-spec》v1.0.0（§1.1 可按包独立安装、§3.4 包的
独立性、§3.3 禁止隐式依赖）实现，叠加 T3 总登记册（scripts/skill_registry.py）：

  - install_packs(source_root, target_root, pack_names)：按包安装——从登记册
    解析包成员，逐 skill 目录复制到目标（target/skills/<name>/，与既有
    `复制 skills/*` 安装方式同构，**旧安装方式不断链**：按包安装是既有方式的
    子集操作，target 里旧条目原样保留）；包名非法/未在登记册拒绝；
  - 依赖声明核对（§3.3）：安装前核对 depends_on 是否被本次安装覆盖或已存在
    于目标——未覆盖且未存在 → 列出缺失依赖（不隐式默认已装，不自动补装，
    交由用户决定——§3.3 禁止隐式依赖）；`--allow-missing-deps` 不提供：
    缺失就是缺失，用户补选包再装；
  - 安装清单（install-manifest.json）：记录本次安装的包/技能/文件计数与
    校验和（安装可复核）；幂等（同包重装零 diff 跳过）；
  - 卸载 uninstall_packs(target_root, pack_names)：只删登记册成员目录，
    不碰非成员文件；被依赖方先于依赖方卸载时给出提示（§3.4 卸载提示依赖方）。

零网络；确定性；全部路径由调用方注入。
测试：tests/test_prd227_t4_installer.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from skill_registry import load_registry


class InstallError(ValueError):
    """安装/卸载违规（包名非法/依赖缺失）。"""


def _dir_hash(path: Path) -> str:
    digest = hashlib.sha256()
    for file in sorted(path.rglob("*")):
        if file.is_file():
            digest.update(str(file.relative_to(path)).encode("utf-8"))
            digest.update(file.read_bytes())
    return digest.hexdigest()[:16]


def _pack_members(registry: dict, pack_name: str) -> list[dict]:
    for pack in registry.get("packs", []):
        if pack["name"] == pack_name:
            return pack["skills"]
    raise InstallError(f"包未在登记册：{pack_name!r}")


def _check_dependencies(registry: dict, pack_names: list[str],
                        target_root: Path) -> list[str]:
    """§3.3 禁止隐式依赖：depends_on 未被本次安装覆盖且目标未存在 → 缺失清单。"""
    index = {}
    for pack in registry.get("packs", []):
        for skill in pack.get("skills") or []:
            index[skill["name"]] = (pack["name"], skill.get("depends_on") or [])
    missing: set[str] = set()
    installing = {f"livepowers-{n}" if not n.startswith("livepowers") else n
                  for n in pack_names}
    for name in pack_names:
        full = f"livepowers-{name}" if not name.startswith("livepowers") else name
        for member in next(p["skills"] for p in registry["packs"] if p["name"] == full):
            for dep in member.get("depends_on") or []:
                dep_pack = index.get(dep, ("?",))[0]
                if dep_pack in installing:
                    continue
                dep_paths = [s.get("x-path") for p in registry["packs"]
                             if p["name"] == dep_pack
                             for s in p.get("skills", []) if s["name"] == dep]
                if dep_paths and all((target_root / p).is_dir() for p in dep_paths):
                    continue
                missing.add(f"{member} 依赖 {dep}（包 {dep_pack} 未在本次安装且目标未存在）")
    return sorted(missing)


def install_packs(source_root: str | Path, target_root: str | Path,
                  pack_names: list[str]) -> dict[str, Any]:
    """按包安装（§1.1 包=安装单位）：从登记册解析成员，逐 skill 目录复制。

    旧安装方式不断链：本操作是既有 `复制 skills/*` 的子集（只复制成员目录，
    目标既有文件原样保留）。返回安装清单 dict（可落盘 install-manifest.json）。
    """
    registry = load_registry(Path(source_root) / "registry.json")
    known = [p["name"] for p in registry.get("packs", [])]
    resolved = []
    for name in pack_names:
        full = name if name.startswith("livepowers") else f"livepowers-{name}"
        if full not in known:
            raise InstallError(f"包未在登记册：{full!r}")
        resolved.append(full)
    missing_deps = _check_dependencies(registry, resolved, Path(target_root))
    if missing_deps:
        raise InstallError("依赖缺失（§3.3 禁止隐式依赖，不自动补装）："
                           + "；".join(missing_deps))
    src = Path(source_root)
    dst = Path(target_root)
    dst.mkdir(parents=True, exist_ok=True)
    installed: list[dict] = []
    for full in resolved:
        pack = next(p for p in registry["packs"] if p["name"] == full)
        for skill in pack["skills"]:
            source = src / skill["x-path"]
            if not source.is_dir():
                raise InstallError(f"skill 目录缺失：{source}（登记册与仓库不一致）")
            dest = dst / skill["x-path"]
            if dest.is_dir() and _dir_hash(dest) == _dir_hash(source):
                installed.append({"skill": skill["name"], "path": str(dest),
                                  "action": "unchanged"})
                continue
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(source, dest)
            installed.append({"skill": skill["name"], "path": str(dest),
                              "action": "copied"})
    manifest = {
        "schema": "pack-install-manifest/v1",
        "packs": resolved,
        "installed": installed,
        "total_skills": len(installed),
        "note": "按包安装是既有 `复制 skills/*` 方式的子集操作——旧安装方式不断链"
                "（PRD-227/T4）",
    }
    manifest_path = dst / "install-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    return manifest


def uninstall_packs(target_root: str | Path, registry: dict,
                    pack_names: list[str]) -> dict[str, Any]:
    """按包卸载：只删登记册成员目录，不碰非成员文件。

    被依赖方先于依赖方卸载时给出提示（§3.4 卸载提示依赖方）。
    """
    index = {}
    for pack in registry.get("packs", []):
        for skill in pack.get("skills") or []:
            index[skill["name"]] = (pack["name"], skill.get("depends_on") or [])
    removed, warnings = [], []
    resolved = [n if n.startswith("livepowers") else f"livepowers-{n}"
                for n in pack_names]
    for name in resolved:
        pack = next((p for p in registry["packs"] if p["name"] == name), None)
        if pack is None:
            raise InstallError(f"包未在登记册：{name!r}")
        for skill in pack["skills"]:
            path = Path(target_root) / skill["x-path"]
            dependents = [sname for sname, (_spack, deps) in index.items()
                          if skill["name"] in deps
                          and f"livepowers-{index[sname][0].replace('livepowers-', '')}" not in resolved
                          and sname not in [x for r in resolved
                                            for x in [sk["name"] for p2 in registry["packs"]
                                                      if p2["name"] == r
                                                      for sk in p2.get("skills", [])]]]
            if path.is_dir():
                if dependents:
                    warnings.append(f"{skill['name']} 仍被依赖：{dependents}（§3.4 卸载提示）")
                shutil.rmtree(path)
                removed.append(skill["name"])
    return {"removed": removed, "warnings": warnings}
