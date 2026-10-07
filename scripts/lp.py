#!/usr/bin/env python3
"""
lp —— Livepowers 命令行工具（只依赖 Python 3.9+ 标准库）

证据与路由
  init                          在当前项目创建 .livepowers/ 工作区
  evidence add ...              追加一条运行证据（JSONL）
  evidence stats                按意图汇总：次数、成功率、S1/S2 占比、平均成本、自动补记数
  hook post-tool | stop         由 Claude Code 钩子调用（stdin 为钩子 JSON）：自动采集 S1 调用与 S2 探索证据
  registry add ...              注册一项 System 1 能力（能力包；--supersedes 发新版本并退役旧版）
  registry find <query>         按意图查找已固化能力（System 1 路由；HIT=0，MISS=2）
  registry list [--all]         列出能力
  registry retire <id>          退役能力（去固化）
  registry review               复核：近期失败 / 长期闲置 / 验证模型与当前模型不一致 / 久未复验

固化门禁
  score ...                     F-V-S-R 评分 + 盈亏平衡 n*
  candidates                    从证据中挑出固化候选

任务看板（状态机）
  task new / move / show / list 待澄清→规格确认→探索→待验证→已注册→生产运行；任何状态可→异常接管，
                                接管后重开须 --reset-loops / --extend-budget；已关闭为终态

结果与资产
  outcome baseline / measure / cost / accept / report   结果台账：基线（--direction lower 表示越低越好）、增量、
                                单位验收任务成本、首次价值交付时间
  asset add / gate / list       现场创新入库四道门（可抽象、可版本化、可评测、可复用）与资产回流率

夜间
  pending add / list / done     夜间固化产物清单（意图、评分、n*、测试结果、位置、生成者），供早晨验收
  canary record / compare / list 金丝雀评测：记录每晚结果，与历史比较通过率与 token 用量
  job validate <file.json>      校验统一作业契约（必填字段、悬空依赖、环、单段时长不超过模型可稳定时长）
  report                        生成晨间报告（Markdown；汇总 pending 清单与金丝雀结果）

数据全部存放在 .livepowers/ 下（可用环境变量 LIVEPOWERS_HOME 改位置），建议纳入 git。
"""
import argparse
import contextlib
import io
import json
import os
import re
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

__version__ = "1.3.0"

ROOT = os.environ.get("LIVEPOWERS_HOME", ".livepowers")
EVID = os.path.join(ROOT, "evidence.jsonl")
REG = os.path.join(ROOT, "registry.json")
TASKS = os.path.join(ROOT, "tasks.json")
OUTCOME = os.path.join(ROOT, "outcomes.jsonl")
ASSETS = os.path.join(ROOT, "assets.json")
REPORTS = os.path.join(ROOT, "reports")
CANARY = os.path.join(ROOT, "canary.jsonl")
PENDING = os.path.join(ROOT, "pending")
SESSIONS = os.path.join(ROOT, "sessions")


# ---------------------------------------------------------------- utils
def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_ts(s):
    """解析 ISO 时间；不带时区的按本地时区处理，避免与带时区时间相减出错。"""
    try:
        t = datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None
    if t.tzinfo is None:
        t = t.astimezone()
    return t


def jload(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def jsave(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def jsonl_read(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out


def jsonl_append(path, rec):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def ensure():
    os.makedirs(REPORTS, exist_ok=True)
    if not os.path.exists(REG):
        jsave(REG, {"version": 2, "capabilities": []})
    if not os.path.exists(TASKS):
        jsave(TASKS, {"version": 1, "tasks": []})
    if not os.path.exists(ASSETS):
        jsave(ASSETS, {"version": 1, "assets": []})
    for p in (EVID, OUTCOME):
        if not os.path.exists(p):
            open(p, "a").close()


def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def slug(s):
    s = re.sub(r"[^a-z0-9一-鿿]+", "_", s.lower()).strip("_")
    return s or uuid.uuid4().hex[:8]


# ---------------------------------------------------------------- init
def cmd_init(a):
    ensure()
    print(f"已初始化 {ROOT}/（evidence.jsonl, registry.json, tasks.json, outcomes.jsonl, assets.json, reports/）")


# ---------------------------------------------------------------- evidence
def cmd_evidence_add(a):
    ensure()
    rec = {
        "id": "ev_" + uuid.uuid4().hex[:10], "ts": now(),
        "intent": a.intent, "system": a.system, "outcome": a.outcome,
        "tokens": a.tokens, "seconds": a.seconds, "cost": a.cost,
        "capability": a.capability, "task": a.task, "model": a.model,
        "domain": a.domain, "writes_state": a.writes_state, "verifiable": a.verifiable,
        "note": a.note,
    }
    jsonl_append(EVID, rec)
    if a.capability:
        r = jload(REG, {"capabilities": []})
        for c in r["capabilities"]:
            if c["id"] == a.capability:
                c["calls"] = c.get("calls", 0) + 1
                c["last_called"] = rec["ts"]
                if a.outcome == "fail":
                    c["fails"] = c.get("fails", 0) + 1
                jsave(REG, r)
                break
    print(rec["id"])


def group_by(xs, key):
    g = defaultdict(list)
    for x in xs:
        g[x.get(key, "?")].append(x)
    return g


def avg(xs, k):
    return (sum((x.get(k) or 0) for x in xs) / len(xs)) if xs else 0.0


def cmd_evidence_stats(a):
    ev = jsonl_read(EVID)
    rows = []
    for intent, es in group_by(ev, "intent").items():
        n = len(es)
        ok = sum(1 for e in es if e.get("outcome") == "success")
        s1 = [e for e in es if e.get("system") == "S1"]
        s2 = [e for e in es if e.get("system") == "S2"]
        rows.append((intent, n, ok / n if n else 0, len(s1), len(s2), avg(s2, "cost"), avg(s1, "cost")))
    rows.sort(key=lambda r: -r[1])
    print(f"{'intent':40} {'n':>4} {'成功率':>6} {'S1':>4} {'S2':>4} {'S2均成本':>9} {'S1均成本':>9}")
    for r in rows:
        print(f"{r[0][:40]:40} {r[1]:>4} {r[2]:>6.0%} {r[3]:>4} {r[4]:>4} {r[5]:>9.4f} {r[6]:>9.4f}")
    tot = len(ev)
    if tot:
        s2n = sum(1 for e in ev if e.get("system") == "S2")
        auto = [e for e in ev if e.get("auto")]
        pend = sum(1 for e in auto if e.get("outcome") == "partial")
        print(f"\n总计 {tot} 次；System 2 调用占比 {s2n / tot:.0%}（健康的活产品应随时间下降）")
        if auto:
            print(f"钩子自动采集 {len(auto)} 条，其中自动补记、待确认结论 {pend} 条")
        weekly = s2_share_by_week(ev)
        if len(weekly) > 1:
            print("按周 S2 占比：" + "  ".join(f"{w}:{v:.0%}" for w, v in weekly))


def s2_share_by_week(ev):
    g = defaultdict(lambda: [0, 0])
    for e in ev:
        t = parse_ts(e.get("ts"))
        if not t:
            continue
        y, w, _ = t.isocalendar()
        k = f"{y}-W{w:02d}"
        g[k][0] += 1
        g[k][1] += 1 if e.get("system") == "S2" else 0
    return [(k, v[1] / v[0]) for k, v in sorted(g.items())]


# ---------------------------------------------------------------- registry
def cmd_registry_add(a):
    ensure()
    r = jload(REG, {"capabilities": []})
    cid = a.id or ("cap_" + slug(a.name))
    if any(c["id"] == cid and c["status"] == "active" for c in r["capabilities"]):
        die(f"能力 {cid} 已存在且为 active；发新版本请换 --id 并用 --supersedes {cid}，或先 retire 旧版本")
    old = None
    if a.supersedes:
        old = next((c for c in r["capabilities"] if c["id"] == a.supersedes and c["status"] == "active"), None)
        if not old:
            die(f"--supersedes 指向的能力 {a.supersedes} 不存在或已非 active")
    if a.writes_state and not a.tests:
        die("写操作能力必须提供 --tests（八项检查测试集），否则不予注册")
    if a.generated_by and a.accepted_by and a.generated_by == a.accepted_by:
        die("生成者不能验收自己：--accepted-by 必须不同于 --generated-by")
    cap = {
        "id": cid, "name": a.name, "kind": a.kind,
        "intents": [s.strip() for s in a.intents.split(",") if s.strip()],
        "entry": a.entry, "inputs": a.inputs, "outputs": a.outputs,
        "preconditions": a.preconditions, "permissions": a.permissions,
        "writes_state": a.writes_state, "tests": a.tests, "version": a.version,
        "owner": a.owner, "ontology_version": a.ontology_version,
        "package": a.package, "validated_model": a.validated_model,
        "generated_by": a.generated_by, "accepted_by": a.accepted_by,
        "status": "active", "created": now(), "last_verified": now(),
        "calls": 0, "fails": 0, "supersedes": a.supersedes or None,
    }
    if old:
        old["status"] = "retired"
        old["retired"] = now()
        old["retire_reason"] = f"被 {cid} v{a.version} 取代"
        old["superseded_by"] = cid
    r["capabilities"].append(cap)
    jsave(REG, r)
    print(f"已注册 {cid} v{a.version}" + (f"（已退役旧版本 {old['id']}，调用方请迁移）" if old else ""))


CJK = re.compile(r"[^一-鿿]")


def bigrams(x):
    x = CJK.sub("", x)
    return {x[i:i + 2] for i in range(len(x) - 1)}


def score_match(q, cap):
    q = q.lower()
    toks = [t for t in re.split(r"[\s,，;；/]+", q) if len(t) > 1]
    hay = " ".join(cap.get("intents", []) + [cap.get("name", "")]).lower()
    s = sum(1 for t in toks if t in hay)
    for it in cap.get("intents", []):
        if it.lower() in q:
            s += 3
    qb = bigrams(q)
    if qb:  # 中文无空格：用字符二元组重叠度补充匹配
        for it in cap.get("intents", []):
            ib = bigrams(it.lower())
            if ib:
                ov = len(qb & ib) / len(ib)
                if ov >= 0.5:
                    s += round(ov * 3)
    return s


def cmd_registry_find(a):
    r = jload(REG, {"capabilities": []})
    hits = sorted(((score_match(a.query, c), c) for c in r["capabilities"] if c["status"] == "active"),
                  key=lambda x: -x[0])
    hits = [h for h in hits if h[0] >= a.min_score]
    if not hits:
        print("MISS —— 未命中已固化能力 → 转 System 2 探索（记得记录证据）")
        sys.exit(2)
    print("HIT —— 命中已固化能力 → 走 System 1 执行：")
    for s, c in hits[: a.top]:
        flag = "  [写操作]" if c.get("writes_state") else ""
        print(f"  [{s}] {c['id']} v{c['version']} ({c['kind']}) entry: {c['entry']}{flag}  置信度 {confidence(c):.2f}")
        if c.get("preconditions"):
            print(f"       前置条件: {c['preconditions']}")


def confidence(c):
    """拉普拉斯平滑的成功率：(成功 + 1) / (调用 + 2)。新能力 0.5，随 S1 调用的成功 / 失败升降。"""
    calls, fails = c.get("calls", 0), c.get("fails", 0)
    return (calls - fails + 1) / (calls + 2)


def cmd_registry_list(a):
    r = jload(REG, {"capabilities": []})
    for c in r["capabilities"]:
        if a.all or c["status"] == "active":
            print(f"{c['status']:8} {c['id']:36} v{c['version']:6} {c['kind']:7} calls={c.get('calls', 0):<4} "
                  f"置信度={confidence(c):.2f} intents={','.join(c['intents'])}")


def cmd_registry_retire(a):
    r = jload(REG, {"capabilities": []})
    for c in r["capabilities"]:
        if c["id"] == a.id and c["status"] == "active":
            c.update(status="retired", retired=now(), retire_reason=a.reason)
            jsave(REG, r)
            print(f"已退役 {a.id}（去固化，后续请求将回到 System 2）：{a.reason}")
            return
    die(f"未找到 active 能力 {a.id}")


def cmd_registry_verify(a):
    r = jload(REG, {"capabilities": []})
    for c in r["capabilities"]:
        if c["id"] == a.id and c["status"] == "active":
            c["last_verified"] = now()
            if a.model:
                c["validated_model"] = a.model
            jsave(REG, r)
            print(f"已记录复验 {a.id}" + (f"（模型 {a.model}）" if a.model else ""))
            return
    die(f"未找到 active 能力 {a.id}")


def review_findings(caps, ev, idle_days, verify_days, current_model):
    """返回 [(cap_id, 原因)]。"""
    out = []
    t_now = datetime.now(timezone.utc).astimezone()
    recent_fail = defaultdict(int)
    by_cap = group_by([e for e in ev if e.get("capability")], "capability")
    for cid, es in by_cap.items():
        es = sorted(es, key=lambda e: e.get("ts", ""))
        streak = 0
        for e in reversed(es):
            if e.get("outcome") == "fail":
                streak += 1
            else:
                break
        recent_fail[cid] = streak
    for c in caps:
        if c["status"] != "active":
            continue
        if recent_fail[c["id"]] >= 2:
            out.append((c["id"], f"连续失败 {recent_fail[c['id']]} 次 → 去固化信号，改走 System 2 并复核"))
        elif c.get("calls", 0) >= 3 and confidence(c) < 0.6:
            out.append((c["id"], f"置信度 {confidence(c):.2f}（{c.get('fails', 0)}/{c['calls']} 失败）→ 复核或去固化"))
        last = parse_ts(c.get("last_called") or c.get("created"))
        if last and t_now - last > timedelta(days=idle_days):
            out.append((c["id"], f"超过 {idle_days} 天无调用 → 考虑退役，避免能力库变成新的死软件"))
        lv = parse_ts(c.get("last_verified") or c.get("created"))
        if lv and t_now - lv > timedelta(days=verify_days):
            out.append((c["id"], f"超过 {verify_days} 天未复验 → 重跑测试集"))
        if current_model and c.get("kind") == "skill" and c.get("validated_model") and \
                c["validated_model"] != current_model:
            out.append((c["id"], f"在 {c['validated_model']} 上验证，当前模型为 {current_model} → 换模型须重跑基准"))
    return out


def cmd_registry_review(a):
    r = jload(REG, {"capabilities": []})
    f = review_findings(r["capabilities"], jsonl_read(EVID), a.idle_days, a.verify_days, a.current_model)
    if not f:
        print("复核：无待处理项。")
        return
    print("复核发现：")
    for cid, why in f:
        print(f"- {cid}: {why}")


# ---------------------------------------------------------------- score
def fvsr(freq_per_month, verifiable, stability, writes_state):
    f = 0 if freq_per_month < 4 else (1 if freq_per_month < 20 else 2)
    risk_bonus = 1 if writes_state else 0
    total = f * 2 + verifiable * 1.5 + stability * 1 + risk_bonus
    return round(min(total, 10), 1), {"F": f, "V": verifiable, "S": stability, "R": risk_bonus}


def breakeven(c2, c1, K, M, p=1.0, h=0.0):
    c2_eff = c2 / p + (1 - p) * h / p if p > 0 else float("inf")
    if c2_eff <= c1:
        return float("inf"), c2_eff
    return (K + M) / (c2_eff - c1), c2_eff


def cmd_score(a):
    sc, parts = fvsr(a.freq, a.verifiable, a.stability, a.writes_state)
    n_star, c2e = breakeven(a.c2, a.c1, a.K, a.M, a.p, a.h)
    calls = a.freq * a.months
    print(f"F-V-S-R 评分: {sc}/10  分项 {parts}")
    print(f"System 2 有效单次成本 c2' = {c2e:.4f}（含失败重试与人工兜底）")
    print(f"盈亏平衡调用次数 n* = {n_star:.1f}；预计 {a.months:g} 个月内调用 {calls:.0f} 次")
    if a.verifiable < 1:
        print("⚠ 不可验证（V=0）——即使高频也不应固化")
    ok = a.verifiable >= 1 and calls > n_star and sc >= 5
    print(f"建议: {'固化' if ok else '保持 System 2 / 会话级'}")
    if ok and a.writes_state:
        print("提示: 写操作——固化前必须完成 oltp-action-safety 八项检查测试")
    sys.exit(0 if ok else 3)


# ---------------------------------------------------------------- candidates
def candidates(min_count):
    ev = jsonl_read(EVID)
    r = jload(REG, {"capabilities": []})
    covered = {i.lower() for c in r["capabilities"] if c["status"] == "active" for i in c["intents"]}
    out = []
    for intent, es in group_by(ev, "intent").items():
        if intent.lower() in covered:
            continue
        s2 = [e for e in es if e.get("system") == "S2"]
        if len(s2) < min_count:
            continue
        out.append({
            "intent": intent, "s2_calls": len(s2),
            "success": sum(1 for e in s2 if e.get("outcome") == "success") / len(s2),
            "verifiable_ratio": sum(1 for e in s2 if e.get("verifiable")) / len(s2),
            "avg_cost": avg(s2, "cost"),
            "writes_state": any(e.get("writes_state") for e in s2),
        })
    out.sort(key=lambda c: -(c["s2_calls"] * (0.5 + c["verifiable_ratio"])))
    return out


def cmd_candidates(a):
    cands = candidates(a.min_count)
    if a.json:
        print(json.dumps(cands, ensure_ascii=False, indent=2))
        return
    if not cands:
        print("暂无固化候选。")
        return
    print("固化候选（按 调用次数 × 可验证度 排序）：")
    for c in cands:
        flag = "（写操作：需 oltp-action-safety）" if c["writes_state"] else ""
        print(f"- {c['intent']}: S2 {c['s2_calls']} 次, 成功率 {c['success']:.0%}, "
              f"可验证 {c['verifiable_ratio']:.0%}, 均成本 {c['avg_cost']:.4f} {flag}")


# ---------------------------------------------------------------- task board
STATES = ["clarify", "spec", "explore", "verify", "registered", "running", "takeover", "closed"]
STATE_CN = {"clarify": "待澄清", "spec": "规格确认", "explore": "探索", "verify": "待验证",
            "registered": "已注册", "running": "生产运行", "takeover": "异常接管", "closed": "已关闭"}
TRANSITIONS = {
    "clarify": {"spec", "explore", "closed"},          # 会话级需求可直接探索
    "spec": {"explore", "clarify", "closed"},
    "explore": {"verify", "explore", "spec", "closed"},  # explore→explore 记一轮
    "verify": {"registered", "explore", "closed"},
    "registered": {"running", "explore"},
    "running": {"explore", "closed"},                  # 去固化：回到探索
    "takeover": {"clarify", "spec", "explore", "closed"},   # 重开后仍须经 待验证 → 已注册 才能进生产
    "closed": set(),                                        # 终态
}


def load_tasks():
    ensure()
    return jload(TASKS, {"tasks": []})


def find_task(db, tid):
    for t in db["tasks"]:
        if t["id"] == tid:
            return t
    die(f"未找到任务 {tid}")


def cmd_task_new(a):
    db = load_tasks()
    tid = a.id or "t_" + uuid.uuid4().hex[:8]
    if any(t["id"] == tid for t in db["tasks"]):
        die(f"任务 {tid} 已存在")
    t = {"id": tid, "title": a.title, "intent": a.intent, "level": a.level, "owner": a.owner,
         "contract_version": a.contract_version, "max_loops": a.max_loops, "budget": a.budget,
         "loops": 0, "spent": 0.0, "state": "clarify", "executor": None,
         "history": [{"ts": now(), "to": "clarify", "by": a.owner or "?", "reason": "created"}]}
    db["tasks"].append(t)
    jsave(TASKS, db)
    print(tid)


def cmd_task_move(a):
    db = load_tasks()
    t = find_task(db, a.id)
    src, dst = t["state"], a.to
    if dst not in STATES:
        die(f"未知状态 {dst}；可选 {STATES}")
    if dst == "takeover" and src != "closed":
        pass  # 已关闭之外的任何状态都可转入异常接管
    elif dst not in TRANSITIONS[src]:
        die(f"不允许的迁移 {STATE_CN[src]} → {STATE_CN[dst]}；允许：{[STATE_CN[s] for s in TRANSITIONS[src]] or '无'}")
    if not a.reason:
        die("每次状态迁移都必须写明 --reason（条件或依据）")
    if a.cost:
        t["spent"] = round(t.get("spent", 0) + a.cost, 6)
    if src == "takeover" and dst == "explore":
        # 接管后重开：必须显式重置轮次或追加预算，否则止损条件仍然成立
        if a.reset_loops:
            t["loops"] = 0
            t["spent"] = 0.0
        if a.extend_budget:
            t["budget"] = (t.get("budget") or 0) + a.extend_budget
            if a.max_loops:
                t["max_loops"] = a.max_loops
        t["executor"] = None  # 接管后换人重开，重新记录执行者
    if dst == "explore":
        t["loops"] += 1
        t["executor"] = t.get("executor") or a.by
        over_loop = t.get("max_loops") and t["loops"] > t["max_loops"]
        over_budget = t.get("budget") and t["spent"] > t["budget"]
        if over_loop or over_budget:
            why = "超过最大探索轮次" if over_loop else "超过探索预算"
            t["state"] = "takeover"
            t["history"].append({"ts": now(), "to": "takeover", "by": "lp", "reason": f"止损：{why}"})
            jsave(TASKS, db)
            die(f"止损：{why}（轮次 {t['loops']}/{t.get('max_loops')}，花费 {t['spent']}/{t.get('budget')}）"
                f" → 已转入异常接管，交付可诊断记录，不要继续重试", 4)
    if src == "verify" and dst == "registered":
        if not a.evidence:
            die("待验证 → 已注册 必须提供 --evidence（测试 / 验收记录位置）")
        if t.get("executor") and a.by == t["executor"]:
            die(f"生成者不评审自己：{a.by} 是该任务的执行者，不能把它迁移为已注册")
    if dst == "spec" and not t.get("contract_version") and a.contract_version:
        t["contract_version"] = a.contract_version
    t["state"] = dst
    t["history"].append({"ts": now(), "from": src, "to": dst, "by": a.by, "reason": a.reason,
                         "evidence": a.evidence, "cost": a.cost})
    jsave(TASKS, db)
    print(f"{t['id']}: {STATE_CN[src]} → {STATE_CN[dst]}")


def cmd_task_show(a):
    t = find_task(load_tasks(), a.id)
    print(json.dumps(t, ensure_ascii=False, indent=2))


def cmd_task_list(a):
    db = load_tasks()
    by = group_by(db["tasks"], "state")
    for s in STATES:
        ts = by.get(s, [])
        if not ts or (s == "closed" and not a.all):
            continue
        print(f"### {STATE_CN[s]}（{len(ts)}）")
        for t in ts:
            print(f"- {t['id']} {t['title']}  意图={t.get('intent') or '-'} 轮次={t['loops']}/{t.get('max_loops') or '∞'}"
                  f" 花费={t.get('spent', 0)}/{t.get('budget') or '∞'}")


# ---------------------------------------------------------------- outcome ledger
def cmd_outcome_baseline(a):
    ensure()
    if a.confirmed_at and parse_ts(a.confirmed_at) is None:
        die("--confirmed-at 须为 ISO 时间，如 2026-01-15 或 2026-01-15T09:00:00+08:00")
    jsonl_append(OUTCOME, {"ts": now(), "type": "baseline", "scenario": a.scenario, "metric": a.metric,
                           "value": a.value, "target": a.target, "base": a.base, "owner": a.owner,
                           "direction": a.direction, "confirmed_at": a.confirmed_at or now()})
    print(f"已登记基线 {a.scenario}/{a.metric} = {a.value}")


def cmd_outcome_measure(a):
    ensure()
    ol = jsonl_read(OUTCOME)
    if not any(o["type"] == "baseline" and o["scenario"] == a.scenario and o["metric"] == a.metric for o in ol):
        die("没有基线的结果不计入台账：先 lp outcome baseline")
    jsonl_append(OUTCOME, {"ts": now(), "type": "measure", "scenario": a.scenario, "metric": a.metric,
                           "value": a.value, "note": a.note})
    print("ok")


COST_KINDS = ["human", "inference", "tool", "rework", "ops", "amortization", "takeover"]


def has_baseline(scenario):
    return any(o["type"] == "baseline" and o["scenario"] == scenario for o in jsonl_read(OUTCOME))


def cmd_outcome_cost(a):
    ensure()
    if not has_baseline(a.scenario):
        die("没有基线的场景不归集成本：先 lp outcome baseline")
    jsonl_append(OUTCOME, {"ts": now(), "type": "cost", "scenario": a.scenario, "kind": a.kind,
                           "amount": a.amount, "note": a.note})
    print("ok")


def cmd_outcome_accept(a):
    ensure()
    jsonl_append(OUTCOME, {"ts": now(), "type": "accept", "scenario": a.scenario, "task": a.task,
                           "accepted": not a.rejected, "adopted_by": a.by, "first_production": a.first})
    print("ok")


def outcome_summary(include_evidence_cost=True):
    ol = jsonl_read(OUTCOME)
    ev = jsonl_read(EVID)
    scen = defaultdict(lambda: {"baselines": {}, "measures": defaultdict(list), "cost": defaultdict(float),
                                "accepted": 0, "rejected": 0, "first_value_days": None})
    for o in ol:
        s = scen[o["scenario"]]
        if o["type"] == "baseline":
            s["baselines"][o["metric"]] = o
        elif o["type"] == "measure":
            s["measures"][o["metric"]].append(o)
        elif o["type"] == "cost":
            s["cost"][o["kind"]] += o["amount"]
        elif o["type"] == "accept":
            if o["accepted"]:
                s["accepted"] += 1
            else:
                s["rejected"] += 1
            if o.get("first_production") and s["first_value_days"] is None:
                starts = [parse_ts(b["confirmed_at"]) for b in s["baselines"].values() if b.get("confirmed_at")]
                t1 = parse_ts(o["ts"])
                if starts and t1:
                    s["first_value_days"] = round((t1 - min(starts)).total_seconds() / 86400, 2)
    if include_evidence_cost:  # 证据里按 note 'scenario=<名>' 归集推理成本
        for e in ev:
            m = re.search(r"scenario=([^\s;,]+)", e.get("note") or "")
            if m and m.group(1) in scen:
                scen[m.group(1)]["cost"]["inference"] += e.get("cost") or 0
    return scen


def cmd_outcome_report(a):
    scen = outcome_summary()
    if not scen:
        print("结果台账为空。先 lp outcome baseline。")
        return
    for name, s in scen.items():
        print(f"### 场景 {name}")
        for metric, b in s["baselines"].items():
            ms = s["measures"].get(metric, [])
            cur = ms[-1]["value"] if ms else None
            line = f"- {metric}: 基线 {b['value']}"
            if b.get("target") is not None:
                line += f" → 目标 {b['target']}"
            if cur is not None:
                delta = cur - b["value"]
                rate = delta / b["value"] if b["value"] else 0
                if b.get("direction") == "lower":  # 越低越好：下降才是正向增量
                    rate = -rate
                line += f"；当前 {cur}（Δ {delta:+g}，{rate:+.1%}）"
                if b.get("base"):
                    line += f"；增量价值 ΔV = B×u = {b['base']:,.10g}×{rate:.4f} = {b['base'] * rate:,.2f}"
            print(line)
        total = sum(s["cost"].values())
        n = s["accepted"]
        print(f"- 归集成本 {total:,.2f}（" + "，".join(f"{k} {v:,.2f}" for k, v in s["cost"].items()) + "）")
        print(f"- 通过验收任务 {n}，未通过 {s['rejected']}；验收任务平均成本 = "
              + (f"{total / n:,.2f}" if n else "—（暂无通过验收的任务）"))
        if s["first_value_days"] is not None:
            print(f"- 首次价值交付时间：{s['first_value_days']} 天（自范围确认至首个生产任务被采纳）")


# ---------------------------------------------------------------- assets
GATES = ["abstractable", "versioned", "evaluated", "reusable"]
GATE_CN = {"abstractable": "可抽象", "versioned": "可版本化", "evaluated": "可评测", "reusable": "可复用"}


def cmd_asset_add(a):
    ensure()
    db = jload(ASSETS, {"assets": []})
    aid = a.id or "as_" + slug(a.name)
    if any(x["id"] == aid for x in db["assets"]):
        die(f"资产 {aid} 已存在")
    db["assets"].append({"id": aid, "name": a.name, "kind": a.kind, "origin": a.origin,
                         "ownership": a.ownership, "gates": {}, "status": "candidate", "created": now(),
                         "reused_in": []})
    jsave(ASSETS, db)
    print(aid)


def cmd_asset_gate(a):
    db = jload(ASSETS, {"assets": []})
    for x in db["assets"]:
        if x["id"] == a.id:
            if a.gate not in GATES:
                die(f"未知门：{a.gate}；可选 {GATES}")
            if x["ownership"] == "client":
                die("客户所有的资产（数据、凭证、专有制度、本体实例）不得进入公共参考库")
            idx = GATES.index(a.gate)
            missing = [g for g in GATES[:idx] if not x["gates"].get(g)]
            if missing:
                die(f"四道门须依次通过；尚未通过：{[GATE_CN[g] for g in missing]}")
            x["gates"][a.gate] = {"ts": now(), "by": a.by, "evidence": a.evidence}
            if all(x["gates"].get(g) for g in GATES):
                x["status"] = "reference"
            jsave(ASSETS, db)
            print(f"{a.id}: 通过「{GATE_CN[a.gate]}」" + ("；已入公共参考库" if x["status"] == "reference" else ""))
            return
    die(f"未找到资产 {a.id}")


def cmd_asset_reuse(a):
    db = jload(ASSETS, {"assets": []})
    for x in db["assets"]:
        if x["id"] == a.id:
            if x["status"] != "reference":
                die("只有已入参考库的资产才计入复用")
            x["reused_in"].append({"ts": now(), "project": a.project, "version": a.version,
                                   "verified": a.verified})
            jsave(ASSETS, db)
            print("ok")
            return
    die(f"未找到资产 {a.id}")


def asset_stats():
    db = jload(ASSETS, {"assets": []})
    field = [x for x in db["assets"] if x["origin"] == "field"]
    ref = [x for x in field if x["status"] == "reference"]
    reuse = sum(1 for x in db["assets"] for r in x["reused_in"] if r.get("verified"))
    return len(field), len(ref), reuse


def cmd_asset_list(a):
    db = jload(ASSETS, {"assets": []})
    for x in db["assets"]:
        g = "".join("●" if x["gates"].get(k) else "○" for k in GATES)
        print(f"{x['status']:10} {x['id']:30} {x['kind']:10} 归属={x['ownership']:8} 门={g} 复用={len(x['reused_in'])}")
    n_field, n_ref, reuse = asset_stats()
    if n_field:
        print(f"\n资产回流率 = 入库现场创新 / 现场创新总数 = {n_ref}/{n_field} = {n_ref / n_field:.0%}；"
              f"经重新验证的复用次数 {reuse}")


# ---------------------------------------------------------------- job contract
JOB_REQUIRED = ["job_id", "tenant", "stage_id", "dependency", "priority", "deadline",
                "model_capability", "resources", "max_cost", "retry_limit", "stop_condition",
                "checkpoint", "preemptible", "resume_policy", "data_classification", "acceptance",
                "handoff", "expected_minutes"]


def cmd_job_validate(a):
    with open(a.file, encoding="utf-8") as f:
        doc = json.load(f)
    jobs = doc if isinstance(doc, list) else doc.get("jobs", [doc])
    horizons = {} if isinstance(doc, list) else doc.get("model_horizon_minutes", {})
    bad = 0
    ids = {j.get("job_id") for j in jobs}
    for j in jobs:
        errs = []
        miss = [k for k in JOB_REQUIRED if k not in j]
        if miss:
            errs.append(f"缺字段 {miss}")
        dangling = [d for d in j.get("dependency", []) if d not in ids]
        if dangling:
            errs.append(f"悬空依赖 {dangling}")
        h = horizons.get(j.get("model_capability"))
        if h and j.get("expected_minutes", 0) > h:
            errs.append(f"预计 {j['expected_minutes']} 分钟超过模型 {j['model_capability']} 可稳定时长 {h} 分钟，须再切段")
        ho = j.get("handoff") or {}
        if "handoff" in j and not (isinstance(ho, dict) and ho.get("actual_end_state") and ho.get("checker")):
            errs.append("handoff 须包含 actual_end_state（前段实际终态的位置）与 checker（独立完成度检查者）")
        if errs:
            bad += 1
            print(f"✗ {j.get('job_id', '?')}: " + "；".join(errs))
        else:
            print(f"✓ {j['job_id']}")
    graph = {j["job_id"]: j.get("dependency", []) for j in jobs if "job_id" in j}
    seen, stack = set(), set()

    def dfs(n):
        if n in stack:
            return True
        if n in seen:
            return False
        seen.add(n)
        stack.add(n)
        cyc = any(dfs(m) for m in graph.get(n, []) if m in graph)
        stack.discard(n)
        return cyc

    if any(dfs(n) for n in list(graph)):
        bad += 1
        print("✗ 作业依赖存在环，不是 DAG")
    sys.exit(1 if bad else 0)


# ---------------------------------------------------------------- report
def cmd_report(a):
    ensure()
    ev = jsonl_read(EVID)
    r = jload(REG, {"capabilities": []})
    tot = len(ev)
    s2n = sum(1 for e in ev if e.get("system") == "S2")
    active = [c for c in r["capabilities"] if c["status"] == "active"]
    retired = [c for c in r["capabilities"] if c["status"] == "retired"]
    day = datetime.now().strftime("%Y-%m-%d")
    L = [f"# 晨间报告 · {day}", "",
         f"- 证据总数：{tot}；System 2 占比：{(s2n / tot if tot else 0):.0%}",
         f"- 已固化能力（active）：{len(active)}；已退役：{len(retired)}"]
    weekly = s2_share_by_week(ev)
    if len(weekly) > 1:
        L.append("- 按周 S2 占比：" + " → ".join(f"{w} {v:.0%}" for w, v in weekly[-6:]))
    n_field, n_ref, _ = asset_stats()
    if n_field:
        L.append(f"- 资产回流率：{n_ref}/{n_field} = {n_ref / n_field:.0%}")

    def capture(fn, ns):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                fn(ns)
            except SystemExit:
                pass
        return buf.getvalue().strip()

    L += ["", "## 待人工验收的固化产物", ""]
    pend = pending_list()
    if pend:
        for m in pend:
            flag = "【写操作】" if m.get("writes_state") else ""
            L.append(f"- {flag}`{m['intent']}`：评分 {m.get('score')}，n* {m.get('n_star')}，"
                     f"测试 `{m.get('tests')}` → {m.get('result')}；位置 {m.get('location')}；"
                     f"生成者 {m.get('generated_by')}；采纳人须不同于生成者")
    else:
        L.append("暂无（夜间 Agent 用 lp pending add 登记产物）")
    auto_pend = [e for e in ev if e.get("auto") and e.get("outcome") == "partial"]
    L += ["", "## 自动采集待确认", ""]
    if auto_pend:
        L.append(f"钩子补记了 {len(auto_pend)} 条未显式记录的 S2 探索（结论暂记 partial）。请核对后用 "
                 "`lp evidence add` 补一条带结论的记录，或忽略：")
        for e in auto_pend[-10:]:
            L.append(f"- {e['ts'][:16]} `{e['intent']}` tokens={e.get('tokens', 0)} {e.get('note', '')}")
    else:
        L.append("无")
    L += ["", "## 固化候选（来自证据）", "",
          capture(cmd_candidates, argparse.Namespace(min_count=a.min_count, json=False)) or "暂无",
          "", "## 金丝雀", "",
          capture(cmd_canary_compare, argparse.Namespace(name="", pass_threshold=0.1, token_threshold=0.3)) or "暂无",
          "", "## 能力复核", "",
          capture(cmd_registry_review, argparse.Namespace(idle_days=a.idle_days, verify_days=a.verify_days,
                                                          current_model=a.current_model)) or "暂无",
          "", "## 任务看板", "", capture(cmd_task_list, argparse.Namespace(all=False)) or "暂无",
          "", "## 结果台账", "", capture(cmd_outcome_report, argparse.Namespace()) or "暂无",
          "", "## 最近注册的能力", ""]
    for c in sorted(active, key=lambda c: c["created"], reverse=True)[:10]:
        L.append(f"- `{c['id']}` v{c['version']}（{c['kind']}）— {', '.join(c['intents'])}")
    L += ["", "## 需要人决定的事", "",
          "- [ ] 逐项验收上面的固化产物（通过 → lp registry add + lp pending done --accepted；不通过 → lp pending done 写明原因）",
          "- [ ] 处理能力复核项（退役 / 复验 / 重跑基准）",
          "- [ ] 处理异常接管中的任务（见 takeover-handling；重开用 lp task move <id> explore --reset-loops）",
          "- [ ] 金丝雀有回归时：先核对样例，再决定是否换模型 / 补 Harness"]
    path = os.path.join(REPORTS, f"morning-{day}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(path)


# ---------------------------------------------------------------- pending（夜间产物清单）
def pending_dir(intent):
    return os.path.join(PENDING, slug(intent))


def pending_list():
    out = []
    if not os.path.isdir(PENDING):
        return out
    for d in sorted(os.listdir(PENDING)):
        mp = os.path.join(PENDING, d, "manifest.json")
        if os.path.isfile(mp):
            m = jload(mp, {})
            if m.get("status", "pending") == "pending":
                out.append(m)
    return out


def cmd_pending_add(a):
    ensure()
    d = pending_dir(a.intent)
    mp = os.path.join(d, "manifest.json")
    if os.path.isfile(mp) and jload(mp, {}).get("status", "pending") == "pending":
        die(f"{a.intent} 已有待验收产物（{mp}）；先 lp pending done，或换意图名")
    os.makedirs(d, exist_ok=True)
    m = {"intent": a.intent, "score": a.score, "n_star": a.n_star, "tests": a.tests, "result": a.result,
         "location": a.location, "generated_by": a.generated_by, "writes_state": a.writes_state,
         "model": a.model, "note": a.note, "status": "pending", "created": now()}
    jsave(mp, m)
    print(mp)


def cmd_pending_list(a):
    pend = pending_list()
    if not pend:
        print("没有待验收的固化产物。")
        return
    for m in pend:
        flag = "[写操作] " if m.get("writes_state") else ""
        print(f"- {flag}{m['intent']}  评分={m.get('score')} n*={m.get('n_star')} 测试={m.get('result')}"
              f" 位置={m.get('location')} 生成者={m.get('generated_by')}")


def cmd_pending_done(a):
    mp = os.path.join(pending_dir(a.intent), "manifest.json")
    if not os.path.isfile(mp):
        die(f"未找到 {a.intent} 的待验收产物")
    m = jload(mp, {})
    if m.get("generated_by") and m["generated_by"] == a.by:
        die(f"生成者不能验收自己：{a.by} 是该产物的生成者")
    m["status"] = "accepted" if a.accepted else "rejected"
    m["decided_by"] = a.by
    m["decided"] = now()
    m["decision_reason"] = a.reason
    jsave(mp, m)
    print(f"{a.intent}: {m['status']}")


# ---------------------------------------------------------------- canary（金丝雀评测）
def cmd_canary_record(a):
    ensure()
    if a.total <= 0 or a.passed > a.total:
        die("--pass 不能大于 --total，且 --total > 0")
    jsonl_append(CANARY, {"ts": now(), "name": a.name, "model": a.model, "passed": a.passed, "total": a.total,
                          "tokens": a.tokens, "seconds": a.seconds, "note": a.note})
    print(f"已记录 {a.name}: {a.passed}/{a.total}（{a.model or '未注明模型'}）")


def canary_runs():
    by = defaultdict(list)
    for r in jsonl_read(CANARY):
        by[r["name"]].append(r)
    return by


def cmd_canary_compare(a):
    by = canary_runs()
    names = [a.name] if a.name else sorted(by)
    if a.name and a.name not in by:
        die(f"没有名为 {a.name} 的金丝雀记录；先 lp canary record")
    if not names:
        print("没有金丝雀记录。")
        return
    regressed = False
    for n in names:
        runs = by[n]
        cur = runs[-1]
        rate = cur["passed"] / cur["total"]
        head = f"- {n}: 最新 {cur['passed']}/{cur['total']}（{rate:.0%}，{cur.get('model') or '?'}）"
        if len(runs) < 2:
            print(head + " — 首次记录，无可比较基线")
            continue
        hist = runs[:-1]
        best = max(r["passed"] / r["total"] for r in hist)
        base_tok = [r["tokens"] for r in hist if r.get("tokens")]
        issues = []
        if best - rate > a.pass_threshold:
            issues.append(f"通过率下降 {best:.0%} → {rate:.0%}")
        if base_tok and cur.get("tokens"):
            avg = sum(base_tok) / len(base_tok)
            if cur["tokens"] > avg * (1 + a.token_threshold):
                issues.append(f"token 用量上升 {avg:.0f} → {cur['tokens']}（+{cur['tokens'] / avg - 1:.0%}）")
        if issues:
            regressed = True
            print(head + " ⚠ 回归：" + "；".join(issues))
        else:
            print(head + " 无回归")
    if regressed:
        sys.exit(5)


def cmd_canary_list(a):
    by = canary_runs()
    if not by:
        print("没有金丝雀记录。")
        return
    for n, runs in sorted(by.items()):
        print(f"- {n}: {len(runs)} 次；" + " → ".join(f"{r['passed']}/{r['total']}" for r in runs[-6:]))


# ---------------------------------------------------------------- hook（自动采集证据）
FIND_RE = re.compile(r"(?:^|[\s;&|])(?:lp|lp\.py|python3?\s+\S*lp\.py)\s+registry\s+find\s+(.+)", re.S)
EVIDENCE_RE = re.compile(r"(?:^|[\s;&|])(?:lp|lp\.py|python3?\s+\S*lp\.py)\s+evidence\s+add\b")
CAP_RE = re.compile(r"\b(cap_[^\s]+?)\s+v\S+")


def _session_path(sid):
    return os.path.join(SESSIONS, re.sub(r"[^A-Za-z0-9_.-]", "_", sid or "default") + ".json")


def _entry_prefix(entry):
    """取 entry 里参数占位符之前的固定部分，用于识别 Agent 是否调用了该能力。"""
    pre = entry.split("{")[0].strip()
    toks = pre.split()
    return " ".join(toks[:3]) if toks else ""


def _turn_tokens(transcript_path):
    """累加 transcript 里最后一个用户提问之后所有 assistant 消息的 token。"""
    try:
        lines = []
        with open(transcript_path, encoding="utf-8") as f:
            for line in f:
                try:
                    lines.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        return 0
    start = 0
    for i, d in enumerate(lines):
        if d.get("type") == "user" and not d.get("toolUseResult"):
            start = i
    tot = 0
    for d in lines[start:]:
        if d.get("type") == "assistant":
            u = (d.get("message") or {}).get("usage") or {}
            tot += int(u.get("input_tokens", 0) or 0) + int(u.get("output_tokens", 0) or 0)
    return tot


def _auto_evidence(**kw):
    rec = {"id": "ev_" + uuid.uuid4().hex[:10], "ts": now(), "tokens": 0, "seconds": 0, "cost": 0,
           "capability": None, "task": None, "model": None, "domain": None, "writes_state": False,
           "verifiable": False, "note": "", "auto": True}
    rec.update(kw)
    jsonl_append(EVID, rec)
    if rec.get("capability"):
        r = jload(REG, {"capabilities": []})
        for c in r["capabilities"]:
            if c["id"] == rec["capability"]:
                c["calls"] = c.get("calls", 0) + 1
                c["last_called"] = rec["ts"]
                if rec["outcome"] == "fail":
                    c["fails"] = c.get("fails", 0) + 1
                jsave(REG, r)
                break
    return rec


def hook_post_tool(d, st):
    if d.get("tool_name") != "Bash":
        return
    cmd = (d.get("tool_input") or {}).get("command") or ""
    resp = d.get("tool_response") or {}
    if isinstance(resp, str):
        resp = {"stdout": resp}
    stdout, stderr = str(resp.get("stdout", "")), str(resp.get("stderr", ""))
    code = resp.get("exit_code")
    m = FIND_RE.search(cmd)
    if m:
        q = m.group(1).strip().split("\n")[0].strip().strip("\"'")
        q = re.sub(r"\s+--\S+.*$", "", q).strip().strip("\"'")
        hit = stdout.lstrip().startswith("HIT") or code == 0 and "HIT" in stdout
        cm = CAP_RE.search(stdout) if hit else None
        st["pending"] = {"intent": q, "hit": bool(hit), "capability": cm.group(1) if cm else None,
                         "ts": now(), "s1_calls": 0}
        st["explicit"] = False
        return
    if EVIDENCE_RE.search(cmd):
        st["explicit"] = True
        return
    pend = st.get("pending")
    if pend and pend.get("hit") and pend.get("capability"):  # 命中后每次调用 entry 都记一条 S1
        r = jload(REG, {"capabilities": []})
        cap = next((c for c in r["capabilities"] if c["id"] == pend["capability"]), None)
        prefix = _entry_prefix(cap["entry"]) if cap else ""
        if prefix and prefix in cmd:
            failed = (code not in (None, 0)) or bool(stderr.strip())
            _auto_evidence(intent=pend["intent"], system="S1", outcome="fail" if failed else "success",
                           capability=pend["capability"], writes_state=bool(cap.get("writes_state")),
                           note=f"auto: hook 观测到调用 {prefix}" + (f"；exit={code}" if code not in (None, 0) else ""))
            pend["s1_calls"] = pend.get("s1_calls", 0) + 1


def hook_stop(d, st):
    pend = st.get("pending")
    if pend and not pend.get("hit") and not st.get("explicit"):
        tokens = _turn_tokens(d.get("transcript_path") or "")
        _auto_evidence(intent=pend["intent"], system="S2", outcome="partial", tokens=tokens,
                       note=f"auto: registry find MISS 后本轮未显式记证据，钩子补记；session={d.get('session_id', '')}")
    st["pending"] = None
    st["explicit"] = False


def cmd_hook(a):
    """永不阻塞 Agent：任何异常都吞掉并 exit 0；未 init 的项目不创建文件。"""
    try:
        if os.environ.get("LP_HOOK_CAPTURE", "1") == "0":
            return
        d = json.loads(sys.stdin.read() or "{}")
        cwd = d.get("cwd")
        if cwd and os.path.isdir(cwd):
            os.chdir(cwd)
        if not os.path.isdir(ROOT):
            return
        os.makedirs(SESSIONS, exist_ok=True)
        sp = _session_path(d.get("session_id"))
        st = jload(sp, {"pending": None, "explicit": False})
        if a.event == "post-tool":
            hook_post_tool(d, st)
        elif a.event == "stop":
            hook_stop(d, st)
        jsave(sp, st)
    except Exception as e:  # noqa: BLE001 —— 钩子里不允许任何失败外溢
        try:
            os.makedirs(ROOT, exist_ok=True) if os.path.isdir(ROOT) else None
            with open(os.path.join(ROOT, "hook-errors.log"), "a", encoding="utf-8") as f:
                f.write(f"{now()} {a.event}: {e!r}\n")
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------- argparse
def main(argv=None):
    p = argparse.ArgumentParser(prog="lp", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"lp {__version__}")
    sp = p.add_subparsers(dest="cmd", required=True, metavar="<命令>")
    sp.add_parser("init", help="在当前项目创建 .livepowers/ 工作区").set_defaults(fn=cmd_init)

    ev = sp.add_parser("evidence", help="运行证据：add / stats").add_subparsers(dest="sub", required=True)
    e = ev.add_parser("add", help="追加一条探索或执行证据（每轮探索结束都记）")
    e.add_argument("--intent", required=True, help="规范化意图，如 'weekly revenue by region'")
    e.add_argument("--system", choices=["S1", "S2"], required=True, help="S1 已固化能力 / S2 Agent 探索")
    e.add_argument("--outcome", choices=["success", "fail", "partial"], required=True)
    e.add_argument("--tokens", type=int, default=0, help="消耗 token")
    e.add_argument("--seconds", type=float, default=0, help="耗时秒")
    e.add_argument("--cost", type=float, default=0, help="本次成本（任意货币单位，与 score 的 c2 同单位）")
    e.add_argument("--capability", help="S1 调用的能力 id（自动累计调用 / 失败次数）")
    e.add_argument("--task", help="任务看板 id")
    e.add_argument("--model", help="本次使用的模型标识")
    e.add_argument("--domain", help="OLAP / OLTP / HTAP / 其他")
    e.add_argument("--writes-state", action="store_true", help="本次动作写了生产状态")
    e.add_argument("--verifiable", action="store_true", help="结果已被样例/断言自动核验")
    e.add_argument("--note", default="", help="可写 scenario=<场景名> 以归集到结果台账")
    e.set_defaults(fn=cmd_evidence_add)
    ev.add_parser("stats", help="按意图汇总次数、成功率、S1/S2 占比、周趋势").set_defaults(fn=cmd_evidence_stats)

    rg = sp.add_parser("registry", help="System 1 能力注册表：add / find / list / retire / verify / review"
                       ).add_subparsers(dest="sub", required=True)
    ra = rg.add_parser("add", help="注册一项已通过验收的能力（写操作必须带 --tests；生成者 ≠ 采纳人）")
    ra.add_argument("--name", required=True, help="能力名（默认据此生成 id：cap_<slug>）")
    ra.add_argument("--id", help="自定义 id")
    ra.add_argument("--kind", choices=["cli", "sql", "skill", "script", "mcp", "view", "workflow"], required=True,
                    help="能力形态；给业务 Agent 用的剧本请注册为 skill（review 才会检查模型变化）")
    ra.add_argument("--intents", required=True, help="逗号分隔的意图关键字（中英文都写）")
    ra.add_argument("--entry", required=True, help="调用入口（命令 / SQL 文件 / 工作流 id）")
    for k, h in (("inputs", "输入说明"), ("outputs", "输出说明"), ("preconditions", "前置条件"),
                 ("permissions", "所需权限"), ("owner", "维护主体"), ("tests", "测试命令或测试集位置")):
        ra.add_argument(f"--{k}", default="", help=h)
    ra.add_argument("--writes-state", action="store_true", help="写操作能力（必须带 --tests）")
    ra.add_argument("--version", default="1.0.0", help="能力版本（语义化）")
    ra.add_argument("--ontology-version", default="", help="依赖的本体版本")
    ra.add_argument("--package", default="", help="能力包清单路径（templates/capability-package.yaml）")
    ra.add_argument("--validated-model", default="", help="Skill 类能力在哪个模型上验证通过")
    ra.add_argument("--generated-by", default="", help="生成者（Agent 或人）")
    ra.add_argument("--accepted-by", default="", help="采纳人（必须不同于生成者）")
    ra.add_argument("--supersedes", default="", help="发新版本：自动退役该旧能力 id 并记录取代关系")
    ra.set_defaults(fn=cmd_registry_add)
    rf = rg.add_parser("find", help="按意图查找能力（HIT exit 0 / MISS exit 2）；命中后仍要核对前置条件")
    rf.add_argument("query", help="用户原话或规范化意图，中文可不分词")
    rf.add_argument("--top", type=int, default=3, help="最多列出几条")
    rf.add_argument("--min-score", type=int, default=2, help="低于此分视为 MISS")
    rf.set_defaults(fn=cmd_registry_find)
    rl = rg.add_parser("list", help="列出能力（默认只列 active）")
    rl.add_argument("--all", action="store_true", help="含已退役")
    rl.set_defaults(fn=cmd_registry_list)
    rr = rg.add_parser("retire", help="退役能力（去固化）")
    rr.add_argument("id")
    rr.add_argument("--reason", required=True, help="退役原因")
    rr.set_defaults(fn=cmd_registry_retire)
    rv = rg.add_parser("verify", help="记录一次复验（重跑测试集通过）")
    rv.add_argument("id")
    rv.add_argument("--model", default="", help="复验所用模型")
    rv.set_defaults(fn=cmd_registry_verify)
    rw = rg.add_parser("review", help="复核：近期失败 / 长期闲置 / 验证模型与当前模型不一致 / 久未复验")
    rw.add_argument("--idle-days", type=int, default=60, help="超过多少天未调用算闲置")
    rw.add_argument("--verify-days", type=int, default=30, help="超过多少天未复验算久未复验")
    rw.add_argument("--current-model", default=os.environ.get("LP_CURRENT_MODEL", ""),
                    help="当前模型（默认环境变量 LP_CURRENT_MODEL）")
    rw.set_defaults(fn=cmd_registry_review)

    s = sp.add_parser("score", help="F-V-S-R 评分与盈亏平衡（建议固化 exit 0，否则 3）")
    s.add_argument("--freq", type=float, required=True, help="每月预计调用次数")
    s.add_argument("--verifiable", type=int, choices=[0, 1, 2], required=True, help="可验证性 0-2（0 一票否决）")
    s.add_argument("--stability", type=int, choices=[0, 1, 2], required=True, help="口径稳定性 0-2")
    s.add_argument("--writes-state", action="store_true", help="写操作（提高风险系数）")
    s.add_argument("--c2", type=float, required=True, help="System 2 单次成本")
    s.add_argument("--c1", type=float, default=0.0, help="System 1 单次成本")
    s.add_argument("--K", type=float, required=True, help="固化一次性成本")
    s.add_argument("--M", type=float, default=0.0, help="生命周期维护成本")
    s.add_argument("--p", type=float, default=1.0, help="System 2 成功率")
    s.add_argument("--h", type=float, default=0.0, help="失败时人工兜底成本")
    s.add_argument("--months", type=float, default=6, help="回收期（月）")
    s.set_defaults(fn=cmd_score)

    c = sp.add_parser("candidates", help="从证据中挑出固化候选（同一意图多次 S2 成功）")
    c.add_argument("--min-count", type=int, default=3, help="至少几次成功才算候选")
    c.add_argument("--json", action="store_true", help="JSON 输出")
    c.set_defaults(fn=cmd_candidates)

    tk = sp.add_parser("task", help="任务看板状态机：new / move / show / list").add_subparsers(dest="sub", required=True)
    tn = tk.add_parser("new", help="新建任务（待澄清），设轮次与预算上限")
    tn.add_argument("--title", required=True, help="任务标题")
    tn.add_argument("--id", help="自定义 id（默认 t_xxxxxxxx）")
    tn.add_argument("--intent", default="", help="规范化意图（与 evidence 一致）")
    tn.add_argument("--level", choices=["session", "feature", "ontology"], default="feature", help="变化层级")
    tn.add_argument("--owner", default="", help="业务负责人")
    tn.add_argument("--contract-version", default="", help="契约版本")
    tn.add_argument("--max-loops", type=int, default=5, help="最大探索轮次（止损）")
    tn.add_argument("--budget", type=float, default=0, help="探索预算（0 为不限）")
    tn.set_defaults(fn=cmd_task_new)
    tm = tk.add_parser("move", help="迁移状态：" + " → ".join(STATE_CN[x] for x in STATES[:6]) + "；任何状态可 → 异常接管")
    tm.add_argument("id")
    tm.add_argument("to", help="/".join(STATES))
    tm.add_argument("--by", required=True, help="操作者（待验证 → 已注册 不能是执行者本人）")
    tm.add_argument("--reason", default="", help="迁移依据（必填）")
    tm.add_argument("--evidence", default="", help="产物 / 验收记录位置（待验证 → 已注册 必填）")
    tm.add_argument("--cost", type=float, default=0, help="本次花费（累计到预算）")
    tm.add_argument("--contract-version", default="", help="进入规格确认时记录契约版本")
    tm.add_argument("--reset-loops", action="store_true", help="接管后重开：轮次与花费归零")
    tm.add_argument("--extend-budget", type=float, default=0, help="接管后重开：追加预算")
    tm.add_argument("--max-loops", type=int, default=0, help="接管后重开：改最大轮次（与 --extend-budget 同用）")
    tm.set_defaults(fn=cmd_task_move)
    ts_ = tk.add_parser("show", help="查看任务与历史")
    ts_.add_argument("id")
    ts_.set_defaults(fn=cmd_task_show)
    tl = tk.add_parser("list", help="列出任务（默认不含已关闭）")
    tl.add_argument("--all", action="store_true", help="含已关闭")
    tl.set_defaults(fn=cmd_task_list)

    oc = sp.add_parser("outcome", help="结果台账：baseline / measure / cost / accept / report"
                       ).add_subparsers(dest="sub", required=True)
    ob = oc.add_parser("baseline", help="登记基线（承诺任何业务结果之前）")
    ob.add_argument("--scenario", required=True, help="场景名（evidence --note scenario=<名> 归集到此）")
    ob.add_argument("--metric", required=True, help="指标名")
    ob.add_argument("--value", type=float, required=True, help="基线值")
    ob.add_argument("--target", type=float, help="目标值")
    ob.add_argument("--base", type=float, help="业务基数 B（用于 ΔV = B × u）")
    ob.add_argument("--direction", choices=["higher", "lower"], default="higher",
                    help="指标方向：higher 越高越好（默认）/ lower 越低越好（如逾期数、时长）")
    ob.add_argument("--owner", default="", help="结果负责人")
    ob.add_argument("--confirmed-at", default="", help="范围确认时间（ISO），默认现在")
    ob.set_defaults(fn=cmd_outcome_baseline)
    om = oc.add_parser("measure", help="记录一次测量（须已有基线）")
    om.add_argument("--scenario", required=True)
    om.add_argument("--metric", required=True)
    om.add_argument("--value", type=float, required=True)
    om.add_argument("--note", default="")
    om.set_defaults(fn=cmd_outcome_measure)
    ocost = oc.add_parser("cost", help="归集成本（含失败、返工、接管；须已有基线）")
    ocost.add_argument("--scenario", required=True)
    ocost.add_argument("--kind", choices=COST_KINDS, required=True, help="成本类型")
    ocost.add_argument("--amount", type=float, required=True)
    ocost.add_argument("--note", default="")
    ocost.set_defaults(fn=cmd_outcome_cost)
    oa = oc.add_parser("accept", help="记录一次验收采纳 / 拒绝")
    oa.add_argument("--scenario", required=True)
    oa.add_argument("--task", default="", help="任务看板 id")
    oa.add_argument("--by", required=True, help="采纳主体")
    oa.add_argument("--rejected", action="store_true", help="未通过验收")
    oa.add_argument("--first", action="store_true", help="首个生产任务被采纳（计首次价值交付时间）")
    oa.set_defaults(fn=cmd_outcome_accept)
    oc.add_parser("report", help="输出台账：增量、ΔV、验收任务平均成本、首次价值交付时间").set_defaults(fn=cmd_outcome_report)

    asp = sp.add_parser("asset", help="现场资产四道门与回流：add / gate / reuse / list").add_subparsers(dest="sub", required=True)
    aa = asp.add_parser("add", help="登记一项现场创新资产")
    aa.add_argument("--name", required=True)
    aa.add_argument("--id")
    aa.add_argument("--kind", default="skill", help="skill/tool/ontology/spec/template/benchmark/role")
    aa.add_argument("--origin", choices=["field", "product"], default="field", help="来源")
    aa.add_argument("--ownership", choices=["client", "vendor", "joint"], default="vendor", help="归属（client 不入库）")
    aa.set_defaults(fn=cmd_asset_add)
    ag = asp.add_parser("gate", help="通过一道门（须按顺序）")
    ag.add_argument("id")
    ag.add_argument("gate", help="/".join(GATES))
    ag.add_argument("--by", required=True)
    ag.add_argument("--evidence", default="")
    ag.set_defaults(fn=cmd_asset_gate)
    au = asp.add_parser("reuse", help="记录一次跨项目复用")
    au.add_argument("id")
    au.add_argument("--project", required=True)
    au.add_argument("--version", default="")
    au.add_argument("--verified", action="store_true", help="完成适配并重新验证")
    au.set_defaults(fn=cmd_asset_reuse)
    asp.add_parser("list", help="列出资产、门禁进度与回流率").set_defaults(fn=cmd_asset_list)

    pd = sp.add_parser("pending", help="夜间固化产物清单：add / list / done").add_subparsers(dest="sub", required=True)
    pa = pd.add_parser("add", help="登记一个待验收的固化产物（写 .livepowers/pending/<意图>/manifest.json）")
    pa.add_argument("--intent", required=True, help="规范化意图")
    pa.add_argument("--score", type=float, required=True, help="F-V-S-R 评分")
    pa.add_argument("--n-star", type=float, required=True, help="盈亏平衡调用次数 n*")
    pa.add_argument("--tests", required=True, help="测试命令或测试集位置")
    pa.add_argument("--result", choices=["pass", "fail", "partial"], required=True, help="测试结果")
    pa.add_argument("--location", required=True, help="产物位置（分支 / 目录）")
    pa.add_argument("--generated-by", required=True, help="生成者（采纳人必须不同）")
    pa.add_argument("--writes-state", action="store_true", help="写操作能力（需 oltp-action-safety）")
    pa.add_argument("--model", default="", help="生成所用模型")
    pa.add_argument("--note", default="")
    pa.set_defaults(fn=cmd_pending_add)
    pd.add_parser("list", help="列出待验收产物").set_defaults(fn=cmd_pending_list)
    pdn = pd.add_parser("done", help="记录验收结论（采纳 / 拒绝）")
    pdn.add_argument("intent")
    pdn.add_argument("--by", required=True, help="采纳人（不能是生成者）")
    pdn.add_argument("--accepted", action="store_true", help="通过验收（默认拒绝）")
    pdn.add_argument("--reason", default="", help="结论依据")
    pdn.set_defaults(fn=cmd_pending_done)

    cn = sp.add_parser("canary", help="金丝雀评测：record / compare / list").add_subparsers(dest="sub", required=True)
    cr = cn.add_parser("record", help="记录一次金丝雀运行结果")
    cr.add_argument("--name", required=True, help="样例套件名")
    cr.add_argument("--model", default="", help="所用模型")
    cr.add_argument("--pass", dest="passed", type=int, required=True, help="通过样例数")
    cr.add_argument("--total", type=int, required=True, help="样例总数")
    cr.add_argument("--tokens", type=int, default=0, help="总 token 用量")
    cr.add_argument("--seconds", type=float, default=0, help="总耗时")
    cr.add_argument("--note", default="")
    cr.set_defaults(fn=cmd_canary_record)
    cc = cn.add_parser("compare", help="最新一次与历史比较（回归 exit 5）")
    cc.add_argument("--name", default="", help="只比较某个套件（默认全部）")
    cc.add_argument("--pass-threshold", type=float, default=0.1, help="通过率下降超过此值算回归")
    cc.add_argument("--token-threshold", type=float, default=0.3, help="token 用量较历史均值上升超过此比例算回归")
    cc.set_defaults(fn=cmd_canary_compare)
    cn.add_parser("list", help="列出各套件历史").set_defaults(fn=cmd_canary_list)

    j = sp.add_parser("job", help="夜间作业契约：validate").add_subparsers(dest="sub", required=True)
    jv = j.add_parser("validate", help="校验作业契约 JSON（必填字段、悬空依赖、环、单段时长）")
    jv.add_argument("file")
    jv.set_defaults(fn=cmd_job_validate)

    hk = sp.add_parser("hook", help="钩子入口（Claude Code PostToolUse / Stop 调用；stdin 为钩子 JSON）")
    hk.add_argument("event", choices=["post-tool", "stop"])
    hk.set_defaults(fn=cmd_hook)

    rp = sp.add_parser("report", help="生成晨间报告 Markdown（固化候选、能力复核、看板、台账、待决事项）")
    rp.add_argument("--min-count", type=int, default=3, help="固化候选的最少成功次数")
    rp.add_argument("--idle-days", type=int, default=60)
    rp.add_argument("--verify-days", type=int, default=30)
    rp.add_argument("--current-model", default=os.environ.get("LP_CURRENT_MODEL", ""))
    rp.set_defaults(fn=cmd_report)

    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
