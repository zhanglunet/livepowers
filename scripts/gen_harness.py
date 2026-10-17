#!/usr/bin/env python3
"""harness 生成器原型（PRD-013/T2）。

读 capability.yaml，用字符串模板生成一个最小可用的 agent harness：
    harness/<name>/cli.py          # argparse 分发 + --json + 错误码
    harness/<name>/SKILL.md        # frontmatter + Quick Start + 命令章节
    harness/<name>/capability.yaml # 输入原样存档（可追溯）

用法：
    gen_harness.py [-o OUTDIR] [--json] capability.yaml

退出码：0=成功，1=失败（校验/读写错误），2=用法错误（argparse 默认）。

仅用 Python 标准库。注意：本脚本**不依赖 PyYAML**，内含一个仅够解析
capability.yaml schema 的最小 YAML 子集解析器，其限制如下（超出会直接报错，
不会静默误读）：
  - 只认 2 空格缩进（tab、奇数缩进直接报错）；
  - 只支持 `key: value`、`key:`（嵌套块）、`- ` 列表项；
  - `#` 注释：行首或空白后的 # 才算注释（引号内的 # 保留）；
  - 标量：双引号/单引号字符串（含基本转义）、true/false、null/~、
    整数、浮点数，其余按原样当字符串；
  - 不支持：锚点/别名（&、*）、多行块标量（|、>)、流式集合（{}、[]）、
    跨行续行、复杂 key。capability.yaml 请按 docs/HARNESS-DESIGN.md §1 的
    风格手写（2 空格缩进、字符串加引号）。

原型约定（见 HARNESS-DESIGN.md §3 走查）：
  - 每个 command 默认是"记录"语义：把参数连同时间戳 append 到 jsonl；
  - 名为 recent 的命令（或显式 kind: recent）是"读取"语义：读最后 N 条，
    要求有一个名为 limit 的参数；
  - 第一期只支持 storage: jsonl（sqlite 待定，见设计文档 §5）。
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9-]+$")
ARG_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
DRAFT_LINE = "由 harness 生成器生成（草稿，需人工 review）"


# ---------------------------------------------------------------- YAML 子集
class YAMLError(Exception):
    """YAML 子集解析失败。"""


class CapabilityError(Exception):
    """capability.yaml 校验失败。"""


def _strip_comment(line):
    """去掉行尾注释。'#' 仅在行首或空白之后、且不在引号内时才算注释起止。"""
    in_single = in_double = False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "'" and not in_double:
            if in_single and i + 1 < len(line) and line[i + 1] == "'":
                i += 2  # '' 是单引号内的转义，不切换状态
                continue
            in_single = not in_single
        elif ch == '"' and not in_single:
            bs = 0
            j = i - 1
            while j >= 0 and line[j] == "\\":
                bs += 1
                j -= 1
            if bs % 2 == 0:
                in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            if i == 0 or line[i - 1] in (" ", "\t"):
                return line[:i]
        i += 1
    return line


def _parse_scalar(text, lineno):
    s = text.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        inner = s[1:-1]
        if s[0] == '"':
            inner = (inner.replace("\\\\", "\\").replace('\\"', '"')
                     .replace("\\n", "\n").replace("\\t", "\t"))
        else:
            inner = inner.replace("''", "'")
        return inner
    low = s.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low in ("null", "~", ""):
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _try_split_kv(content, lineno):
    """在引号外找 'key:'（冒号后须是空白或行尾），返回 (key, value) 或 None。"""
    in_single = in_double = False
    i = 0
    start = 0
    if content.startswith(("'", '"')):
        q = content[0]
        i = 1
        while i < len(content):
            if content[i] == "\\" and q == '"' :
                i += 2
                continue
            if content[i] == q:
                if q == "'" and i + 1 < len(content) and content[i + 1] == "'":
                    i += 2
                    continue
                break
            i += 1
        if i >= len(content):
            raise YAMLError(f"第 {lineno} 行：引号未闭合")
        start = i + 1
        # key 是引号字符串，冒号必须紧跟其后
        rest = content[start:].lstrip(" ")
        if not rest.startswith(":") or not (len(rest) == 1 or rest[1] in (" ", "\t")):
            return None
        key = _parse_scalar(content[: start], lineno)
        return key, rest[1:].strip()
    while i < len(content):
        ch = content[i]
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == ":" and not in_single and not in_double:
            if i + 1 == len(content) or content[i + 1] in (" ", "\t"):
                key = content[:i].strip()
                if not key:
                    return None
                return key, content[i + 1 :].strip()
        i += 1
    return None


def _parse_block(lines, i, indent):
    content = lines[i][1]
    if content == "-" or content.startswith("- "):
        return _parse_seq(lines, i, indent)
    return _parse_map(lines, i, indent)


def _parse_seq(lines, i, indent):
    items = []
    while i < len(lines):
        ind, content, lineno = lines[i]
        if ind != indent or not (content == "-" or content.startswith("- ")):
            break
        rest = content[1:].strip()
        i += 1
        if not rest:
            if i >= len(lines) or lines[i][0] <= indent:
                raise YAMLError(f"第 {lineno} 行：'-' 后缺少内容")
            node, i = _parse_block(lines, i, lines[i][0])
            items.append(node)
            continue
        kv = _try_split_kv(rest, lineno)
        if kv is None:
            items.append(_parse_scalar(rest, lineno))
            continue
        # '- key: value' 开头：把后续更深缩进行并入同一个 mapping
        j = i
        while j < len(lines) and lines[j][0] > indent:
            j += 1
        sub = [(indent + 2, rest, lineno)] + list(lines[i:j])
        node, nxt = _parse_map(sub, 0, indent + 2)
        if nxt != len(sub):
            raise YAMLError(f"第 {sub[nxt][2]} 行：列表项内有多余内容")
        items.append(node)
        i = j
    return items, i


def _parse_map(lines, i, indent):
    mapping = {}
    while i < len(lines):
        ind, content, lineno = lines[i]
        if ind != indent:
            break
        if content == "-" or content.startswith("- "):
            raise YAMLError(f"第 {lineno} 行：此处应为 key: value")
        kv = _try_split_kv(content, lineno)
        if kv is None:
            raise YAMLError(f"第 {lineno} 行：不是合法的 key: value")
        key, value = kv
        if key in mapping:
            raise YAMLError(f"第 {lineno} 行：重复的 key '{key}'")
        i += 1
        if value == "":
            if i < len(lines) and lines[i][0] > indent:
                node, i = _parse_block(lines, i, lines[i][0])
                mapping[key] = node
            else:
                mapping[key] = None
        else:
            mapping[key] = _parse_scalar(value, lineno)
    return mapping, i


def parse_yaml(text):
    """解析 YAML 子集，返回 Python 对象（顶层应为 dict）。"""
    lines = []
    for num, raw in enumerate(text.splitlines(), 1):
        code = _strip_comment(raw)
        if not code.strip():
            continue
        indent = len(code) - len(code.lstrip(" "))
        if code[:indent] != " " * indent:
            raise YAMLError(f"第 {num} 行：缩进含 tab，请用 2 空格缩进")
        if indent % 2 != 0:
            raise YAMLError(f"第 {num} 行：缩进必须是 2 的倍数（仅支持 2 空格缩进）")
        lines.append((indent, code.strip(), num))
    if not lines:
        raise YAMLError("空文档")
    node, nxt = _parse_block(lines, 0, 0)
    if nxt != len(lines):
        raise YAMLError(f"第 {lines[nxt][2]} 行：顶层有多余内容")
    if not isinstance(node, dict):
        raise YAMLError("顶层必须是 mapping（key: value）")
    return node


# ---------------------------------------------------------------- 校验
def _req_str(mapping, key, where):
    v = mapping.get(key)
    if not isinstance(v, str) or not v:
        raise CapabilityError(f"{where}: '{key}' 必填且为非空字符串")
    return v


def validate(spec):
    """校验 capability dict，返回规范化后的能力描述。失败抛 CapabilityError。"""
    allowed_top = {"name", "description", "version", "commands", "storage"}
    for k in spec:
        if k not in allowed_top:
            raise CapabilityError(f"顶层未知字段 '{k}'（允许：{sorted(allowed_top)}）")

    name = _req_str(spec, "name", "顶层")
    if not NAME_RE.match(name):
        raise CapabilityError(f"顶层: name '{name}' 必须匹配 ^[a-z0-9-]+$")
    description = _req_str(spec, "description", "顶层")
    version = spec.get("version", "")
    version = "" if version is None else str(version)
    if not version:
        raise CapabilityError("顶层: 'version' 必填")

    storage = spec.get("storage", "jsonl")
    if storage != "jsonl":
        raise CapabilityError(
            f"顶层: 第一期仅支持 storage: jsonl（sqlite 待定），当前为 '{storage}'"
        )

    commands = spec.get("commands")
    if not isinstance(commands, list) or not commands:
        raise CapabilityError("顶层: 'commands' 必填且至少 1 个")
    seen_cmds = set()
    norm_cmds = []
    for idx, cmd in enumerate(commands):
        where = f"commands[{idx}]"
        if not isinstance(cmd, dict):
            raise CapabilityError(f"{where}: 必须是 mapping")
        for k in cmd:
            if k not in {"name", "description", "args", "examples", "kind"}:
                raise CapabilityError(f"{where}: 未知字段 '{k}'")
        cname = _req_str(cmd, "name", where)
        if not NAME_RE.match(cname):
            raise CapabilityError(f"{where}: name '{cname}' 必须匹配 ^[a-z0-9-]+$")
        if cname in seen_cmds:
            raise CapabilityError(f"{where}: 重复的命令名 '{cname}'")
        seen_cmds.add(cname)
        cdesc = _req_str(cmd, "description", where)
        examples = cmd.get("examples")
        if not isinstance(examples, list) or not examples or not all(
            isinstance(e, str) and e for e in examples
        ):
            raise CapabilityError(f"{where}: 'examples' 至少 1 个非空字符串（没例子=没验收）")
        kind = cmd.get("kind")
        if kind is None:
            kind = "recent" if cname == "recent" else "record"
        if kind not in ("record", "recent"):
            raise CapabilityError(f"{where}: kind 只能是 record|recent，当前为 '{kind}'")

        norm_args = []
        seen_args = set()
        for aidx, arg in enumerate(cmd.get("args") or []):
            awhere = f"{where}.args[{aidx}]"
            if not isinstance(arg, dict):
                raise CapabilityError(f"{awhere}: 必须是 mapping")
            for k in arg:
                if k not in {"name", "help", "flag", "optional", "default"}:
                    raise CapabilityError(f"{awhere}: 未知字段 '{k}'")
            aname = _req_str(arg, "name", awhere)
            if not ARG_RE.match(aname):
                raise CapabilityError(
                    f"{awhere}: name '{aname}' 须是合法标识符（字母/数字/下划线，数字不开头）"
                )
            if aname in seen_args:
                raise CapabilityError(f"{awhere}: 重复的参数名 '{aname}'")
            seen_args.add(aname)
            is_flag = bool(arg.get("flag", False))
            is_optional = bool(arg.get("optional", False))
            default = arg.get("default")
            if default is not None:
                default = str(default)
            if is_flag and default is not None:
                raise CapabilityError(f"{awhere}: flag 参数不能设 default")
            if not is_flag and not is_optional and default is not None:
                raise CapabilityError(f"{awhere}: 位置参数不能设 default")
            norm_args.append(
                {
                    "name": aname,
                    "help": str(arg.get("help") or ""),
                    "flag": is_flag,
                    "optional": is_optional,
                    "default": default if default is not None else ("" if is_optional and not is_flag else None),
                }
            )
        if kind == "recent" and "limit" not in seen_args:
            raise CapabilityError(
                f"{where}: kind=recent 的命令需要一个名为 limit 的参数（原型约定）"
            )
        norm_cmds.append(
            {
                "name": cname,
                "func": "cmd_" + cname.replace("-", "_"),
                "description": cdesc,
                "examples": examples,
                "args": norm_args,
                "kind": kind,
            }
        )
    return {
        "name": name,
        "description": description,
        "version": version,
        "storage": storage,
        "commands": norm_cmds,
    }


# ---------------------------------------------------------------- 生成
def _py_str(s):
    """把字符串转成合法的 Python 字符串字面量（双引号风格）。"""
    return json.dumps(s, ensure_ascii=False)


def _gen_cli(cap):
    name = cap["name"]
    L = []
    A = L.append
    A("#!/usr/bin/env python3")
    A(f'"""{cap["description"]}')
    A(f"{DRAFT_LINE}。")
    A('"""')
    A("import argparse")
    A("import json")
    A("import sys")
    A("from datetime import datetime, timezone")
    A("from pathlib import Path")
    A("")
    A(f'DATA = Path(__file__).resolve().parent / {_py_str(name + ".jsonl")}')
    A("")
    for cmd in cap["commands"]:
        if cmd["kind"] == "record":
            A(f"def {cmd['func']}(args):")
            A("    entry = {")
            A('        "ts": datetime.now(timezone.utc).isoformat(),')
            A(f'        "command": {_py_str(cmd["name"])},')
            for a in cmd["args"]:
                A(f"        {_py_str(a['name'])}: args.{a['name']},")
            A("    }")
            A("    try:")
            A('        with open(DATA, "a", encoding="utf-8") as f:')
            A('            f.write(json.dumps(entry, ensure_ascii=False) + "\\n")')
            A("    except OSError as e:")
            A('        raise RuntimeError(f"写入 {DATA} 失败: {e}")')
            A("    if args.json:")
            A('        print(json.dumps({"ok": True, "recorded": entry}, ensure_ascii=False))')
            A("    else:")
            A('        print("recorded")')
            A("    return 0")
        else:  # recent
            A(f"def {cmd['func']}(args):")
            A("    try:")
            A("        limit = int(args.limit)")
            A("    except (TypeError, ValueError):")
            A('        raise RuntimeError(f"--limit 非法: {args.limit!r}")')
            A("    rows = []")
            A("    if DATA.exists():")
            A('        for line in DATA.read_text(encoding="utf-8").splitlines():')
            A("            line = line.strip()")
            A("            if line:")
            A("                rows.append(json.loads(line))")
            A("    rows = rows[-limit:] if limit > 0 else []")
            A("    if args.json:")
            A('        print(json.dumps({"ok": True, "rows": rows}, ensure_ascii=False))')
            A("    else:")
            A("        for r in rows:")
            A('            print(json.dumps(r, ensure_ascii=False))')
            A("    return 0")
        A("")
    A("def main(argv=None):")
    A("    common = argparse.ArgumentParser(add_help=False)")
    A('    common.add_argument("--json", action="store_true", help="机器可读输出（agent 用）")')
    A("    parser = argparse.ArgumentParser(")
    A(f"        prog={_py_str(name)},")
    A(f"        description={_py_str(cap['description'])},")
    A("        parents=[common],")
    A("    )")
    A('    sub = parser.add_subparsers(dest="command", required=True)')
    A("")
    for cmd in cap["commands"]:
        A(f"    p = sub.add_parser({_py_str(cmd['name'])}, help={_py_str(cmd['description'])},")
        A("        parents=[common])")
        for a in cmd["args"]:
            if a["flag"]:
                A(f"    p.add_argument('--{a['name']}', action='store_true', "
                  f"help={_py_str(a['help'])})")
            elif a["optional"]:
                A(f"    p.add_argument('--{a['name']}', default={_py_str(a['default'])}, "
                  f"help={_py_str(a['help'])})")
            else:
                A(f"    p.add_argument({_py_str(a['name'])}, help={_py_str(a['help'])})")
        A(f"    p.set_defaults(func={cmd['func']})")
        A("")
    A("    args = parser.parse_args(argv)")
    A("    try:")
    A("        return args.func(args)")
    A("    except BrokenPipeError:")
    A("        return 0")
    A("    except Exception as e:  # noqa: BLE001 —— 生成器模板统一出口，人工可收紧")
    A("        if args.json:")
    A('            print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))')
    A("        else:")
    A('            print(f"error: {e}", file=sys.stderr)')
    A("        return 1")
    A("")
    A('if __name__ == "__main__":')
    A("    sys.exit(main())")
    return "\n".join(L) + "\n"


def _gen_skillmd(cap):
    name = cap["name"]
    L = []
    A = L.append
    A("---")
    A(f"name: {name}")
    A(f"description: {_py_str(cap['description'])}")
    A("---")
    A(f"> {DRAFT_LINE}。")
    A("")
    A(f"# {name}")
    A("")
    A(cap["description"])
    A("")
    A("## 30 秒速览")
    A("")
    A("```bash")
    for cmd in cap["commands"][:2]:
        ex = cmd["examples"][0]
        if ex.startswith(name + " "):
            ex = ex[len(name) + 1 :]
        A(f"python3 harness/{name}/cli.py {ex}")
    A("```")
    A("")
    A("## 命令")
    A("")
    for cmd in cap["commands"]:
        A(f"### {cmd['name']} — {cmd['description']}")
        A("")
        A("```bash")
        for ex in cmd["examples"]:
            A(ex)
        A("```")
        A("")
        if cmd["args"]:
            A("| 参数 | 类型 | 说明 |")
            A("|---|---|---|")
            for a in cmd["args"]:
                if a["flag"]:
                    typ = "flag"
                elif a["optional"]:
                    typ = f"可选，默认 {a['default']}" if a["default"] else "可选"
                else:
                    typ = "位置参数"
                cell = f"--{a['name']}" if (a["flag"] or a["optional"]) else a["name"]
                A(f"| {cell} | {typ} | {a['help']} |")
            A("")
    A("退出码：`0`=成功，`1`=失败，`2`=用法错误。加 `--json` 得机器可读输出。")
    A("")
    A("---")
    A("*本文件由 harness 生成器生成（草稿，需人工 review 后使用）。*")
    return "\n".join(L) + "\n"


def generate(cap, outdir):
    """生成 harness/<name>/ 下的三个文件，返回相对路径列表。"""
    dest = Path(outdir) / "harness" / cap["name"]
    dest.mkdir(parents=True, exist_ok=True)
    written = []
    cli_path = dest / "cli.py"
    cli_path.write_text(_gen_cli(cap), encoding="utf-8")
    os.chmod(cli_path, 0o755)
    written.append(cli_path)
    skill_path = dest / "SKILL.md"
    skill_path.write_text(_gen_skillmd(cap), encoding="utf-8")
    written.append(skill_path)
    return [str(p) for p in written]


def _emit_ok(as_json, payload):
    if as_json:
        print(json.dumps({"ok": True, **payload}, ensure_ascii=False))
    else:
        for line in payload.get("lines", []):
            print(line)
    return 0


def _emit_fail(as_json, message):
    if as_json:
        print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))
    else:
        print(f"error: {message}", file=sys.stderr)
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="gen_harness.py",
        description="从 capability.yaml 生成 harness 原型（cli.py + SKILL.md），仅用标准库。",
    )
    ap.add_argument("capability", help="capability.yaml 路径")
    ap.add_argument(
        "-o",
        "--outdir",
        default=".",
        help="输出根目录（默认当前目录），生成物放在 <outdir>/harness/<name>/",
    )
    ap.add_argument("--json", action="store_true", help="机器可读输出")
    args = ap.parse_args(argv)

    try:
        text = Path(args.capability).read_text(encoding="utf-8")
    except OSError as e:
        return _emit_fail(args.json, f"读取 capability.yaml 失败: {e}")
    try:
        spec = parse_yaml(text)
    except YAMLError as e:
        return _emit_fail(args.json, f"YAML 解析失败: {e}")
    try:
        cap = validate(spec)
    except CapabilityError as e:
        return _emit_fail(args.json, f"capability.yaml 校验失败: {e}")
    try:
        files = generate(cap, args.outdir)
        # 输入原样存档
        archive = Path(args.outdir) / "harness" / cap["name"] / "capability.yaml"
        archive.write_bytes(Path(args.capability).read_bytes())
        files.append(str(archive))
    except OSError as e:
        return _emit_fail(args.json, f"写入生成物失败: {e}")

    rel = [str(Path(f).relative_to(args.outdir)) for f in files]
    return _emit_ok(
        args.json,
        {
            "name": cap["name"],
            "version": cap["version"],
            "outdir": str(args.outdir),
            "files": rel,
            "lines": [
                f"已生成 harness/{cap['name']}/（{len(files)} 个文件）：",
                *[f"  - {r}" for r in rel],
            ],
        },
    )


if __name__ == "__main__":
    sys.exit(main())
