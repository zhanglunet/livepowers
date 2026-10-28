#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-279/T3：scripts/install_flow.py 的单元测试。

验收口径（trend #1398）：安装前快照自动发生，有测试。
虚构技能 example-skill（v0.3.1 → v0.4.0）全样本，不落真实数据。
红线：安检管进门、快照管退出——admitted=False 不快照不安装；快照失败
必须中止安装（fail-close）；本入口不产生任何放行语义。
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

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

ADMITTED = {"admitted": True, "report": {"decision": "admitted"},
            "checklist": {"gate_decision": "admitted"}}
DENIED = {"admitted": False, "report": {"decision": "blocked"},
          "checklist": {"gate_decision": "blocked"}}


def write_tree(root, files):
    root = Path(root)
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def read_tree(root):
    root = Path(root)
    return {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
            for p in sorted(root.rglob("*")) if p.is_file()}


class InstallFlowTest(unittest.TestCase):
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

    def test_admitted_true_snapshots_before_install(self):
        result = flow.install_with_snapshot(
            "example-skill", self.skill_dir, OLD_VERSION, "operator", ADMITTED)
        # 先快照：安装动作落地时快照已在槽内，且快照的是装前旧版内容
        self.assertTrue(result["installed"])
        self.assertEqual(read_tree(self.skill_dir), OLD_FILES)  # 模拟安装只记录不落盘
        snap = ins.latest_snapshot("example-skill")
        self.assertIsNotNone(snap)
        self.assertEqual(snap["dir_files"], OLD_FILES)
        # 调用方声明的 old_version 随最小清单入快照（回滚 to_version 可溯）
        self.assertEqual(snap["old_version"], OLD_VERSION)
        self.assertEqual(snap["change_kind"], "upgrade")
        # 安装动作引用刚生成的快照——次序上快照在前、安装在后
        performed = [e for e in flow.export_events()
                     if e["event"] == "install-performed"]
        self.assertEqual(len(performed), 1)
        self.assertEqual(performed[0]["snapshot_id"], snap["snapshot_id"])
        self.assertLessEqual(snap["taken_at"], performed[0]["at"])
        self.assertEqual(performed[0]["from_version"], OLD_VERSION)
        # T2 审计确有快照事件
        self.assertEqual([e["event"] for e in ins.export_events()],
                         ["snapshot-taken"])

    def test_admitted_false_rejected_without_snapshot(self):
        result = flow.install_with_snapshot(
            "example-skill", self.skill_dir, OLD_VERSION, "operator", DENIED)
        # 安检管进门：拒绝即不快照、不安装、不占槽
        self.assertFalse(result["installed"])
        self.assertIsNone(result["snapshot"])
        self.assertFalse(result["rollback_available"])
        self.assertIsNone(ins.latest_snapshot("example-skill"))
        self.assertEqual([e for e in ins.export_events()
                          if e["event"] == "snapshot-taken"], [])
        self.assertEqual([e for e in flow.export_events()
                          if e["event"] == "install-performed"], [])
        rejected = [e for e in flow.export_events()
                    if e["event"] == "install-rejected"]
        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0]["reason"], "admission_denied")
        self.assertEqual(read_tree(self.skill_dir), OLD_FILES)

    def test_missing_admission_result_fails_closed(self):
        # 安检结论不明确（缺字段/非字典/None）不得进门——fail-close
        for bad in (None, {}, {"report": {"decision": "admitted"}}):
            result = flow.install_with_snapshot(
                "example-skill", self.skill_dir, OLD_VERSION, "operator", bad)
            self.assertFalse(result["installed"])
            self.assertIsNone(result["snapshot"])
            self.assertFalse(result["rollback_available"])
        self.assertIsNone(ins.latest_snapshot("example-skill"))
        self.assertEqual(len(flow.export_events()), 3)  # 三次都是 install-rejected
        self.assertTrue(all(e["event"] == "install-rejected"
                            for e in flow.export_events()))

    def test_snapshot_failure_aborts_install(self):
        # 空目录 → take_snapshot 必然失败 → 安装中止（fail-close：
        # 宁可装不上，不可回不去）
        empty = self.base / "skills" / "empty-example-skill"
        empty.mkdir(parents=True)
        result = flow.install_with_snapshot(
            "example-skill", empty, OLD_VERSION, "operator", ADMITTED)
        self.assertFalse(result["installed"])
        self.assertIsNone(result["snapshot"])
        self.assertFalse(result["rollback_available"])
        self.assertEqual(result["reason"], "snapshot_failed")
        aborted = [e for e in flow.export_events()
                   if e["event"] == "install-aborted"]
        self.assertEqual(len(aborted), 1)
        self.assertEqual(aborted[0]["reason"], "snapshot_failed")
        self.assertEqual(aborted[0]["error_type"], "ValueError")
        # 中止后无安装动作、无快照入槽
        self.assertEqual([e for e in flow.export_events()
                          if e["event"] == "install-performed"], [])
        self.assertEqual([e for e in ins.export_events()
                          if e["event"] == "snapshot-taken"], [])

    def test_rollback_available_marker(self):
        result = flow.install_with_snapshot(
            "example-skill", self.skill_dir, OLD_VERSION, "operator", ADMITTED)
        self.assertTrue(result["rollback_available"])
        # 标记为真即可真回滚：用 T2 restore 一键回到快照里的上一版
        record = ins.restore(result["snapshot"], self.skill_dir,
                             from_version=NEW_VERSION, actor="operator",
                             reason="新版有问题，回上一版")
        self.assertEqual(record["event"], "rolled-back")
        self.assertEqual(record["from_version"], NEW_VERSION)
        self.assertEqual(record["to_version"], OLD_VERSION)
        self.assertEqual(read_tree(self.skill_dir), OLD_FILES)

    def test_audit_events(self):
        # 拒绝一次、通过一次：两条流（本模块动作流 + T2 快照流）都如实留痕
        flow.install_with_snapshot("example-skill", self.skill_dir,
                                   OLD_VERSION, "operator", DENIED)
        flow.install_with_snapshot("example-skill", self.skill_dir,
                                   OLD_VERSION, "operator", ADMITTED)
        events = flow.export_events()
        json.dumps(events, ensure_ascii=False)  # 全部事件可 JSON 序列化
        self.assertEqual([e["event"] for e in events],
                         ["install-rejected", "install-performed"])
        self.assertEqual([e["event"] for e in ins.export_events()],
                         ["snapshot-taken"])
        for event in events:
            self.assertTrue(event["at"])
            self.assertEqual(event["skill_name"], "example-skill")
            self.assertEqual(event["actor"], "operator")
        # 导出的是副本：改导出结果不影响进程内审计（append-only 视图）
        events.clear()
        self.assertEqual(len(flow.export_events()), 2)

    def test_single_slot_connection(self):
        # 同技能连续两次安装：单槽覆盖（只留"上一版"），每次安装动作
        # 各引用当次快照——本入口与 T2 单槽完全衔接，不自建第二套槽位
        first = flow.install_with_snapshot(
            "example-skill", self.skill_dir, OLD_VERSION, "operator", ADMITTED)
        second = flow.install_with_snapshot(
            "example-skill", self.skill_dir, OLD_VERSION, "operator", ADMITTED)
        latest = ins.latest_snapshot("example-skill")
        self.assertIsNotNone(latest)
        # 槽内就是最后一次安装前的快照（单槽覆盖；同一秒内两次快照
        # snapshot_id 可能同串——覆盖语义由 slot-overwritten 事件作证）
        self.assertEqual(latest, second["snapshot"])
        self.assertTrue(second["rollback_available"])
        performed = [e for e in flow.export_events()
                     if e["event"] == "install-performed"]
        self.assertEqual([e["snapshot_taken_at"] for e in performed],
                         [first["snapshot"]["taken_at"],
                          second["snapshot"]["taken_at"]])
        overwritten = [e for e in ins.export_events()
                       if e["event"] == "slot-overwritten"]
        self.assertEqual(len(overwritten), 1)  # 第二次快照覆盖旧槽入审计
        self.assertEqual(overwritten[0]["skill_name"], "example-skill")
        # 其他技能槽位不受影响
        other_dir = self.base / "skills" / "other-example-skill"
        write_tree(other_dir, {"SKILL.md": "---\nname: other-example-skill\n---\n"})
        other = flow.install_with_snapshot(
            "other-example-skill", other_dir, "1.0.0", "operator", ADMITTED)
        self.assertTrue(other["installed"])
        self.assertEqual(ins.latest_snapshot("example-skill"), latest)
        self.assertEqual(ins.latest_snapshot("other-example-skill")["skill_name"],
                         "other-example-skill")


if __name__ == "__main__":
    unittest.main()
