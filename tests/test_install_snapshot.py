"""PRD-279/T2：scripts/install_snapshot.py 的单元测试。

验收口径（trend #1397）：样例可快照可回滚，审计可查，有测试。
虚构技能 example-skill（v0.3.1 → v0.4.0）全样本，不落真实数据。
安检管进门、快照管退出：本模块测试不涉及任何放行语义。
"""
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "install_snapshot.py"
_spec = importlib.util.spec_from_file_location("install_snapshot", SCRIPT)
ins = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ins)

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
    # v0.4.0 误删了 references/template.md
}

MANIFEST = {
    "schema": "installed-manifest-v1",
    "generated_at": "2026-10-29T10:00:00+08:00",
    "skills": [
        {"name": "example-skill", "version": OLD_VERSION,
         "source": "marketplace", "installed_at": "2026-10-20T08:00:00+08:00"},
        {"name": "other-example-skill", "version": "1.0.0",
         "source": "local", "installed_at": "2026-10-21T08:00:00+08:00"},
    ],
}

OTHER_FILES = {"SKILL.md": "---\nname: other-example-skill\nversion: 1.0.0\n---\n"}


def write_tree(root, files):
    """把 root 同步成 files 的内容（不在 files 里的既有文件删掉）。"""
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


class InstallSnapshotTest(unittest.TestCase):
    def setUp(self):
        ins.reset_audit()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name)
        self.skill_dir = self.base / "skills" / "example-skill"
        write_tree(self.skill_dir, OLD_FILES)

    def tearDown(self):
        ins.reset_audit()

    def test_snapshot_fields_complete(self):
        snap = ins.take_snapshot("example-skill", self.skill_dir, MANIFEST)
        self.assertEqual(snap["schema"], "install-snapshot-v1")
        self.assertEqual(snap["skill_name"], "example-skill")
        self.assertEqual(snap["old_version"], OLD_VERSION)
        self.assertEqual(snap["change_kind"], "upgrade")
        self.assertEqual(snap["dir_files"], OLD_FILES)          # 还原数据内联自足
        self.assertEqual(snap["manifest_snapshot"], MANIFEST)   # 已装清单完整副本
        self.assertTrue(snap["snapshot_id"].startswith("iss-"))
        self.assertTrue(snap["taken_at"])
        fps = snap["fingerprints"]
        self.assertEqual(fps["algorithm"], "sha256-per-file")
        self.assertEqual(len(fps["dir"]), 64)
        self.assertEqual(fps["files"]["SKILL.md"],
                         hashlib.sha256(OLD_FILES["SKILL.md"].encode()).hexdigest())
        # 深拷贝：快照后改动原清单不影响快照副本
        MANIFEST["skills"][0]["version"] = NEW_VERSION
        self.assertEqual(snap["manifest_snapshot"]["skills"][0]["version"], OLD_VERSION)
        MANIFEST["skills"][0]["version"] = OLD_VERSION

    def test_fingerprint_deterministic(self):
        a = ins.take_snapshot("example-skill", self.skill_dir, MANIFEST)
        twin = self.base / "twin" / "example-skill"
        write_tree(twin, OLD_FILES)
        b = ins.take_snapshot("twin-slot", twin, MANIFEST)
        # 同内容不同目录/时间：目录指纹一致（与路径、时间戳无关）
        self.assertEqual(a["fingerprints"]["dir"], b["fingerprints"]["dir"])
        changed = self.base / "changed" / "example-skill"
        write_tree(changed, {**OLD_FILES,
                             "references/template.md": "示例引用模板 v0.3.1 改一字节\n"})
        c = ins.take_snapshot("changed-slot", changed, MANIFEST)
        self.assertNotEqual(a["fingerprints"]["dir"], c["fingerprints"]["dir"])

    def test_restore_dir_identical(self):
        snap = ins.take_snapshot("example-skill", self.skill_dir, MANIFEST)
        write_tree(self.skill_dir, NEW_FILES)  # 升级落盘：改 SKILL.md、删引用模板
        self.assertEqual(read_tree(self.skill_dir), NEW_FILES)
        record = ins.restore(snap, self.skill_dir, from_version=NEW_VERSION, actor="operator")
        # 目录级还原：新版删掉的文件回来、目录与快照逐文件一致
        self.assertEqual(read_tree(self.skill_dir), OLD_FILES)
        # 还原后重算指纹与快照一致
        disk = ins._fingerprints(read_tree(self.skill_dir))["dir"]
        self.assertEqual(disk, snap["fingerprints"]["dir"])

    def test_rollback_record_four_elements(self):
        snap = ins.take_snapshot("example-skill", self.skill_dir, MANIFEST)
        write_tree(self.skill_dir, NEW_FILES)
        record = ins.restore(snap, self.skill_dir,
                             from_version=NEW_VERSION, actor="operator",
                             reason="新版误删引用模板，恢复上一版")
        # 四要素：技能名 / 版本（from→to）/ 时间 / 触发者，缺一不可
        self.assertEqual(record["event"], "rolled-back")
        self.assertEqual(record["skill_name"], "example-skill")
        self.assertEqual(record["from_version"], NEW_VERSION)
        self.assertEqual(record["to_version"], OLD_VERSION)
        self.assertTrue(record["at"])
        self.assertEqual(record["actor"], "operator")
        self.assertEqual(record["verify"], "passed")
        self.assertIn(record, ins.export_events())

    def test_single_slot_overwrite(self):
        first = ins.take_snapshot("example-skill", self.skill_dir, MANIFEST)
        write_tree(self.skill_dir, NEW_FILES)
        second = ins.take_snapshot("example-skill", self.skill_dir, MANIFEST)
        # 单槽：同技能再次快照覆盖旧槽，只留"上一版"，不做多版本历史
        self.assertEqual(ins.latest_snapshot("example-skill"), second)
        self.assertNotEqual(ins.latest_snapshot("example-skill"), first)
        overwritten = [e for e in ins.export_events() if e["event"] == "slot-overwritten"]
        self.assertEqual(len(overwritten), 1)
        # 不同技能槽位互不覆盖
        other_dir = self.base / "skills" / "other-example-skill"
        write_tree(other_dir, OTHER_FILES)
        ins.take_snapshot("other-example-skill", other_dir, MANIFEST)
        self.assertEqual(ins.latest_snapshot("example-skill"), second)
        self.assertEqual(ins.latest_snapshot("other-example-skill")["skill_name"],
                         "other-example-skill")

    def test_events_serializable(self):
        snap = ins.take_snapshot("example-skill", self.skill_dir, MANIFEST)
        write_tree(self.skill_dir, NEW_FILES)
        ins.restore(snap, self.skill_dir, from_version=NEW_VERSION, actor="operator")
        events = ins.export_events()
        json.dumps(events, ensure_ascii=False)  # 全部事件可 JSON 序列化
        self.assertEqual([e["event"] for e in events],
                         ["snapshot-taken", "rolled-back"])
        self.assertEqual(events[0]["change_kind"], "upgrade")
        # 导出的是副本：改导出结果不影响进程内审计（append-only 视图）
        events.clear()
        self.assertTrue(ins.export_events())

    def test_empty_dir_rejected(self):
        empty = self.base / "skills" / "empty-example-skill"
        empty.mkdir(parents=True)
        with self.assertRaises(ValueError):
            ins.take_snapshot("empty-example-skill", empty, MANIFEST)
        with self.assertRaises(NotADirectoryError):
            ins.take_snapshot("missing-example-skill", self.base / "no-such-dir", MANIFEST)
        # 拒绝后不占槽位、不留事件
        self.assertIsNone(ins.latest_snapshot("empty-example-skill"))
        self.assertEqual([e for e in ins.export_events() if e["event"] == "snapshot-taken"], [])

    def test_restore_fingerprint_mismatch(self):
        snap = ins.take_snapshot("example-skill", self.skill_dir, MANIFEST)
        tampered = dict(snap, dir_files={**snap["dir_files"],
                                         "SKILL.md": snap["dir_files"]["SKILL.md"] + "被篡改的一行\n"})
        with self.assertRaises(ins.FingerprintMismatch):
            ins.restore(tampered, self.skill_dir, from_version=NEW_VERSION, actor="operator")
        # 目录未被半还原；审计记 restore-failed 且没有成功回滚记录
        self.assertEqual(read_tree(self.skill_dir), OLD_FILES)
        events = ins.export_events()
        self.assertEqual([e for e in events if e["event"] == "rolled-back"], [])
        self.assertTrue(any(e["event"] == "restore-failed" and e["verify"] == "failed"
                            for e in events))

    def test_first_install_no_manifest_entry(self):
        # 首次安装：清单里没有该技能（或暂无清单）——old_version 为 None，change_kind: install
        no_entry = {"schema": "installed-manifest-v1", "generated_at": "2026-10-29T10:00:00+08:00",
                    "skills": MANIFEST["skills"][:1]}
        snap = ins.take_snapshot("brand-new-example-skill", self.skill_dir, no_entry)
        self.assertIsNone(snap["old_version"])
        self.assertEqual(snap["change_kind"], "install")
        snap2 = ins.take_snapshot("another-new-example-skill", self.skill_dir, None)
        self.assertIsNone(snap2["old_version"])
        self.assertIsNone(snap2["manifest_snapshot"])


if __name__ == "__main__":
    unittest.main()
