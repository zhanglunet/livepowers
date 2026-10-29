#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-279/T5：验收试运行——虚构技能安装回放 + 回滚演练 + 文档无密钥（trend #1400）。

验收口径（计划 §6）：快照回滚全链通过；红线断言全过；文档无密钥。

- P-1 全链演练：install_with_snapshot（收录通过）→ 安装内嵌第一步自动快照 →
  模拟升级落盘 → 新版本出问题 → restore 目录级回滚（还原后指纹校验）→
  「已回滚到 v0.3.1」记录四要素齐全（技能名 / from→to / 时间 / 触发者）；
- 红线断言（安检管进门、快照管退出）：先快照后安装（快照是 install_with_snapshot
  的内嵌第一步，admitted 非 True 不快照不安装不占槽）、单槽覆盖（每技能恒只有
  一份"上一版"，覆盖事件入审计）、审计序列（install-performed → snapshot-taken
  → rolled-back 跨流 snapshot_id 闭环、append-only 可序列化）；
- N-2 篡改快照 fail-close：verify: failed 入审计、不产生成功回滚记录；
- 空目录拒绝：空目录没有可回滚的"上一版"，take_snapshot 直接拒绝；
- 零网络：模块零网络 import + 全流程 socket 全封环境下照跑；
- 密钥扫描：交付面（两模块源码 + 本测试文件 + T1 设计文档）密钥标记 /
  真实网段字样 0 命中；
- 确定性：固定时钟下同一演练跑两遍，事件流逐事件一致。

虚构技能 example-skill（v0.3.1 → v0.4.0）全样本，不落真实数据。全链零 LLM
零网络。恢复不重扫放行：槽位保留，新版再进仍须重新过安检。
"""
import hashlib
import json
import os
import socket as socket_module
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
# 新版：改判 SKILL.md、删掉 references/template.md——演练中"新版本出问题"
NEW_FILES = {
    "SKILL.md": (
        "---\n"
        "name: example-skill\n"
        f"version: {NEW_VERSION}\n"
        "description: Use when 示例触发条件\n"
        "---\n"
        "# example-skill\n\n虚构技能正文（新版，示例：误删引用模板）。\n"
    ),
}

ADMITTED = {"admitted": True, "report": {"decision": "admitted"},
            "checklist": {"gate_decision": "admitted"}}
DENIED = {"admitted": False, "report": {"decision": "blocked"},
          "checklist": {"gate_decision": "blocked"}}

# 密钥标记用拼接构造：本文件自身也在被扫描交付面里，拼接保证扫描词表
# 不以连续字面量出现在源码里（否则自扫必命中自身定义）。
SECRET_MARKERS = ("BEGIN " "PRIVATE KEY", "BEGIN " "RSA", "BEGIN " "EC",
                  "api_" "key=", "ap" "ikey=", "pass" "word=", "s" "k-",
                  "gh" "p_", "AK" "IA", "xox" "b-")
REAL_HOST_MARKERS = ("192." "168.", "10." "0.", "127." "0.0.1")

REPO_ROOT = Path(__file__).resolve().parents[1]


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


class AcceptanceBase(unittest.TestCase):
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

    def full_rehearsal(self, actor="operator"):
        """P-1 全流程演练：收录通过安装（内嵌先快照）→ 升级落盘（新版出问题）
        → restore 回滚 → 返回 (安装结果, 快照, 回滚记录)。"""
        installed = flow.install_with_snapshot(
            "example-skill", self.skill_dir, OLD_VERSION, actor, ADMITTED)
        self.assertTrue(installed["installed"])
        snap = installed["snapshot"]
        write_tree(self.skill_dir, NEW_FILES)  # 新版落盘（升级动作）
        record = ins.restore(snap, self.skill_dir,
                             from_version=NEW_VERSION, actor=actor,
                             reason="示例：新版误删引用模板，回滚到上一版")
        return installed, snap, record


class P1FullChainRehearsal(AcceptanceBase):
    """P-1：安装 → 快照 → 升级 → 新版本出问题 → 回滚 → 四要素记录。"""

    def test_p1_full_chain_install_snapshot_upgrade_rollback(self):
        # 全链（步骤展开，便于断言每个中间态）：
        # 收录通过 → 安装内嵌第一步自动快照 → 升级落盘 → 一键恢复
        installed = flow.install_with_snapshot(
            "example-skill", self.skill_dir, OLD_VERSION, "operator", ADMITTED)
        self.assertTrue(installed["installed"])
        self.assertTrue(installed["rollback_available"])
        snap = installed["snapshot"]
        # 快照（安装内嵌第一步自动发生）：schema / 版本链 / 指纹 / 内联自足
        self.assertEqual(snap["schema"], "install-snapshot-v1")
        self.assertEqual(snap["skill_name"], "example-skill")
        self.assertEqual(snap["old_version"], OLD_VERSION)
        self.assertEqual(snap["change_kind"], "upgrade")
        self.assertEqual(snap["dir_files"], OLD_FILES)
        self.assertEqual(snap["fingerprints"]["files"]["references/template.md"],
                         hashlib.sha256(
                             OLD_FILES["references/template.md"].encode()).hexdigest())
        datetime.fromisoformat(snap["taken_at"])
        # 升级落盘：新版在盘上（SKILL.md 改判、references/ 被新版删掉）
        write_tree(self.skill_dir, NEW_FILES)
        self.assertEqual(read_tree(self.skill_dir), NEW_FILES)
        # 新版本出问题 → 一键回滚：目录整体对齐快照，逐字节回到 v0.3.1 原样
        record = ins.restore(snap, self.skill_dir,
                             from_version=NEW_VERSION, actor="operator",
                             reason="示例：新版误删引用模板，回滚到上一版")
        self.assertEqual(record["event"], "rolled-back")
        self.assertEqual(record["to_version"], OLD_VERSION)
        self.assertEqual(record["verify"], "passed")
        self.assertEqual(read_tree(self.skill_dir), OLD_FILES)
        self.assertEqual(ins._fingerprints(read_tree(self.skill_dir))["dir"],
                         snap["fingerprints"]["dir"])

    def test_rollback_record_four_elements_complete(self):
        # 「已回滚到 v0.3.1」记录四要素必填：技能名 / 版本 from→to / 时间 / 触发者
        _, snap, record = self.full_rehearsal(actor="ops-example")
        self.assertEqual(record["skill_name"], "example-skill")
        self.assertEqual(record["from_version"], NEW_VERSION)
        self.assertEqual(record["to_version"], OLD_VERSION)
        self.assertTrue(record["at"])
        datetime.fromisoformat(record["at"])
        self.assertEqual(record["actor"], "ops-example")
        # 四要素之外的闭环字段：快照号 / 指纹 / 一句话 reason
        self.assertEqual(record["snapshot_id"], snap["snapshot_id"])
        self.assertEqual(record["dir_fingerprint"], snap["fingerprints"]["dir"])
        self.assertEqual(record["reason"], "示例：新版误删引用模板，回滚到上一版")
        # 记录原样在审计流里可查
        self.assertIn(record, ins.export_events())


class SnapshotBeforeInstallHandshake(AcceptanceBase):
    """先快照后安装衔接（T3 install_flow）：快照是安装的内嵌第一步。"""

    def test_snapshot_is_embedded_first_step_before_install_event(self):
        # 次序：T2 snapshot-taken 先于 T3 install-performed（同时钟可直比），
        # install-performed 携带的 snapshot_id 就是刚落袋的那份快照
        installed, snap, _ = self.full_rehearsal()
        taken = [e for e in ins.export_events() if e["event"] == "snapshot-taken"]
        performed = [e for e in flow.export_events()
                     if e["event"] == "install-performed"]
        self.assertEqual(len(taken), 1)
        self.assertEqual(len(performed), 1)
        self.assertLessEqual(taken[0]["at"], performed[0]["at"])
        self.assertEqual(performed[0]["snapshot_id"], snap["snapshot_id"])
        self.assertEqual(performed[0]["snapshot_taken_at"], snap["taken_at"])
        self.assertEqual(performed[0]["from_version"], OLD_VERSION)
        # 槽位里就是这份快照（调用方没有手动快照，快照由流程结构性保证）
        self.assertEqual(
            ins.latest_snapshot("example-skill")["snapshot_id"], snap["snapshot_id"])

    def test_denied_admission_no_snapshot_no_slot(self):
        # 安检管进门：admitted 非 True 直接拒绝——不快照、不安装、不占槽
        result = flow.install_with_snapshot(
            "example-skill", self.skill_dir, OLD_VERSION, "operator", DENIED)
        self.assertFalse(result["installed"])
        self.assertIsNone(result["snapshot"])
        self.assertFalse(result["rollback_available"])
        self.assertEqual(result["reason"], "admission_denied")
        self.assertEqual([e["event"] for e in flow.export_events()],
                         ["install-rejected"])
        self.assertEqual(ins.export_events(), [])  # T2 流零事件
        self.assertIsNone(ins.latest_snapshot("example-skill"))  # 槽位未被占用
        # 目录未被安装动作触碰（仍是旧版原样）
        self.assertEqual(read_tree(self.skill_dir), OLD_FILES)


class SingleSlotOverwrite(AcceptanceBase):
    """单槽覆盖：每技能恒只有一份"上一版"快照，覆盖事件入审计。"""

    def test_second_snapshot_overwrites_slot_and_audits(self):
        # 同技能连续两次安装：第二次快照覆盖旧槽，审计记 slot-overwritten
        first = flow.install_with_snapshot(
            "example-skill", self.skill_dir, OLD_VERSION, "operator", ADMITTED)
        write_tree(self.skill_dir, NEW_FILES)  # 第一次升级落盘
        mid_files = dict(NEW_FILES)
        second = flow.install_with_snapshot(
            "example-skill", self.skill_dir, NEW_VERSION, "operator", ADMITTED)
        self.assertTrue(second["installed"])
        # 槽位里只剩第二次的快照（"上一版"= 第一次升级后的新版内容）
        slot = ins.latest_snapshot("example-skill")
        self.assertEqual(slot["snapshot_id"], second["snapshot"]["snapshot_id"])
        self.assertNotEqual(slot["snapshot_id"], first["snapshot"]["snapshot_id"])
        self.assertEqual(slot["dir_files"], mid_files)
        self.assertEqual(slot["old_version"], NEW_VERSION)
        # 覆盖事件入审计：snapshot-taken → slot-overwritten → snapshot-taken
        self.assertEqual([e["event"] for e in ins.export_events()],
                         ["snapshot-taken", "slot-overwritten", "snapshot-taken"])
        overwritten = [e for e in ins.export_events()
                       if e["event"] == "slot-overwritten"][0]
        self.assertEqual(overwritten["kept_snapshot_id"], slot["snapshot_id"])
        self.assertEqual(overwritten["skill_name"], "example-skill")


class AuditEventSequence(AcceptanceBase):
    """审计序列：跨流事件链闭环、append-only、篡改 fail-close。"""

    def test_cross_stream_event_chain_closed_by_snapshot_id(self):
        # 全链事件序列：flow 流 [install-performed]；
        # ins 流 [snapshot-taken, rolled-back]，三方 snapshot_id 闭环
        installed, snap, record = self.full_rehearsal(actor="audit-example")
        flow_events = flow.export_events()
        ins_events = ins.export_events()
        self.assertEqual([e["event"] for e in flow_events], ["install-performed"])
        self.assertEqual([e["event"] for e in ins_events],
                         ["snapshot-taken", "rolled-back"])
        self.assertEqual(flow_events[0]["snapshot_id"], snap["snapshot_id"])
        self.assertEqual(ins_events[0]["snapshot_id"], snap["snapshot_id"])
        self.assertEqual(record["snapshot_id"], snap["snapshot_id"])
        # 时间序：快照 ≤ 安装 ≤ 回滚；事件可 JSON 序列化
        self.assertLessEqual(ins_events[0]["at"], flow_events[0]["at"])
        self.assertLessEqual(flow_events[0]["at"], record["at"])
        json.dumps(flow_events, ensure_ascii=False)
        json.dumps(ins_events, ensure_ascii=False)
        # append-only 视图：清掉导出副本不影响审计流
        ins_events.clear()
        self.assertEqual(len(ins.export_events()), 2)

    def test_tampered_snapshot_fail_close_no_rollback_record(self):
        # N-2 篡改快照被检出：verify failed 入审计、目录不被半还原、无成功回滚记录
        installed = flow.install_with_snapshot(
            "example-skill", self.skill_dir, OLD_VERSION, "operator", ADMITTED)
        snap = installed["snapshot"]
        write_tree(self.skill_dir, NEW_FILES)  # 新版已落盘（出问题待回滚）
        tampered = dict(snap)
        tampered["dir_files"] = dict(snap["dir_files"])
        tampered["dir_files"]["SKILL.md"] = (
            "---\nname: example-skill\nversion: 9.9.9\n---\n篡改\n")
        with self.assertRaises(ins.FingerprintMismatch):
            ins.restore(tampered, self.skill_dir,
                        from_version=NEW_VERSION, actor="operator")
        # 绝不静默半还原：目录仍是新版原样（篡改内容一个字节都没落盘）
        self.assertEqual(read_tree(self.skill_dir), NEW_FILES)
        failed = [e for e in ins.export_events() if e["event"] == "restore-failed"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["verify"], "failed")
        self.assertEqual(failed[0]["stage"], "snapshot_integrity")
        self.assertFalse(any(e["event"] == "rolled-back"
                             for e in ins.export_events()))

    def test_empty_dir_snapshot_refused(self):
        # 空目录拒绝：没有可回滚的"上一版"（多半是路径搞错），直接拒绝
        empty = self.base / "skills" / "empty-skill"
        empty.mkdir(parents=True)
        with self.assertRaises(ValueError) as ctx:
            ins.take_snapshot("empty-skill", empty, None)
        self.assertIn("empty", str(ctx.exception))
        # 安装入口同样 fail-close：快照异常 → 中止安装、不落盘
        result = flow.install_with_snapshot(
            "empty-skill", empty, None, "operator", ADMITTED)
        self.assertFalse(result["installed"])
        self.assertEqual(result["reason"], "snapshot_failed")
        self.assertEqual([e["event"] for e in flow.export_events()],
                         ["install-aborted"])
        self.assertEqual(ins.export_events(), [])


class ZeroNetworkAndSecrets(AcceptanceBase):
    """零网络 + 密钥扫描 + 确定性。"""

    def test_no_network_imports_and_rehearsal_runs_without_sockets(self):
        # 模块零网络 import；全流程在 socket 全封环境下照跑
        for module in (flow, ins):
            source = Path(module.__file__).read_text(encoding="utf-8")
            for marker in ("import socket", "import urllib", "import http.client",
                           "import requests", "urlopen", "ftplib", "smtplib",
                           "httpx"):
                self.assertNotIn(marker, source,
                                 f"零网络红线：{module.__name__} 源码含 {marker}")
        real_socket = socket_module.socket

        class _Blocked(real_socket):
            def __init__(self, *args, **kwargs):
                raise AssertionError("零网络红线：演练流程试图建 socket")

        socket_module.socket = _Blocked
        try:
            _, snap, record = self.full_rehearsal()
        finally:
            socket_module.socket = real_socket
        self.assertEqual(read_tree(self.skill_dir), OLD_FILES)
        self.assertEqual(record["verify"], "passed")
        self.assertEqual(record["to_version"], OLD_VERSION)

    def test_no_secret_markers_in_deliverables(self):
        # 密钥扫描：交付面（两模块源码 + 本测试 + T1 设计文档 + T4 审计测试）
        # 密钥标记与真实网段字样 0 命中；快照/回滚记录本体一并进扫描
        deliverables = [
            Path(flow.__file__), Path(ins.__file__), Path(__file__),
            REPO_ROOT / "docs" / "plans" / "2026-10-29-prd-279-install-snapshot.md",
            REPO_ROOT / "tests" / "test_prd279_t4_audit.py",
        ]
        blobs = [p.read_text(encoding="utf-8") for p in deliverables]
        _, snap, record = self.full_rehearsal()
        blobs.append(json.dumps(snap, ensure_ascii=False))
        blobs.append(json.dumps(record, ensure_ascii=False))
        blobs.append(json.dumps(ins.export_events(), ensure_ascii=False))
        blobs.append(json.dumps(flow.export_events(), ensure_ascii=False))
        for blob in blobs:
            for marker in SECRET_MARKERS:
                self.assertNotIn(marker, blob, f"疑似密钥标记: {marker}")
            for host_marker in REAL_HOST_MARKERS:
                self.assertNotIn(host_marker, blob, f"疑似真实主机/IP: {host_marker}")
        # 示例全虚构：本测试文件带虚构声明
        self.assertIn("虚构", blobs[2])

    def test_deterministic_full_rehearsal_fixed_clock(self):
        # 确定性：固定时钟下同一演练（同目录同内容重置重跑）跑两遍，
        # 两段事件流逐事件一致（含 snapshot_id 与回滚记录全字段）
        fixed_at = "2026-10-29T12:00:00+08:00"
        with mock.patch.object(flow, "_now", lambda: fixed_at), \
                mock.patch.object(ins, "_now", lambda: fixed_at):
            self.full_rehearsal()
            first = (json.dumps(flow.export_events(), ensure_ascii=False,
                                sort_keys=True),
                     json.dumps(ins.export_events(), ensure_ascii=False,
                                sort_keys=True))
            flow.reset_audit()
            ins.reset_audit()
            write_tree(self.skill_dir, OLD_FILES)  # 同一场景重置重跑
            self.full_rehearsal()
            second = (json.dumps(flow.export_events(), ensure_ascii=False,
                                 sort_keys=True),
                      json.dumps(ins.export_events(), ensure_ascii=False,
                                 sort_keys=True))
        self.assertEqual(first, second)
        self.assertIn(fixed_at, first[0])  # 时钟确实被钉住
        self.assertIn("iss-20261029-", first[1])  # 快照号与路径/时刻解耦


if __name__ == "__main__":
    unittest.main()
