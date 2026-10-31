"""PRD-279/T2：技能安装/升级快照存储与回滚最小实现（install-snapshot-v1）。

trend issue #1397；设计文档 docs/plans/2026-10-29-prd-279-install-snapshot.md。
纯 stdlib、零网络、纯本地文件操作。与收录安检互补成完整生命周期：
**安检管进门、快照管退出**——本模块不产生任何放行语义，恢复不重扫：
旧版当初装进来时已过安检，恢复只是回到那个已过安检的状态；新版要再
进来仍须重新走 admission_flow（PRD-255，T3 衔接）。

- take_snapshot(skill_name, skill_dir, installed_manifest)  安装/升级落盘前
  强制调用：快照旧版技能目录全量文件（dir_files 内联，自足可恢复）、
  已装清单完整副本（manifest_snapshot）与逐文件/目录指纹；快照失败由
  调用方中止安装（fail-close：宁可装不上，不可回不去）；
- restore(snapshot, target_dir, from_version=..., actor=...)  目录级还原
  （整体对齐快照）+ 还原后目录指纹校验（不一致抛 FingerprintMismatch，
  绝不静默半还原）+「已回滚到某版」回滚记录（四要素必填：
  技能名 / 版本 from→to / 时间 / 触发者角色）；
- export_events()  审计事件查询（append-only，可 JSON 序列化）。

槽位：每技能只保留最近一次变更前的快照（"上一版"），同技能再次快照
覆盖旧槽（覆盖事件入审计）；不做多版本历史——更早状态靠 git 历史。

红线：安检管进门、快照管退出；fail-close；快照/记录零密钥零外联；
示例全虚构；文档与示例无真实内部主机名/IP/账号/密钥。
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path

SCHEMA = "install-snapshot-v1"

# 单槽快照存储：skill_name -> 该技能最近一次变更前的快照（"上一版"）
_SLOTS: dict = {}
# 审计事件（append-only，进程内）；export_events() 供审计查询
_EVENTS: list = []


class FingerprintMismatch(Exception):
    """目录指纹与快照记录不一致（fail-close，绝不静默半还原）。"""


def _canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _file_manifest(files_bytes: dict) -> list:
    """目录清单：按相对路径排序的 {path, sha256, bytes} 条目。"""
    return [
        {"path": rel, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
        for rel, data in sorted(files_bytes.items())
    ]


def dir_fingerprint(files_bytes: dict) -> str:
    """目录内容指纹：文件清单 canonical JSON 的 sha256（与顺序/时间戳无关）。"""
    return hashlib.sha256(_canonical_json(_file_manifest(files_bytes)).encode("utf-8")).hexdigest()


def _fingerprints(files: dict) -> dict:
    files_bytes = {rel: content.encode("utf-8") for rel, content in files.items()}
    return {
        "algorithm": "sha256-per-file",
        "files": {rel: hashlib.sha256(data).hexdigest() for rel, data in sorted(files_bytes.items())},
        "dir": dir_fingerprint(files_bytes),
    }


def _read_skill_files(skill_dir) -> dict:
    """读取技能目录全部文件为 {rel_path: text}（utf-8；技能文件是文本）。"""
    root = Path(skill_dir)
    if not root.is_dir():
        raise NotADirectoryError(f"skill dir not found: {skill_dir}")
    files = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        data = path.read_bytes()
        try:
            files[rel] = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"skill file is not utf-8 text: {rel}") from exc
    return files


def _old_version_from_manifest(installed_manifest, skill_name):
    """已装清单里该技能的版本（首次安装/无清单时为 None，change_kind: install）。"""
    if not isinstance(installed_manifest, dict):
        return None
    for entry in installed_manifest.get("skills") or []:
        if isinstance(entry, dict) and entry.get("name") == skill_name:
            return entry.get("version")
    return None


def take_snapshot(skill_name, skill_dir, installed_manifest=None) -> dict:
    """安装/升级落盘前强制调用：快照旧版技能目录 + 已装清单副本。

    空目录拒绝（空目录没有可回滚的"上一版"，多半是路径搞错）；
    installed_manifest 为机读已装清单 dict（installed-manifest-v1），
    快照内保存其完整副本——恢复时一并还原，防止"目录回去了、清单说
    新版还在"的漂移。同技能再次快照覆盖旧槽（覆盖事件入审计）。
    """
    if not isinstance(skill_name, str) or not skill_name:
        raise ValueError("skill_name must be a non-empty string")
    if installed_manifest is not None and not isinstance(installed_manifest, dict):
        raise TypeError("installed_manifest must be a dict (installed-manifest-v1)")
    files = _read_skill_files(skill_dir)
    if not files:
        raise ValueError(f"refusing to snapshot empty skill dir: {skill_dir}")
    taken_at = _now()
    fps = _fingerprints(files)
    old_version = _old_version_from_manifest(installed_manifest, skill_name)
    snap = {
        "schema": SCHEMA,
        "snapshot_id": f"iss-{taken_at[:10].replace('-', '')}-{fps['dir'][:8]}",
        "skill_name": skill_name,
        "skill_dir": str(skill_dir),
        "old_version": old_version,
        "change_kind": "upgrade" if old_version else "install",
        "dir_files": files,
        "manifest_snapshot": deepcopy(installed_manifest) if installed_manifest is not None else None,
        "fingerprints": fps,
        "taken_at": taken_at,
    }
    if skill_name in _SLOTS:
        _EVENTS.append({
            "event": "slot-overwritten",
            "at": taken_at,
            "skill_name": skill_name,
            "kept_snapshot_id": snap["snapshot_id"],
        })
    _SLOTS[skill_name] = snap
    _EVENTS.append({
        "event": "snapshot-taken",
        "at": taken_at,
        "schema": SCHEMA,
        "snapshot_id": snap["snapshot_id"],
        "skill_name": skill_name,
        "old_version": old_version,
        "change_kind": snap["change_kind"],
        "dir_fingerprint": fps["dir"],
        "file_count": len(files),
    })
    return snap


def latest_snapshot(skill_name):
    """槽位中该技能的最近一份快照（单槽；没有则 None）。"""
    return deepcopy(_SLOTS.get(skill_name))


def restore(snapshot, target_dir, *, from_version, actor="operator", reason="") -> dict:
    """从快照目录级还原技能到 target_dir，返回「已回滚到某版」回滚记录。

    from_version / actor 是回滚记录四要素之二（技能名与 to_version 取自
    快照、时间取还原时刻），由调用方如实提供；reason 必填一句话口径在
    T4 审计断言收口，这里可选记录。还原后重算目录指纹必须与快照一致，
    不一致抛 FingerprintMismatch 并把 verify: failed 记入审计——绝不
    静默半还原。恢复不重扫放行：槽位保留，新版再进仍须重新过安检。
    """
    if not isinstance(snapshot, dict) or snapshot.get("schema") != SCHEMA:
        raise ValueError(f"unsupported snapshot schema: "
                         f"{snapshot.get('schema') if isinstance(snapshot, dict) else type(snapshot)}")
    if not from_version:
        raise ValueError("from_version is required (回滚记录四要素：from→to)")
    files = snapshot.get("dir_files")
    if not isinstance(files, dict) or not files:
        raise ValueError("snapshot has no inline dir_files")
    expected = (snapshot.get("fingerprints") or {}).get("dir")
    skill_name = snapshot.get("skill_name")

    # 0) 快照自洽预检：被篡改的快照在落盘前即被拒（fail-close）
    precheck = _fingerprints(files)["dir"]
    if precheck != expected:
        _EVENTS.append({"event": "restore-failed", "at": _now(), "verify": "failed",
                        "stage": "snapshot_integrity", "skill_name": skill_name,
                        "expected": expected, "actual": precheck})
        raise FingerprintMismatch(
            f"snapshot integrity check failed: expected {expected}, got {precheck}")

    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    # 1) 逐文件还原（utf-8 编码写回，与快照逐字节等价）
    for rel in sorted(files):
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(files[rel].encode("utf-8"))
    # 2) 删除快照之外的多余文件（目录整体对齐快照；只删文件不删目录）
    removed = 0
    for path in target.rglob("*"):
        if path.is_file() and path.relative_to(target).as_posix() not in files:
            path.unlink()
            removed += 1
    # 3) 还原后重算目录指纹，必须与快照记录一致
    disk_fingerprint = _fingerprints(_read_skill_files(target))["dir"]
    if disk_fingerprint != expected:
        _EVENTS.append({"event": "restore-failed", "at": _now(), "verify": "failed",
                        "stage": "post_restore", "skill_name": skill_name,
                        "expected": expected, "actual": disk_fingerprint})
        raise FingerprintMismatch(
            f"post-restore fingerprint mismatch: expected {expected}, got {disk_fingerprint}")

    record = {
        "event": "rolled-back",
        "skill_name": skill_name,
        "from_version": from_version,
        "to_version": snapshot.get("old_version"),
        "at": _now(),
        "actor": actor,
        "snapshot_id": snapshot.get("snapshot_id"),
        "dir_fingerprint": expected,
        "files_restored": len(files),
        "extra_files_removed": removed,
        "verify": "passed",
    }
    if reason:
        record["reason"] = reason
    _EVENTS.append(record)
    return record


def export_events() -> list:
    """审计事件导出（append-only 视图，JSON 可序列化）。"""
    return [deepcopy(event) for event in _EVENTS]


def reset_audit() -> None:
    """清空进程内审计事件与快照槽位（仅供测试隔离；生产不调用）。"""
    _EVENTS.clear()
    _SLOTS.clear()
