#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-199/T2（trend #996）：skills frontmatter 对齐 Agent Skills 开放规范——批量增强 + 校验。

T1 差距清单（docs/plans/2026-10-26-agentskills-gap-list.md）四项缺口，本脚本补齐三项：
  license（skill 级 MIT 声明，21/21 缺失）
  metadata.when_not_to_use（适用边界/否定触发，21/21 部分对齐 → 补否定句）
  compatibility（环境要求声明，21/21 缺失）
  metadata.output（输出物声明，20/21 缺失——T1 记 1 条已部分对齐）
不改动 name/description（T1 判已对齐）；不改 allowed-tools（工具声明属 T3 审计）。

本脚本只做「按 gap 清单逐 skill 增强后的规范校验器」+「逐条增强写入」两件事，
frontmatter 增强内容本体由 T4 白名单维护在 AGENTSKILLS_FILL 表内（逐 skill 显式、
不做自动生成——输出物与边界是内容判断，不是机械变换）。

MIT 许可；示例全虚构。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SKILLS_ROOT = Path(__file__).resolve().parents[1] / "skills"
REQUIRED_BY_SPEC = ("name", "description", "license", "metadata")
METADATA_KEYS = ("when_not_to_use", "output", "compatibility")
SKILL_LEVEL_LICENSE = "MIT"

# 逐 skill 显式增强表（T4 白名单维护；输出物与边界为内容判断，逐条人工拟定）
AGENTSKILLS_FILL: dict[str, dict[str, str]] = {
    "using-livepowers": {"when_not_to_use": "纯前端静态页面、与业务软件无关的创作类任务不适用", "output": "路由决策：指向最适合当前任务的能力包", "compatibility": "需 Bash 与 Read 工具"},
    "acceptance-gates": {"when_not_to_use": "非交付类任务（纯探索、纯阅读）不适用", "output": "验收门清单与逐门判定记录", "compatibility": "需 Bash 与 Read 工具"},
    "agent-harness-for-tools": {"when_not_to_use": "不涉及工具包装的纯文档任务不适用", "output": "工具 harness 配置与包装说明", "compatibility": "需 Bash（Python 子进程）"},
    "auditable-agent-comms": {"when_not_to_use": "无外部 agent 通信的场景不适用", "output": "可审计通信记录格式", "compatibility": "需 Bash 与 Read 工具"},
    "crystallize-to-system1": {"when_not_to_use": "首次探索（尚未成功重复）的意图不适用", "output": "System 1 能力包草稿", "compatibility": "需 Bash 与 Read 工具"},
    "delivery-chain": {"when_not_to_use": "非交付链路的分析任务不适用", "output": "交付链路核对记录", "compatibility": "需 Bash 与 Read 工具"},
    "digital-role-spec": {"when_not_to_use": "非角色定义类任务不适用", "output": "数字角色规格文档", "compatibility": "需 Read 工具"},
    "env-scan-ontology": {"when_not_to_use": "非环境扫描类任务不适用", "output": "环境扫描本体对照表", "compatibility": "需 Bash 与 Read 工具"},
    "explore-with-evidence": {"when_not_to_use": "已有充分证据的结论复核不适用", "output": "带证据引用的探索记录", "compatibility": "需 Bash 与 Read 工具"},
    "fde-delivery": {"when_not_to_use": "非客户现场交付类任务不适用", "output": "现场交付（FDE）执行记录", "compatibility": "需 Bash 与 Read 工具"},
    "generalizing-skills": {"when_not_to_use": "只为单一项目硬编码的一次性任务不适用", "output": "跨项目通用化改造说明", "compatibility": "需 Bash 与 Read 工具"},
    "living-surface": {"when_not_to_use": "无固化诉求的次抛分析不适用", "output": "活页面固化方案", "compatibility": "需 Bash 与 Read 工具"},
    "night-loop-planning": {"when_not_to_use": "短平快任务不适用", "output": "夜间/长程任务计划", "compatibility": "需 Bash、Write 与 Task 工具"},
    "nightly-crystallization-review": {"when_not_to_use": "非收工/夜间回顾场景不适用", "output": "固化候选与晨报", "compatibility": "需 Bash 与 Read 工具"},
    "oltp-action-safety": {"when_not_to_use": "只读分析任务不适用", "output": "OLTP 写操作安全检查清单", "compatibility": "需 Bash 与 Read 工具"},
    "ontology-evolution": {"when_not_to_use": "本体定义已满足需求的任务不适用", "output": "本体演进条目", "compatibility": "需 Bash、Read 与 Write 工具"},
    "outcome-ledger": {"when_not_to_use": "非业务结果衡量场景不适用", "output": "业务结果台账与价值论证", "compatibility": "需 Bash 与 Read 工具"},
    "system1-first": {"when_not_to_use": "需从零推理的全新任务不适用", "output": "System 1 现成固化能力检索", "compatibility": "需 Bash 与 Read 工具"},
    "takeover-handling": {"when_not_to_use": "无止损/接管场景不适用", "output": "异常接管操作记录", "compatibility": "需 Bash 与 Read 工具"},
    "writing-livepowers-skills": {"when_not_to_use": "非 skill 编写任务不适用", "output": "skill 编写规范与骨架", "compatibility": "需 Read 工具"},
    "ontology-grounded-spec": {"when_not_to_use": "非本体对齐的规格任务不适用", "output": "本体对齐规格（含输出物章节）", "compatibility": "需 Bash 与 Read 工具"},
}


def parse_frontmatter(skill_md: Path) -> tuple[dict[str, Any], str, str]:
    """解析 SKILL.md frontmatter（简易 YAML 子集：顶层标量+列表）。"""
    raw = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", raw, re.S)
    if not m:
        return {}, "", raw
    meta: dict[str, Any] = {}
    current_key = None
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        if line.startswith("- ") and current_key:
            meta[current_key] = meta.get(current_key, [])
            if isinstance(meta[current_key], list):
                meta[current_key].append(line[2:].strip())
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if val == "[]":
            meta[key] = []
        elif val:
            meta[key] = val
        else:
            meta[key] = []
        current_key = key
    return meta, m.group(1), raw


def gaps_for(skill_name: str, meta: dict[str, Any]) -> list[str]:
    """返回该 skill 相对规范的缺口（对齐 T1 差距清单四项）。"""
    gaps = []
    if not meta.get("license"):
        gaps.append("license")
    if not meta.get("when_not_to_use"):
        gaps.append("metadata.when_not_to_use")
    if not meta.get("output"):
        gaps.append("metadata.output")
    if not meta.get("compatibility"):
        gaps.append("metadata.compatibility")
    return gaps


def align_skill(skill_md: Path) -> dict[str, Any]:
    """确定性对齐：完全重建 frontmatter（name/description 原值 + license + metadata 块），幂等。"""
    name = skill_md.parent.name
    fill = AGENTSKILLS_FILL.get(name)
    if fill is None:
        raise ValueError(f"AGENTSKILLS_FILL 缺 {name} 条目（逐 skill 显式，不做自动生成）")
    raw = skill_md.read_text(encoding="utf-8")
    meta, _, body = parse_frontmatter(skill_md)
    while body.startswith("---\n"):
        body = body[4:]  # 前次坏写入可能残留多个 frontmatter 关闭线
    gaps_before = gaps_for(name, meta)

    description = meta.get("description") or ""
    allowed_tools = meta.get("allowed-tools")
    md_meta = meta.get("metadata") if isinstance(meta.get("metadata"), dict) else {}

    new_lines = [
        "---",
        f"name: {meta.get('name') or name}",
        f"description: {description}",
    ]
    if allowed_tools:
        new_lines.append(f"allowed-tools: {allowed_tools}")
    new_lines.append("license: " + (meta.get("license") or SKILL_LEVEL_LICENSE))
    if fill.get("when_not_to_use") and not md_meta.get("when_not_to_use"):
        new_lines.append("metadata:")
        new_lines.append(f"  when_not_to_use: {fill['when_not_to_use']}")
    if fill.get("output") and not md_meta.get("output"):
        new_lines.append("  output: " + fill["output"])
    if fill.get("compatibility") and not md_meta.get("compatibility"):
        new_lines.append("  compatibility: " + fill["compatibility"])
    if md_meta.get("when_not_to_use"):
        new_lines.append("metadata:")
        new_lines.append(f"  when_not_to_use: {md_meta['when_not_to_use']}")
    new_lines.append("---")
    out_text = "\n".join(new_lines) + "\n" + body

    # 幂等自检：重建后不得出现第二个 metadata 块
    if out_text.count("metadata:") > 1:
        raise ValueError("幂等检查失败：frontmatter 出现多个 metadata 块")
    skill_md.write_text(out_text, encoding="utf-8")
    return {"skill": name, "gaps_before": gaps_before,
             "changes": ["license", "metadata.when_not_to_use", "metadata.output",
                          "metadata.compatibility"]}


def validate_all(skills_root: Path = SKILLS_ROOT) -> list[str]:
    """规范校验器：全部 SKILL.md 四项缺口清零（T3 发布门挂接点）。"""
    errors = []
    for skill_md in sorted(skills_root.glob("*/SKILL.md")):
        meta, _, _ = parse_frontmatter(skill_md)
        rel = str(skill_md.relative_to(skills_root))
        for gap in gaps_for(meta.get("name") or rel, meta):
            errors.append(f"{rel}: {gap}")
    return errors


def main(argv: list[str]) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="agentskills frontmatter 对齐")
    parser.add_argument("cmd", choices=["align", "validate"])
    parser.add_argument("--skills-root", default=str(SKILLS_ROOT))
    args = parser.parse_args(argv)
    root = Path(args.skills_root)
    if args.cmd == "validate":
        errors = validate_all(root)
        for e in errors:
            print(f"GAP: {e}")
        print(f"{len(errors)} gaps" if errors else "all aligned")
        return 1 if errors else 0
    reports = [align_skill(p) for p in sorted(root.glob("*/SKILL.md"))]
    for r in reports:
        print(json.dumps(r, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))
