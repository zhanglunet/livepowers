#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-255/T4（trend #1278）：误报白名单与复核人签字——可审计的复核放行。

按 PRD-255/T1 设计（docs/plans/2026-10-28-prd-255-market-gate.md）§3.3 实现：
被拦技能（HIGH+ 不收录硬闸门）进待复核清单后，复核人可确认某条 finding 为误报，
凭**理由 + 签字**写入白名单。条目字段（T1 §3.3）:

    entry_id    wl-NNNN，唯一
    rule_id     放行的规则（只放行单条规则，不整体放行技能）
    scope       生效范围（技能名或 name@version；"*" 通配全部）
    reason      误报理由，必填非空
    reviewer    复核人标识，必填（签字）
    decided_at  复核日期；expires_at 默认 decided_at + 90 天，过期自动回拦

纪律（与 PRD-247 白名单同族同纪律）：
  - reason 或 reviewer 缺失/空白 → ValueError——无理由无签字不放行；
  - 过期条目 check() 恒为 False（过期回拦），条目仍保留在 audit_log 里可追溯；
  - audit_log() 导出全部条目（谁、放行了哪条规则、为什么、何时失效）；
  - 命中留痕由 market_gate_flow.admission_flow 写入报告 whitelist_applied 与
    PRD-094 清单 gate_whitelist 字段——放行永不静默。

本模块不联网、不删除任何条目；示例与默认值全虚构占位。
"""
from __future__ import annotations

import copy
import datetime
import json
import os
from typing import Any

SCHEMA = "market-gate-whitelist-v1"
DEFAULT_EXPIRES_DAYS = 90  # T1 §3.3: 复核决定默认 90 天有效，过期回拦


def _parse_ts(value):
    """解析 ISO 日期（YYYY-MM-DD）或完整 ISO 时间戳；非法返回 None。"""
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.datetime.combine(
                datetime.date.fromisoformat(text[:10]), datetime.time.min)
        except ValueError:
            return None


class WhitelistManager:
    """市场收录误报白名单：加载/新增/命中判断/审计导出（纯内存 + JSON 文件，零网络）。"""

    def __init__(self, entries: list[dict[str, Any]] | None = None):
        self._entries = [dict(e) for e in (entries or [])]

    # ------------------------------------------------------------ 加载 ----
    @classmethod
    def load(cls, path: str) -> "WhitelistManager":
        """从 JSON 文件加载白名单（{"schema": …, "entries": […]}）。"""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        entries = data.get("entries") if isinstance(data, dict) else None
        if not isinstance(entries, list):
            raise ValueError(f"白名单文件缺少 entries 列表: {path}")
        return cls(entries)

    def save(self, path: str) -> str:
        """白名单落盘（原子写；条目含理由与签字，diff 即审计）。"""
        tmp = path + ".tmp"
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"schema": SCHEMA, "entries": self._entries},
                      f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp, path)
        return path

    # ------------------------------------------------------------ 新增 ----
    def add(self, entry_id: str, rule_id: str, scope: str, reason: str, reviewer: str,
            decided_at: str, expires_days: int = DEFAULT_EXPIRES_DAYS) -> dict[str, Any]:
        """新增一条白名单条目；理由或复核人缺失即拒绝（签字纪律）。"""
        if not str(reason or "").strip():
            raise ValueError("白名单条目缺 reason——无理由不放行（T1 §3.3 复核签字纪律）")
        if not str(reviewer or "").strip():
            raise ValueError("白名单条目缺 reviewer——无复核人签字不放行")
        if not str(entry_id or "").strip():
            raise ValueError("白名单条目缺 entry_id（wl-NNNN，唯一）")
        if not str(rule_id or "").strip():
            raise ValueError("白名单条目缺 rule_id——白名单只放行单条规则")
        decided = _parse_ts(decided_at)
        if decided is None:
            raise ValueError(f"decided_at 不是合法 ISO 日期: {decided_at!r}")
        if not isinstance(expires_days, int) or expires_days < 0:
            raise ValueError(f"expires_days 必须是非负整数: {expires_days!r}")
        if any(e.get("entry_id") == entry_id for e in self._entries):
            raise ValueError(f"entry_id 重复: {entry_id}")
        expires_at = (decided + datetime.timedelta(days=expires_days)).date().isoformat()
        entry = {
            "entry_id": str(entry_id),
            "rule_id": str(rule_id),
            "scope": str(scope or "").strip() or "*",
            "reason": str(reason).strip(),
            "reviewer": str(reviewer).strip(),
            "decided_at": str(decided_at).strip(),
            "expires_days": expires_days,
            "expires_at": expires_at,
        }
        self._entries.append(entry)
        return copy.deepcopy(entry)

    # ------------------------------------------------------------ 命中 ----
    def match(self, rule_id: str, scope: str,
              now: datetime.datetime | None = None) -> dict[str, Any] | None:
        """返回命中的未过期条目（dict）；不命中或已过期返回 None。

        scope 匹配：条目 scope 为 "*" 通配全部，否则须与传入 scope 完全一致。
        过期判定：now 的日期晚于 expires_at 即过期（expires_at 当天仍有效）。
        """
        now = now or datetime.datetime.now().astimezone()
        now_date = now.date() if isinstance(now, datetime.datetime) else now
        for entry in self._entries:
            if entry.get("rule_id") != rule_id:
                continue
            if entry.get("scope", "*") != "*" and entry.get("scope") != scope:
                continue
            expires = _parse_ts(entry.get("expires_at"))
            if expires is None or now_date > expires.date():
                continue  # 过期条目自动失效，但保留在 audit_log 可追溯
            return copy.deepcopy(entry)
        return None

    def check(self, rule_id: str, scope: str,
              now: datetime.datetime | None = None) -> bool:
        """命中未过期条目 → True；不命中或过期 → False。"""
        return self.match(rule_id, scope, now) is not None

    # ------------------------------------------------------------ 审计 ----
    def audit_log(self) -> list[dict[str, Any]]:
        """导出全部条目（含已过期）——谁、放行了哪条规则、为什么、何时失效。"""
        return copy.deepcopy(self._entries)

    def __len__(self) -> int:
        return len(self._entries)
