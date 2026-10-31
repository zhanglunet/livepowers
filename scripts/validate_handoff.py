#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-256/T2（trend #1281）：handoff-v1 交接合同机器校验入口。

校验 templates/pi-subagents/handoff.schema.json 对给定合同 JSON：
  用法: validate_handoff.py <handoff.json> [schema.json]
  退出码: 0 合法 / 1 非法（stdout 打出违规路径）

jsonschema 缺失时退化为内置最小校验（required 字段+枚举）——同样判 0/1。
零网络；虚构示例。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DEFAULT_SCHEMA = Path(__file__).resolve().parents[1] / "templates" / "pi-subagents" / "handoff.schema.json"


def builtin_validate(data: dict, schema: dict) -> list[str]:
    """jsonschema 不可用时的最小校验（required + enum + minItems）。"""
    errors: list[str] = []

    def check(obj, sch, path):
        for key in sch.get("required", []):
            if key not in obj:
                errors.append(f"{path}: 缺必填 {key}")
        props = sch.get("properties", {})
        for key, sub in props.items():
            if key not in obj:
                continue
            val = obj[key]
            p = f"{path}.{key}"
            if "enum" in sub and val not in sub["enum"]:
                errors.append(f"{p}: {val!r} 不在枚举 {sub['enum']}")
            if "const" in sub and val != sub["const"]:
                errors.append(f"{p}: 必须为 {sub['const']!r}")
            if "pattern" in sub and isinstance(val, str) and not re.match(sub["pattern"], val):
                errors.append(f"{p}: {val!r} 不匹配 {sub['pattern']}")
            if sub.get("type") == "array":
                if not isinstance(val, list):
                    errors.append(f"{p}: 应为数组")
                elif len(val) < sub.get("minItems", 0):
                    errors.append(f"{p}: 少于 {sub['minItems']} 项")
            if sub.get("type") == "object" and isinstance(val, dict):
                check(val, sub, p)
            if sub.get("type") == "string" and not isinstance(val, str):
                errors.append(f"{p}: 应为字符串")

    check(data, schema, "$")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) < 1:
        print("用法: validate_handoff.py <handoff.json> [schema.json]", file=sys.stderr)
        return 1
    data = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    schema_path = Path(argv[1]) if len(argv) > 1 else DEFAULT_SCHEMA
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        import jsonschema  # noqa: F401
        import jsonschema.validators

        validator = jsonschema.validators.Draft7Validator(schema)
        errors = [e.message for e in validator.iter_errors(data)]
    except ImportError:
        errors = builtin_validate(data, schema)
    if errors:
        for e in errors:
            print(f"invalid: {e}")
        return 1
    print("valid handoff-v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
