#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-293/T2（trend issue #1467）：skill 间 @引用解析最小实现。

按 T1 设计（docs/plans/2026-11-04-prd-293-at-skill-ref-design.md）§3/§4/§5/§6
实现，候选集为 PRD-227 总登记册形态（注入式纯函数——registry.json 未并线前
测试用同形态合成登记册，生产装配在 227 合并后对接）：

  - parse(raw)：@技能名 单形态——禁止形态（节锚 #正文/版本后缀/双写/空名）
    抛 RefSyntaxError；自引用在 resolve 依 from_skill 判定（REF_SELF_LOOP）；
  - resolve(raw, registry, from_skill)：精确匹配登记册 skill 名（全库唯一
    不变量）→ 0 命中 REF_NOT_FOUND（**fail-closed 不降级**，R2）；>1 命中
    = 登记册不变量破坏 → REF_REGISTRY_CORRUPT；自引用 → REF_SELF_LOOP；
    引用环（沿 x-references 边 DFS）→ REF_CYCLE。命中 → 契约解析：
    trigger_conditions=triggers（触发句原文）、output_contract=examples
    （验收例=登记册机械派生口径）——**零正文读取**（登记册无正文字段，
    组装器只接受本产物，R1/R3 类型级保证）；
  - RefAudit：引用关系审计（§6）——append-only、from/to 双侧留痕、可重建
    依赖图；静态边落 frontmatter x-references 归装配侧（T1 §6 双载体）。

零网络；示例全虚构占位。
测试：tests/test_prd293_t2_skill_ref.py
"""
from __future__ import annotations

import re
from typing import Any

REF_SCHEMA = "skill-ref-resolution/v1"
NAME_RE = re.compile(r"^@(?P<name>[^@\s#]+)$")

ERROR_CODES = ("REF_SYNTAX_ERROR", "REF_NOT_FOUND", "REF_SELF_LOOP",
               "REF_CYCLE", "REF_REGISTRY_CORRUPT")


class RefSyntaxError(ValueError):
    """§3.2 禁止形态——出现即拒绝，不尝试理解。"""


def parse(raw: str) -> str:
    """@语法解析：返回技能名（不含 @）；禁止形态抛 RefSyntaxError。"""
    if not isinstance(raw, str) or not raw.strip():
        raise RefSyntaxError(f"引用为空或非字符串：{raw!r}")
    token = raw.strip()
    if token.startswith("@@") or "@" in token[1:] or '"' in token:
        raise RefSyntaxError(f"禁止形态（双写/引号/内嵌@）：{raw!r}（§3.2）")
    m = NAME_RE.match(token)
    if not m:
        raise RefSyntaxError(f"禁止形态（缺 @/含空白）：{raw!r}（§3.2）")
    name = m.group("name")
    if "#" in name:
        raise RefSyntaxError(f"禁止形态（节锚——正文永不引用，R1）：{raw!r}（§3.2）")
    if re.search(r"\s+v\d", name) or name.endswith((".0", "V2")) and " v" in name:
        raise RefSyntaxError(f"禁止形态（版本后缀——版本归 PRD-227 包管理）：{raw!r}（§3.2）")
    return name


def resolve(raw: str, registry: dict[str, Any], *,
            from_skill: str | None = None) -> dict[str, Any]:
    """@名→契约解析（§4.2）：精确匹配 + 不变量裁决 + 环检测。

    registry：PRD-227 登记册形态 {"packs": [{"skills": [{"name", "triggers",
    "examples", "x-references"?…}]}]}（注入；登记册无正文字段=零正文读取的结构保证）。
    返回 Resolution | Refusal（二值，T1 §5）。
    """
    name = parse(raw)
    skills = [s for p in (registry or {}).get("packs", []) for s in p.get("skills", [])]
    hits = [s for s in skills if s.get("name") == name]
    if from_skill and name == from_skill:
        return _refusal(raw, "REF_SELF_LOOP", [],
                        "自引用拒绝（§3.2 防环）")
    if len(hits) > 1:
        return _refusal(raw, "REF_REGISTRY_CORRUPT",
                        [s.get("name") for s in hits],
                        "登记册全库唯一不变量破坏（数据异常显形，T1 §4.2）")
    if not hits:
        # fail-closed（R2）：不静默跳过、不空契约占位——引用方整体不可用
        return _refusal(raw, "REF_NOT_FOUND", [],
                        "登记册无此技能——引用方不可用（§5 fail-closed）")
    entry = hits[0]
    # 引用环检测：沿 x-references 静态边 DFS，含本次拟新增边
    graph: dict[str, list[str]] = {}
    for s in skills:
        # x-references 形态为 @名——边统一去 @ 前缀（与节点名同空间）
        graph[s.get("name", "")] = [
            (r[1:] if isinstance(r, str) and r.startswith("@") else r)
            for r in (s.get("x-references") or [])]
    if from_skill:
        graph.setdefault(from_skill, []).append(name)
    cycle = _find_cycle(from_skill or name, graph, visiting=set(), done=set())
    if cycle:
        return _refusal(raw, "REF_CYCLE", cycle,
                        f"引用环：{' → '.join(cycle)}（§5 拒绝）")
    return {
        "schema": REF_SCHEMA,
        "raw": raw,
        "skill": entry["name"],
        "trigger_conditions": entry.get("triggers"),
        "output_contract": entry.get("examples"),
        "resolution": {"status": "resolved", "candidates": 1, "strategy": "exact"},
    }


def _find_cycle(node: str, graph: dict[str, list[str]],
                visiting: set[str], done: set[str]) -> list[str] | None:
    """DFS 环检测：返回环路径（None=无环）。"""
    if node in visiting:
        return [node]
    if node in done or node not in graph:
        return None
    visiting.add(node)
    for nxt in graph[node]:
        cycle = _find_cycle(nxt, graph, visiting, done)
        if cycle:
            return [node] + cycle
    visiting.discard(node)
    done.add(node)
    return None


def _refusal(raw: str, code: str, candidates: list, detail: str) -> dict[str, Any]:
    return {
        "schema": REF_SCHEMA, "raw": raw, "skill": None,
        "trigger_conditions": None, "output_contract": None,
        "resolution": {"status": "refused", "error_code": code,
                       "candidates": candidates, "detail": detail},
    }


class RefAudit:
    """引用关系审计（§6）：append-only、from/to 双侧、可重建依赖图。"""

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def log(self, raw: str, outcome: dict[str, Any], *, at: str,
            from_skill: str | None = None) -> dict[str, Any]:
        res = outcome.get("resolution", {})
        entry = {"ts": at, "raw": raw, "from_skill": from_skill,
                 "to_skill": outcome.get("skill")}
        if res.get("status") == "resolved":
            entry.update({"status": "resolved",
                          "trigger_conditions": outcome.get("trigger_conditions"),
                          "output_contract": outcome.get("output_contract")})
        else:
            entry.update({"status": "refused", "candidates": res.get("candidates", []),
                          "error_code": res.get("error_code"),
                          "detail": res.get("detail")})
        self.records.append(entry)  # 只增不删
        return dict(entry)

    def resolve_logged(self, raw: str, registry: dict[str, Any], *, at: str,
                       from_skill: str | None = None) -> dict[str, Any]:
        """一步解析+留痕（语法错也记审计）。"""
        try:
            outcome = resolve(raw, registry, from_skill=from_skill)
        except RefSyntaxError as exc:
            entry = {"ts": at, "raw": raw, "from_skill": from_skill,
                     "to_skill": None, "status": "refused", "candidates": [],
                     "error_code": "REF_SYNTAX_ERROR", "detail": str(exc)}
            self.records.append(entry)
            return {"refused": True, "error_code": "REF_SYNTAX_ERROR",
                    "detail": str(exc), "audit": entry}
        entry = self.log(raw, outcome, at=at, from_skill=from_skill)
        if outcome["resolution"]["status"] == "refused":
            return {"refused": True,
                    "error_code": outcome["resolution"]["error_code"],
                    "detail": outcome["resolution"].get("detail"), "audit": entry}
        return {"refused": False, "resolution": outcome, "audit": entry}

    def dependency_graph(self) -> dict[str, list[str]]:
        """从审计重建引用依赖图（成功解析的 from→to 边）。"""
        graph: dict[str, list[str]] = {}
        for r in self.records:
            if r.get("status") == "resolved" and r.get("from_skill"):
                graph.setdefault(r["from_skill"], []).append(r["to_skill"])
        return graph
