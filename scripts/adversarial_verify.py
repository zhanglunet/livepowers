#!/usr/bin/env python3
"""adversarial_verify —— PRD-171/T2：skill 对抗式验收 verifier 机检（最小实现）。

规范：docs/plans/2026-10-25-adversarial-acceptance.md（PRD-171/T1，trend issue
#855）。分工边界：**执行用例的是独立 verifier 会话（人 / agent），本脚本只做
机检**，不代执行、不代判定、不改任何文件——

1. `cases`：校验 tests/adversarial/<skill>/cases.jsonl（字段 schema、编号、
   safety 标记、锚点真实存在、T1 §3 数量下限）。用例文件随规范评审合入即冻结，
   本脚本对它只读；verifier 认为用例本身有误 → 在 record 加 case_error 备注
   并给 needs_validation，不得私改用例（T1 §6.2）。
2. `check`：校验 findings.json 三态记录。T1 §5 判据写死：confirmed 须
   evidence + ≥1 条 falsification_attempts；needs_validation 须 unresolved_fact；
   rejected 须 disproved_by。**独立性机检：verifier 会话标识 == author 即
   FAIL**（作者会话不可自签，T1 §6.1，与 lp registry add 拒绝
   --generated-by == --accepted-by 同一铁律）。
3. `gate`：published 前置条件的判定输入（T1 §5）：存在 findings.json、core
   用例全部 confirmed、未 confirmed 项须有有效豁免（exempt_ref 指向工程门
   豁免台账 docs/engineering-checklist/exemptions.md 里登记的 EX- ID，且其
   对象为该 skill）。**safety 用例一律不可豁免**；rejected 无豁免通道。
   CI / published 的强制接线是 T3（#857）范围，本命令只输出判定。
4. `template`：打印 findings.json 起始骨架（--example 附一条构造样例记录，
   仅供对照字段，不得原样入库）。

用法：
    python3 scripts/adversarial_verify.py cases system1-first
    python3 scripts/adversarial_verify.py cases --all
    python3 scripts/adversarial_verify.py check --all
    python3 scripts/adversarial_verify.py gate acceptance-gates [--json]
    python3 scripts/adversarial_verify.py template system1-first [--example]
通用选项：--root <目录>（默认仓库根，测试可指向夹具目录）、--exemptions <文件>
（默认 <root>/docs/engineering-checklist/exemptions.md，测试可另指）。

退出码：PASS / EXEMPT=0，FAIL=1。只用 Python 标准库，Python 3.9 兼容。
"""
import argparse
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADVERSARIAL_REL = os.path.join("tests", "adversarial")
DEFAULT_EXEMPTIONS_REL = os.path.join("docs", "engineering-checklist", "exemptions.md")

# T1 §3：红线 skill 名单沿用瘦身门红线（写死；调整名单须先改规范）。
REDLINE_SKILLS = ("oltp-action-safety", "acceptance-gates",
                  "auditable-agent-comms", "takeover-handling")

CASE_TYPES = ("POS-EX", "POS-TR", "NEG-TR", "NEG-RED")
# case_id 里的类型短码。T1 §3 示例给出 POS-EX→POS、NEG-RED→RED；
# POS-TR / NEG-TR 按同一风格取 TR / NEG（用例文件照此落）。
TYPE_CODES = {"POS-EX": "POS", "POS-TR": "TR", "NEG-TR": "NEG", "NEG-RED": "RED"}
VERDICTS = ("confirmed", "needs_validation", "rejected")
PRIORITIES = ("core", "extended")

CASE_FIELDS = ("case_id", "skill", "type", "claim", "claim_source", "input",
               "expected", "safety", "priority")
RECORD_FIELDS = ("record_id", "case_id", "verdict", "evidence",
                 "falsification_attempts", "unresolved_fact", "disproved_by",
                 "verifier", "verifier_model", "author", "date")
RECORD_OPTIONAL_FIELDS = ("case_error", "exempt_ref")

CASE_ID_RE = re.compile(
    r"^AC-(?P<skill>[a-z0-9]+(?:-[a-z0-9]+)*)-(?:POS|TR|NEG|RED)\d{2}$")
RECORD_ID_RE = re.compile(
    r"^AV-(?P<day>\d{8})-(?P<skill>[a-z0-9]+(?:-[a-z0-9]+)*)-\d{2}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# 豁免台账数据行：| EX-YYYYMMDD-NN | 对象 | 条目 | ...
EXEMPT_ROW_RE = re.compile(r"^\s*\|\s*(EX-\d{8}-\d{2})\s*\|\s*([^|]+?)\s*\|")
NA_MARKER_TYPES = ("NEG-RED",)  # T1 §3：确无"严禁"级主张可标 N/A 并留理由


def fail_out(errors):
    for e in errors:
        print("  - " + e)
    return 1 if errors else 0


# ---------------------------------------------------------------- cases ----

def anchor_exists(root, skill, claim_source):
    """锚点必须真实存在：SKILL.md#节名 或仓库相对文件路径（T1 §3）。"""
    prefix = "skills/%s/SKILL.md#" % skill
    if claim_source.startswith(prefix):
        section = claim_source[len(prefix):]
        path = os.path.join(root, "skills", skill, "SKILL.md")
        if not os.path.isfile(path):
            return False
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("## ") and line[3:].rstrip() == section:
                    return True
        return False
    if claim_source.startswith(("skills/", "tests/")) and "#" not in claim_source:
        return os.path.isfile(os.path.join(root, claim_source))
    return False


def validate_case_line(root, skill, obj, lineno):
    """校验一条用例，返回 (case 或 None, errors)。"""
    errors = []
    if not isinstance(obj, dict):
        return None, ["第 %d 行：应为 JSON 对象" % lineno]
    for k in obj:
        if k not in CASE_FIELDS:
            errors.append("第 %d 行：未知字段 %r（用例文件随评审冻结，字段以 T1 §4 为准）" % (lineno, k))
    for k in CASE_FIELDS:
        if k not in obj:
            errors.append("第 %d 行：缺必填字段 %r" % (lineno, k))
    if errors:
        return None, errors
    case_id, ctype = obj["case_id"], obj["type"]
    m = CASE_ID_RE.match(case_id) if isinstance(case_id, str) else None
    if not m:
        errors.append("第 %d 行：case_id %r 不符合 AC-<skill>-<类><两位序号>" % (lineno, case_id))
    elif m.group("skill") != skill:
        errors.append("第 %d 行：case_id 中的 skill 段与目录 %s 不一致" % (lineno, skill))
    if ctype not in CASE_TYPES:
        errors.append("第 %d 行：type %r 不在 %s" % (lineno, ctype, "/".join(CASE_TYPES)))
    elif m and isinstance(case_id, str):
        code = case_id.split("-")[-1].rstrip("0123456789")
        if code != TYPE_CODES[ctype]:
            errors.append("第 %d 行：case_id 类型短码 %r 与 type %s（%s）不一致"
                          % (lineno, code, ctype, TYPE_CODES[ctype]))
    for k in ("claim", "claim_source", "input"):
        if not isinstance(obj[k], str) or not obj[k].strip():
            errors.append("第 %d 行：%s 须为非空字符串" % (lineno, k))
    if not isinstance(obj["expected"], list) or not obj["expected"] or \
            not all(isinstance(x, str) and x.strip() for x in obj["expected"]):
        errors.append("第 %d 行：expected 须为非空字符串数组（可观察判据）" % lineno)
    if not isinstance(obj["safety"], bool):
        errors.append("第 %d 行：safety 须为布尔" % lineno)
    elif ctype == "NEG-RED" and not obj["safety"]:
        errors.append("第 %d 行：NEG-RED 用例 safety 恒 true（T1 §3）" % lineno)
    elif ctype != "NEG-RED" and obj["safety"]:
        errors.append("第 %d 行：仅 NEG-RED 可标 safety=true" % lineno)
    if obj["priority"] not in PRIORITIES:
        errors.append("第 %d 行：priority %r 不在 core/extended" % (lineno, obj["priority"]))
    claim_source = obj["claim_source"]
    if isinstance(claim_source, str) and claim_source.strip() and \
            not anchor_exists(root, skill, claim_source):
        errors.append("第 %d 行：锚点不存在：%s（无锚点的用例无效，T1 §3）" % (lineno, claim_source))
    return (obj if not errors else None), errors


def check_minimums(skill, cases, na_reason):
    """T1 §3 数量下限：POS-EX ≥1、POS-TR ≥1、NEG-TR ≥2、
    NEG-RED：红线 skill ≥2，非红线 skill ≥1 或标 N/A 留理由。"""
    errors = []
    count = {"POS-EX": 0, "POS-TR": 0, "NEG-TR": 0, "NEG-RED": 0}
    for c in cases:
        count[c["type"]] += 1
    if count["POS-EX"] < 1:
        errors.append("数量下限：POS-EX ≥1，实际 %d" % count["POS-EX"])
    if count["POS-TR"] < 1:
        errors.append("数量下限：POS-TR ≥1，实际 %d" % count["POS-TR"])
    if count["NEG-TR"] < 2:
        errors.append("数量下限：NEG-TR ≥2，实际 %d" % count["NEG-TR"])
    if skill in REDLINE_SKILLS:
        if count["NEG-RED"] < 2:
            errors.append("红线 skill 数量下限：NEG-RED ≥2，实际 %d（红线名单见 T1 §3）" % count["NEG-RED"])
    elif count["NEG-RED"] < 1 and not na_reason:
        errors.append("数量下限：NEG-RED ≥1（确无\"严禁\"级主张时须标 N/A 并留理由，T1 §3）")
    return errors


def load_cases(root, skill):
    """读取并校验单个 skill 的 cases.jsonl。

    返回 (cases, na_reason, errors)；cases 为通过校验的用例列表。
    """
    errors = []
    path = os.path.join(root, ADVERSARIAL_REL, skill, "cases.jsonl")
    if not os.path.isfile(path):
        return [], None, ["缺 %s/%s/cases.jsonl" % (ADVERSARIAL_REL, skill)]
    cases, na_reason = [], None
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError as exc:
                errors.append("第 %d 行：非法 JSON（%s）" % (lineno, exc))
                continue
            if isinstance(obj, dict) and "na" in obj:
                # N/A 标记行：{"na": "NEG-RED", "reason": "<理由>"}（本仓约定）
                if obj.get("na") not in NA_MARKER_TYPES:
                    errors.append("第 %d 行：na 标记仅支持 %s" % (lineno, "/".join(NA_MARKER_TYPES)))
                elif not isinstance(obj.get("reason"), str) or not obj["reason"].strip():
                    errors.append("第 %d 行：N/A 须留理由" % lineno)
                elif skill in REDLINE_SKILLS:
                    errors.append("第 %d 行：红线 skill 不可对 NEG-RED 标 N/A" % lineno)
                else:
                    na_reason = obj["reason"].strip()
                continue
            case, errs = validate_case_line(root, skill, obj, lineno)
            errors.extend(errs)
            if case:
                cases.append(case)
    errors.extend(check_minimums(skill, cases, na_reason))
    ids = [c["case_id"] for c in cases]
    if len(set(ids)) != len(ids):
        errors.append("case_id 在本文件内重复")
    return cases, na_reason, errors


def list_case_skills(root):
    d = os.path.join(root, ADVERSARIAL_REL)
    if not os.path.isdir(d):
        return []
    return sorted(n for n in os.listdir(d)
                  if os.path.isdir(os.path.join(d, n))
                  and os.path.isfile(os.path.join(d, n, "cases.jsonl")))


def load_all_case_ids(root):
    """全仓 case_id 唯一性（T1 §3）用。返回 ({skill: cases}, [全局错误])。"""
    all_cases, errors, seen = {}, [], {}
    for skill in list_case_skills(root):
        cases, _, errs = load_cases(root, skill)
        errors.extend("%s: %s" % (skill, e) for e in errs)
        all_cases[skill] = cases
        for c in cases:
            cid = c["case_id"]
            if cid in seen:
                errors.append("case_id 全仓重复：%s（%s 与 %s）" % (cid, seen[cid], skill))
            seen[cid] = skill
    return all_cases, errors


# -------------------------------------------------------------- findings ----

def load_exempt_ledger(path):
    """解析工程门豁免台账，返回 {EX- ID: 对象列}；文件缺失返回空表。"""
    out = {}
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = EXEMPT_ROW_RE.match(line)
            if m:
                out[m.group(1)] = m.group(2)
    return out


def check_records(root, skill, cases_by_id, exempt_ledger):
    """校验 findings.json 三态记录（T1 §4/§5/§6），返回错误列表。"""
    errors = []
    path = os.path.join(root, ADVERSARIAL_REL, skill, "findings.json")
    if not os.path.isfile(path):
        return ["缺 %s/%s/findings.json（verifier 尚未写入三态记录）" % (ADVERSARIAL_REL, skill)]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except ValueError as exc:
        return ["findings.json 非法 JSON（%s）" % exc]
    if not isinstance(data, dict) or set(data) != {"records"} or \
            not isinstance(data.get("records"), list):
        return ["findings.json 顶层须为 {\"records\": [...]}"]
    for idx, rec in enumerate(data["records"], 1):
        where = "record #%d" % idx
        if not isinstance(rec, dict):
            errors.append("%s：应为 JSON 对象" % where)
            continue
        for k in rec:
            if k not in RECORD_FIELDS and k not in RECORD_OPTIONAL_FIELDS:
                errors.append("%s：未知字段 %r" % (where, k))
        for k in RECORD_FIELDS:
            if k not in rec:
                errors.append("%s：缺必填字段 %r" % (where, k))
        if any(not isinstance(rec.get(k), str) or not rec.get(k, "").strip()
               for k in ("record_id", "case_id", "verdict", "verifier",
                         "verifier_model", "author", "date")):
            errors.append("%s：必填字符串字段不得为空" % where)
            continue
        verdict = rec["verdict"]
        m = RECORD_ID_RE.match(rec["record_id"])
        if not m:
            errors.append("%s：record_id %r 不符合 AV-<YYYYMMDD>-<skill>-<两位序号>"
                          % (where, rec["record_id"]))
        elif m.group("skill") != skill:
            errors.append("%s：record_id 的 skill 段与目录 %s 不一致" % (where, skill))
        if not DATE_RE.match(rec["date"]):
            errors.append("%s：date %r 须为 YYYY-MM-DD" % (where, rec["date"]))
        if verdict not in VERDICTS:
            errors.append("%s：verdict %r 不在 %s" % (where, verdict, "/".join(VERDICTS)))
            continue
        # 三态判据（T1 §5，写死）：判据字段缺失即记录无效。
        if verdict == "confirmed":
            if not isinstance(rec.get("evidence"), str) or not rec["evidence"].strip():
                errors.append("%s：confirmed 须填 evidence（第三方可按此重放）" % where)
            if not isinstance(rec.get("falsification_attempts"), list) or \
                    not rec["falsification_attempts"] or \
                    not all(isinstance(x, str) and x.strip() for x in rec["falsification_attempts"]):
                errors.append("%s：confirmed 须 ≥1 条证伪尝试（falsification_attempts 非空字符串数组）" % where)
        elif verdict == "needs_validation":
            if not isinstance(rec.get("unresolved_fact"), str) or not rec["unresolved_fact"].strip():
                errors.append("%s：needs_validation 须填 unresolved_fact（一个精确的未落定事实）" % where)
        else:  # rejected
            if not isinstance(rec.get("disproved_by"), str) or not rec["disproved_by"].strip():
                errors.append("%s：rejected 须填 disproved_by（最小复现）" % where)
        if isinstance(rec.get("unresolved_fact"), str) and rec["unresolved_fact"].strip() \
                and verdict != "needs_validation":
            errors.append("%s：unresolved_fact 仅 needs_validation 可填（T1 §4）" % where)
        if isinstance(rec.get("disproved_by"), str) and rec["disproved_by"].strip() \
                and verdict != "rejected":
            errors.append("%s：disproved_by 仅 rejected 可填（T1 §4）" % where)
        # 独立性机检（T1 §6.1）：作者会话不可自签。
        if rec["verifier"] == rec["author"]:
            errors.append("%s：verifier == author（%r）——作者会话不可自签，独立性机检 FAIL"
                          % (where, rec["verifier"]))
        case_error = rec.get("case_error", "")
        if isinstance(case_error, str) and case_error.strip() and verdict != "needs_validation":
            errors.append("%s：case_error 备注只可搭配 needs_validation（T1 §6.2）" % where)
        exempt_ref = rec.get("exempt_ref", "")
        if isinstance(exempt_ref, str) and exempt_ref.strip():
            case = cases_by_id.get(rec["case_id"])
            if verdict != "needs_validation":
                errors.append("%s：exempt_ref 仅 needs_validation 可填" % where)
            elif case is not None and case.get("safety"):
                errors.append("%s：safety 用例不可豁免（exempt_ref 须留空，T1 §5 禁令）" % where)
            elif exempt_ref not in exempt_ledger:
                errors.append("%s：exempt_ref %s 未在豁免台账登记" % (where, exempt_ref))
            elif exempt_ledger[exempt_ref] != "skill:" + skill:
                errors.append("%s：豁免 %s 的台账对象为 %r，不是 skill:%s"
                              % (where, exempt_ref, exempt_ledger[exempt_ref], skill))
        if rec["case_id"] not in cases_by_id:
            errors.append("%s：case_id %s 不在冻结用例清单中（verifier 不得私改用例）"
                          % (where, rec["case_id"]))
    return errors


# ------------------------------------------------------------------ gate ----

def gate_skill(root, skill, cases_by_id, exempt_ledger):
    """T1 §5 门禁判定输入：缺 findings.json = 未过门；core 全 confirmed；
    未 confirmed 项须有效豁免；safety 用例不可豁免；extended 不阻塞。

    返回 (ok, 核心通过数, 核心总数, 阻塞项, 豁免项, 仅报告项)。
    """
    blocking, exempted, report = [], [], []
    path = os.path.join(root, ADVERSARIAL_REL, skill, "findings.json")
    if not os.path.isfile(path):
        return False, 0, 0, ["缺 findings.json：未过门（T1 §5 门禁规则）"], exempted, report
    current = {}  # case_id -> 最新 record（records 追加式，同 case_id 取最后一条）
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for rec in data.get("records", []):
        current[rec["case_id"]] = rec
    core_total = core_pass = 0
    for case in cases_by_id.values():
        rec = current.get(case["case_id"])
        if rec is None:
            if case["priority"] == "core":
                core_total += 1
                blocking.append("%s：core 用例无三态记录" % case["case_id"])
            else:
                report.append("%s：extended 用例无记录（不阻塞）" % case["case_id"])
            continue
        confirmed = rec["verdict"] == "confirmed"
        if case["priority"] == "core":
            core_total += 1
            if confirmed:
                core_pass += 1
                continue
            if case.get("safety"):
                blocking.append("%s：safety 用例 verdict=%s 且不可豁免（T1 §5 禁令）"
                                % (case["case_id"], rec["verdict"]))
            elif rec["verdict"] == "rejected":
                blocking.append("%s：rejected 为终态，无豁免通道（修复回 skill 跟踪）" % case["case_id"])
            else:
                ref = rec.get("exempt_ref", "")
                if ref and ref in exempt_ledger and exempt_ledger[ref] == "skill:" + skill:
                    exempted.append("%s：needs_validation，豁免 %s（人工留痕）" % (case["case_id"], ref))
                else:
                    blocking.append("%s：verdict=%s 且无有效豁免" % (case["case_id"], rec["verdict"]))
        elif not confirmed:
            note = "%s：extended 用例 verdict=%s（不阻塞）" % (case["case_id"], rec["verdict"])
            if case.get("safety") and rec["verdict"] != "confirmed":
                note += "——safety 用例不可豁免，仅不阻塞 extended 汇报"
            report.append(note)
    return (not blocking), core_pass, core_total, blocking, exempted, report


# ------------------------------------------------------------------ cli ----

def cmd_cases(args):
    root = args.root
    errors = []
    if args.all:
        _, errors = load_all_case_ids(root)
    else:
        _, _, errs = load_cases(root, args.skill)
        errors = errs
    print("[cases] %s：%s" % ("全部" if args.all else args.skill,
                              "PASS" if not errors else "FAIL"))
    return fail_out(errors)


def cmd_check(args):
    root = args.root
    exempt_ledger = load_exempt_ledger(args.exemptions)
    all_cases, load_errors = load_all_case_ids(root)
    errors = list(load_errors)
    skills = list_case_skills(root) if args.all else [args.skill]
    for skill in skills:
        if skill not in all_cases:
            errors.append("%s: 缺 %s/%s/cases.jsonl（未过门）" % (skill, ADVERSARIAL_REL, skill))
        cases = {c["case_id"]: c for c in all_cases.get(skill, [])}
        errs = check_records(root, skill, cases, exempt_ledger)
        print("[check] %s：%s（%d 条记录校验）"
              % (skill, "PASS" if not errs else "FAIL",
                 _record_count(root, skill)))
        errors.extend("%s: %s" % (skill, e) for e in errs)
    return fail_out(errors)


def _record_count(root, skill):
    path = os.path.join(root, ADVERSARIAL_REL, skill, "findings.json")
    if not os.path.isfile(path):
        return 0
    try:
        with open(path, encoding="utf-8") as f:
            return len(json.load(f).get("records", []))
    except ValueError:
        return 0


def cmd_gate(args):
    root = args.root
    exempt_ledger = load_exempt_ledger(args.exemptions)
    all_cases, load_errors = load_all_case_ids(root)
    errors = list(load_errors)
    skills = list_case_skills(root) if args.all else [args.skill]
    ok_all = not load_errors
    report = []
    for skill in skills:
        if skill not in all_cases:
            load_errors.append("%s: 缺 %s/%s/cases.jsonl（未过门）" % (skill, ADVERSARIAL_REL, skill))
        cases = {c["case_id"]: c for c in all_cases.get(skill, [])}
        errs = check_records(root, skill, cases, exempt_ledger)
        if errs:
            ok = False
            blocking = ["记录校验未过（见 check）：%d 条" % len(errs)] + errs[:3]
            exempted, notes, core_pass, core_total = [], [], 0, 0
        else:
            ok, core_pass, core_total, blocking, exempted, notes = gate_skill(
                root, skill, cases, exempt_ledger)
        ok_all = ok_all and ok
        errors.extend("%s: %s" % (skill, e) for e in blocking)
        report.append({"skill": skill, "ok": ok,
                       "core_confirmed": core_pass, "core_total": core_total,
                       "exempt": exempted, "blocking": blocking, "notes": notes})
        print("[gate] %s：%s（core %d/%d confirmed，豁免 %d，阻塞 %d）"
              % (skill, "PASS" if ok else "FAIL", core_pass, core_total,
                 len(exempted), len(blocking)))
        for line in blocking:
            print("  - " + line)
        for line in exempted:
            print("  ~ " + line)
        for line in notes:
            print("  · " + line)
    if args.json:
        print(json.dumps({"ok": ok_all, "skills": report}, ensure_ascii=False, indent=2))
    return 0 if ok_all else 1


TEMPLATE_EXAMPLE = {
    "record_id": "AV-20261025-<skill>-01",
    "case_id": "AC-<skill>-POS01",
    "verdict": "confirmed",
    "evidence": "<构造样例> 重跑正文示例命令：退出码 0，输出含命中条目（摘录见验收记录路径）",
    "falsification_attempts": [
        "<构造样例> 尝试 A：换输入变体重跑，观察与主张一致，未推翻",
    ],
    "unresolved_fact": "",
    "disproved_by": "",
    "verifier": "<verifier 会话标识，不得等于 author>",
    "verifier_model": "<模型披露字段>",
    "author": "<skill 内容作者会话标识>",
    "date": "2026-10-25",
    "case_error": "",
    "exempt_ref": "",
}


def cmd_template(args):
    print('=== findings.json 起始骨架（tests/adversarial/%s/findings.json）===' % args.skill)
    print('{"records": []}')
    if args.example:
        print('=== 构造样例记录（仅供对照字段，不得原样入库；判据见 T1 §5）===')
        print(json.dumps({"records": [TEMPLATE_EXAMPLE]}, ensure_ascii=False, indent=2))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=REPO, help="仓库根目录（默认本仓库，测试可指向夹具）")
    ap.add_argument("--exemptions", default=None,
                    help="工程门豁免台账路径（默认 <root>/%s）" % DEFAULT_EXEMPTIONS_REL)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("cases", help="校验用例清单（只读，冻结文件）")
    p.add_argument("skill", nargs="?", default=None)
    p.add_argument("--all", action="store_true")
    p = sub.add_parser("check", help="校验 findings.json 三态记录与独立性")
    p.add_argument("skill", nargs="?", default=None)
    p.add_argument("--all", action="store_true")
    p = sub.add_parser("gate", help="published 前置条件判定输入（T3 接线 CI）")
    p.add_argument("skill", nargs="?", default=None)
    p.add_argument("--all", action="store_true")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("template", help="打印 findings.json 起始骨架")
    p.add_argument("skill")
    p.add_argument("--example", action="store_true", help="附一条构造样例记录（不得原样入库）")
    args = ap.parse_args(argv)
    if args.exemptions is None:
        args.exemptions = os.path.join(args.root, DEFAULT_EXEMPTIONS_REL)
    if args.cmd in ("cases", "check") and not args.all and not args.skill:
        ap.error("%s 需要指定 skill 或 --all" % args.cmd)
    if args.cmd == "cases":
        return cmd_cases(args)
    if args.cmd == "check":
        return cmd_check(args)
    if args.cmd == "gate":
        if not args.all and not args.skill:
            ap.error("gate 需要指定 skill 或 --all")
        return cmd_gate(args)
    if args.cmd == "template":
        return cmd_template(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
