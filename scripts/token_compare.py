#!/usr/bin/env python3
"""PRD-046/T4：5 个典型场景"改造前 vs 改造后"输出 token 对比（可复现）。

用法（仓库根目录）：
    python3 scripts/token_compare.py

做法：在临时目录搭固定 fixture，对每个场景各跑两次——
  * 改造前：LIVEPOWERS_VERBOSE=1（T3 已证明与改造前逐字节一致，直接当基线）
  * 改造后：默认简洁模式
用同一近似法计数，打印 Markdown 对比表。纯标准库。

token 计数方法（近似）：
  CJK 字符（含汉字、全角标点）按 1 token/字；其余非空白字符按 0.25 token/字；
  空白字符不计。绝对数值与真实分词器（如 tiktoken）会有偏差，但同一方法
  作用于改造前后，降幅比值可比。详见 docs/plans/2026-10-19-token-compare.md §2。
"""

import json
import os
import pty
import re
import sqlite3
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, "scripts")

CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3000-\u303f\uff00-\uffef]")


def count_tokens(text):
    """近似 token 数：CJK 1/字，其余非空白 0.25/字。"""
    cjk = len(CJK_RE.findall(text))
    other = len(re.sub(r"\s", "", CJK_RE.sub("", text)))
    return cjk + other / 4


def run(cmd, workdir, home, verbose, use_pty=False):
    """跑一条命令，返回 stdout（str，已做 \\r\\n 归一化）。"""
    env = {k: v for k, v in os.environ.items()
           if k not in ("LIVEPOWERS_VERBOSE", "LP_CURRENT_MODEL")}
    env["LIVEPOWERS_HOME"] = os.path.join(home, ".livepowers")
    if verbose:
        env["LIVEPOWERS_VERBOSE"] = "1"
    if not use_pty:
        p = subprocess.run([sys.executable] + cmd, cwd=workdir,
                           capture_output=True, text=True, env=env)
        return p.stdout.replace("\r\n", "\n"), p.returncode
    # pty：模拟人直接看终端（scan 指纹摘要只在 tty 下生效）
    m, s = pty.openpty()
    p = subprocess.Popen([sys.executable] + cmd, cwd=workdir,
                         stdout=s, stderr=subprocess.DEVNULL, env=env)
    os.close(s)
    out = b""
    while True:
        try:
            chunk = os.read(m, 4096)
        except OSError:
            break
        if not chunk:
            break
        out += chunk
    os.close(m)
    rc = p.wait()
    return out.decode("utf-8", "replace").replace("\r\n", "\n"), rc


def lp(*args):
    return [os.path.join(SCRIPTS, "lp.py")] + list(args)


# ---------------------------------------------------------------- fixtures

def fixture_review(home):
    """场景1 诊断：6 个闲置能力 → 6 条复核发现（固定旧日期，与当前时间无关）。"""
    live = os.path.join(home, ".livepowers")
    os.makedirs(live, exist_ok=True)
    caps = [{
        "id": f"cap_{i:02d}", "version": "1.0.0", "status": "active",
        "kind": "skill", "intents": [f"意图{i}"], "calls": 0, "fails": 0,
        "created": "2026-01-01T00:00:00+08:00",
        "last_called": "2020-01-01T00:00:00+08:00",      # 必超 idle-days=60
        "last_verified": "2026-10-18T00:00:00+08:00",     # 未超 verify-days=30
    } for i in range(1, 7)]
    with open(os.path.join(live, "registry.json"), "w", encoding="utf-8") as f:
        json.dump({"capabilities": caps}, f, ensure_ascii=False)


def fixture_evidence(home):
    """场景4 查询：12 条证据，4 个意图，跨 2 个 ISO 周（含自动采集）。"""
    live = os.path.join(home, ".livepowers")
    os.makedirs(live, exist_ok=True)
    ev, k = [], 0
    for w in ("2026-09-07T10:00:00+08:00", "2026-10-12T10:00:00+08:00"):
        for intent in ("意图A", "意图B", "意图C", "意图D"):
            for _ in range(2 if w.startswith("2026-09") else 1):
                k += 1
                ev.append({"ts": w, "intent": intent,
                           "outcome": "success" if k % 3 else "fail",
                           "system": "S2" if k % 2 else "S1",
                           "cost": round(0.5 + 0.1 * k, 2),
                           "auto": (k % 4 == 0)})
    with open(os.path.join(live, "evidence.jsonl"), "w", encoding="utf-8") as f:
        for e in ev:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def fixture_scan_db(path):
    """场景3 生成：4 表 × 8 列的 sqlite 库（固定 schema 与数据）。"""
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    for t in ("orders", "customers", "products", "payments"):
        cols = ", ".join(f"c{i} TEXT" for i in range(1, 6))
        con.execute(f"CREATE TABLE {t} (id INTEGER PRIMARY KEY, {cols},"
                    " status TEXT, created_at TEXT)")
        for r in range(30):
            con.execute(
                f"INSERT INTO {t} (c1,c2,c3,c4,c5,status,created_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (f"v{r}", f"w{r}", f"x{r}", f"y{r}", f"z{r}",
                 "active" if r % 2 else "pending", "2026-01-01"))
    con.commit()
    con.close()


def fixture_drift(tmp):
    """场景5 报错：新旧指纹差出 6 项变更（>5 触发折叠；exit 5 不变）。"""
    def fp(tables):
        return {"tables": {
            t: {"columns": {c: {"type": "TEXT"} for c in cols},
                "pk": ["id"], "rows": 10}
            for t, cols in tables.items()}}
    old = fp({"orders": ["id", "amount", "status"],
              "customers": ["id", "name"],
              "products": ["id", "price"]})
    new = fp({"orders": ["id", "amount", "status", "discount", "note"],
              "customers": ["id", "name", "level"],
              "products": ["id"],
              "refunds": ["id", "order_id", "reason"]})
    new["tables"]["orders"]["columns"]["amount"] = {"type": "REAL"}
    o, n = os.path.join(tmp, "old_fp.json"), os.path.join(tmp, "new_fp.json")
    for p, d in ((o, old), (n, new)):
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    return o, n


# ---------------------------------------------------------------- scenarios

def scenario_review(home, tmp):
    fixture_review(home)
    v, _ = run(lp("registry", "review"), tmp, home, verbose=True)
    c, _ = run(lp("registry", "review"), tmp, home, verbose=False)
    return ("registry review（6 项待处理）", "诊断", v, c,
            "列表 6 项 > 折叠阈值 5，折叠 1 项")


def scenario_score(home, tmp):
    args = ["score", "--freq", "30", "--verifiable", "2", "--stability", "2",
            "--writes-state", "--c2", "5", "--c1", "1", "--K", "10", "--M", "2",
            "--months", "6"]
    v, _ = run(lp(*args), tmp, home, verbose=True)
    c, _ = run(lp(*args), tmp, home, verbose=False)
    return ("score（建议固化）", "执行", v, c,
            "纯参数场景，无需 fixture；exit 0 两边一致")


def scenario_scan(home, tmp):
    db = os.path.join(tmp, "fixture.db")
    fixture_scan_db(db)
    v, _ = run([os.path.join(SCRIPTS, "scan_sqlite.py"), db,
                "--fingerprint", os.path.join(tmp, "fp_v.json")],
               tmp, home, verbose=True, use_pty=False)   # 管道：YAML 全文
    c, _ = run([os.path.join(SCRIPTS, "scan_sqlite.py"), db,
                "--fingerprint", os.path.join(tmp, "fp_c.json")],
               tmp, home, verbose=False, use_pty=True)    # tty：摘要行
    return ("scan_sqlite 指纹（4 表 32 列）", "生成", v, c,
            "简洁侧用 pty 模拟 tty；管道/重定向时原文不动（设计如此）")


def scenario_stats(home, tmp):
    fixture_evidence(home)
    v, _ = run(lp("evidence", "stats"), tmp, home, verbose=True)
    c, _ = run(lp("evidence", "stats"), tmp, home, verbose=False)
    return ("evidence stats（12 条/4 意图）", "查询", v, c,
            "7 列表格 → 结论行 + 折叠")


def scenario_drift(home, tmp):
    o, n = fixture_drift(tmp)
    v, rc_v = run([os.path.join(SCRIPTS, "scan_sqlite.py"),
                   "--diff", o, n], tmp, home, verbose=True)
    c, rc_c = run([os.path.join(SCRIPTS, "scan_sqlite.py"),
                   "--diff", o, n], tmp, home, verbose=False)
    assert (rc_v, rc_c) == (5, 5), f"drift exit changed: {rc_v}/{rc_c}"
    return ("scan --diff（6 项变更）", "报错", v, c,
            "exit 5 两边一致；变更 6 项 > 折叠阈值 5")


SCENARIOS = [scenario_review, scenario_score, scenario_scan,
             scenario_stats, scenario_drift]


def main():
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        home = os.path.join(tmp, "home")
        for fn in SCENARIOS:
            name, cat, verbose_text, concise_text, note = fn(home, tmp)
            tv, tc = count_tokens(verbose_text), count_tokens(concise_text)
            drop = (tv - tc) / tv * 100 if tv else 0.0
            rows.append((name, cat, tv, tc, drop, note))
    print("| 场景 | 类别 | 改造前 token | 改造后 token | 降幅 | 备注 |")
    print("|---|---|---|---|---|---|")
    tot_v = tot_c = 0.0
    for name, cat, tv, tc, drop, note in rows:
        tot_v += tv
        tot_c += tc
        print(f"| {name} | {cat} | {tv:.0f} | {tc:.0f} | {drop:.0f}% | {note} |")
    print(f"| **合计** |  | **{tot_v:.0f}** | **{tot_c:.0f}** |"
          f" **{(tot_v - tot_c) / tot_v * 100:.0f}%** |  |")
    print()
    print("计数方法：CJK 1 token/字，其余非空白 0.25 token/字（近似值，"
          "前后同法对比，降幅可比）。")


if __name__ == "__main__":
    main()
