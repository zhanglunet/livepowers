#!/usr/bin/env python3
"""
scan_sqlite —— 环境感知示例：只读扫描一个 SQLite 数据库，生成本体草稿与环境指纹，并做漂移比对。
其他数据库（MySQL / PostgreSQL / 数仓）请按同样的输出结构改写为查询 information_schema。

用法：
  python scan_sqlite.py DB [--sample 20] [--fingerprint fp.json] > .livepowers/ontology.draft.yaml
      输出本体草稿：对象、字段、候选主键、候选关系（外键 / *_id 命名推断）、
      候选状态字段及其抽样取值、候选时间字段；敏感字段只记字段名与类型，不抽样。
      --fingerprint 同时写出环境指纹（表、列、类型、状态取值集合），供夜间漂移检测。
  python scan_sqlite.py --diff OLD_FP.json NEW_FP.json
      比较两次指纹：新增 / 删除的表与列、类型变化、状态字段新取值。有漂移时退出码 5。

只依赖标准库；以只读 URI 打开数据库，绝不写库。
"""
import argparse
import json
import re
import sqlite3
import sys

SENSITIVE = re.compile(r"(phone|mobile|tel|email|id_?card|idno|ssn|passport|password|passwd|secret|token|"
                       r"bank|card_?no|account_?no|address|birth|salary|身份证|手机|电话|密码|银行卡|住址)", re.I)
STATUS = re.compile(r"(status|state|stage|phase|type)$", re.I)
TIME = re.compile(r"(_at|_time|date|_ts)$", re.I)


def q(name):
    return '"' + name.replace('"', '""') + '"'


def scan(path, sample):
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    cur = con.cursor()
    tables = [r[0] for r in cur.execute(
        "select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")]
    fp = {"source": f"sqlite:{path}", "tables": {}}
    for t in tables:
        cols = list(cur.execute(f"pragma table_info({q(t)})"))
        fks = list(cur.execute(f"pragma foreign_key_list({q(t)})"))
        n = cur.execute(f"select count(*) from {q(t)}").fetchone()[0]
        info = {"rows": n, "columns": {}, "fks": [[fk[3], fk[2], fk[4]] for fk in fks],
                "pk": [c[1] for c in cols if c[5]]}
        for c in cols:
            name, ctype = c[1], (c[2] or "ANY")
            col = {"type": ctype, "nullable": not c[3]}
            if SENSITIVE.search(name):
                col["sensitive"] = True
            elif STATUS.search(name):
                vals = [r[0] for r in cur.execute(
                    f"select distinct {q(name)} from {q(t)} where {q(name)} is not null limit ?", (sample,))]
                col["status_values"] = sorted(str(v) for v in vals)
            elif TIME.search(name):
                col["time"] = True
            info["columns"][name] = col
        fp["tables"][t] = info
    con.close()
    return fp


def to_yaml(fp):
    tables = list(fp["tables"])
    out = ["# 本体草稿（scan_sqlite.py 自动生成）——须业务确认后才能晋升为 ontology.yaml",
           f"source: {fp['source']}", "ontology_version: 0.1.0-draft", "objects:"]
    rels = []
    for t, info in fp["tables"].items():
        pk = info["pk"] or [c for c in info["columns"] if c.lower() in ("id", f"{t.lower()}_id")]
        out += [f"  - name: {t}", '    description: ""   # TODO(需业务确认) 业务含义',
                f"    identity: {pk}", f"    row_count: {info['rows']}", "    attributes:"]
        for name, col in info["columns"].items():
            note = ""
            if col.get("sensitive"):
                note = "  # 敏感字段：只记名称与类型，未抽样"
            elif "status_values" in col:
                note = f"  # 候选状态字段，抽样取值 {col['status_values']}：请定义状态机"
            elif col.get("time"):
                note = "  # 候选时间字段：事件时间还是快照时间？"
            out.append(f"      - {{name: {name}, type: {col['type']}, nullable: {str(col['nullable']).lower()}}}{note}")
        fk_cols = {f[0] for f in info["fks"]}
        for f in info["fks"]:
            rels.append((t, f[0], f[1], f[2] or "id", "foreign_key"))
        for name in info["columns"]:
            m = re.match(r"(.+)_id$", name.lower())
            if m and name not in fk_cols:
                target = next((x for x in tables if x.lower() in (m.group(1), m.group(1) + "s", m.group(1) + "es")), None)
                if target and target != t:
                    rels.append((t, name, target, "id", "name_inferred"))
    out.append("relations:")
    for a, col, b, bcol, how in rels:
        out.append(f"  - {{from: {a}.{col}, to: {b}.{bcol}, cardinality: many_to_one, evidence: {how}}}"
                   + ("   # 推断，须确认" if how == "name_inferred" else ""))
    out += ["rules: []        # TODO(需业务确认) 口径、阈值、约束；每条写来源、适用范围、生效时间",
            "permissions: []  # TODO(需业务确认) 角色与可见范围",
            "actions: []      # TODO 原子行动（见 templates/action.yaml）"]
    return "\n".join(out)


def diff(old, new):
    changes = []
    ot, nt = old["tables"], new["tables"]
    for t in sorted(set(nt) - set(ot)):
        changes.append(f"新增表 {t}")
    for t in sorted(set(ot) - set(nt)):
        changes.append(f"删除表 {t}（依赖它的已固化能力须复核）")
    for t in sorted(set(ot) & set(nt)):
        oc, nc = ot[t]["columns"], nt[t]["columns"]
        for c in sorted(set(nc) - set(oc)):
            changes.append(f"{t}: 新增列 {c}")
        for c in sorted(set(oc) - set(nc)):
            changes.append(f"{t}: 删除列 {c}")
        for c in sorted(set(oc) & set(nc)):
            if oc[c]["type"] != nc[c]["type"]:
                changes.append(f"{t}.{c}: 类型 {oc[c]['type']} → {nc[c]['type']}")
            new_vals = set(nc[c].get("status_values", [])) - set(oc[c].get("status_values", []))
            if new_vals:
                changes.append(f"{t}.{c}: 状态出现新取值 {sorted(new_vals)}（状态机须更新）")
    return changes


def main():
    p = argparse.ArgumentParser(prog="scan_sqlite")
    p.add_argument("db", nargs="?")
    p.add_argument("--sample", type=int, default=20)
    p.add_argument("--fingerprint")
    p.add_argument("--diff", nargs=2, metavar=("OLD", "NEW"))
    a = p.parse_args()
    if a.diff:
        with open(a.diff[0], encoding="utf-8") as f1, open(a.diff[1], encoding="utf-8") as f2:
            ch = diff(json.load(f1), json.load(f2))
        if not ch:
            print("无漂移")
            return
        print("环境漂移：")
        for c in ch:
            print(f"- {c}")
        sys.exit(5)
    if not a.db:
        p.error("需要 DB 路径或 --diff")
    fp = scan(a.db, a.sample)
    if a.fingerprint:
        with open(a.fingerprint, "w", encoding="utf-8") as f:
            json.dump(fp, f, ensure_ascii=False, indent=2)
    print(to_yaml(fp))


if __name__ == "__main__":
    main()
