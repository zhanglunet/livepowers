#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-279/T4：回滚记录审计断言（trend issue #1399）。

验收口径：审计断言通过。回滚记录四要素必填、缺一不可：

- 技能名（skill_name）/ 版本链（from_version→to_version）/ 时间（at）/
  触发者（actor）；
- from→to 版本链闭环：install-performed 的 from_version（装前旧版）与
  rolled-back 的 to_version（回到的版本）同指旧版，rolled-back 的
  from_version 是调用方如实声明的装后新版——装→回滚闭环可溯；
- 审计事件时序：install-performed → rolled-back（跨 install_flow 与
  install_snapshot 两段 append-only 流，由 snapshot_id 闭环）；
- 快照指纹在案：回滚记录携带 dir_fingerprint 且与快照/还原后目录一致；
- 事件可 JSON 序列化；固定时钟下全流程逐事件确定。

虚构技能 example-skill（v0.3.1 → v0.4.0）全样本，不落真实数据。
红线：安检管进门、快照管退出——本组断言只查审计，不产生任何放行语义。
"""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))
import install_flow as flow  # noqa: E402
import install_snapshot as ins  # noqa: E402

OLD_VERSION = "0.3.1"
NEW_VERSION = "0.4.0"

OLD_FILES = {
    "SKILL.md": (
        "---\n"
        "name: example-skill\n"
        f"version: {OLD_VERSION}\n"
        "description: Use when 示例触发条件\n"
        "---\n"
        "# example-skill\n\n虚构技能正文。\n"
    ),
    "references/template.md": "示例引用模板 v0.3.1\n",
}

NEW_FILES = {
    "SKILL.md": (
        "---\n"
        "name: example-skill\n"
        f"version: {NEW_VERSION}\n"
        "description: Use when 示例触发条件\n"
        "---\n"
        "# example-skill\n\n虚构技能正文（新版）。\n"
    ),
}

ADMITTED = {"admitted": True, "report": {"decision": "admitted"},
            "checklist": {"gate_decision": "admitted"}}


def write_tree(root, files):
    root = Path(root)
    if root.is_dir():
        for p in root.rglob("*"):
            if p.is_file() and p.relative_to(root).as_posix() not in files:
                p.unlink()
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def read_tree(root):
    root = Path(root)
    return {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
            for p in sorted(root.rglob("*")) if p.is_file()}


class RollbackAuditTest(unittest.TestCase):
    def setUp(self):
        flow.reset_audit()
        ins.reset_audit()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name)
        self.skill_dir = self.base / "skills" / "example-skill"
        write_tree(self.skill_dir, OLD_FILES)

    def tearDown(self):
        flow.reset_audit()
        ins.reset_audit()

    def install_then_rollback(self, actor="operator", reason=""):
        """标准场景：收录通过安装 v0.4.0 → 新版落盘 → 回滚到 v0.3.1。"""
        result = flow.install_with_snapshot(
            "example-skill", self.skill_dir, OLD_VERSION, actor, ADMITTED)
        self.assertTrue(result["installed"])
        snap = result["snapshot"]
        write_tree(self.skill_dir, NEW_FILES)  # 新版落盘（升级动作）
        record = ins.restore(snap, self.skill_dir,
                             from_version=NEW_VERSION, actor=actor,
                             reason=reason or "示例：回滚到上一版")
        return snap, record

    def test_rollback_record_four_elements(self):
        # 四要素：技能名 / 版本（from→to）/ 时间 / 触发者，缺一不可
        snap, record = self.install_then_rollback()
        self.assertEqual(record["event"], "rolled-back")
        self.assertEqual(record["skill_name"], "example-skill")
        self.assertEqual(record["from_version"], NEW_VERSION)
        self.assertEqual(record["to_version"], OLD_VERSION)
        self.assertTrue(record["at"])
        datetime.fromisoformat(record["at"])  # 时间可解析
        self.assertEqual(record["actor"], "operator")
        self.assertEqual(record["verify"], "passed")
        # 记录在审计流里可查（append-only 原样在案）
        self.assertIn(record, ins.export_events())

    def test_from_to_version_chain_closed_loop(self):
        # 版本链闭环：install-performed 的 from_version（装前旧版）与
        # rolled-back 的 to_version 同指 v0.3.1；rolled-back 的 from_version
        # 是装后新版 v0.4.0——装→回滚整链可溯，无断点
        snap, record = self.install_then_rollback()
        performed = [e for e in flow.export_events()
                     if e["event"] == "install-performed"]
        self.assertEqual(len(performed), 1)
        self.assertEqual(performed[0]["from_version"], OLD_VERSION)
        self.assertEqual(record["from_version"], NEW_VERSION)
        self.assertEqual(record["to_version"], OLD_VERSION)
        self.assertEqual(record["to_version"], snap["old_version"])
        self.assertEqual(record["from_version"], NEW_VERSION)
        # to_version 快照可证：回滚后目录就是 to_version 的原样
        self.assertEqual(read_tree(self.skill_dir), OLD_FILES)

    def test_audit_event_sequence_install_then_rolled_back(self):
        # 审计事件时序：install-performed → rolled-back（跨两段事件流，
        # 由 snapshot_id 闭环；rolled-back 之前必先 snapshot-taken）
        snap, record = self.install_then_rollback()
        flow_events = flow.export_events()
        ins_events = ins.export_events()
        self.assertEqual([e["event"] for e in flow_events], ["install-performed"])
        self.assertEqual([e["event"] for e in ins_events],
                         ["snapshot-taken", "rolled-back"])
        # 时间序：安装动作不晚于回滚记录（ISO 同格式可直比）
        self.assertLessEqual(flow_events[0]["at"], record["at"])
        # snapshot_id 三方闭环：install-performed → snapshot-taken → rolled-back
        self.assertEqual(flow_events[0]["snapshot_id"], snap["snapshot_id"])
        self.assertEqual(ins_events[0]["snapshot_id"], snap["snapshot_id"])
        self.assertEqual(record["snapshot_id"], snap["snapshot_id"])
        # 审计只增不改：两段流事件数不变（append-only 视图）
        self.assertEqual(len(flow.export_events()), 1)
        self.assertEqual(len(ins.export_events()), 2)

    def test_snapshot_fingerprint_on_record(self):
        # 快照指纹在案：回滚记录携带 dir_fingerprint，与快照记录、还原后
        # 目录重算指纹一致；逐文件指纹与快照内容对得上
        snap, record = self.install_then_rollback()
        self.assertEqual(record["dir_fingerprint"], snap["fingerprints"]["dir"])
        disk = ins._fingerprints(read_tree(self.skill_dir))["dir"]
        self.assertEqual(disk, record["dir_fingerprint"])
        for rel, content in OLD_FILES.items():
            self.assertEqual(snap["fingerprints"]["files"][rel],
                             hashlib.sha256(content.encode()).hexdigest())
        # 指纹与快照槽位在案可查：latest_snapshot 的指纹同串
        self.assertEqual(ins.latest_snapshot("example-skill")["fingerprints"]["dir"],
                         record["dir_fingerprint"])

    def test_actor_propagates_and_queryable(self):
        # 触发者贯穿安装与回滚两段审计：同一 actor 可跨流检索
        actor = "auditor-example"
        snap, record = self.install_then_rollback(actor=actor)
        self.assertEqual(record["actor"], actor)
        performed = [e for e in flow.export_events()
                     if e["event"] == "install-performed"]
        self.assertEqual(performed[0]["actor"], actor)
        # 按触发者查询：两段流各命中其动作事件
        by_actor_flow = [e for e in flow.export_events() if e.get("actor") == actor]
        by_actor_ins = [e for e in ins.export_events() if e.get("actor") == actor]
        self.assertEqual([e["event"] for e in by_actor_flow], ["install-performed"])
        self.assertEqual([e["event"] for e in by_actor_ins], ["rolled-back"])
        # reason 一句话口径随记录在案
        _, record_reason = self.install_then_rollback(reason="新版误删引用模板")
        self.assertEqual(record_reason["reason"], "新版误删引用模板")

    def test_events_serializable_and_append_only_view(self):
        # 事件可 JSON 序列化（含回滚记录本体）；导出是副本，改导出不影响审计
        snap, record = self.install_then_rollback()
        flow_dump = json.dumps(flow.export_events(), ensure_ascii=False)
        ins_dump = json.dumps(ins.export_events(), ensure_ascii=False)
        self.assertIn("rolled-back", ins_dump)
        self.assertIn("install-performed", flow_dump)
        json.dumps(record, ensure_ascii=False)  # 回滚记录本体可序列化
        exported = ins.export_events()
        exported.clear()
        self.assertTrue(ins.export_events())  # append-only 视图未被影响

    def test_deterministic_full_flow_fixed_clock(self):
        # 确定性：固定时钟下同一场景跑两遍（重置审计后），两段事件流
        # 逐事件一致（含 snapshot_id 与回滚记录全字段）
        fixed_at = "2026-10-29T12:00:00+08:00"
        with mock.patch.object(flow, "_now", lambda: fixed_at), \
                mock.patch.object(ins, "_now", lambda: fixed_at):
            self.install_then_rollback()
            first = (json.dumps(flow.export_events(), ensure_ascii=False,
                                sort_keys=True),
                     json.dumps(ins.export_events(), ensure_ascii=False,
                                sort_keys=True))
            flow.reset_audit()
            ins.reset_audit()
            write_tree(self.skill_dir, OLD_FILES)  # 同一场景重置重跑
            self.install_then_rollback()
            second = (json.dumps(flow.export_events(), ensure_ascii=False,
                                 sort_keys=True),
                      json.dumps(ins.export_events(), ensure_ascii=False,
                                 sort_keys=True))
        self.assertEqual(first, second)
        self.assertIn(fixed_at, first[0])  # 时钟确实被钉住


if __name__ == "__main__":
    unittest.main()
