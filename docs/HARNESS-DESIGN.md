# PRD-013/T1 草稿：harness 生成器设计（含完整走查示例）

> 状态：草稿。借鉴 HKUDS/CLI-Anything（Apache-2.0）"自动生成 CLI 控制层 + SKILL.md"。
> 本文档定义输入 schema，并用一个虚构但完整的能力 `ping-ledger`
> 走通"输入 YAML → CLI 代码 → SKILL.md"全链路，证明设计可落地。

## 1. 输入 schema（`capability.yaml`）

```yaml
# 必填
name: ping-ledger                 # [a-z0-9-]+，同时是目录名、CLI 名、skill 名
description: "记录一次心跳探测的结果，供值班 agent 查询最近 N 次心跳是否正常"
version: "0.1.0"
commands:
  - name: record                  # 子命令
    description: "记录一次心跳"
    args:
      - name: target              # 位置参数
        help: "探测目标，如 db-primary"
      - name: ok                  # flag 参数
        flag: true
        help: "心跳正常时传 --ok"
      - name: note                # 可选参数
        optional: true
        help: "备注"
    examples:
      - "ping-ledger record db-primary --ok"
      - "ping-ledger record db-primary --note '超时 2s'"
  - name: recent
    description: "查最近 N 次心跳"
    args:
      - name: limit
        optional: true
        default: "10"
        help: "条数，默认 10"
    examples:
      - "ping-ledger recent --limit 5"
# 选填
storage: jsonl                    # record 落盘格式：jsonl（默认）| sqlite
```

约束：
- `name` 必须匹配 `^[a-z0-9-]+$`（目录/CLI/skill 三处同名，防手滑写劈叉）；
- 每个 command 至少 1 个 example（没例子 = 没验收）；
- 只用标准库生成（不引入新依赖）。

## 2. 输出约定

```
harness/<name>/
  cli.py          # 生成：argparse 分发 + --json + 错误码
  SKILL.md        # 生成：frontmatter + Quick Start + 命令章节
  capability.yaml # 输入原样存档（可追溯）
```

错误码规范（照搬 CLI-Anything 的 agent 友好约定）：
`0`=成功，`1`=失败，`2`=用法错误（argparse 默认）。

## 3. 完整走查：输入上面的 YAML，生成物如下

### 3.1 生成的 `cli.py`（可直接运行）

```python
#!/usr/bin/env python3
"""ping-ledger: 记录一次心跳探测的结果，供值班 agent 查询最近 N 次心跳是否正常
由 harness 生成器生成（草稿，需人工 review）。
"""
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).with_suffix("") .parent / "ping-ledger.jsonl"
# 注：生成器模板里 DATA 指向 harness/ping-ledger/ping-ledger.jsonl；
# 上面写法为排版简化，落仓版用绝对化路径。

def cmd_record(args):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "target": args.target,
        "ok": args.ok,
        "note": args.note or "",
    }
    with open(DATA, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    out = {"ok": True, "recorded": entry}
    print(json.dumps(out, ensure_ascii=False) if args.json else "recorded")
    return 0

def cmd_recent(args):
    rows = []
    if DATA.exists():
        for line in DATA.read_text(encoding="utf-8").splitlines()[-int(args.limit):]:
            rows.append(json.loads(line))
    if args.json:
        print(json.dumps({"ok": True, "rows": rows}, ensure_ascii=False))
    else:
        for r in rows:
            print(f"{r['ts']} {r['target']} {'OK' if r['ok'] else 'FAIL'} {r['note']}")
    return 0

def main(argv=None):
    p = argparse.ArgumentParser(prog="ping-ledger",
        description="记录一次心跳探测的结果，供值班 agent 查询最近 N 次心跳是否正常")
    p.add_argument("--json", action="store_true", help="机器可读输出（agent 用）")
    sub = p.add_subparsers(dest="command", required=True)
    pr = sub.add_parser("record", help="记录一次心跳")
    pr.add_argument("target", help="探测目标，如 db-primary")
    pr.add_argument("--ok", action="store_true", help="心跳正常时传 --ok")
    pr.add_argument("--note", default="", help="备注")
    pr.set_defaults(func=cmd_record)
    pq = sub.add_parser("recent", help="查最近 N 次心跳")
    pq.add_argument("--limit", default="10", help="条数，默认 10")
    pq.set_defaults(func=cmd_recent)
    args = p.parse_args(argv)
    try:
        return args.func(args)
    except BrokenPipeError:
        return 0
    except Exception as e:  # noqa: BLE001 —— 生成器模板统一出口，人工可收紧
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)
              if args.json else f"error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

### 3.2 生成的 `SKILL.md`（草稿）

```markdown
---
name: ping-ledger
description: "记录一次心跳探测的结果，供值班 agent 查询最近 N 次心跳是否正常。当需要记录心跳、查询最近心跳是否正常时使用。"
---

# ping-ledger

记录一次心跳探测的结果，供值班 agent 查询最近 N 次心跳是否正常。

## 30 秒速览

```bash
python3 harness/ping-ledger/cli.py record db-primary --ok   # 记一次
python3 harness/ping-ledger/cli.py recent --limit 5 --json   # 查最近 5 次（agent 用 --json）
```

## 命令

### record — 记录一次心跳

```bash
ping-ledger record db-primary --ok
ping-ledger record db-primary --note '超时 2s'
```

| 参数 | 类型 | 说明 |
|---|---|---|
| target | 位置参数 | 探测目标，如 db-primary |
| --ok | flag | 心跳正常时传 |
| --note | 可选 | 备注 |

### recent — 查最近 N 次心跳

```bash
ping-ledger recent --limit 5
```

| 参数 | 类型 | 说明 |
|---|---|---|
| --limit | 可选，默认 10 | 条数 |

退出码：`0`=成功，`1`=失败，`2`=用法错误。加 `--json` 得机器可读输出。

---
*本文件由 harness 生成器生成（草稿，需人工 review 后使用）。*
```

## 4. 生成器实现要点（T2/T3 照此做）

- 一个 Python 脚本 `scripts/gen_harness.py`，读 `capability.yaml`，用字符串模板吐出 `cli.py` + `SKILL.md`；
  模板里凡是"示例/描述"都来自 YAML，生成器自己不编造业务语义。
- 生成后自检（T3 做）：跑一遍 `python3 cli.py --help`（退出码 0）；
  用 PRD-012 的契约测试扫一遍生成的 SKILL.md（frontmatter/引用）。
- 生成物头部统一标注"草稿，需人工 review"（防直接上生产）。

## 5. 待定（T4 e2e 时回答）

- `storage: sqlite` 要不要在第一期支持（默认 jsonl 够不够用）；
- 生成器要不要顺手生成 `tests/` 空壳（与 PRD-012 握手）。
