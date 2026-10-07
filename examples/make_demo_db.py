#!/usr/bin/env python3
"""生成一个虚构的演示数据库（客户 / 负责人 / 商机 / 跟进活动），用于体验 Livepowers 的扫描与漂移检测。数据全部虚构。"""
import sqlite3, sys

path = sys.argv[1] if len(sys.argv) > 1 else "demo.sqlite"
drift = "--drift" in sys.argv
con = sqlite3.connect(path)
c = con.cursor()
c.executescript("""
drop table if exists activities; drop table if exists opportunities; drop table if exists customers; drop table if exists owners;
create table owners(id integer primary key, name text, region text, phone text);
create table customers(id integer primary key, name text, tier text, region text);
create table opportunities(id integer primary key, customer_id integer references customers(id), owner_id integer,
  amount real, stage text, last_followup_at text, version integer default 1);
create table activities(id integer primary key, opportunity_id integer, kind text, created_at text);
""")
c.executemany("insert into owners values (?,?,?,?)", [(1, "Owner A", "east", "000-0000"), (2, "Owner B", "south", "000-0001")])
c.executemany("insert into customers values (?,?,?,?)", [(1, "Customer X", "A", "east"), (2, "Customer Y", "B", "south")])
stages = ["lead", "qualified", "proposal", "won", "lost"] + (["on_hold"] if drift else [])
c.executemany("insert into opportunities(id,customer_id,owner_id,amount,stage,last_followup_at) values (?,?,?,?,?,?)",
              [(i, 1 + i % 2, 1 + i % 2, 100000 * i, stages[i % len(stages)], f"2026-0{1 + i % 9}-1{i % 9}") for i in range(1, 13)])
if drift:
    c.execute("alter table customers add column industry text")
con.commit()
print(path)
