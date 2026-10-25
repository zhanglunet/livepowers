#!/usr/bin/env python3
"""adversarial_gate —— PRD-171/T3：对抗验收发布门禁（非 confirmed 不可 published）。

规范：docs/plans/2026-10-25-adversarial-acceptance.md（PRD-171/T1，trend issue
#855）§5；本任务 trend issue #857。判定输入由 scripts/adversarial_verify.py 的
`gate` 命令给出（PRD-171/T2 落），本脚本把判定接进发布面与 CI：

1. published 锚点**沿用瘦身门定稿口径**（三处登记：① `using-livepowers`
   路由表 ② 根 README 技能表 ③ `plugins/<name>/skills/` 拷贝），直接复用
   scripts/slim_gate.py 的 `published_map`，不另立一套锚点——对抗验收卡在
   三处登记之前：没有对抗验收记录，不得开始三处登记；
2. **基线存量豁免**：docs/adversarial-gate/baseline-*.md 登记的存量 skill
   不要求对抗验收记录（口径对齐瘦身门基线：存量全量巡检不在本期）；入组
   验收通过后可移出基线，移出即按基线外规则强制；
3. **基线外强制**：三处登记（published）的 skill 必须过对抗验收门——
   - 存在 tests/adversarial/<skill>/cases.jsonl（用例清单，缺目录即未过门）；
   - findings.json 判定 PASS：core 用例全部 confirmed，未 confirmed 项均有
     有效豁免（exempt_ref 指向工程门豁免台账
     docs/engineering-checklist/exemptions.md 里登记的 EX- ID，且对象为该
     skill）；**safety 用例一律不可豁免**；rejected 无豁免通道；extended
     不阻塞；**缺 findings.json = 未过门（缺 findings 即拒）**。

门禁链位置：选题（PRD-078）→ 瘦身门（PRD-148）→ 工程门（PRD-147）→
**对抗验收（本门，动态证伪）** → 收录（PRD-094）。

用法：
    python3 scripts/adversarial_gate.py                # 全量检查（违规退出 1）
    python3 scripts/adversarial_gate.py --report-only  # 恒退出 0
    python3 scripts/adversarial_gate.py --root <目录>   # 测试可指向夹具目录
只报告，不自动修改任何文件（对齐既有门禁口径）。Python 3.9 兼容。
"""
import argparse
import datetime
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adversarial_verify as av  # noqa: E402
import slim_gate as sg  # noqa: E402

BASELINE_DIR = os.path.join("docs", "adversarial-gate")
EXEMPT_LEDGER_REL = av.DEFAULT_EXEMPTIONS_REL  # docs/engineering-checklist/exemptions.md


def load_baseline(repo=REPO):
    """基线清单：docs/adversarial-gate/baseline-*.md 里的 `- \\`name\\`` 列表项。"""
    names = set()
    d = os.path.join(repo, BASELINE_DIR)
    if not os.path.isdir(d):
        return names
    for fn in sorted(os.listdir(d)):
        if not (fn.startswith("baseline-") and fn.endswith(".md")):
            continue
        path = os.path.join(d, fn)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for m in re.finditer(r"^\s*-\s*`([a-z0-9-]+)`", text, re.M):
            names.add(m.group(1))
    return names


def check(repo=REPO):
    """返回 (违规清单, 报告行)。

    违规 = 基线外的 published skill 未过对抗验收门（缺用例清单 / 缺
    findings.json / core 未全 confirmed 且无有效豁免 / 记录或用例校验未过）。
    """
    names = sg.skills_root(repo)
    baseline = load_baseline(repo)
    pub = sg.published_map(repo, names)
    exempt_ledger = av.load_exempt_ledger(os.path.join(repo, EXEMPT_LEDGER_REL))
    all_cases, load_errors = av.load_all_case_ids(repo)
    out_scope = [n for n in names if n not in baseline]
    out_scope_set = set(out_scope)

    violations, notes, table = [], [], []

    # 用例清单的全仓校验错误：基线外 published 的算违规，其余只提示。
    load_err_pub = set()
    for e in load_errors:
        sk = e.split(":", 1)[0]
        if sk in out_scope_set and pub.get(sk) == []:
            violations.append("skill `%s` 用例清单校验未过：%s" % (sk, e.split(":", 1)[1]))
            load_err_pub.add(sk)
        else:
            notes.append("用例清单校验提示：%s" % e)

    for n in out_scope:
        miss = pub.get(n)
        if miss is None:
            continue
        if miss:
            notes.append("skill `%s` 未三处登记（缺 %s）：未视为 published，"
                         "不要求对抗验收记录" % (n, "、".join(miss)))
            table.append(("OK ", n, "未发布（缺 %s）" % "、".join(miss), "不要求"))
            continue
        if n in load_err_pub:
            table.append(("!! ", n, "published", "用例清单校验未过（见违规）"))
            continue
        cases = all_cases.get(n) or []
        if not cases:
            violations.append(
                "skill `%s` 已三处登记（published）但缺对抗验收用例清单："
                "补 tests/adversarial/%s/cases.jsonl（T1 §4，缺目录即未过门）" % (n, n))
            table.append(("!! ", n, "published", "缺用例清单：未过门"))
            continue
        if not os.path.isfile(os.path.join(repo, av.ADVERSARIAL_REL, n, "findings.json")):
            violations.append(
                "skill `%s` 已三处登记（published）但缺 findings.json：未过门"
                "（缺 findings 即拒，T1 §5 门禁规则）" % n)
            table.append(("!! ", n, "published", "缺 findings.json：未过门"))
            continue
        cases_by_id = {c["case_id"]: c for c in cases}
        rec_errs = av.check_records(repo, n, cases_by_id, exempt_ledger)
        if rec_errs:
            violations.append("skill `%s` 三态记录校验未过（%d 条）：%s"
                              % (n, len(rec_errs), "；".join(rec_errs[:3])))
            table.append(("!! ", n, "published", "记录校验未过（见违规）"))
            continue
        ok, core_pass, core_total, blocking, exempted, _r = av.gate_skill(
            repo, n, cases_by_id, exempt_ledger)
        state = "gate PASS（core %d/%d confirmed，豁免 %d）" % (core_pass, core_total, len(exempted))
        if not ok:
            violations.append(
                "skill `%s` 已三处登记（published）但对抗验收未过门（非 confirmed "
                "不可 published）：%s" % (n, "；".join(blocking)))
            table.append(("!! ", n, "published", "gate FAIL：%s" % "；".join(blocking[:2])))
        else:
            table.append(("OK ", n, "published", state))

    entered = [n for n in names if n in baseline and all_cases.get(n)]
    if entered:
        notes.append("基线内已入对抗程序（有用例清单）：%s——findings 随 T5 批次补齐，"
                     "验收通过后移出基线即按基线外规则强制" % "、".join(entered))

    lines = []
    lines.append("对抗验收发布门禁（PRD-171/T3）：非 confirmed 不可 published")
    lines.append("published 锚点：沿用瘦身门三处登记（scripts/slim_gate.py published_map）")
    lines.append("skills：%d 个；基线存量：%d 个；基线外：%d 个；已入对抗程序：%d 个"
                 % (len(names), len(baseline), len(out_scope),
                    len([n for n in names if all_cases.get(n)])))
    lines.append("-" * 64)
    for mark, n, state, info in table:
        lines.append("%s%-40s %-12s %s" % (mark, n, state, info))
    if not table:
        lines.append("（基线外无 published skill，无新增发布需要核对）")
    lines.append("-" * 64)
    if violations:
        lines.append("FAIL：%d 条违规" % len(violations))
        lines += ["  - %s" % v for v in violations]
    else:
        lines.append("PASS：基线外 published skill 均过对抗验收门")
    for note in notes:
        lines.append("提示：%s" % note)
    return violations, lines


def head_sha(repo):
    return sg.head_sha(repo)


def main(argv=None):
    ap = argparse.ArgumentParser(description="PRD-171/T3 对抗验收发布门禁（只报告，不删不改）")
    ap.add_argument("--root", default=REPO, help="仓库根目录（默认本仓库，测试可指向夹具）")
    ap.add_argument("--report-only", action="store_true", help="恒退出 0")
    args = ap.parse_args(argv)
    violations, lines = check(args.root)
    print("HEAD：%s；日期：%s" % (head_sha(args.root), datetime.date.today().isoformat()))
    print("\n".join(lines))
    if args.report_only:
        return 0
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
