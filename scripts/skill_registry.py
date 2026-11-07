#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-227/T3（trend #1137）：总登记册实现——检索 / 触发词 / 验收例。

按 T1 规范《skill-pack-layering-spec》v1.0.0（docs/plans/2026-10-26-skill-pack-layering-spec.md）
§4/§5/§6 实现，消费 T2（scripts/subpack_registry.py）的 SKILL_SUBPACKS 分包映射：

  - build_registry(skills_root)：skills/ 目录 → 规范合规总登记册——
    包条目 5 必填（name/positioning/version/spec_version/skills）+ skill 条目
    2 必填（name/triggers）；skill 条目 name 与 SKILL.md frontmatter 严格一致
    （§4.4），triggers 取 frontmatter description 原文（§4.4 一致性，不另编）；
    examples（验收例）从 SKILL.md metadata.output 机械派生（「产出满足 metadata.output：
    <原文>」，不虚构）；每 skill 附 x-path/x-subpack/x-one_line（T2 口径沿用）。
  - validate_registry(registry)：§4.2 必填、§5.1 包名 <库前缀>-<领域词>、§5.2 skill 名
    kebab-case 全库唯一、§6.3 semver、§6.4 spec_version 与 alignment 声明一致、
    §4.3 未知非 x- 字段拒绝、包名/定位唯一。
  - search(registry, query)：触发词检索（trigger/positioning/one_line/name 大小写
    不敏感子串，OR 语义，命中按包名+skill 名排序）——「可检索」验收。
  - render_md(registry)：由权威源生成人读总表 REGISTRY.md（双载体同源，禁止手改）。

登记册权威源为仓库根 registry.json（§4.1 可发现位置）；测试机判「重新生成 ==
落盘文件」防漂移（§7）。版本政策：全库 lockstep 0.1.0（§6.3 允许的本地政策）。
零网络；只读。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from subpack_registry import SKILL_SUBPACKS, SubpackError

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
REGISTRY_PATH = REPO_ROOT / "registry.json"
REGISTRY_MD_PATH = REPO_ROOT / "REGISTRY.md"

#: 规范版本（§6.4 引用与对齐声明；T1 草案 v1.0.0）
SPEC_NAME = "skill-pack-layering-spec"
SPEC_VERSION = "1.0.0"
#: 包版本（全库 lockstep，§6.3 本地政策）
PACK_VERSION = "0.1.0"
#: 包名前缀（§5.1 <库前缀>-<领域词>）
LIBRARY_PREFIX = "livepowers"
#: 四领域 sub-pack 的一句话定位（包级 positioning；T2 one_line 是 skill 级）
PACK_POSITIONING = {
    "delivery": "交付域：端到端交付链、FDE 实施路径与可持续演进的活页面交付面",
    "governance": "治理与安全域：验收门、写操作安全边界、人机接管与可审计通信",
    "methodology": "方法论域：技能写作规范、结晶泛化与本体锚定的规格与演化",
    "ops": "运行域：环境扫描、循证探索、夜巡规划复盘与结果台账",
}
PACK_REQUIRED_FIELDS = ("name", "positioning", "version", "spec_version", "skills")
SKILL_REQUIRED_FIELDS = ("name", "triggers")
SPEC_OPTIONAL_FIELDS = ("description", "keywords", "stage", "roles", "depends_on",
                        "status", "license", "homepage", "examples")
RE_PACK_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)+$")
RE_SKILL_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RE_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _frontmatter(text: str) -> dict[str, str]:
    """极简 frontmatter 顶层平面字段（name/description），不引 yaml 依赖。"""
    fields: dict[str, str] = {}
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return fields
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if ":" in stripped and stripped and not line.startswith((" ", "\t")):
            key, _, value = stripped.partition(":")
            fields.setdefault(key.strip(), value.strip())
    return fields


def _metadata_output(text: str) -> str | None:
    """SKILL.md metadata.output 原文（验收例派生源，不虚构）。"""
    match = re.search(r"^\s+output:\s*(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def build_registry(skills_root: str | Path = SKILLS_ROOT) -> dict:
    """skills/ 目录 → 规范合规总登记册（§4）。分包定位缺失/未登记 skill 报错。"""
    root = Path(skills_root)
    found = sorted(d.name for d in root.iterdir() if d.is_dir() and (d / "SKILL.md").exists())
    errors: list[str] = []
    for name in found:
        if name not in SKILL_SUBPACKS:
            errors.append(f"{name}: 未登记分包（T2 SKILL_SUBPACKS）")
    missing = [n for n in SKILL_SUBPACKS if n not in found]
    if missing:
        errors.append(f"分包映射引用不存在的 skill: {missing}")
    if errors:
        raise SubpackError("; ".join(errors))

    packs: dict[str, list[dict]] = {}
    for name in found:
        subpack, one_line = SKILL_SUBPACKS[name]
        skill_md = (root / name / "SKILL.md").read_text(encoding="utf-8")
        fm = _frontmatter(skill_md)
        if fm.get("name") != name:
            raise SubpackError(f"{name}: frontmatter name={fm.get('name')!r} 与目录名不一致（§4.4）")
        description = fm.get("description", "")
        if not description:
            raise SubpackError(f"{name}: SKILL.md 缺 description（triggers 来源，§4.4）")
        skill_entry: dict = {
            "name": name,
            "triggers": description,  # 一句话触发描述（§4.2 允许数组或一句话）
            "x-path": f"skills/{name}",
            "x-subpack": subpack,
            "x-one_line": one_line,
        }
        output = _metadata_output(skill_md)
        if output:
            skill_entry["examples"] = [
                f"按 skills/{name}/SKILL.md 执行，产出满足 metadata.output：{output}"
            ]
        packs.setdefault(subpack, []).append(skill_entry)

    registry: dict = {
        "schema": "skill-pack-registry/v1",
        "alignment": f"{SPEC_NAME}@{SPEC_VERSION}",
        "alignment_note": (
            f"技能包分层规范：{SPEC_NAME}@{SPEC_VERSION}"
            "（docs/plans/2026-10-26-skill-pack-layering-spec.md，评审通过后定版）。"
            "本登记册为包归属与检索的单一事实源（规范 §7）；人读 REGISTRY.md 由本文件生成。"
        ),
        "borrowed_form": (
            "「分层 + 总登记册」组织形态借鉴 AgriciDaniel/claude-seo（MIT License，"
            "Copyright (c) Daniel Agrici，https://github.com/AgriciDaniel/claude-seo）："
            "只复用形态，未复用其代码与文本。"
        ),
        "version_policy": f"全库 lockstep {PACK_VERSION}（规范 §6.3 允许的本地政策；"
                          "包内 skill 增删或定位变更至少升 MINOR）",
        "packs": [],
    }
    for subpack in sorted(packs):
        registry["packs"].append({
            "name": f"{LIBRARY_PREFIX}-{subpack}",
            "positioning": PACK_POSITIONING[subpack],
            "version": PACK_VERSION,
            "spec_version": SPEC_VERSION,
            "skills": packs[subpack],
        })
    return registry


def validate_registry(registry: dict) -> list[str]:
    """规范合规校验（§4/§5/§6），返回错误清单（空 = 通过）。"""
    errors: list[str] = []
    if registry.get("alignment") != f"{SPEC_NAME}@{SPEC_VERSION}":
        errors.append(f"alignment 必须为 {SPEC_NAME}@{SPEC_VERSION}（§6.4 未写明版本视为未对齐）")
    packs = registry.get("packs")
    if not isinstance(packs, list) or not packs:
        errors.append("packs 必须为非空数组（§4.1 登记册由包条目数组构成）")
        return errors
    pack_names: set[str] = set()
    skill_names: set[str] = set()
    for pack in packs:
        label = f"包 {pack.get('name', '?')}"
        for field in PACK_REQUIRED_FIELDS:
            if field not in pack:
                errors.append(f"{label} 缺必填字段 {field}（§4.2）")
        name = pack.get("name")
        if not isinstance(name, str) or not RE_PACK_NAME.match(name or ""):
            errors.append(f"{label} 包名必须为 <库前缀>-<领域词>（§5.1）")
        elif name in pack_names:
            errors.append(f"包名重复: {name}（§4.2 全库唯一）")
        pack_names.add(name or "")
        if not (isinstance(pack.get("positioning"), str) and pack["positioning"].strip()):
            errors.append(f"{label} positioning 必须为一句话定位（§4.2）")
        if not RE_SEMVER.match(str(pack.get("version", ""))):
            errors.append(f"{label} version 必须为 semver（§6.3）")
        if pack.get("spec_version") != SPEC_VERSION:
            errors.append(f"{label} spec_version 必须为 {SPEC_VERSION}（§6.4）")
        allowed_pack = set(PACK_REQUIRED_FIELDS) | set(SPEC_OPTIONAL_FIELDS)
        for key in pack:
            if key not in allowed_pack and not key.startswith("x-"):
                errors.append(f"{label} 含未声明的非 x- 字段: {key}（§4.3）")
        skills = pack.get("skills")
        if not isinstance(skills, list) or not skills:
            errors.append(f"{label} skills 必须为非空数组（§4.2）")
            continue
        for skill in skills:
            slabel = f"技能 {skill.get('name', '?')}"
            for field in SKILL_REQUIRED_FIELDS:
                if field not in skill:
                    errors.append(f"{slabel}（{label}）缺必填字段 {field}（§4.2）")
            sname = skill.get("name")
            if not isinstance(sname, str) or not RE_SKILL_NAME.match(sname or ""):
                errors.append(f"{slabel} 名必须为全小写 kebab-case（§5.2）")
            elif sname in skill_names:
                errors.append(f"技能名重复: {sname}（§5.2 全库唯一，不靠包名消歧）")
            skill_names.add(sname or "")
            triggers = skill.get("triggers")
            ok_triggers = (
                (isinstance(triggers, str) and triggers.strip())
                or (isinstance(triggers, list) and triggers
                    and all(isinstance(t, str) and t.strip() for t in triggers))
            )
            if not ok_triggers:
                errors.append(f"{slabel} triggers 必须为非空数组或一句话（§4.2）")
            allowed_skill = set(SKILL_REQUIRED_FIELDS) | set(SPEC_OPTIONAL_FIELDS)
            for key in skill:
                if key not in allowed_skill and not key.startswith("x-"):
                    errors.append(f"{slabel} 含未声明的非 x- 字段: {key}（§4.3）")
            examples = skill.get("examples")
            if examples is not None and not (
                isinstance(examples, list) and all(isinstance(e, str) and e.strip() for e in examples)
            ):
                errors.append(f"{slabel} examples 必须为非空字符串数组（验收例）")
    return errors


def load_registry(path: str | Path = REGISTRY_PATH) -> dict:
    """加载登记册并校验；不合规抛 SubpackError（载入即校验）。"""
    registry = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = validate_registry(registry)
    if errors:
        raise SubpackError("; ".join(errors))
    return registry


def search(registry: dict, query: str, min_len: int = 2) -> list[dict]:
    """触发词检索（§4.2 triggers 为检索依据）：大小写不敏感子串，OR 语义。

    检索域：triggers / 包与技能 positioning / x-one_line / name。
    返回 [{pack, name, one_line, triggers}]，按 (pack, name) 排序。
    """
    terms = [t for t in re.split(r"[\s/／,，、]+", (query or "").strip()) if t]
    if not terms or min(len(t) for t in terms) < min_len:
        raise SubpackError(f"检索词至少 {min_len} 个字符")
    hits = []
    for pack in registry.get("packs", []):
        for skill in pack.get("skills", []):
            haystack = " ".join([
                pack.get("positioning", ""),
                skill.get("x-one_line", ""),
                str(skill.get("triggers", "")),
                skill.get("name", ""),
            ]).lower()
            if any(term.lower() in haystack for term in terms):
                hits.append({
                    "pack": pack["name"],
                    "name": skill["name"],
                    "one_line": skill.get("x-one_line", ""),
                    "triggers": skill.get("triggers", ""),
                })
    return sorted(hits, key=lambda h: (h["pack"], h["name"]))


def render_md(registry: dict) -> str:
    """由权威源生成人读总表（REGISTRY.md 由此产出，禁止手改，双载体同源 §7）。"""
    lines: list[str] = []
    total = sum(len(p.get("skills", [])) for p in registry.get("packs", []))
    lines.append("# livepowers 技能包分层总登记册（REGISTRY）")
    lines.append("")
    lines.append(f"> PRD-227/T3（trend #1137）落地。机读权威源：[`registry.json`](registry.json)"
                 f"（{len(registry.get('packs', []))} 包 / {total} 技能）；本文件由其生成——"
                 "生成命令 `python3 scripts/skill_registry.py --render > REGISTRY.md`，"
                 "**禁止手改本文件**，两载体不一致即漂移（规范 §7，测试机判）。")
    lines.append(">")
    lines.append(f"> {registry.get('alignment_note', '')}")
    lines.append(">")
    lines.append(f"> {registry.get('borrowed_form', '')}")
    lines.append("")
    lines.append("检索：`python3 scripts/skill_registry.py <触发词…>`（例：`交付`、`验收`、"
                 "`本体`、`夜巡`）。")
    lines.append("")
    for pack in registry.get("packs", []):
        lines.append(f"## {pack['name']} — {pack['positioning']}")
        lines.append("")
        lines.append(f"version {pack['version']} ｜ spec_version {pack['spec_version']}")
        lines.append("")
        lines.append("| skill | 触发词（frontmatter description 原文） | 验收例 |")
        lines.append("|---|---|---|")
        for skill in pack.get("skills", []):
            examples = "；".join(skill.get("examples", [])) or "—（SKILL.md 无 metadata.output，待补）"
            lines.append(f"| **{skill['name']}** | {skill.get('triggers', '')} | {examples} |")
        lines.append("")
    lines.append(f"版本政策：{registry.get('version_policy', '')}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    import sys
    if "--render" in argv:
        registry = load_registry()
        print(render_md(registry), end="")
        return 0
    if "--check" in argv:
        registry = load_registry()
        errors = validate_registry(registry)
        print("registry OK" if not errors else "; ".join(errors))
        return 0 if not errors else 1
    query = " ".join(argv)
    registry = load_registry()
    if not query:
        packs = registry.get("packs", [])
        print(f"用法: python3 scripts/skill_registry.py <检索词…>（如: 交付 验收 本体）")
        print(f"条目统计: {len(packs)} 包 / "
              f"{sum(len(p.get('skills', [])) for p in packs)} 技能")
        return 0
    try:
        hits = search(registry, query)
    except SubpackError as exc:
        print(f"检索失败: {exc}")
        return 2
    for hit in hits:
        print(f"[{hit['pack']}] {hit['name']}")
        print(f"  定位: {hit['one_line']}")
        print(f"  触发: {hit['triggers']}")
    print(f"命中 {len(hits)} 条")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
