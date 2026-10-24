#!/usr/bin/env python3
"""eng_checklist —— PRD-147 工程标准 checklist 机检脚本（T2 最小实现）。

条目与口径以 PRD-147/T1 checklist v0.1 为准（trend issue #735，草案见 PR #86
的 docs/plans/2026-10-23-compound-eng-checklist.md）。本脚本只做机检：
能自动查的查（文件存在性、tests/ 三件套、触发用例数、登记三处、凭据 /
识别信息模式扫描、manifest 路径等），不能自动查的输出"人工"标记，
不打自由分、不代改任何文件（评审只报告，修复回各 skill 跟踪，即 T4）。

打分口径（T1 第 2 节）：0 / 1 / 2；2=完全满足，1=部分满足，0=缺失或违反；
不适用标 N/A（写明理由，不计入分母）；豁免读 docs/engineering-checklist/
exemptions.md 台账，输出 EXEMPT（从达标率分母剔除）。

用法：
    python3 scripts/eng_checklist.py --plugin livepowers-night   # 插件走查（含其 skills 与仓库级条目）
    python3 scripts/eng_checklist.py --skill night-loop-planning
    python3 scripts/eng_checklist.py --repo                      # 只打仓库级条目
    python3 scripts/eng_checklist.py                             # 全仓（21 skills + 6 插件 + 仓库）
    追加：--format markdown|text（默认 text）、--out <file>、--report-only

退出码：默认 FAIL=1、其余 0；--report-only 恒 0（CI 用，当前主分支尚未全绿，
门禁强制在 T4/T5 收口后再开）。
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 机检覆盖的发布面（识别信息 / 凭据扫描只扫这些；tests/ 的构造样例不算发布面，
# 且 TestNoIdentifyingInfo 另有全仓策略扫描）。
PUBLISH_DIRS = ("skills", "plugins", "docs", "examples", "hooks",
                "scripts", "templates", "commands", "bin", "functions")
SELF_PATH = os.path.abspath(__file__)

# E-条目登记表：编号 -> (类别, 级别, 适用层, 一句话要求)。
# 级别：阻断 / 常规（T1 第 2 节）。机检方式见各 check_* 函数 docstring。
ITEMS = {
    "E-T01": ("测试", "阻断", "skill", "tests/<name>/test_examples.py 存在且三层（契约/示例/反例）可辨"),
    "E-T02": ("测试", "阻断", "skill", "tests/triggers/<name>.jsonl ≥3 正例、≥2 反例"),
    "E-T03": ("测试", "阻断", "skill", "示例可复现、反例不误触发（需最近一次 discover 输出）"),
    "E-T04": ("测试", "阻断", "plugin", "plugins/<name>/skills/ 与根 skills/ 逐字节一致"),
    "E-T05": ("测试", "常规", "repo", "CI 三版本矩阵全绿（Python 3.9/3.11/3.13 + denylist job）"),
    "E-D01": ("文档", "阻断", "plugin", "插件 README 四节：用途/安装/快速上手/配置项"),
    "E-D02": ("文档", "常规", "skill", "SKILL.md 正文 ≤500 行（简洁判读另行人工）"),
    "E-D03": ("文档", "阻断", "skill", "引用完整：反引号 skill 名、skills/ 路径、同目录文件、lp 命令语义"),
    "E-D04": ("文档", "阻断", "skill", "三处登记：using-livepowers 路由表 + 根 README 技能表 + CHANGELOG"),
    "E-D05": ("文档", "常规", "skill", "description 双语（英文触发条件 + 中文一句话）"),
    "E-X01": ("示例", "阻断", "skill", "正文 ≥1 个可抄示例：命令代码块 + 预期结果（退出码或输出语义）"),
    "E-X02": ("示例", "常规", "repo", "examples/walkthrough.sh 与最小链示例在位（实跑记录另行人工）"),
    "E-X03": ("示例", "阻断", "skill", "示例数据脱敏：TestNoIdentifyingInfo 在位 + 抽查（抽查另行人工）"),
    "E-X04": ("示例", "常规", "repo", "新形态最小示例在位（templates/parallel-experts/ README 文件表）"),
    "E-S01": ("安全", "阻断", "plugin/repo", "凭据不入库：无字面 token/密钥/密码（${VAR} 占位除外）"),
    "E-S02": ("安全", "阻断", "plugin/repo", "manifest 路径全相对、不逃逸、目标存在"),
    "E-S03": ("安全", "常规", "skill", "allowed-tools 声明 ⊇ 正文工具引用"),
    "E-S04": ("安全", "阻断", "skill", "写操作类正文含先仿真后执行并挂 oltp-action-safety 口径"),
    "E-S05": ("安全", "阻断", "skill/plugin/repo", "无真实主机名/IP/账号/密钥（占位符除外）"),
}

# E-S04 的写操作类粗判关键词（强标记：命中才机检；否则交人工分类）。
WRITE_OP_STRONG = re.compile(
    r"生产库|线上库|落库|DELETE\s+FROM|INSERT\s+INTO|UPDATE\s+[a-zA-Z_]")
# oltp-action-safety 是本条口径的来源，自指不打分。
E_S04_STANDARD_SOURCE = "oltp-action-safety"

CRED_PATTERNS = [
    ("字面密钥赋值", re.compile(
        r"(?i)\b(api[_-]?key|secret|password|passwd|token)\b\s*[:=]\s*"
        r"[\"'][^\"'${}<]{12,}[\"']")),
    ("AWS AccessKey", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("私钥文件头", re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\bghp_[A-Za-z0-9]{20,}\b")),
]
PRIV_IP = re.compile(
    r"\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}"
    r"|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b")

TOOL_NAMES = ("Bash", "Read", "Write", "Edit", "MultiEdit", "Grep", "Glob",
              "Task", "WebFetch", "WebSearch", "TodoWrite", "NotebookEdit")
# 与 tests/test_repo.py 同口径的豁免引用名。
REF_ALLOW = {"model-a", "model-b"}


class Result:
    """单条机检结果。score=None 表示"人工"（机检不可判）。"""

    def __init__(self, item, obj, score, status, evidence, note=""):
        self.item = item
        self.obj = obj                      # "skill:x" / "plugin:x" / "repo"
        self.score = score                  # 2/1/0/None(人工)
        self.status = status                # PASS/PARTIAL/FAIL/MANUAL/EXEMPT/NA
        self.evidence = evidence or []
        self.note = note

    @property
    def level(self):
        return ITEMS[self.item][1]

    def line(self):
        s = {2: "2", 1: "1", 0: "0", None: "人工"}.get(self.score, "?")
        head = "%s [%s] %-7s %s -> %s" % (self.item, self.level, self.status,
                                          self.obj, s)
        detail = "".join("\n      %s" % e for e in self.evidence)
        if self.note:
            detail += "\n      说明：%s" % self.note
        return head + detail


def parse_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}, text
    fm = {}
    for raw in m.group(1).splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or ":" not in s:
            continue
        k, v = s.split(":", 1)
        fm[k.strip()] = v.strip()
    return fm, text[m.end():]


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def iter_publish_files(root, subdirs=None):
    """遍历发布面文件（跳过 tests/、.git、二进制）。"""
    if subdirs is None:
        subdirs = PUBLISH_DIRS
    for d in subdirs:
        base = os.path.join(root, d)
        for cur, dirs, files in os.walk(base):
            dirs[:] = [x for x in dirs if x not in (".git", "__pycache__",
                                                    "node_modules")]
            for f in files:
                p = os.path.join(cur, f)
                if os.path.abspath(p) == SELF_PATH:
                    continue
                try:
                    read(p)
                except (UnicodeDecodeError, OSError):
                    continue
                yield p


class Checker:
    def __init__(self, repo=REPO, exemptions=None):
        self.repo = repo
        self.skills_root = os.path.join(repo, "skills")
        self.skills = sorted(p for p in os.listdir(self.skills_root)
                             if os.path.isdir(os.path.join(self.skills_root, p)))
        self.exemptions = exemptions or {}
        self.manual_notes = []      # 机检报告之外待人工补的复核项

    # ---------- 通用小工具 ----------

    def skill_text(self, name):
        p = os.path.join(self.skills_root, name, "SKILL.md")
        return read(p) if os.path.isfile(p) else ""

    def exempted(self, item, obj):
        return self.exemptions.get((obj, item))

    def finish(self, item, obj, score, status, evidence, note=""):
        ex = self.exempted(item, obj)
        if ex and ITEMS[item][1] != "阻断":
            return Result(item, obj, None, "EXEMPT",
                          ["豁免 %s（见台账）" % ex, "原机检：%s" % status],
                          "EXEMPT 不计入达标率分母")
        if ex:
            self.manual_notes.append(
                "台账违规：%s 对 %s 是阻断级条目，不可豁免（T1 规则①），本次按原分计" % (item, obj))
        return Result(item, obj, score, status, evidence, note)

    # ---------- 测试类 ----------

    def check_t01(self, name):
        d = os.path.join(self.repo, "tests", name)
        f = os.path.join(d, "test_examples.py")
        if not os.path.isfile(f):
            return self.finish("E-T01", "skill:" + name, 0, "FAIL",
                               ["缺 %s" % os.path.relpath(f, self.repo)])
        text = read(f)
        layers = [m for m in ("契约", "示例", "反例",
                              "Contract", "Examples", "Negative",
                              "L1", "L2", "L3") if m in text]
        if len(layers) >= 3:
            return self.finish("E-T01", "skill:" + name, 2, "PASS",
                               ["%s 存在" % os.path.relpath(f, self.repo),
                                "三层标记：%s" % ", ".join(layers[:6])])
        return self.finish("E-T01", "skill:" + name, 1, "PARTIAL",
                           ["%s 存在" % os.path.relpath(f, self.repo)],
                           "三层（契约/示例/反例）不可辨，需人工核对测试结构")

    def check_t02(self, name):
        f = os.path.join(self.repo, "tests", "triggers", name + ".jsonl")
        rel = os.path.relpath(f, self.repo)
        if not os.path.isfile(f):
            return self.finish("E-T02", "skill:" + name, 0, "FAIL", ["缺 " + rel])
        pos = neg = bad = 0
        for line in read(f).splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except ValueError:
                bad += 1
                continue
            pos += 1 if name in d.get("expect", []) else 0
            neg += 1 if name in d.get("reject", []) else 0
        ev = ["%s：正例 %d、反例 %d" % (rel, pos, neg)]
        if bad:
            ev.append("%d 行无法解析" % bad)
        if pos >= 3 and neg >= 2 and not bad:
            return self.finish("E-T02", "skill:" + name, 2, "PASS", ev)
        return self.finish("E-T02", "skill:" + name, 1, "PARTIAL", ev,
                           "门槛：≥3 正例、≥2 反例")

    def check_t03(self, name):
        f = os.path.join(self.repo, "tests", name, "test_examples.py")
        skips = read(f).count("skipIf") if os.path.isfile(f) else 0
        return self.finish("E-T03", "skill:" + name, None, "MANUAL",
                           ["skipIf 标注 %d 处（%s）" % (skips, os.path.relpath(f, self.repo)),
                            "需最近一次 python -m unittest discover -s tests 输出核对"],
                           "机检不可判：需最近一次全量输出与逐条 skip 理由")

    def check_t04(self, plugin):
        proot = os.path.join(self.repo, "plugins", plugin, "skills")
        if not os.path.isdir(proot):
            return self.finish("E-T04", "plugin:" + plugin, 0, "FAIL",
                               ["缺 plugins/%s/skills/" % plugin])
        drift, missing = [], []
        for cur, dirs, files in os.walk(proot):
            dirs[:] = [d for d in dirs if d not in ("__pycache__",)]
            for f in files:
                p = os.path.join(cur, f)
                skill = os.path.relpath(p, proot).split(os.sep)[0]
                root_f = os.path.join(self.skills_root, os.path.relpath(p, proot))
                if not os.path.isfile(root_f):
                    missing.append(os.path.relpath(p, self.repo))
                elif read(p) != read(root_f):
                    drift.append(os.path.relpath(p, self.repo))
        ev = ["比对 plugins/%s/skills/ 与根 skills/ 共 %d 个文件"
              % (plugin, sum(len(fs) for _, _, fs in os.walk(proot)))]
        if missing:
            ev.append("根 skills/ 缺对应文件：%s" % missing)
        if drift:
            ev.append("内容漂移：%s" % drift)
        if not drift and not missing:
            return self.finish("E-T04", "plugin:" + plugin, 2, "PASS", ev)
        return self.finish("E-T04", "plugin:" + plugin, 0, "FAIL", ev)

    def check_t05(self):
        f = os.path.join(self.repo, ".github", "workflows", "test.yml")
        ok = False
        if os.path.isfile(f):
            t = read(f)
            ok = all(v in t for v in ('"3.9"', '"3.11"', '"3.13"')) and "LP_DENYLIST" in t
        return self.finish("E-T05", "repo", None, "MANUAL",
                           ["test.yml 矩阵与 denylist job 配置%s在位" % ("" if ok else "不")],
                           "机检不可判：需最近一次 CI run 链接（三个 job 全 success）")

    # ---------- 文档类 ----------

    def check_d01(self, plugin):
        f = os.path.join(self.repo, "plugins", plugin, "README.md")
        rel = os.path.relpath(f, self.repo)
        if not os.path.isfile(f):
            return self.finish("E-D01", "plugin:" + plugin, 0, "FAIL", ["缺 " + rel])
        text = read(f)
        intro = text.split("\n## ", 1)[0]
        have = {"用途（开篇简介）": bool(re.search(r"[^\s#>|`-]", intro.split("\n", 2)[-1])),
                "安装": "\n## 安装" in text,
                "快速上手": "\n## 快速上手" in text,
                "配置项": "\n## 配置项" in text}
        missing = [k for k, v in have.items() if not v]
        ev = ["%s 四节核对：%s" % (rel, "、".join(k for k, v in have.items() if v) or "无")]
        if not missing:
            return self.finish("E-D01", "plugin:" + plugin, 2, "PASS", ev)
        return self.finish("E-D01", "plugin:" + plugin, 1, "PARTIAL",
                           ev + ["缺节：%s" % "、".join(missing)],
                           "T1 口径：缺一节即 1 分；缺 README 才记 0")

    def check_d02(self, name):
        text = self.skill_text(name)
        n = len(text.splitlines())
        if n > 500:
            return self.finish("E-D02", "skill:" + name, 0, "FAIL",
                               ["SKILL.md %d 行 > 500" % n])
        self.manual_notes.append("E-D02 skill:%s 行数达标（%d 行），简洁可执行判读需人工" % (name, n))
        return self.finish("E-D02", "skill:" + name, 2, "PASS",
                           ["SKILL.md %d 行 ≤ 500" % n],
                           "简洁判读为人工面（存疑标待复核，T1 口径）")

    def check_d03(self, name):
        text = self.skill_text(name)
        fm, body = parse_frontmatter(text)
        known = set(self.skills) | REF_ALLOW
        broken = []
        for tok in set(re.findall(r"`([a-z][a-z0-9-]{2,})`", body)):
            if "-" in tok and tok not in known and "." not in tok:
                broken.append("反引号引用不存在：`%s`" % tok)
        for ref in set(re.findall(r"skills/([a-z0-9-]+)", body)):
            if ref not in self.skills:
                broken.append("skills/%s 目录不存在" % ref)
        sdir = os.path.join(self.skills_root, name)
        runtime_refs = []
        for f in os.listdir(sdir):
            if not f.endswith(".md"):
                continue
            t = read(os.path.join(sdir, f))
            for ref in set(re.findall(r"`([\w.-]+\.(?:md|json|ya?ml))`", t)):
                if "/" in ref or os.path.isfile(os.path.join(sdir, ref)):
                    continue
                # .md 引用必须存在（与 tests/test_repo.py 安装存活检查同口径）；
                # .json/.yaml 可能是运行时产物名（如链运行目录里的 manifest.json），
                # 缺失降级为待人工，不硬判 0。
                if ref.endswith(".md"):
                    broken.append("%s 引用同目录文件 %s 不存在" % (f, ref))
                else:
                    runtime_refs.append("%s 提到 %s（目录中无此文件，需人工判断是否运行时产物）"
                                        % (f, ref))
        weak = []
        for m in re.finditer(r"`(lp [a-z ]+)`", body):
            window = body[max(0, m.start() - 120):m.end() + 160]
            after = body[m.end():m.end() + 160]
            if not ("退出码" in window or re.search(r"exit\s*\d", window)
                    or re.search(r"[\u4e00-\u9fff]{6,}", after)):
                weak.append(m.group(1))
        ev = broken + runtime_refs + (["lp 命令缺退出码/语义说明：%s" % weak] if weak else [])
        if broken:
            return self.finish("E-D03", "skill:" + name, 0, "FAIL", ev)
        if weak or runtime_refs:
            return self.finish("E-D03", "skill:" + name, 1, "PARTIAL", ev,
                               "引用都在，但命令语义或文件引用需人工复核（T1：同段应有退出码或语义）")
        return self.finish("E-D03", "skill:" + name, 2, "PASS",
                           ["反引号引用、skills/ 路径、同目录文件引用全部在位",
                            "lp 命令均带退出码或语义说明"])

    def check_d04(self, name):
        router = os.path.join(self.skills_root, "using-livepowers", "SKILL.md")
        # using-livepowers 本身就是路由表，自引用按满足计（tests/test_repo.py 同口径豁免）。
        in_router = True if name == "using-livepowers" else "`%s`" % name in read(router)
        where = {
            "using-livepowers 路由表": in_router,
            "根 README 技能表": "`%s`" % name in read(os.path.join(self.repo, "README.md")),
            "CHANGELOG": name in read(os.path.join(self.repo, "CHANGELOG.md")),
        }
        missing = [k for k, v in where.items() if not v]
        ev = ["%s：%s" % (k, "在" if v else "缺") for k, v in where.items()]
        if missing:
            return self.finish("E-D04", "skill:" + name, 0, "FAIL", ev,
                               "缺任一处即 0 分（T1 口径）")
        return self.finish("E-D04", "skill:" + name, 2, "PASS", ev,
                           "新 skill 还须落在 CHANGELOG 的 Unreleased 节（机检不分节，人工注意）")

    def check_d05(self, name):
        fm, _ = parse_frontmatter(self.skill_text(name))
        d = fm.get("description", "")
        has_en = bool(re.search(r"[A-Za-z]", d))
        has_zh = bool(re.search(r"[\u4e00-\u9fff]", d))
        if has_en and has_zh:
            return self.finish("E-D05", "skill:" + name, 2, "PASS",
                               ["description 含英文触发条件与中文一句话"])
        return self.finish("E-D05", "skill:" + name, 1, "PARTIAL",
                           ["description 单一语言：en=%s zh=%s" % (has_en, has_zh)],
                           "只有单一语言即 1 分（T1 口径）")

    # ---------- 示例类 ----------

    def check_x01(self, name):
        _, body = parse_frontmatter(self.skill_text(name))
        expect_rx = r"退出码|exit\s*\d|预期|输出|→|应|结果"
        cmds, with_expect = [], []
        pos = 0
        for b in re.findall(r"```[a-z]*\n(.*?)```", body, re.DOTALL):
            idx = body.find(b, pos)
            pos = (idx + len(b)) if idx >= 0 else pos
            lines = [l for l in b.splitlines() if l.strip()]
            if not lines or not any(re.match(
                    r"\s*(lp|python|bash|sh|npm|npx|git|pytest|unittest)\b", l)
                    for l in lines):
                continue
            cmd = lines[0].strip()
            cmds.append(cmd)
            tail = body[pos:pos + 200]
            before = body[max(0, idx - 200):idx]
            if ("#" in lines[0] or re.search(expect_rx, tail)
                    or re.search(expect_rx, b) or re.search(expect_rx, before)):
                with_expect.append(cmd)
        if not cmds:
            return self.finish("E-X01", "skill:" + name, 0, "FAIL",
                               ["正文找不到命令代码块"])
        if len(with_expect) == len(cmds):
            return self.finish("E-X01", "skill:" + name, 2, "PASS",
                               ["命令示例 %d 个，均带预期结果或语义" % len(cmds)])
        return self.finish("E-X01", "skill:" + name, 1, "PARTIAL",
                           ["命令示例 %d 个，带预期的 %d 个" % (len(cmds), len(with_expect)),
                            "缺预期的示例需人工逐个复核"])

    def check_x02(self):
        walk = os.path.join(self.repo, "examples", "walkthrough.sh")
        chain = os.path.join(self.repo, "skills", "delivery-chain",
                             "examples", "minimal-chain")
        have_w = os.path.isfile(walk)
        have_c = os.path.isdir(chain)
        ev = ["examples/walkthrough.sh：%s" % ("在" if have_w else "缺"),
              "最小链示例 skills/delivery-chain/examples/minimal-chain/：%s"
              % ("在" if have_c else "缺")]
        if have_w and have_c:
            self.manual_notes.append("E-X02 repo：两处示例在位，发版前实跑记录需人工存档")
            return self.finish("E-X02", "repo", 2, "PASS", ev,
                               "机检只验在位；一键走通需每次发版前实跑（T1 口径）")
        if have_w or have_c:
            return self.finish("E-X02", "repo", 1, "PARTIAL", ev)
        return self.finish("E-X02", "repo", 0, "FAIL", ev)

    def check_x03(self, name):
        tr = os.path.join(self.repo, "tests", "test_repo.py")
        wf = os.path.join(self.repo, ".github", "workflows", "test.yml")
        ok = (os.path.isfile(tr) and "TestNoIdentifyingInfo" in read(tr)
              and os.path.isfile(wf) and "TestNoIdentifyingInfo" in read(wf))
        if not ok:
            return self.finish("E-X03", "skill:" + name, 0, "FAIL",
                               ["TestNoIdentifyingInfo 未在位或未接入 CI"])
        self.manual_notes.append("E-X03 skill:%s：denylist 扫描在位，示例业务数据抽查需人工" % name)
        return self.finish("E-X03", "skill:" + name, 2, "PASS",
                           ["TestNoIdentifyingInfo 在 tests/test_repo.py 并接入 test.yml"],
                           "示例数据只用通用业务对象需人工抽查（T1 口径）")

    def check_x04(self):
        d = os.path.join(self.repo, "templates", "parallel-experts")
        if not os.path.isdir(d):
            return self.finish("E-X04", "repo", 0, "FAIL", ["缺 templates/parallel-experts/"])
        readme = os.path.join(d, "README.md")
        ev = ["templates/parallel-experts/ 在位（%d 个文件）"
              % sum(len(fs) for _, _, fs in os.walk(d))]
        if os.path.isfile(readme):
            listed = [f for f in re.findall(r"`([\w./-]+\.\w+)`", read(readme))
                      if "/" not in f]
            ok = all(os.path.isfile(os.path.join(d, f)) for f in listed)
            ev.append("README 文件表核对：README 提到的 %d 个文件%s"
                      % (len(listed), "全部存在" if ok else "存在缺失"))
            if ok:
                return self.finish("E-X04", "repo", 2, "PASS", ev)
            return self.finish("E-X04", "repo", 1, "PARTIAL", ev, "README 文件表与目录不一致")
        return self.finish("E-X04", "repo", 1, "PARTIAL", ev, "缺 README 文件表")

    # ---------- 安全类 ----------

    def scan_patterns(self, subdirs, pats):
        hits = []
        for p in iter_publish_files(self.repo, subdirs):
            text = read(p)
            for label, rx in pats:
                for m in rx.finditer(text):
                    hits.append("%s：%s（%s）"
                                % (os.path.relpath(p, self.repo), label, m.group(0)[:40]))
        return hits

    def check_s01(self, obj, subdirs):
        hits = self.scan_patterns(subdirs, CRED_PATTERNS)
        if hits:
            return self.finish("E-S01", obj, 0, "FAIL", hits)
        ev = ["凭据模式扫描 0 命中（%s）" % "+".join(subdirs)]
        return self.finish("E-S01", obj, 2, "PASS", ev,
                           "机密应一律 ${VAR} 占位并在 manifest variables 声明名")

    def check_s02(self, obj, manifests):
        problems, checked = [], []
        path_keys = ("icon", "source", "skills", "hooks")
        for rel in manifests:
            p = os.path.join(self.repo, rel)
            if not os.path.isfile(p):
                problems.append("缺 %s" % rel)
                continue
            data = json.loads(read(p))
            # 路径解析基准：先按仓库根，再按 manifest 所在插件根（plugins/<name>/）
            bases = [self.repo, os.path.dirname(os.path.dirname(p))]
            items = [data] if isinstance(data, dict) else []
            if isinstance(data, dict):
                items += [pl for pl in data.get("plugins", []) or [] if isinstance(pl, dict)]
            for entry in items:
                for key in path_keys:
                    val = entry.get(key)
                    if not val or not isinstance(val, str) or "/" not in val and not val.startswith("."):
                        continue
                    checked.append("%s %s=%s" % (rel, key, val))
                    if val.startswith("/") or ".." in val or re.match(r"[a-z]+://", val):
                        problems.append("%s %s=%s 非相对或外链" % (rel, key, val))
                        continue
                    if not any(os.path.exists(os.path.normpath(os.path.join(b, val)))
                               for b in bases):
                        problems.append("%s %s=%s 目标不存在" % (rel, key, val))
        if problems:
            return self.finish("E-S02", obj, 0, "FAIL", problems)
        return self.finish("E-S02", obj, 2, "PASS",
                           checked or ["无路径字段需要核对"])

    def check_s03(self, name):
        fm, body = parse_frontmatter(self.skill_text(name))
        declared = [t.strip() for t in fm.get("allowed-tools", "").split(",") if t.strip()]
        if not declared:
            return self.finish("E-S03", "skill:" + name, 0, "FAIL",
                               ["frontmatter 缺 allowed-tools 声明"])
        used = sorted(t for t in TOOL_NAMES if re.search(r"\b%s\b" % t, body))
        undeclared = sorted(set(used) - set(declared))
        ev = ["声明：%s" % ", ".join(declared),
              "正文引用工具：%s" % (", ".join(used) or "无")]
        if undeclared:
            return self.finish("E-S03", "skill:" + name, 1, "PARTIAL",
                               ev + ["未声明即引用：%s" % ", ".join(undeclared)],
                               "高危工具是否与任务无关需人工判断")
        return self.finish("E-S03", "skill:" + name, 2, "PASS", ev,
                           "无关高危工具判断为人工面")

    def check_s04(self, name):
        if name == E_S04_STANDARD_SOURCE:
            return self.finish("E-S04", "skill:" + name, None, "NA",
                               ["本条口径的来源 skill，自指不打分"],
                               "N/A：标准自身")
        _, body = parse_frontmatter(self.skill_text(name))
        if not WRITE_OP_STRONG.search(body):
            return self.finish("E-S04", "skill:" + name, None, "MANUAL",
                               ["未见强写操作标记（生产库/落库/DML 等）"],
                               "写操作类判定需人工确认；确认在写操作类后按判据复核")
        has_sim = "仿真" in body
        has_ref = E_S04_STANDARD_SOURCE in body
        ev = ["写操作类（命中 %r）" % WRITE_OP_STRONG.search(body).group(0),
              "仿真步骤：%s；挂 oltp-action-safety 口径：%s" % (has_sim, has_ref)]
        if has_sim and has_ref:
            return self.finish("E-S04", "skill:" + name, 2, "PASS", ev)
        if has_sim or has_ref:
            return self.finish("E-S04", "skill:" + name, 1, "PARTIAL", ev)
        return self.finish("E-S04", "skill:" + name, 0, "FAIL", ev,
                           "缺仿真步骤即 0 分（T1 口径）")

    def check_s05(self, obj, subdirs):
        hits = self.scan_patterns(subdirs, [("私有网段 IP", PRIV_IP)])
        tr = os.path.join(self.repo, "tests", "test_repo.py")
        ev = (["识别信息模式扫描 0 命中（%s）" % "+".join(subdirs),
               "TestNoIdentifyingInfo 在位：%s" % ("是" if os.path.isfile(tr) else "否")])
        if hits:
            return self.finish("E-S05", obj, 0, "FAIL", hits)
        self.manual_notes.append("E-S05 %s：占位符规约（<HOST>/<TOKEN>/example.com）核对需人工" % obj)
        return self.finish("E-S05", obj, 2, "PASS", ev,
                           "占位符规约核对为人工面（T1 口径）")

    # ---------- 汇总入口 ----------

    def run_skill(self, name):
        return [self.check_t01(name), self.check_t02(name), self.check_t03(name),
                self.check_d02(name), self.check_d03(name), self.check_d04(name),
                self.check_d05(name), self.check_x01(name), self.check_x03(name),
                self.check_s03(name), self.check_s04(name)]

    def run_plugin(self, plugin):
        proot = os.path.join(self.repo, "plugins", plugin, "skills")
        skills = sorted(p for p in os.listdir(proot)
                        if os.path.isdir(os.path.join(proot, p))) \
            if os.path.isdir(proot) else []
        res = []
        for s in skills:
            res += self.run_skill(s)
        res += [self.check_t04(plugin), self.check_d01(plugin),
                self.check_s01("plugin:" + plugin, [os.path.join("plugins", plugin)]),
                self.check_s02("plugin:" + plugin,
                               [os.path.join("plugins", plugin, ".claude-plugin", "plugin.json")]),
                self.check_s05("plugin:" + plugin, [os.path.join("plugins", plugin)])]
        return res, skills

    def run_repo(self):
        return [self.check_t05(), self.check_x02(), self.check_x04(),
                self.check_s01("repo", ["hooks", "scripts", "examples", "templates"]),
                self.check_s02("repo", [os.path.join(".claude-plugin", "plugin.json"),
                                        os.path.join(".claude-plugin", "marketplace.json"),
                                        os.path.join(".cursor-plugin", "marketplace.json"),
                                        os.path.join(".cursor-plugin", "plugin.json")]),
                self.check_s05("repo", ["skills", "plugins", "docs", "examples",
                                        "hooks", "scripts", "templates", "commands"])]

    def plugins(self):
        proot = os.path.join(self.repo, "plugins")
        return sorted(p for p in os.listdir(proot)
                      if os.path.isdir(os.path.join(proot, p)))


def load_exemptions(repo):
    """解析豁免台账（docs/engineering-checklist/exemptions.md 的表格行）。

    HTML 注释块（<!-- -->，放构造样例演示格式）不参与解析。
    """
    f = os.path.join(repo, "docs", "engineering-checklist", "exemptions.md")
    mapping = {}
    if not os.path.isfile(f):
        return mapping
    text = re.sub(r"<!--.*?-->", "", read(f), flags=re.DOTALL)
    for line in text.splitlines():
        m = re.match(r"^\|\s*(EX-\d{8}-\d{2})\s*\|\s*([^|]+?)\s*\|\s*(E-[A-Z]\d{2})\s*\|", line)
        if m:
            mapping[(m.group(2).strip(), m.group(3))] = m.group(1)
    return mapping


def head_sha(repo):
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             cwd=repo, capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def verdict(results):
    blocking = [r for r in results if r.level == "阻断" and r.status not in ("NA", "EXEMPT")]
    regular = [r for r in results if r.level == "常规" and r.status not in ("NA", "EXEMPT")]
    denom = [r for r in regular if r.score is not None]
    ratio = (sum(1 for r in denom if r.score == 2) / len(denom)) if denom else 1.0
    manual = [r for r in results if r.status == "MANUAL"]
    hard = [r for r in blocking if r.score in (0, 1)]  # 阻断级 0/1 分即挡发布（不可豁免）
    if hard:
        return "FAIL", ratio
    if ratio < 0.9:
        return "FAIL", ratio
    if manual:
        return "PASS(机检，另有待人工)", ratio
    return "PASS", ratio


def render(results, scope_desc, repo, extra_manual):
    v, ratio = verdict(results)
    n = lambda s: sum(1 for r in results if r.status == s)
    lines = []
    lines.append("工程标准 checklist 机检报告（PRD-147/T2）")
    lines.append("范围：%s" % scope_desc)
    lines.append("HEAD：%s；日期：%s" % (head_sha(repo), datetime.date.today().isoformat()))
    lines.append("条目来源：PRD-147/T1 checklist v0.1（trend #735 / PR #86）")
    lines.append("-" * 64)
    for r in results:
        lines.append(r.line())
    lines.append("-" * 64)
    lines.append("汇总：PASS %d | PARTIAL %d | FAIL %d | MANUAL %d | EXEMPT %d | NA %d"
                 % (n("PASS"), n("PARTIAL"), n("FAIL"), n("MANUAL"), n("EXEMPT"), n("NA")))
    lines.append("阻断级未过：%d 条；常规级达标率：%.0f%%" % (
        sum(1 for r in results if r.level == "阻断" and r.score in (0, 1)), ratio * 100))
    lines.append("判定：%s（过门口径：阻断全 2 分且常规达标率 ≥90%%）" % v)
    if extra_manual:
        lines.append("")
        lines.append("待人工复核清单：")
        for m in extra_manual:
            lines.append("  - %s" % m)
    return "\n".join(lines), v


def main(argv=None):
    ap = argparse.ArgumentParser(description="PRD-147 工程标准 checklist 机检（报告不代改）")
    ap.add_argument("--plugin", action="append", default=[])
    ap.add_argument("--skill", action="append", default=[])
    ap.add_argument("--repo", action="store_true")
    ap.add_argument("--format", choices=("text", "markdown"), default="text")
    ap.add_argument("--out")
    ap.add_argument("--report-only", action="store_true",
                    help="恒退出 0（CI 用；门禁强制在 T4/T5 收口后开启）")
    args = ap.parse_args(argv)

    c = Checker(exemptions=load_exemptions(REPO))
    results, scope_parts = [], []
    include_repo = args.repo or bool(args.plugin)  # 插件走查带一次仓库级条目（T1 §6）

    if not (args.plugin or args.skill or args.repo):
        args.plugin = c.plugins()
        include_repo = True
    for s in args.skill:
        if s not in c.skills:
            print("未知 skill：%s" % s, file=sys.stderr)
            return 2
        results += c.run_skill(s)
        scope_parts.append("skill:" + s)
    for p in args.plugin:
        res, skills = c.run_plugin(p)
        results += res
        scope_parts.append("plugin:%s（skills: %s）" % (p, ", ".join(skills)))
    if include_repo:
        results += c.run_repo()
        scope_parts.append("repo")

    text, v = render(results, "；".join(scope_parts) or "repo", REPO, c.manual_notes)
    if args.format == "markdown":
        text = "```\n%s\n```" % text
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    if args.report_only:
        return 0
    return 1 if v.startswith("FAIL") else 0


if __name__ == "__main__":
    sys.exit(main())
