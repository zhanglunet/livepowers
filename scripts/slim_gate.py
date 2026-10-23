#!/usr/bin/env python3
"""slim_gate —— PRD-148 skill 瘦身门·发布前强制项（T2 最小实现）。

规则（T1 §1/§7）：无瘦身门决策记录，不可标为 published。
published 的判定锚点取本仓事实——一个 skill 同时进入三处登记即视为 published：
  ① `using-livepowers` 路由表（skills/using-livepowers/SKILL.md）
  ② 根 README 技能表（README.md）
  ③ 插件拷贝（plugins/<name>/skills/<skill>/）
（即 PRD-147 条目 E-D04 的三处。using-livepowers 本身是路由表本体，①按在位计。）

存量豁免：PRD-078 已做一轮事后全量审计，存量全量巡检不在本期（T1 §1）。
基线清单 docs/slim-gate/baseline-2026-10-23.md 记录启用日的 21 个存量 skill，
基线内的 skill 不要求补记录；基线外（新增/大改后发布）的 published skill 必须
有 decision: approved 的决策记录，否则本脚本报告失败（CI 打回）。

决策记录：docs/slim-gate/records/<YYYYMMDD>-<skill-slug>.md，YAML frontmatter
字段见 templates/slim-gate-record.md（T1 §3 模板）。记录有效性要求：
  - 必填 record / skill / decision；decision ∈ 五值枚举；
  - proposer 不得与 reviewer 相同（生成者 ≠ 采纳人，T1 §3）；
  - 同一 skill 多条记录时取 date 最大的一条（终态不可逆，翻案须新记录引用旧 ID）。

用法：
    python3 scripts/slim_gate.py             # 全量检查（违规退出 1）
    python3 scripts/slim_gate.py --report-only
不自动删除、不自动修改任何已发布 skill（PRD 非目标红线）。
"""
import argparse
import datetime
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DECISIONS = ("approved", "merged", "rejected", "downgraded", "deferred")
REQUIRED_KEYS = ("record", "skill", "decision")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def parse_frontmatter(path):
    """极简 YAML 子集解析：顶层数值/字符串 + 一层嵌套（ladder:）。"""
    text = read(path)
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return None, "缺 frontmatter（--- ... ---）"
    fm, problems = {}, []
    current = None
    for raw in m.group(1).splitlines():
        s = raw.rstrip()
        if not s.strip() or s.strip().startswith("#"):
            continue
        if ":" not in s:
            problems.append("无法解析的行：%s" % s.strip())
            continue
        indent = len(s) - len(s.lstrip())
        k, v = s.strip().split(":", 1)
        v = v.strip().strip('"').strip("'").strip()
        if indent == 0:
            if v == "":
                fm[k] = {}
                current = k
            else:
                fm[k] = v
                current = None
        elif current:
            fm[current][k] = v
        else:
            problems.append("缩进行不在任何键下：%s" % s.strip())
    return fm, problems


def skills_root(repo=REPO):
    root = os.path.join(repo, "skills")
    return sorted(p for p in os.listdir(root) if os.path.isdir(os.path.join(root, p)))


def load_baseline(repo=REPO):
    """基线清单：docs/slim-gate/baseline-*.md 里的 `- \\`name\\`` 列表项。"""
    names = set()
    d = os.path.join(repo, "docs", "slim-gate")
    if not os.path.isdir(d):
        return names
    for fn in sorted(os.listdir(d)):
        if not (fn.startswith("baseline-") and fn.endswith(".md")):
            continue
        for m in re.finditer(r"^\s*-\s*`([a-z0-9-]+)`", read(os.path.join(d, fn)), re.M):
            names.add(m.group(1))
    return names


def load_records(repo=REPO):
    """枚举决策记录，返回 (按 skill 归组的最新有效记录, 无效记录清单)。"""
    latest, invalid = {}, []
    rdir = os.path.join(repo, "docs", "slim-gate", "records")
    if not os.path.isdir(rdir):
        return latest, invalid
    for fn in sorted(os.listdir(rdir)):
        if not fn.endswith(".md") or fn == "README.md":
            continue
        path = os.path.join(rdir, fn)
        fm, problems = parse_frontmatter(path)
        if fm is None:
            invalid.append((fn, problems))
            continue
        problems += ["缺必填字段：%s" % k for k in REQUIRED_KEYS if k not in fm]
        if fm.get("decision") and fm["decision"] not in DECISIONS:
            problems.append("decision=%r 不在枚举 %s" % (fm["decision"], DECISIONS))
        if fm.get("proposer") and fm.get("proposer") == fm.get("reviewer"):
            problems.append("proposer 与 reviewer 相同（生成者 ≠ 采纳人，T1 §3）")
        if problems:
            invalid.append((fn, "；".join(problems)))
            continue
        skill = fm["skill"]
        prev = latest.get(skill)
        if prev is None or str(fm.get("date", "")) >= str(prev.get("date", "")):
            fm["_file"] = fn
            latest[skill] = fm
    return latest, invalid


def published_map(repo=REPO, names=None):
    """三处登记锚点：返回 {skill: [未命中的锚点]}（空列表 = 已发布）。"""
    names = names if names is not None else skills_root(repo)
    router = read(os.path.join(repo, "skills", "using-livepowers", "SKILL.md")) \
        if os.path.isfile(os.path.join(repo, "skills", "using-livepowers", "SKILL.md")) else ""
    readme = read(os.path.join(repo, "README.md")) \
        if os.path.isfile(os.path.join(repo, "README.md")) else ""
    out = {}
    for n in names:
        miss = []
        # ① 路由表（using-livepowers 是表本体，按在位计）
        if n != "using-livepowers" and "`%s`" % n not in router:
            miss.append("①using-livepowers 路由表")
        # ② 根 README 技能表
        if "`%s`" % n not in readme:
            miss.append("②根 README 技能表")
        # ③ 插件拷贝
        proot = os.path.join(repo, "plugins")
        copied = False
        if os.path.isdir(proot):
            for p in os.listdir(proot):
                if os.path.isdir(os.path.join(proot, p, "skills", n)):
                    copied = True
                    break
        if not copied:
            miss.append("③插件拷贝 plugins/*/skills/%s/" % n)
        out[n] = miss
    return out


def check(repo=REPO):
    """返回 (违规清单, 报告行)。违规 = 基线外的 published skill 无 approved 记录。"""
    names = skills_root(repo)
    baseline = load_baseline(repo)
    records, invalid = load_records(repo)
    pub = published_map(repo, names)
    violations, notes = [], []

    unlisted = [n for n in names if n not in baseline]
    for n in unlisted:
        if pub.get(n) == []:
            rec = records.get(n)
            if rec is None:
                violations.append(
                    "skill `%s` 已三处登记（published）但缺瘦身门决策记录："
                    "补 docs/slim-gate/records/<YYYYMMDD>-%s.md（模板 templates/slim-gate-record.md），"
                    "或走 rejected/merged 处置" % (n, n))
            elif rec["decision"] != "approved":
                violations.append(
                    "skill `%s` 已三处登记（published），但最新记录 %s 的 decision=%s 不是 approved"
                    % (n, rec["_file"], rec["decision"]))
            elif str(rec.get("status")) == "provisional":
                notes.append("skill `%s` 的批准记录 %s 仍是 provisional（仅构造证据，观察清单），"
                             "真实记录补齐后转 final" % (n, rec["_file"]))

    for fn, why in invalid:
        # 无效记录不直接违规（可能只是草稿），但发布判定不会采信它
        notes.append("记录 %s 无效（%s），gate 不采信" % (fn, why))

    for n in unlisted:
        if pub.get(n):
            notes.append("skill `%s` 未三处登记（缺 %s）：未视为 published，不要求记录"
                         % (n, "、".join(pub[n])))

    lines = []
    lines.append("瘦身门发布检查（PRD-148/T2）：无决策记录不可标为 published")
    lines.append("published 锚点：①路由表 ②根 README 技能表 ③插件拷贝（T1 §1）")
    lines.append("skills：%d 个；基线存量：%d 个；基线外：%d 个；决策记录：%d 条（无效 %d 条）"
                 % (len(names), len(baseline), len(unlisted), len(records), len(invalid)))
    if not os.path.isfile(os.path.join(REPO, "templates", "slim-gate-record.md")):
        notes.append("缺决策记录模板 templates/slim-gate-record.md")
    lines.append("-" * 64)
    for n in unlisted:
        rec = records.get(n)
        is_pub = pub.get(n) == []
        state = "published" if is_pub else "未发布（缺 %s）" % "、".join(pub[n])
        rinfo = ("记录 %s：decision=%s status=%s"
                 % (rec["_file"], rec["decision"], rec.get("status", "?"))
                 if rec else "无记录")
        ok = (not is_pub) or (rec is not None and rec["decision"] == "approved")
        lines.append("%s%-40s %-28s %s" % ("OK " if ok else "!! ", n, state, rinfo))
    if not unlisted:
        lines.append("（全部 skill 均在基线内，无新增发布需要核对）")
    lines.append("-" * 64)
    if violations:
        lines.append("FAIL：%d 条违规" % len(violations))
        lines += ["  - %s" % v for v in violations]
    else:
        lines.append("PASS：基线外 published skill 均有 approved 决策记录")
    for note in notes:
        lines.append("提示：%s" % note)
    return violations, lines


def head_sha(repo):
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             cwd=repo, capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def main(argv=None):
    ap = argparse.ArgumentParser(description="PRD-148 瘦身门发布检查（只报告，不删不改）")
    ap.add_argument("--report-only", action="store_true", help="恒退出 0")
    args = ap.parse_args(argv)
    violations, lines = check(REPO)
    print("HEAD：%s；日期：%s" % (head_sha(REPO), datetime.date.today().isoformat()))
    print("\n".join(lines))
    if args.report_only:
        return 0
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
