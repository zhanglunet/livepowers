#!/usr/bin/env python3
"""PRD-172/T4：发行前强制走 PRD-171 对抗验收（trend #863）。

判定：role-packs/manifest.json 中状态为 published 的角色包，其成员 skill 的
acceptance.state 必须为 confirmed，或为 exempt 且 exempt_ref 指向工程门豁免
台账 EX- ID（清单 schema 口径：pending/confirmed/exempt/blocked，T1 §4.2；
safety 条目在 PRD-171 层不可豁免，此处不需要另设开关）。未通过即退出码 1
——「未通过不可进发行清单」的机器化。

零依赖（Python 3.9+ 标准库）；判定输入只读 manifest.json 与
scripts/adversarial_verify.py gate 的输出文件（不重复实现判定）。
"""
from __future__ import annotations

import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(REPO, "role-packs", "manifest.json")
ENGINEERING_EXEMPTIONS = os.path.join(
    REPO, "docs", "engineering-checklist", "exemptions.md")


def load_manifest(path: str = MANIFEST) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_exempt_refs(path: str = ENGINEERING_EXEMPTIONS) -> set:
    """从工程门豁免台账抓 EX- ID（登记在案即可，豁免有效性归工程门）。"""
    if not os.path.isfile(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return set(__import__("re").findall(r"EX-\d{2,}", f.read()))


def check_pack(pack: dict, exempt_refs: set | None = None) -> list:
    """返回违规清单（空 = 该包发行就绪）。"""
    exempt_refs = exempt_refs if exempt_refs is not None else load_exempt_refs()
    violations = []
    pack_name = pack.get("pack_id") or pack.get("name", "?")
    status = pack.get("status")
    if status != "published":
        return violations  # draft/审阅中的包不强制
    for skill in pack.get("skills", []):
        name = skill.get("name", "?")
        acc = skill.get("acceptance") or {}
        state = acc.get("state")
        if state == "confirmed":
            continue
        if state in ("exempt", "needs_validation"):
            # exempt 是清单 schema 口径（T1 §4.2）；needs_validation 兼容旧写法。
            ref = acc.get("exempt_ref")
            if not ref:
                violations.append(
                    f"{pack_name}/{name}: {state} 无 exempt_ref（须指向工程门豁免台账 EX- ID）")
            elif ref not in exempt_refs:
                violations.append(
                    f"{pack_name}/{name}: exempt_ref {ref} 未在豁免台账登记")
            continue
        # rejected / pending / 缺失
        violations.append(
            f"{pack_name}/{name}: acceptance.state={state or '缺失'}——"
            f"published 包成员必须 confirmed（PRD-171：非 confirmed 不可 published）")
    return violations


def main(argv=None) -> int:
    manifest_path = argv[0] if argv else MANIFEST
    manifest = load_manifest(manifest_path)
    exempt_refs = load_exempt_refs()
    packs = (manifest.get("packs")
             if isinstance(manifest.get("packs"), list)
             else manifest.get("role_packs", []))
    if packs is None and isinstance(manifest, dict):
        # manifest 顶层可能是 {packs: [...]} 或 {name: {...}} 的包映射
        packs = [v for v in manifest.values() if isinstance(v, dict) and "skills" in v]
    violations = []
    for pack in packs:
        violations.extend(check_pack(pack, exempt_refs))
    for v in violations:
        print("❌", v)
    if violations:
        print(f"\n发行就绪检查：{len(violations)} 项未过——published 包成员必须"
              "confirmed 或带有效 exempt_ref 的 exempt（PRD-171：非 confirmed 且无"
              "有效豁免不可 published）")
        return 1
    print("✅ 发行就绪检查：全部 published 包成员 acceptance 状态合规")
    return 0


if __name__ == "__main__":
    sys.exit(main())
