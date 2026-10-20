#!/usr/bin/env python3
"""链式 skill 运行器原型（PRD-095/T2；定稿口径 2A：先独立脚本原型，稳定后并入 lp chain）。

读 skills/<chain>/chain.yaml，按段契约编排执行一条链：

    chain_runner.py validate <chain> [--repo-root DIR] [--json]
    chain_runner.py run <chain> [--workspace DIR] [--param k=v ...]
                        [--run-id ID] [--from STAGE] [--skip STAGE ...]
                        [--approve] [--by NAME] [--json]
    chain_runner.py status <run-id> [--workspace DIR] [--json]

<chain> 是含 chain.yaml 的目录（或 chain.yaml 文件本身）。
运行产物落在 <workspace>/.livepowers/chains/<chain>/runs/<run-id>/：
每段一个子目录，含产物文件与 manifest.json；下游只读上游 manifest
中按名声明的产物（并验 sha256），不猜目录结构。

退出码：0=成功；1=失败（段失败 / 校验失败 / 非法跳段 / 验收门未确认）；
        2=用法错误（argparse、参数缺失、chain.yaml 结构错误）；
        3=停在人工验收门 awaiting（T1 §3.3）；
        4=上游产物缺失或契约不满足（T1 §3.3 新增）。

仅用 Python 标准库，不依赖 PyYAML：内含一个只够解析 chain.yaml 的
YAML 子集解析器，限制与 scripts/gen_harness.py 的解析器一致：
  - 只认 2 空格缩进（tab、奇数缩进直接报错）；
  - 只支持 `key: value`、`key:`（嵌套块）、`- ` 列表项；
  - `#` 注释：行首或空白后的 # 才算注释（引号内的 # 保留）；
  - 标量：双引号/单引号字符串、true/false、null/~、整数、浮点数，
    其余按原样当字符串；
  - 不支持：锚点/别名（&、*）、流式集合（{}、[]）、多行块标量（|、>），
    超出直接报错，不静默误读。chain.yaml 请按 T1 §2.4 风格手写。

产物口径（定稿 4B）：≤100KB 全量落盘在段目录内；大于阈值的产物移出
运行目录，登记到 .livepowers/chains/<chain>/large/<run-id>/<stage>/，
manifest 只记路径 + sha256 + 大小（stored: external）。

原型边界（重要）：段的真实执行——Agent 按各段 SKILL.md 干活——不在
本脚本内。本脚本内置「模拟执行器」，按段契约生成占位产物与 manifest，
只验证编排、契约、gate 与续跑语义。段 params 中的 {param} 占位在原型
中体现为模拟执行器读取 params 并记入 manifest；真实段调用命令的占位
替换待接入真实执行器时实现。测试钩子（仅测试用，勿写进正式链）：
params.simulate=fail 让该段模拟执行必失败；params.pad_bytes=N 把首个
产物填充到约 N 字节，用于验证大文件登记口径。
"""

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9-]+$")
LARGE_ARTIFACT_BYTES = 100 * 1024  # 定稿口径 4B 的阈值：≤100KB 全量落盘

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_AWAITING = 3
EXIT_MISSING = 4


class ChainError(Exception):
    """链运行/校验失败，带退出码。"""

    def __init__(self, msg, code=EXIT_FAIL):
        super().__init__(msg)
        self.code = code


class YamlError(Exception):
    """YAML 子集解析失败。"""


class SimFail(Exception):
    """模拟执行器报告的段失败。"""


# ---------------------------------------------------------------- YAML 子集
def _strip_comment(line):
    """去掉行尾注释。'#' 仅在行首或空白之后、且不在引号内时才算注释。"""
    in_single = in_double = False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "'" and not in_double:
            if in_single and i + 1 < len(line) and line[i + 1] == "'":
                i += 2
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
    if not s:
        return None
    if s[0] in "[{&*|>":
        raise YamlError(
            "第 %d 行：不支持流式集合/锚点/块标量（%s…），"
            "请按 chain.yaml 子集风格手写" % (lineno, s[:12]))
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
    if low in ("null", "~"):
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


def _split_kv(content, lineno):
    """在引号外找 'key:'（冒号后须是空白或行尾），返回 (key, rest) 或 None。"""
    in_single = in_double = False
    i = 0
    while i < len(content):
        ch = content[i]
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            if content[i - 1] != "\\":
                in_double = not in_double
        elif ch == ":" and not in_single and not in_double:
            if i + 1 == len(content) or content[i + 1] == " ":
                return content[:i].strip(), content[i + 1:].strip()
        i += 1
    return None


def _tokenize(text):
    lines = []
    for n, raw in enumerate(text.splitlines(), 1):
        indent_str = raw[:len(raw) - len(raw.lstrip())]
        if "\t" in indent_str:
            raise YamlError("第 %d 行：缩进含 tab，只认 2 空格缩进" % n)
        stripped = _strip_comment(raw).rstrip()
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        if indent % 2:
            raise YamlError("第 %d 行：奇数缩进，只认 2 空格缩进" % n)
        lines.append((indent, stripped.strip(), n))
    return lines


def _parse_block(lines, i, indent):
    if i >= len(lines) or lines[i][0] != indent:
        raise YamlError("第 %d 行附近：缩进结构错误" % (lines[i][2] if i < len(lines) else -1))
    if lines[i][1] == "-" or lines[i][1].startswith("- "):
        return _parse_list(lines, i, indent)
    return _parse_map(lines, i, indent)


def _parse_list(lines, i, indent):
    out = []
    while i < len(lines) and lines[i][0] == indent and (
            lines[i][1] == "-" or lines[i][1].startswith("- ")):
        content = lines[i][1][1:].strip()
        lineno = lines[i][2]
        if not content:
            j = i + 1
            if j < len(lines) and lines[j][0] > indent:
                val, i = _parse_block(lines, j, lines[j][0])
                out.append(val)
            else:
                out.append(None)
                i += 1
        elif _split_kv(content, lineno) is not None:
            item_indent = indent + 2
            sub = [(item_indent, content, lineno)]
            j = i + 1
            while j < len(lines) and lines[j][0] >= item_indent:
                sub.append(lines[j])
                j += 1
            val, used = _parse_map(sub, 0, item_indent)
            if used != len(sub):
                raise YamlError("第 %d 行附近：列表项结构解析不完整" % lineno)
            out.append(val)
            i = j
        else:
            out.append(_parse_scalar(content, lineno))
            i += 1
    return out, i


def _parse_map(lines, i, indent):
    out = {}
    while i < len(lines) and lines[i][0] == indent and not (
            lines[i][1] == "-" or lines[i][1].startswith("- ")):
        content, lineno = lines[i][1], lines[i][2]
        kv = _split_kv(content, lineno)
        if kv is None:
            raise YamlError("第 %d 行：期望 'key: value'，得到 %r" % (lineno, content))
        key, rest = kv
        if len(key) >= 2 and key[0] == key[-1] and key[0] in ("'", '"'):
            key = _parse_scalar(key, lineno)
        if key in out:
            raise YamlError("第 %d 行：键重复：%s" % (lineno, key))
        if rest:
            out[key] = _parse_scalar(rest, lineno)
            i += 1
        else:
            j = i + 1
            if j < len(lines) and lines[j][0] > indent:
                val, i = _parse_block(lines, j, lines[j][0])
                out[key] = val
            else:
                out[key] = None
                i += 1
    return out, i


def parse_chain_yaml(text):
    lines = _tokenize(text)
    if not lines:
        raise YamlError("空文件")
    obj, used = _parse_block(lines, 0, lines[0][0])
    if used != len(lines):
        raise YamlError("第 %d 行附近：解析未消费全部内容" % lines[used][2])
    if not isinstance(obj, dict):
        raise YamlError("chain.yaml 顶层必须是映射")
    return obj


# ---------------------------------------------------------------- 链加载与校验
def load_chain(chain_arg):
    p = Path(chain_arg)
    if p.is_file():
        chain_file, chain_dir = p, p.parent
    else:
        chain_dir, chain_file = p, p / "chain.yaml"
    if not chain_file.exists():
        raise ChainError("找不到链描述文件：%s" % chain_file, EXIT_FAIL)
    try:
        data = parse_chain_yaml(chain_file.read_text(encoding="utf-8"))
    except YamlError as e:
        raise ChainError("chain.yaml 结构错误：%s" % e, EXIT_USAGE)
    return chain_dir, data


def resolve_repo_root(chain_dir, explicit):
    if explicit:
        return Path(explicit)
    if chain_dir.parent.name == "skills":
        return chain_dir.parent.parent
    return Path.cwd()


def validate_chain(data, chain_dir, repo_root):
    """返回错误字符串列表（空 = 通过）。收集全部问题，不首错即停。"""
    errors = []
    name = data.get("name")
    if not isinstance(name, str) or not NAME_RE.match(name or ""):
        errors.append("name 缺失或不合 kebab-case 规范：%r" % (name,))
    elif Path(chain_dir).name != name:
        errors.append("name 与目录名不一致：name=%s，目录=%s" % (name, Path(chain_dir).name))
    if not data.get("description"):
        errors.append("description 缺失")

    chain_inputs = []
    for item in data.get("inputs") or []:
        if not isinstance(item, dict) or not item.get("name"):
            errors.append("链 inputs 条目须为含 name 的映射：%r" % (item,))
        else:
            chain_inputs.append(item["name"])

    stages = data.get("stages")
    if not isinstance(stages, list) or not stages:
        errors.append("stages 缺失或为空")
        return errors
    by_id = {}
    for idx, st in enumerate(stages):
        if not isinstance(st, dict):
            errors.append("stages[%d] 不是映射" % idx)
            continue
        sid = st.get("id")
        if not isinstance(sid, str) or not NAME_RE.match(sid or ""):
            errors.append("stages[%d] 的 id 缺失或不合规范：%r" % (idx, sid))
            continue
        if sid in by_id:
            errors.append("段 id 重复：%s" % sid)
        by_id[sid] = (idx, st)
        skill = st.get("skill")
        if not skill:
            errors.append("段 %s 缺 skill" % sid)
        elif not (repo_root / "skills" / skill / "SKILL.md").exists():
            errors.append("段 %s 引用的 skill 不存在：skills/%s/SKILL.md 缺失" % (sid, skill))
        outs = st.get("outputs")
        if not isinstance(outs, list) or not outs:
            errors.append("段 %s 的 outputs 缺失或为空" % sid)
        gate = st.get("gate", "none")
        if gate not in ("none", "human") and not (
                isinstance(gate, str) and gate.startswith("checker:") and gate[8:]):
            errors.append("段 %s 的 gate 非法：%r（只认 none / human / checker:<名>）" % (sid, gate))
        rl = st.get("retry_limit", 0)
        if not isinstance(rl, int) or isinstance(rl, bool) or rl < 0:
            errors.append("段 %s 的 retry_limit 非法：%r" % (sid, rl))
        if "optional" in st and not isinstance(st["optional"], bool):
            errors.append("段 %s 的 optional 须为 true/false" % sid)
        if "params" in st and st["params"] is not None and not isinstance(st["params"], dict):
            errors.append("段 %s 的 params 须为映射" % sid)

    order = {sid: idx for sid, (idx, _st) in by_id.items()}
    for sid, (idx, st) in by_id.items():
        ins = st.get("inputs") or {}
        src = ins.get("from", "chain")
        needs = ins.get("needs") or []
        if src == "chain":
            for need in needs:
                if need not in chain_inputs:
                    errors.append(
                        "悬空依赖：段 %s 需要链输入 %s，但链未声明该输入" % (sid, need))
        elif src not in by_id:
            errors.append("悬空依赖：段 %s 的 inputs.from 指向不存在的段 %s" % (sid, src))
        else:
            if order[src] >= idx:
                errors.append(
                    "环依赖/前向引用：段 %s 的 inputs.from 指向不早于自身的段 %s"
                    "（from 只能指向排在前面的段）" % (sid, src))
            src_outs = by_id[src][1].get("outputs") or []
            for need in needs:
                if need not in src_outs:
                    errors.append(
                        "契约不满足：段 %s 需要产物 %s，但上游段 %s 未声明该产物" % (sid, need, src))

    # 显式环检查（防御性：与前向引用规则互为冗余）
    graph = {sid: (st.get("inputs") or {}).get("from")
             for sid, (_i, st) in by_id.items()}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {sid: WHITE for sid in graph}

    def dfs(node, path):
        color[node] = GRAY
        nxt = graph.get(node)
        if nxt in graph:
            if color[nxt] == GRAY:
                errors.append("环依赖：%s" % " → ".join(path + [node, nxt]))
            elif color[nxt] == WHITE:
                dfs(nxt, path + [node])
        color[node] = BLACK

    for sid in graph:
        if color[sid] == WHITE:
            dfs(sid, [])
    return errors


# ---------------------------------------------------------------- 运行期辅助
def _now():
    return datetime.now().isoformat(timespec="seconds")


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path):
    return _sha256_bytes(Path(path).read_bytes())


def _read_json(path):
    path = Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path, obj):
    Path(path).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _runs_root(workspace, chain_name):
    return Path(workspace) / ".livepowers" / "chains" / chain_name / "runs"


def _new_run_id(runs_root):
    base = datetime.now().strftime("%Y%m%d-%H%M%S")
    rid, n = base, 2
    while (runs_root / rid).exists():
        rid = "%s-%d" % (base, n)
        n += 1
    return rid


def _emit(args, payload, lines):
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for ln in lines:
            print(ln)


# ---------------------------------------------------------------- 模拟执行器
def _sim_scan(stage, ctx):
    name = stage["outputs"][0]
    body = """# 环境扫描结果（模拟产物）

- 链输入请求：%s
- 起点类型：%s（params.start）
- 说明：原型模拟产物，未连接真实数据源；真实执行由 Agent 按 env-scan-ontology 的 SKILL.md 完成。

## 候选对象（由请求语义推断）

| 对象 | 关键字段 | 备注 |
|---|---|---|
| 订单 | order_id、region、amount、status | 营收类请求的候选核心对象 |
| 区域 | region_id、name | 维度对象 |

## 待确认

- 金额口径（含税 / 去重 / 确认收入）未定，交规格段澄清，不在本段猜测。
""" % (ctx["request"] or "（未提供）", (stage.get("params") or {}).get("start", "-"))
    return [(name, name + ".md", body.encode("utf-8"))]


def _sim_specify(stage, ctx):
    name = stage["outputs"][0]
    src = (stage.get("inputs") or {}).get("needs", ["-"])[0]
    body = """# 规格（模拟产物）

- 依据产物：%s（sha256 前 12 位：%s）
- 规格模板：%s（params.spec_template）
- 说明：原型模拟产物；真实规格由 Agent 按 ontology-grounded-spec 的 SKILL.md 编译。

## 目标

按链输入请求的口径，产出可核对的分析结果，并给出验收样例。

## 输入 / 输出

- 输入：%s 中的候选对象与字段
- 输出：分析结果的数据口径、粒度与验收样例

## 验收样例

1. 正常：汇总行数与维度表一致。
2. 边界：金额为空的记录不计入汇总。
3. 错误：口径未确认时拒绝执行并回报，不先做一版看看。
""" % (src, ctx["input_digests"].get(src, "-"),
       (stage.get("params") or {}).get("spec_template", "-"), src)
    return [(name, name + ".md", body.encode("utf-8"))]


def _sim_explore(stage, ctx):
    name = stage["outputs"][0]
    src = (stage.get("inputs") or {}).get("needs", ["-"])[0]
    body = """# 分析结果（模拟产物）

- 依据产物：%s（sha256 前 12 位：%s）
- 探索轮次上限：%s（params.max_rounds）
- 说明：原型模拟产物，数字为占位示例，未经真实数据核验；真实探索由 Agent
  按 explore-with-evidence 的 SKILL.md 执行并留证据。

## 假设

按规格口径汇总，维度与指标定义以规格段为准。

## 样例核对

- 正常样例：通过（模拟）。
- 边界样例：通过（模拟）。

## 结论（占位）

| 区域 | 金额汇总（占位） |
|---|---|
| 华东 | 0 |
| 华北 | 0 |
""" % (src, ctx["input_digests"].get(src, "-"),
       (stage.get("params") or {}).get("max_rounds", "-"))
    return [(name, name + ".md", body.encode("utf-8"))]


def _sim_accept(stage, ctx):
    name = stage["outputs"][0]
    src = (stage.get("inputs") or {}).get("needs", ["-"])[0]
    body = """# 验收记录（模拟产物）

- 被验收产物：%s（sha256 前 12 位：%s）
- 要求独立审查：%s（params.require_independent_review）
- 说明：原型模拟产物；真实验收由与生成者分离的审查者按 acceptance-gates 的 SKILL.md 执行。

## 四道门

| # | 门 | 结论 |
|---|---|---|
| 1 | 形式检查 | 通过（模拟） |
| 2 | 契约测试 | 通过（模拟） |
| 3 | 独立对抗审查 | 通过（模拟） |
| 4 | 人工采纳 | 待确认——本段 gate: human，运行停在此处等有权采纳人决定 |

""" % (src, ctx["input_digests"].get(src, "-"),
       (stage.get("params") or {}).get("require_independent_review", "-"))
    return [(name, name + ".md", body.encode("utf-8"))]


def _sim_ledger(stage, ctx):
    name = stage["outputs"][0]
    entry = {
        "scenario": (stage.get("params") or {}).get("scenario", "-"),
        "run_id": ctx["run_id"],
        "task": ctx["run_id"],
        "accepted_by": ctx.get("decided_by"),
        "baseline": None,
        "note": ("原型模拟台账记录：基线/目标未在本原型中登记，真实记录由 Agent "
                 "按 outcome-ledger 的 SKILL.md 用 lp outcome 系列命令完成。"),
    }
    return [(name, name + ".json",
             (json.dumps(entry, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))]


_SIMULATORS = {
    "env-scan-ontology": _sim_scan,
    "ontology-grounded-spec": _sim_specify,
    "explore-with-evidence": _sim_explore,
    "acceptance-gates": _sim_accept,
    "outcome-ledger": _sim_ledger,
}


def simulate_stage(stage, ctx):
    """按段契约生成模拟产物：[(产物名, 文件名, bytes)]。"""
    params = stage.get("params") or {}
    if str(params.get("simulate")) == "fail":
        raise SimFail("params.simulate=fail（测试钩子触发的模拟失败）")
    gen = _SIMULATORS.get(stage["skill"])
    if gen is None:
        return [(o, o + ".md",
                 ("# %s（模拟产物）\n\n由 skill %s 按契约产出（原型模拟）。\n"
                  % (o, stage["skill"])).encode("utf-8"))
                for o in stage["outputs"]]
    artifacts = gen(stage, ctx)
    pad = params.get("pad_bytes")
    if isinstance(pad, int) and pad > 0 and artifacts:
        name, fname, data = artifacts[0]
        if len(data) < pad:
            filler = "\n<!-- 原型填充：验证大文件登记口径（>100KB 只登记路径+哈希） -->\n"
            reps = (pad - len(data)) // len(filler.encode("utf-8")) + 1
            data = data + (filler * reps).encode("utf-8")
        artifacts[0] = (name, fname, data)
    return artifacts


def _materialize(run_dir, chain_name, run_id, workspace, stage_id, artifacts):
    """产物落盘并生成 manifest outputs 条目（4B 大文件口径在此落地）。"""
    sdir = Path(run_dir) / stage_id
    sdir.mkdir(parents=True, exist_ok=True)
    meta = []
    for name, fname, data in artifacts:
        f = sdir / fname
        f.write_bytes(data)
        sha, size = _sha256_bytes(data), len(data)
        if size > LARGE_ARTIFACT_BYTES:
            dest_dir = (Path(workspace) / ".livepowers" / "chains" / chain_name
                        / "large" / run_id / stage_id)
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / fname
            shutil.move(str(f), str(dest))
            meta.append({"name": name, "path": str(dest), "sha256": sha,
                         "size": size, "stored": "external"})
        else:
            meta.append({"name": name, "path": "%s/%s" % (stage_id, fname),
                         "sha256": sha, "size": size, "stored": "run"})
    return meta


def _resolve_inputs(stage, by_id, run_dir):
    """按名解析本段输入，返回 manifest inputs 条目；缺失/不符抛 EXIT_MISSING。"""
    ins = stage.get("inputs") or {}
    provider = ins.get("from", "chain")
    needs = ins.get("needs") or []
    resolved = []
    for need in needs:
        src = provider
        while src != "chain":
            pman = _read_json(Path(run_dir) / src / "manifest.json")
            if pman and pman.get("status") == "skipped":
                src = (by_id[src].get("inputs") or {}).get("from", "chain")
                continue
            break
        if src == "chain":
            f = Path(run_dir) / "inputs" / (need + ".txt")
            if not f.exists():
                raise ChainError("链输入产物缺失：%s（%s）" % (need, f), EXIT_MISSING)
            resolved.append({"name": need, "from_stage": "chain",
                             "path": "inputs/%s.txt" % need,
                             "sha256": _sha256_file(f)})
            continue
        pman = _read_json(Path(run_dir) / src / "manifest.json")
        if not pman:
            raise ChainError(
                "上游段 %s 无 manifest，无法取产物 %s" % (src, need), EXIT_MISSING)
        out = next((o for o in pman.get("outputs", []) if o["name"] == need), None)
        if out is None:
            raise ChainError(
                "契约不满足：上游段 %s 的 manifest 未声明产物 %s" % (src, need),
                EXIT_MISSING)
        f = Path(out["path"]) if out.get("stored") == "external" else Path(run_dir) / out["path"]
        if not f.exists():
            raise ChainError("上游产物缺失：%s（%s）" % (need, f), EXIT_MISSING)
        if _sha256_file(f) != out["sha256"]:
            raise ChainError(
                "上游产物 %s 的 sha256 与 manifest 不一致，疑似被手改；"
                "请回上游段 %s 重跑" % (need, src), EXIT_MISSING)
        resolved.append({"name": need, "from_stage": src,
                         "path": out["path"], "sha256": out["sha256"]})
    return resolved


def _save_cm(run_dir, cm):
    cm["updated"] = _now()
    _write_json(Path(run_dir) / "chain-manifest.json", cm)


# ---------------------------------------------------------------- 子命令
def cmd_validate(args):
    chain_dir, data = load_chain(args.chain)
    repo_root = resolve_repo_root(chain_dir, args.repo_root)
    errors = validate_chain(data, chain_dir, repo_root)
    if errors:
        for e in errors:
            print("校验失败：%s" % e, file=sys.stderr)
        _emit(args, {"ok": False, "chain": data.get("name"), "errors": errors}, [])
        return EXIT_FAIL
    stages = data["stages"]
    _emit(args,
          {"ok": True, "chain": data["name"], "stages": [s["id"] for s in stages]},
          ["结论：校验通过：%s（%d 段）" % (data["name"], len(stages)),
           "关键信息：段顺序 %s" % " → ".join(s["id"] for s in stages)])
    return EXIT_OK


def cmd_run(args):
    chain_dir, data = load_chain(args.chain)
    repo_root = resolve_repo_root(chain_dir, args.repo_root)
    errors = validate_chain(data, chain_dir, repo_root)
    if errors:
        for e in errors:
            print("校验失败：%s" % e, file=sys.stderr)
        return EXIT_FAIL
    chain_name = data["name"]
    stages = data["stages"]
    by_id = {s["id"]: s for s in stages}
    order = {s["id"]: i for i, s in enumerate(stages)}
    workspace = Path(args.workspace)
    runs_root = _runs_root(workspace, chain_name)

    for sid in args.skip or []:
        if sid not in by_id:
            raise ChainError("未知段：--skip %s" % sid, EXIT_FAIL)
        if not by_id[sid].get("optional", False):
            raise ChainError(
                "段 %s 不是 optional，拒绝跳过（不静默降级）；"
                "确需免除先改 chain.yaml 契约并重新校验" % sid, EXIT_FAIL)

    resume = bool(args.run_id and (args.from_stage or args.approve))
    if (args.from_stage or args.approve) and not args.run_id:
        raise ChainError("--from / --approve 续跑必须同时给 --run-id", EXIT_USAGE)
    if resume and args.param:
        raise ChainError("续跑不接受 --param（链输入已在首次运行时落盘）", EXIT_USAGE)

    # ---- 准备运行目录与 chain-manifest
    if resume:
        run_id = args.run_id
        run_dir = runs_root / run_id
        cm = _read_json(run_dir / "chain-manifest.json")
        if cm is None:
            raise ChainError("找不到运行 %s 的 chain-manifest.json" % run_id, EXIT_FAIL)
        skip_set = set(cm.get("skipped", [])) | set(args.skip or [])
        chain_inputs = cm.get("inputs", {})
    else:
        run_id = args.run_id or _new_run_id(runs_root)
        run_dir = runs_root / run_id
        if run_dir.exists():
            raise ChainError("运行目录已存在：%s" % run_dir, EXIT_FAIL)
        declared = [it["name"] for it in data.get("inputs") or []]
        provided = {}
        for pair in args.param or []:
            if "=" not in pair:
                raise ChainError("--param 须为 k=v 形式：%s" % pair, EXIT_USAGE)
            k, v = pair.split("=", 1)
            if k not in declared:
                raise ChainError("未声明的链输入参数：%s" % k, EXIT_USAGE)
            provided[k] = v
        missing = [n for n in declared if n not in provided]
        if missing:
            raise ChainError(
                "缺少链输入参数：%s（用 --param %s=... 提供）"
                % ("、".join(missing), missing[0]), EXIT_USAGE)
        chain_inputs = provided
        skip_set = set(args.skip or [])
        (run_dir / "inputs").mkdir(parents=True)
        for k, v in chain_inputs.items():
            (run_dir / "inputs" / (k + ".txt")).write_text(v, encoding="utf-8")
        cm = {"chain": chain_name, "run_id": run_id, "status": "running",
              "stage_order": [s["id"] for s in stages],
              "inputs": chain_inputs, "skipped": sorted(skip_set),
              "stages": {s["id"]: "pending" for s in stages},
              "current_stage": None, "created": _now()}
        for sid in skip_set:
            sdir = run_dir / sid
            sdir.mkdir(parents=True, exist_ok=True)
            _write_json(sdir / "manifest.json",
                        {"chain": chain_name, "run_id": run_id, "stage": sid,
                         "skill": by_id[sid]["skill"], "status": "skipped",
                         "inputs": [], "outputs": [],
                         "note": "optional 段按 --skip 跳过", "created": _now()})
            cm["stages"][sid] = "skipped"
        _save_cm(run_dir, cm)

    # ---- 定续跑起点
    start_index = 0
    if resume and args.approve:
        if cm.get("status") != "awaiting":
            raise ChainError(
                "运行 %s 当前状态为 %s，不在验收门 awaiting，无门可批"
                % (run_id, cm.get("status")), EXIT_FAIL)
        gate_id = cm.get("current_stage")
        if args.from_stage and args.from_stage != gate_id \
                and order.get(args.from_stage, -1) < order[gate_id]:
            raise ChainError(
                "--from %s 在验收门 %s 之前；先 --approve 处理验收门"
                % (args.from_stage, gate_id), EXIT_FAIL)
        gman_path = run_dir / gate_id / "manifest.json"
        gman = _read_json(gman_path)
        gman["decided_by"] = args.by or "（未具名）"
        gman["decided"] = _now()
        gman["decision_reason"] = "人工采纳（run --approve）"
        gman["gate"] = "passed"
        for out in gman.get("outputs", []):
            if out.get("stored") == "run":
                rec = run_dir / out["path"]
                if rec.exists() and rec.suffix == ".md":
                    with rec.open("a", encoding="utf-8") as fh:
                        fh.write("\n## 人工采纳\n\n- 采纳人：%s\n- 时间：%s\n"
                                 % (gman["decided_by"], gman["decided"]))
                    # 采纳留痕是验收门流程的一部分：回写新哈希与大小，
                    # 使 manifest 继续充当产物的防篡改真源
                    out["sha256"] = _sha256_file(rec)
                    out["size"] = rec.stat().st_size
        _write_json(gman_path, gman)
        cm["status"] = "running"
        cm["current_stage"] = None
        _save_cm(run_dir, cm)
        start_index = order[gate_id] + 1
        if args.from_stage and order[args.from_stage] > order[gate_id]:
            start_index = order[args.from_stage]
    elif resume and args.from_stage:
        if args.from_stage not in by_id:
            raise ChainError("未知段：--from %s" % args.from_stage, EXIT_FAIL)
        if cm.get("status") == "awaiting":
            gate_id = cm["current_stage"]
            if order[args.from_stage] < order[gate_id]:
                raise ChainError(
                    "运行停在验收门 %s；--from 须从该段起，或先 --approve" % gate_id,
                    EXIT_FAIL)
            if order[args.from_stage] > order[gate_id]:
                raise ChainError(
                    "验收门 %s 未确认，不能越过续跑；先 --approve" % gate_id, EXIT_FAIL)
        start_index = order[args.from_stage]

    # ---- 逐段执行
    for idx in range(start_index, len(stages)):
        stage = stages[idx]
        sid = stage["id"]
        if sid in skip_set:
            cm["stages"][sid] = "skipped"
            _save_cm(run_dir, cm)
            continue
        sdir = run_dir / sid
        if resume and sdir.exists():
            shutil.rmtree(sdir)
        resolved = _resolve_inputs(stage, by_id, run_dir)
        ctx = {"request": chain_inputs.get("request", ""),
               "params": stage.get("params") or {},
               "inputs": {},
               "input_digests": {e["name"]: e["sha256"][:12] for e in resolved},
               "run_id": run_id, "decided_by": None}
        for e in resolved:
            f = Path(e["path"]) if not (run_dir / e["path"]).exists() else run_dir / e["path"]
            if f.exists() and f.stat().st_size <= LARGE_ARTIFACT_BYTES:
                ctx["inputs"][e["name"]] = f.read_text(encoding="utf-8", errors="replace")
            if e["from_stage"] != "chain":
                pman = _read_json(run_dir / e["from_stage"] / "manifest.json") or {}
                if pman.get("decided_by"):
                    ctx["decided_by"] = pman["decided_by"]
        artifacts, last_err = None, None
        for _attempt in range(int(stage.get("retry_limit") or 0) + 1):
            try:
                artifacts = simulate_stage(stage, ctx)
                last_err = None
                break
            except SimFail as exc:
                last_err = exc
        started = _now()
        if artifacts is None:
            sdir.mkdir(parents=True, exist_ok=True)
            _write_json(sdir / "manifest.json",
                        {"chain": chain_name, "run_id": run_id, "stage": sid,
                         "skill": stage["skill"], "status": "failed",
                         "inputs": resolved, "outputs": [],
                         "params": stage.get("params") or {},
                         "note": "段执行失败：%s" % last_err, "created": started})
            cm["status"] = "failed"
            cm["current_stage"] = sid
            cm["stages"][sid] = "failed"
            _save_cm(run_dir, cm)
            raise ChainError(
                "段 %s 执行失败（retry_limit=%s）：%s"
                % (sid, stage.get("retry_limit", 0), last_err), EXIT_FAIL)
        outputs_meta = _materialize(run_dir, chain_name, run_id, workspace, sid, artifacts)
        _write_json(sdir / "manifest.json",
                    {"chain": chain_name, "run_id": run_id, "stage": sid,
                     "skill": stage["skill"], "status": "done",
                     "inputs": resolved, "outputs": outputs_meta,
                     "params": stage.get("params") or {},
                     "generated_by": "scripts/chain_runner.py（模拟执行器）",
                     "model": "simulated",
                     "note": "原型模拟产物：仅验证编排/契约/gate/续跑语义，非段 skill 的真实业务执行",
                     "created": started, "finished": _now()})
        cm["stages"][sid] = "done"
        gate = stage.get("gate", "none")
        if gate == "human":
            cm["status"] = "awaiting"
            cm["current_stage"] = sid
            _save_cm(run_dir, cm)
            _emit(args,
                  {"ok": False, "run_id": run_id, "status": "awaiting", "stage": sid},
                  ["结论：停在验收门：%s（待采纳后续跑）" % sid,
                   "关键信息：run-id %s；验收记录 %s" % (run_id, outputs_meta[0]["path"]),
                   "详情：采纳后续跑：run %s --workspace %s --run-id %s --from %s --approve --by <采纳人>"
                   % (args.chain, args.workspace, run_id, sid)])
            return EXIT_AWAITING
        if isinstance(gate, str) and gate.startswith("checker:"):
            cm["status"] = "failed"
            cm["current_stage"] = sid
            _save_cm(run_dir, cm)
            raise ChainError(
                "段 %s 的 checker 校验器 %s 未在原型中实现，拒绝静默放行"
                % (sid, gate[8:]), EXIT_FAIL)
        _save_cm(run_dir, cm)

    cm["status"] = "completed"
    cm["current_stage"] = None
    _save_cm(run_dir, cm)
    done = sum(1 for v in cm["stages"].values() if v in ("done", "skipped"))
    _emit(args,
          {"ok": True, "run_id": run_id, "status": "completed", "stages": cm["stages"]},
          ["结论：全链完成：%s" % run_id,
           "关键信息：%d/%d 段完成；产物根目录 %s" % (done, len(stages), run_dir)])
    return EXIT_OK


def cmd_stage(args):
    """段独立调用（T1 §3.2 的 `chain stage`；T2 原型未实现，T3 验证时补齐的最小实现）。

    stage <chain> <stage-id> [--workspace DIR] [--repo-root DIR]
          [--param k=v ...] [--run <run-id>] [--json]
    不带 --run：开新 run-id，产物自成一次运行（写入 chain-manifest 骨架，
    其余段 pending）；带 --run：写入指定运行目录（无 chain-manifest 时按
    新运行骨架创建），供后续 run --from 复用（T1 §2.6 验证点 5）。
    单段执行块（输入解析/ctx/模拟执行/manifest/gate 语义）与 cmd_run 同源。
    链级状态流转仍归 run：stage 只落本段状态；gate: human 时置 awaiting。
    """
    chain_dir, data = load_chain(args.chain)
    repo_root = resolve_repo_root(chain_dir, args.repo_root)
    errors = validate_chain(data, chain_dir, repo_root)
    if errors:
        for e in errors:
            print("校验失败：%s" % e, file=sys.stderr)
        return EXIT_FAIL
    chain_name = data["name"]
    stages = data["stages"]
    by_id = {s["id"]: s for s in stages}
    if args.stage_id not in by_id:
        raise ChainError(
            "未知段：%s（链 %s 的段：%s）"
            % (args.stage_id, chain_name, "、".join(by_id)), EXIT_FAIL)
    stage = by_id[args.stage_id]
    sid = args.stage_id
    workspace = Path(args.workspace)
    runs_root = _runs_root(workspace, chain_name)

    declared = [it["name"] for it in data.get("inputs") or []]
    provided = {}
    for pair in args.param or []:
        if "=" not in pair:
            raise ChainError("--param 须为 k=v 形式：%s" % pair, EXIT_USAGE)
        k, v = pair.split("=", 1)
        if k not in declared:
            raise ChainError("未声明的链输入参数：%s" % k, EXIT_USAGE)
        provided[k] = v

    # ---- 定位/创建运行目录与 chain-manifest（骨架结构与 cmd_run 一致）
    if args.run_id:
        run_id = args.run_id
        run_dir = runs_root / run_id
        cm = _read_json(run_dir / "chain-manifest.json")
        if cm is None:
            (run_dir / "inputs").mkdir(parents=True, exist_ok=True)
            cm = {"chain": chain_name, "run_id": run_id, "status": "running",
                  "stage_order": [s["id"] for s in stages],
                  "inputs": {}, "skipped": [],
                  "stages": {s["id"]: "pending" for s in stages},
                  "current_stage": None, "created": _now()}
        cm.setdefault("inputs", {})
        for k, v in provided.items():
            f = run_dir / "inputs" / (k + ".txt")
            if not f.exists():
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(v, encoding="utf-8")
            cm["inputs"].setdefault(k, v)
        chain_inputs = cm["inputs"]
        _save_cm(run_dir, cm)
    else:
        run_id = _new_run_id(runs_root)
        run_dir = runs_root / run_id
        (run_dir / "inputs").mkdir(parents=True)
        for k, v in provided.items():
            (run_dir / "inputs" / (k + ".txt")).write_text(v, encoding="utf-8")
        chain_inputs = provided
        cm = {"chain": chain_name, "run_id": run_id, "status": "running",
              "stage_order": [s["id"] for s in stages],
              "inputs": chain_inputs, "skipped": [],
              "stages": {s["id"]: "pending" for s in stages},
              "current_stage": None, "created": _now()}
        _save_cm(run_dir, cm)

    # ---- 执行单个段（与 cmd_run 逐段执行块同语义）
    sdir = run_dir / sid
    if sdir.exists():
        shutil.rmtree(sdir)
    resolved = _resolve_inputs(stage, by_id, run_dir)
    ctx = {"request": chain_inputs.get("request", ""),
           "params": stage.get("params") or {},
           "inputs": {},
           "input_digests": {e["name"]: e["sha256"][:12] for e in resolved},
           "run_id": run_id, "decided_by": None}
    for e in resolved:
        f = Path(e["path"]) if not (run_dir / e["path"]).exists() else run_dir / e["path"]
        if f.exists() and f.stat().st_size <= LARGE_ARTIFACT_BYTES:
            ctx["inputs"][e["name"]] = f.read_text(encoding="utf-8", errors="replace")
        if e["from_stage"] != "chain":
            pman = _read_json(run_dir / e["from_stage"] / "manifest.json") or {}
            if pman.get("decided_by"):
                ctx["decided_by"] = pman["decided_by"]
    artifacts, last_err = None, None
    for _attempt in range(int(stage.get("retry_limit") or 0) + 1):
        try:
            artifacts = simulate_stage(stage, ctx)
            last_err = None
            break
        except SimFail as exc:
            last_err = exc
    started = _now()
    if artifacts is None:
        sdir.mkdir(parents=True, exist_ok=True)
        _write_json(sdir / "manifest.json",
                    {"chain": chain_name, "run_id": run_id, "stage": sid,
                     "skill": stage["skill"], "status": "failed",
                     "inputs": resolved, "outputs": [],
                     "params": stage.get("params") or {},
                     "note": "段执行失败：%s" % last_err, "created": started})
        cm["status"] = "failed"
        cm["current_stage"] = sid
        cm["stages"][sid] = "failed"
        _save_cm(run_dir, cm)
        raise ChainError(
            "段 %s 执行失败（retry_limit=%s）：%s"
            % (sid, stage.get("retry_limit", 0), last_err), EXIT_FAIL)
    outputs_meta = _materialize(run_dir, chain_name, run_id, workspace, sid, artifacts)
    _write_json(sdir / "manifest.json",
                {"chain": chain_name, "run_id": run_id, "stage": sid,
                 "skill": stage["skill"], "status": "done",
                 "inputs": resolved, "outputs": outputs_meta,
                 "params": stage.get("params") or {},
                 "generated_by": "scripts/chain_runner.py stage（T3 补齐子命令；模拟执行器）",
                 "model": "simulated",
                 "note": "原型模拟产物（段独立调用）：仅验证编排/契约语义，非段 skill 的真实业务执行",
                 "created": started, "finished": _now()})
    cm["stages"][sid] = "done"
    gate = stage.get("gate", "none")
    if gate == "human":
        cm["status"] = "awaiting"
        cm["current_stage"] = sid
        _save_cm(run_dir, cm)
        _emit(args,
              {"ok": False, "run_id": run_id, "status": "awaiting", "stage": sid,
               "via": "stage"},
              ["结论：段独立调用停在验收门：%s（待采纳后以 run 续跑）" % sid,
               "关键信息：run-id %s；验收记录 %s" % (run_id, outputs_meta[0]["path"]),
               "详情：采纳后续跑：run %s --workspace %s --run-id %s --from %s --approve --by <采纳人>"
               % (args.chain, args.workspace, run_id, sid)])
        return EXIT_AWAITING
    if isinstance(gate, str) and gate.startswith("checker:"):
        cm["status"] = "failed"
        cm["current_stage"] = sid
        _save_cm(run_dir, cm)
        raise ChainError(
            "段 %s 的 checker 校验器 %s 未在原型中实现，拒绝静默放行"
            % (sid, gate[8:]), EXIT_FAIL)
    _save_cm(run_dir, cm)
    _emit(args,
          {"ok": True, "run_id": run_id, "stage": sid, "status": "done",
           "outputs": [o["name"] for o in outputs_meta], "via": "stage"},
          ["结论：段独立调用完成：%s（run-id %s）" % (sid, run_id),
           "关键信息：产物 %s；清单 %s/manifest.json"
           % ("、".join(o["name"] for o in outputs_meta), sid)])
    return EXIT_OK


def cmd_status(args):
    workspace = Path(args.workspace)
    base = workspace / ".livepowers" / "chains"
    matches = sorted(base.glob("*/runs/%s" % args.run_id)) if base.exists() else []
    if not matches:
        raise ChainError("找不到运行：%s（工作区 %s）" % (args.run_id, workspace), EXIT_FAIL)
    if len(matches) > 1:
        raise ChainError("run-id %s 在多条链下重复，无法定位" % args.run_id, EXIT_FAIL)
    run_dir = matches[0]
    cm = _read_json(run_dir / "chain-manifest.json")
    if cm is None:
        raise ChainError("运行 %s 缺 chain-manifest.json" % args.run_id, EXIT_FAIL)
    stage_rows = []
    for sid in cm["stage_order"]:
        man = _read_json(run_dir / sid / "manifest.json")
        stage_rows.append({
            "stage": sid,
            "status": (man or {}).get("status", cm["stages"].get(sid, "pending")),
            "outputs": [o["name"] for o in (man or {}).get("outputs", [])],
        })
    done = sum(1 for r in stage_rows if r["status"] in ("done", "skipped"))
    _emit(args,
          {"ok": True, "run_id": args.run_id, "chain": cm["chain"],
           "status": cm["status"], "stages": stage_rows},
          ["结论：%s：%s（完成 %d/%d 段）"
           % (args.run_id, cm["status"], done, len(stage_rows)),
           "关键信息：" + "；".join(
               "%s=%s" % (r["stage"], r["status"]) for r in stage_rows)])
    return EXIT_OK


def build_parser():
    parser = argparse.ArgumentParser(
        prog="chain_runner.py",
        description="链式 skill 运行器原型（PRD-095/T2）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("validate", help="校验 chain.yaml")
    p.add_argument("chain")
    p.add_argument("--repo-root")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("run", help="运行/续跑一条链")
    p.add_argument("chain")
    p.add_argument("--workspace", default=".")
    p.add_argument("--repo-root")
    p.add_argument("--param", action="append", default=[])
    p.add_argument("--run-id")
    p.add_argument("--from", dest="from_stage")
    p.add_argument("--skip", action="append", default=[])
    p.add_argument("--approve", action="store_true")
    p.add_argument("--by")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("stage", help="段独立调用（T1 §3.2；T3 补齐）")
    p.add_argument("chain")
    p.add_argument("stage_id")
    p.add_argument("--workspace", default=".")
    p.add_argument("--repo-root")
    p.add_argument("--param", action="append", default=[])
    p.add_argument("--run", dest="run_id")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_stage)

    p = sub.add_parser("status", help="查看某次运行的状态")
    p.add_argument("run_id")
    p.add_argument("--workspace", default=".")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_status)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ChainError as e:
        print("错误：%s" % e, file=sys.stderr)
        return e.code


if __name__ == "__main__":
    sys.exit(main())
