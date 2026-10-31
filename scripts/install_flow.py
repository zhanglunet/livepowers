#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-279/T3：与收录流程衔接——安检管进门、快照管退出的安装入口。

trend issue #1398；设计文档 docs/plans/2026-10-29-prd-279-install-snapshot.md
§3.4（安装唯一入口）。衔接两个既有模块：

  admission_result  ← PRD-255 admission_flow 的返回（{admitted, report,
                      checklist}；其实现 PR 尚未合并，本模块只依赖其接口
                      契约中的 admitted 布尔字段）；
  take_snapshot     ← PRD-279/T2 scripts/install_snapshot.py（单槽快照）。

install_with_snapshot(skill_name, skill_dir, old_version, actor,
admission_result) 的固定次序（快照是安装动作的**内嵌第一步**，不依赖调用
方记得手动快照——"快照遗漏导致不可回滚"由流程结构性排除）：

  1. admission_result.admitted 非 True → 直接拒绝：不快照、不安装、不占槽
     （安检管进门：没进门就没有"上一版"可退）；
  2. admitted 为 True → **先** take_snapshot 快照当前已装目录；快照任何
     异常 → 安装即中止（fail-close：宁可装不上，不可回不去），绝不带病
     落盘；
  3. 快照成功后才模拟安装：记录安装动作入审计（本任务为最小实现，记录
     动作不落盘新版文件；真实落盘与清单更新由后续接线任务收口）；
  4. 返回 {"installed", "snapshot", "rollback_available"}——snapshot 即
     T2 单槽快照对象，rollback_available=True 时调用方可随时用 T2
     restore() 一键回到上一版。

与 T2 的槽位衔接：本入口不做自己的快照存储，直接复用 install_snapshot
的单槽（每技能只留"上一版"，再次安装覆盖旧槽，覆盖事件入 T2 审计）；
本模块自己的审计事件（拒绝/中止/安装动作）另记一条 append-only 流，
export_events() 查询、reset_audit() 仅供测试隔离。

红线：安检管进门、快照管退出——本入口不产生任何放行语义（拒绝不快照、
恢复不重扫）；快照失败必须中止安装；审计 append-only；纯 stdlib 零网络；
示例全虚构，无真实主机名/IP/账号/密钥。
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime

from install_snapshot import take_snapshot

# 单槽快照存储直接复用 T2（install_snapshot._SLOTS）——本模块不自建槽位。


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


# 本模块的审计事件（append-only，进程内）：拒绝 / 中止 / 安装动作。
_EVENTS: list = []


def _reject(skill_name, actor, reason) -> dict:
    """拒绝结果：不快照、不安装、不占槽（安检管进门）。"""
    _EVENTS.append({
        "event": "install-rejected",
        "at": _now(),
        "skill_name": skill_name,
        "actor": actor,
        "reason": reason,
    })
    return {"installed": False, "snapshot": None, "rollback_available": False,
            "reason": reason}


def install_with_snapshot(skill_name, skill_dir, old_version, actor,
                          admission_result) -> dict:
    """收录通过后的安装唯一入口：先快照、后安装（fail-close）。

    skill_name：技能名；skill_dir：当前已装技能目录（快照对象——要能退回
    的"上一版"就住在这里）；old_version：调用方声明的当前已装版本（首次
    安装为 None，随安装动作入审计）；actor：触发者；admission_result：
    PRD-255 admission_flow 的返回（本入口只看其 admitted 字段）。

    返回 {"installed": bool, "snapshot": install-snapshot-v1 | None,
    "rollback_available": bool}；失败路径附 reason。admitted 非 True 一律
    拒绝（缺安检结果也拒绝——安检结论不明确不得进门）。

    T3 最小实现边界：本入口签名只有 old_version、没有整份已装清单——
    old_version 为真时以仅含该技能条目的最小清单副本传给 T2
    take_snapshot，让快照 old_version / 回滚记录 to_version（from→to）
    如实可溯；整份清单快照随后续落盘接线补全，届时以真实清单为准。
    """
    admitted = bool(admission_result.get("admitted")) if isinstance(
        admission_result, dict) else False
    if not admitted:
        return _reject(skill_name, actor, "admission_denied")

    # 内嵌第一步：强制快照，任何异常都中止安装（fail-close）。
    try:
        manifest = None
        if old_version:
            manifest = {
                "schema": "installed-manifest-v1",
                "generated_at": _now(),
                "skills": [{"name": skill_name, "version": old_version}],
            }
        snap = take_snapshot(skill_name, skill_dir, manifest)
    except Exception as exc:  # noqa: BLE001 —— 快照失败必须中止，类型不设限
        _EVENTS.append({
            "event": "install-aborted",
            "at": _now(),
            "skill_name": skill_name,
            "actor": actor,
            "reason": "snapshot_failed",
            "error_type": type(exc).__name__,
        })
        return {"installed": False, "snapshot": None,
                "rollback_available": False, "reason": "snapshot_failed"}

    # 快照落袋后才允许出现安装动作：模拟安装 = 记录动作（真实落盘后续接线）。
    _EVENTS.append({
        "event": "install-performed",
        "at": _now(),
        "skill_name": skill_name,
        "from_version": old_version,
        "actor": actor,
        "snapshot_id": snap["snapshot_id"],
        "snapshot_taken_at": snap["taken_at"],
        "simulation": True,
    })
    return {"installed": True, "snapshot": snap, "rollback_available": True}


def export_events() -> list:
    """本模块审计事件导出（append-only 视图，JSON 可序列化）。"""
    return [deepcopy(event) for event in _EVENTS]


def reset_audit() -> None:
    """清空本模块审计事件（仅供测试隔离；不触碰 T2 槽位与审计）。"""
    _EVENTS.clear()
