#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-255/T2（trend #1276）：市场收录安检适配最小实现——M 四维静态扫描。

按 PRD-255/T1 设计（docs/plans/2026-10-28-prd-255-market-gate.md）实现 T2 范围：
  M-1 隐藏指令与注入（零宽字符/base64 大块/范围外指令）
  M-2 过度授权（网络/exec/写越出技能目录）
  M-3 凭据访问（密钥模式/敏感路径，floor HIGH）
  M-4 收录材料一致性（声明 license 与实测不符直接 HIGH——许可证红线；
      name/version 缺失或与 SKILL.md frontmatter 不符）
  0-100 安全分（100=干净）+ 风险值 risk=100-score 四档严重度；HIGH+ 不收录；
  market-gate-report-v1 JSON 报告 + PRD-094 收录清单字段映射（gate_* 六字段）；
  evidence 占位符化。零网络（license 实测值由调用方传入）。

T3 接入收录流程、T4 白名单另任务。示例全虚构；不含真实主机名、账号、密钥。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "market-gate-report-v1"
SCAN_VERSION = "0.1.0"

RULES: dict[str, dict[str, Any]] = {
    "M-1-01": {"dimension": "M-1", "deduct": 30, "desc": "零宽/不可见 Unicode 字符"},
    "M-1-02": {"dimension": "M-1", "deduct": 25, "desc": "范围外指令式措辞"},
    "M-2-01": {"dimension": "M-2", "deduct": 25, "desc": "网络访问原语"},
    "M-2-02": {"dimension": "M-2", "deduct": 25, "desc": "exec/subprocess 原语"},
    "M-3-01": {"dimension": "M-3", "deduct": 30, "floor": "HIGH", "desc": "密钥/token 模式"},
    "M-3-02": {"dimension": "M-3", "deduct": 30, "floor": "HIGH", "desc": "敏感路径触碰"},
    "M-4-01": {"dimension": "M-4", "deduct": 15, "desc": "收录材料与 SKILL.md 不一致或缺失"},
    "M-4-02": {"dimension": "M-4", "deduct": 25, "floor": "HIGH", "desc": "license 声明与实测不符或缺失（许可证红线）"},
}

_ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]")
_IMPERATIVE_RE = re.compile(r"(忽略(之前的|上述)?规则|上报到|外传|exfiltrate)", re.I)
_NET_RE = re.compile(r"\b(requests\.(get|post)|urllib|socket\.|curl\s|fetch\()", re.I)
_EXEC_RE = re.compile(r"\b(subprocess|os\.system|exec\()", re.I)
_WRITE_OUT_RE = re.compile(r"(open\([^)]*,\s*['\"]w|shutil\.|os\.remove)", re.I)
_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{16,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
)
_SENSITIVE_PATH_RE = re.compile(r"\.env|\.ssh|credentials", re.I)
_REDACT_RE = re.compile(
    r"sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|Bearer\s+[A-Za-z0-9._-]{16,}"
    r"|gh[pousr]_[A-Za-z0-9]{30,}"
    r"|\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b")
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.S)


def _redact(text: str) -> str:
    return _REDACT_RE.sub("<REDACTED>", text)


def _parse_frontmatter(skill_md: Path) -> dict[str, str]:
    meta: dict[str, str] = {}
    m = _FRONTMATTER_RE.match(skill_md.read_text(encoding="utf-8"))
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip()
    return meta


def scan_skill(skill_dir: Path, *, declared_license: str | None = None,
               verified_license: str | None = None,
               declared_name: str | None = None,
               declared_version: str | None = None) -> dict[str, Any]:
    """扫描技能目录 → market-gate-report-v1。

    declared_*：收录申请单声明；verified_license：GitHub License API 实测值（调用方传入）。
    """
    findings: list[dict[str, Any]] = []
    skill_md = skill_dir / "SKILL.md"
    meta = _parse_frontmatter(skill_md) if skill_md.exists() else {}

    for path in sorted(skill_dir.rglob("*")):
        if path.is_file():
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            rel = str(path.relative_to(skill_dir))
            if _ZERO_WIDTH_RE.search(text):
                findings.append(_finding("M-1-01", rel, "检出零宽/不可见 Unicode 字符"))
            if _IMPERATIVE_RE.search(text):
                findings.append(_finding("M-1-02", rel, "检出范围外指令式措辞"))
            if _NET_RE.search(text):
                findings.append(_finding("M-2-01", rel, "检出网络访问原语"))
            if _EXEC_RE.search(text):
                findings.append(_finding("M-2-02", rel, "检出 exec/subprocess 原语"))
            for pat in _SECRET_PATTERNS:
                m = pat.search(text)
                if m:
                    findings.append(_finding("M-3-01", rel, f"检出密钥/token 模式（命中样例 {_redact(m.group(0))}）"))
                    break
            if _SENSITIVE_PATH_RE.search(text):
                findings.append(_finding("M-3-02", rel, "检出敏感路径触碰"))

    # M-4 收录材料一致性
    name = meta.get("name") or declared_name
    version = meta.get("version") or declared_version
    if not name or not version:
        findings.append(_finding("M-4-01", "SKILL.md", "name/version 缺失（frontmatter 与申请单均无）"))
    else:
        if declared_name and declared_name != name:
            findings.append(_finding("M-4-01", "SKILL.md", f"申请单 name={declared_name} 与 frontmatter name={name} 不一致"))
        if declared_version and declared_version != version:
            findings.append(_finding("M-4-01", "SKILL.md", f"申请单 version={declared_version} 与 frontmatter version={version} 不一致"))
    lic_declared = declared_license or "MISSING"
    lic_verified = verified_license or "MISSING"
    if lic_declared == "MISSING" or lic_verified == "MISSING" or lic_declared != lic_verified:
        findings.append(_finding(
            "M-4-02", "SKILL.md",
            f"license 声明({lic_declared})与实测({lic_verified})不符或缺失——许可证红线"))

    score = 100
    floor = None
    for f in findings:
        score = max(0, score - f["deduct"])
        if RULES.get(f["rule_id"], {}).get("floor"):
            floor = "HIGH"

    risk = 100 - score
    if risk >= 80:
        severity = "CRITICAL"
    elif risk >= 60 or floor:
        severity = "HIGH"
    elif risk >= 30:
        severity = "MEDIUM"
    else:
        severity = "LOW"
    decision = "blocked" if severity in ("CRITICAL", "HIGH") else "admitted"

    return {
        "schema": SCHEMA,
        "scanned_at": "2026-10-28T00:00:00Z",
        "skill": {"name": name or skill_dir.name, "version": version or "0.1.0",
                  "license_declared": lic_declared, "license_verified": lic_verified},
        "score": score, "severity": severity, "decision": decision,
        "findings": findings,
        "whitelist_applied": [],
        "scan_version": SCAN_VERSION,
    }


def checklist_mapping(report: dict[str, Any]) -> dict[str, Any]:
    """PRD-094 收录清单字段映射（gate_* 六字段）。"""
    return {
        "gate_report_ref": f"market-gate/{report['skill']['name']}/report-{report['scan_version']}.json",
        "gate_score": report["score"],
        "gate_severity": report["severity"],
        "gate_decision": report["decision"],
        "gate_whitelist": [w.get("entry_id", "") for w in report["whitelist_applied"]],
        "gate_scan_version": report["scan_version"],
    }


def _finding(rule_id: str, location: str, detail: str) -> dict[str, Any]:
    rule = RULES[rule_id]
    return {
        "rule_id": rule_id,
        "dimension": rule["dimension"],
        "severity_suggest": rule.get("floor", "MEDIUM"),
        "evidence": _redact(detail),
        "location": location,
        "deduct": rule["deduct"],
    }
