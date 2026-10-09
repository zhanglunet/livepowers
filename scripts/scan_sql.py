#!/usr/bin/env python3
"""
scan_sql —— 环境感知：只读扫描 PostgreSQL / MySQL 数据库（或兼容 information_schema 的数据库），
生成与 scan_sqlite.py 完全同构的本体草稿与环境指纹，并支持 --diff 跨指纹漂移比对。

零依赖约束：
- 优先支持命令行方式：psql（PostgreSQL）或 mysql（MySQL）
- 兼容常见 Python 驱动（若运行环境安装了 psycopg / psycopg2 / pymysql）
- 以只读角色查询 information_schema，绝不写入数据库。
- 敏感字段只记字段名与类型，跳过抽样。

用法：
  python scan_sql.py --dsn "postgres://user:pass@host:5432/dbname" [--sample 20] [--fingerprint fp.json]
  python scan_sql.py --dsn "mysql://user:pass@host:3306/dbname" [--sample 20] [--fingerprint fp.json]
  python scan_sql.py --diff OLD_FP.json NEW_FP.json
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from urllib.parse import urlparse, unquote

SENSITIVE = re.compile(r"(phone|mobile|tel|email|id_?card|idno|ssn|passport|password|passwd|secret|token|"
                       r"bank|card_?no|account_?no|address|birth|salary|身份证|手机|电话|密码|银行卡|住址)", re.I)
STATUS = re.compile(r"(status|state|stage|phase|type)$", re.I)
TIME = re.compile(r"(_at|_time|date|_ts)$", re.I)


def parse_dsn(dsn):
    u = urlparse(dsn)
    scheme = u.scheme.lower()
    if "+" in scheme:
        scheme = scheme.split("+", 1)[0]
    if scheme in ("postgres", "postgresql", "pg"):
        db_type = "postgres"
    elif scheme in ("mysql", "mariadb"):
        db_type = "mysql"
    else:
        raise ValueError(f"不支持的数据库协议: {u.scheme}（支持 postgres / mysql）")
    return {
        "db_type": db_type,
        "user": unquote(u.username or ""),
        "password": unquote(u.password or ""),
        "host": u.hostname or "127.0.0.1",
        "port": u.port or (5432 if db_type == "postgres" else 3306),
        "database": u.path.lstrip("/"),
    }


def run_query(dsn_info, sql, params=None):
    """根据可用环境执行查询并返回 (columns, rows)"""
    db_type = dsn_info["db_type"]
    if params:
        for p in params:
            val_escaped = "'" + str(p).replace("'", "''") + "'" if isinstance(p, str) else str(p)
            sql = sql.replace("%s", val_escaped, 1).replace("?", val_escaped, 1)

    # 先尝试命令行工具，再回退到可选 Python 驱动。
    if db_type == "postgres":
        if shutil.which("psql"):
            env = dict(os.environ)
            env["PGOPTIONS"] = (env.get("PGOPTIONS", "") + " -c default_transaction_read_only=on").strip()
            if dsn_info["password"]:
                env["PGPASSWORD"] = dsn_info["password"]
            cmd = ["psql", "-h", dsn_info["host"], "-p", str(dsn_info["port"]),
                   "-U", dsn_info["user"], "-d", dsn_info["database"],
                   "-A", "-F", "\t", "--pset", "footer=off", "-c", sql]
            res = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"psql 执行失败: {res.stderr.strip()}")
            lines = [l for l in res.stdout.strip().splitlines() if l]
            if not lines:
                return [], []
            return lines[0].split("\t"), [line.split("\t") for line in lines[1:]]

        try:
            import psycopg  # psycopg v3
            with psycopg.connect(
                host=dsn_info["host"], port=dsn_info["port"], dbname=dsn_info["database"],
                user=dsn_info["user"], password=dsn_info["password"],
                options="-c default_transaction_read_only=on",
            ) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    cols = [d[0] for d in cur.description] if cur.description else []
                    rows = cur.fetchall()
                    return cols, rows
        except ImportError:
            pass

        try:
            import psycopg2  # psycopg v2
            with psycopg2.connect(
                host=dsn_info["host"], port=dsn_info["port"], dbname=dsn_info["database"],
                user=dsn_info["user"], password=dsn_info["password"],
                options="-c default_transaction_read_only=on",
            ) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    cols = [d[0] for d in cur.description] if cur.description else []
                    rows = cur.fetchall()
                    return cols, rows
        except ImportError:
            pass

        raise RuntimeError("未找到 PostgreSQL 客户端驱动或 psql 命令行工具（请安装 psql 或 psycopg/psycopg2）")

    elif db_type == "mysql":
        if shutil.which("mysql"):
            env = dict(os.environ)
            env["MYSQL_PWD"] = dsn_info["password"]
            cmd = ["mysql", "--connect-timeout=10", "-h", dsn_info["host"], "-P", str(dsn_info["port"]),
                   "-u", dsn_info["user"], "-D", dsn_info["database"], "-B", "-e",
                   "START TRANSACTION READ ONLY; " + sql + "; ROLLBACK;"]
            res = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"mysql 执行失败: {res.stderr.strip()}")
            lines = [l for l in res.stdout.strip().splitlines() if l]
            if not lines:
                return [], []
            return lines[0].split("\t"), [line.split("\t") for line in lines[1:]]

        try:
            import pymysql
            conn = pymysql.connect(
                host=dsn_info["host"], port=dsn_info["port"], db=dsn_info["database"],
                user=dsn_info["user"], password=dsn_info["password"],
            )
            with conn.cursor() as cur:
                cur.execute("START TRANSACTION READ ONLY")
                cur.execute(sql)
                cols = [d[0] for d in cur.description] if cur.description else []
                rows = cur.fetchall()
            conn.close()
            return cols, rows
        except ImportError:
            pass

        raise RuntimeError("未找到 MySQL 客户端驱动或 mysql 命令行工具（请安装 mysql 客户端或 pymysql）")


def q(name):
    return '"' + name.replace('"', '""') + '"'


def quote_identifier(name, db_type):
    if db_type == "mysql":
        return '`' + name.replace('`', '``') + '`'
    return q(name)


def scan(dsn, sample=20, query_executor=run_query):
    dsn_info = parse_dsn(dsn)
    db_type = dsn_info["db_type"]
    db_name = dsn_info["database"]

    # 1. 查表清单
    if db_type == "postgres":
        tables_sql = """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name;
        """
    else:
        tables_sql = f"""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = '{db_name}' AND table_type = 'BASE TABLE'
        ORDER BY table_name;
        """
    _, table_rows = query_executor(dsn_info, tables_sql)
    tables = [r[0] for r in table_rows]

    # 2. 查主键与列信息
    if db_type == "postgres":
        cols_sql = """
        SELECT c.table_name, c.column_name, c.data_type, c.is_nullable,
               CASE WHEN tc.constraint_type = 'PRIMARY KEY' THEN 1 ELSE 0 END as is_pk
        FROM information_schema.columns c
        LEFT JOIN information_schema.key_column_usage kcu
          ON c.table_schema = kcu.table_schema AND c.table_name = kcu.table_name AND c.column_name = kcu.column_name
        LEFT JOIN information_schema.table_constraints tc
          ON kcu.table_schema = tc.table_schema AND kcu.table_name = tc.table_name
          AND kcu.constraint_name = tc.constraint_name AND tc.constraint_type = 'PRIMARY KEY'
        WHERE c.table_schema = 'public'
        ORDER BY c.table_name, c.ordinal_position;
        """
        fks_sql = """
        SELECT kcu.table_name, kcu.column_name, kcu2.table_name AS foreign_table_name, kcu2.column_name AS foreign_column_name
        FROM information_schema.referential_constraints rc
        JOIN information_schema.key_column_usage kcu
          ON kcu.constraint_catalog = rc.constraint_catalog
         AND kcu.constraint_schema = rc.constraint_schema
         AND kcu.constraint_name = rc.constraint_name
        JOIN information_schema.key_column_usage kcu2
          ON kcu2.constraint_catalog = rc.unique_constraint_catalog
         AND kcu2.constraint_schema = rc.unique_constraint_schema
         AND kcu2.constraint_name = rc.unique_constraint_name
         AND kcu2.ordinal_position = kcu.position_in_unique_constraint
        WHERE kcu.table_schema = 'public'
        ORDER BY kcu.table_name, kcu.constraint_name, kcu.ordinal_position;
        """
    else:
        cols_sql = f"""
        SELECT c.table_name, c.column_name, c.data_type, c.is_nullable,
               CASE WHEN c.column_key = 'PRI' THEN 1 ELSE 0 END as is_pk
        FROM information_schema.columns c
        WHERE c.table_schema = '{db_name}'
        ORDER BY c.table_name, c.ordinal_position;
        """
        fks_sql = f"""
        SELECT table_name, column_name, referenced_table_name, referenced_column_name
        FROM information_schema.key_column_usage
        WHERE table_schema = '{db_name}' AND referenced_table_name IS NOT NULL;
        """

    _, cols_rows = query_executor(dsn_info, cols_sql)
    _, fks_rows = query_executor(dsn_info, fks_sql)

    table_cols = {}
    for r in cols_rows:
        tname, colname, ctype, isnull, ispk = r[0], r[1], r[2], r[3], int(r[4])
        if tname not in table_cols:
            table_cols[tname] = []
        table_cols[tname].append((colname, ctype, str(isnull).upper() in ("YES", "TRUE", "1"), bool(ispk)))

    table_fks = {}
    for r in fks_rows:
        tname, colname, fktable, fkcol = r[0], r[1], r[2], r[3]
        if tname not in table_fks:
            table_fks[tname] = []
        table_fks[tname].append([colname, fktable, fkcol])

    fp = {"source": f"{db_type}:{db_name}", "tables": {}}
    for t in tables:
        # 行数统计
        cnt_sql = f"SELECT count(*) FROM {quote_identifier(t, db_type)};"
        try:
            _, cnt_res = query_executor(dsn_info, cnt_sql)
            rows_cnt = int(cnt_res[0][0])
        except Exception:
            rows_cnt = 0

        cols = table_cols.get(t, [])
        fks = table_fks.get(t, [])
        pk = [c[0] for c in cols if c[3]]

        info = {
            "rows": rows_cnt,
            "columns": {},
            "fks": fks,
            "pk": pk
        }

        for c in cols:
            name, ctype, nullable, _ = c
            col_info = {"type": ctype, "nullable": nullable}
            if SENSITIVE.search(name):
                col_info["sensitive"] = True
            elif STATUS.search(name):
                qi = quote_identifier(name, db_type)
                qt = quote_identifier(t, db_type)
                sample_sql = f"SELECT DISTINCT {qi} FROM {qt} WHERE {qi} IS NOT NULL LIMIT {sample};"
                try:
                    _, s_rows = query_executor(dsn_info, sample_sql)
                    col_info["status_values"] = sorted(str(sr[0]) for sr in s_rows if sr[0] is not None)
                except Exception:
                    col_info["status_values"] = []
            elif TIME.search(name):
                col_info["time"] = True
            info["columns"][name] = col_info

        fp["tables"][t] = info

    return fp


def to_yaml(fp):
    tables = list(fp["tables"])
    out = ["# 本体草稿（scan_sql.py 自动生成）——须业务确认后才能晋升为 ontology.yaml",
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
    p = argparse.ArgumentParser(prog="scan_sql")
    p.add_argument("--dsn", help="数据库连接 DSN，如 postgres://user:pass@host:5432/db 或 mysql://...")
    p.add_argument("--sample", type=int, default=20, help="状态字段抽样上限")
    p.add_argument("--fingerprint", help="输出指纹 JSON 文件路径")
    p.add_argument("--diff", nargs=2, metavar=("OLD", "NEW"), help="比对两次指纹文件")
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

    if not a.dsn:
        p.error("需要 --dsn 或 --diff")

    fp = scan(a.dsn, a.sample)
    if a.fingerprint:
        with open(a.fingerprint, "w", encoding="utf-8") as f:
            json.dump(fp, f, ensure_ascii=False, indent=2)
    print(to_yaml(fp))


if __name__ == "__main__":
    main()
