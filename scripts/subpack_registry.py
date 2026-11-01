#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-227/T2（trend #1136）：19+ skills 分包落地——按领域拆 sub-pack + 每包一句话定位。

按 T1 设计（口径以 PRD-199/227 分层登记册为准）实现：
  SKILL_SUBPACKS：20 个 skill → 四领域 sub-pack（delivery 交付 / governance 治理与
    安全 / methodology 方法论 / ops 运行与巡检），每包一句话定位；
  build_registry(skills_root)：扫 skills/ 目录 → 总登记册（机读 JSON：每 skill 的
    sub-pack / one_line / skill 数对账）；分包定位缺失即报错（验收「每包定位齐全」）。
只读；零网络。

测试：tests/test_prd227_t2_registry.py
"""
from __future__ import annotations
import json
from pathlib import Path

SKILL_SUBPACKS = {
    "delivery-chain": ("delivery", "交付链：从需求到验收的交付过程纪律"),
    "fde-delivery": ("delivery", "FDE 交付：面向交付工程师的实施路径"),
    "living-surface": ("delivery", "活页面：产出可持续演进的交付面"),
    "acceptance-gates": ("governance", "验收门：交付前的可判定门禁"),
    "oltp-action-safety": ("governance", "OLTP 动作安全：写操作的安全边界"),
    "takeover-handling": ("governance", "接管处理：人机交接与降级纪律"),
    "auditable-agent-comms": ("governance", "可审计通信：智能体通信留痕可查"),
    "agent-harness-for-tools": ("methodology", "工具套件：给工具套上执行纪律"),
    "crystallize-to-system1": ("methodology", "结晶到系统一：把重复劳动沉淀为直觉"),
    "generalizing-skills": ("methodology", "技能泛化：从个案提炼通用方法"),
    "ontology-grounded-spec": ("methodology", "本体锚定规格：以本体驱动规格编写"),
    "ontology-evolution": ("methodology", "本体演化：领域模型随业务生长"),
    "system1-first": ("methodology", "系统一优先：快慢两档的执行取舍"),
    "writing-livepowers-skills": ("methodology", "技能写作：本仓 skill 的写作规范"),
    "digital-role-spec": ("methodology", "数字角色规格：数字同事的角色定义"),
    "env-scan-ontology": ("ops", "环境扫描：运行环境的本体化盘点"),
    "explore-with-evidence": ("ops", "循证探索：探索结论必须带证据"),
    "night-loop-planning": ("ops", "夜巡规划：夜间自动循环的计划纪律"),
    "nightly-crystallization-review": ("ops", "夜间结晶复盘：夜间产出的复盘机制"),
    "outcome-ledger": ("ops", "结果台账：执行结果的台账化沉淀"),
    "using-livepowers": ("ops", "上手指南：本套技能的使用入口"),
}


class SubpackError(ValueError):
    """分包登记不一致。"""


def build_registry(skills_root: str | Path) -> dict:
    root = Path(skills_root)
    found = sorted(d.name for d in root.iterdir() if d.is_dir() and (d / "SKILL.md").exists())
    errors = []
    for name in found:
        if name not in SKILL_SUBPACKS:
            errors.append(f"{name}: 未登记分包（每包定位须齐全）")
    missing = [n for n in SKILL_SUBPACKS if n not in found]
    if missing:
        errors.append(f"登记了不存在的 skill: {missing}")
    registry = {"schema": "subpack-registry/v1", "subpacks": {}, "skills": {}}
    packs: dict[str, list[str]] = {}
    for name in found:
        if name not in SKILL_SUBPACKS:
            continue  # 未登记 skill 已在 errors 中报告，不崩溃
        subpack, one_line = SKILL_SUBPACKS[name]
        packs.setdefault(subpack, []).append(name)
        registry["skills"][name] = {"subpack": subpack, "one_line": one_line}
    for subpack, members in sorted(packs.items()):
        registry["subpacks"][subpack] = {
            "one_line": SKILL_SUBPACKS[members[0]][1],
            "count": len(members),
            "members": sorted(members),
        }
    registry["errors"] = errors
    registry["ok"] = not errors
    return registry


def main(argv: list[str]) -> int:
    import sys
    root = argv[0] if argv else "skills"
    registry = build_registry(root)
    print(json.dumps(registry, ensure_ascii=False, indent=2))
    return 0 if registry["ok"] else 1


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
