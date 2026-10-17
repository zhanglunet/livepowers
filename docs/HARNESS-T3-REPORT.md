# PRD-013/T3 自检报告：harness 生成器

> 日期：2026-10-17
> 对象：`scripts/gen_harness.py`（PR #36 合并版）+ `tests/_contract/run_contract.py`（PR #35 合并版）
> 输入：`docs/HARNESS-DESIGN.md` §1 的 ping-ledger `capability.yaml`（逐字重建）

## 自检方法

```bash
python3 scripts/gen_harness.py -o /tmp/selfcheck capability.yaml
```

生成物放在 `/tmp`，不进仓库。

## 结果（4/4 通过）

| # | 检查项 | 结果 |
|---|---|---|
| 1 | 生成 `harness/ping-ledger/`：`cli.py` + `SKILL.md` + 存档 `capability.yaml` | ✅ 退出码 0，3 个文件齐；存档与输入逐字节一致 |
| 2 | `python3 cli.py --help` 退出码 | ✅ 0 |
| 3 | `record` → `recent` 往返 | ✅ `record db-primary --ok` / `record db-primary --note '超时 2s'` 落盘为合法 JSONL（2 行）；`recent --limit 5 --json` 输出可被 `json.load` 解析，rows=2，数据正确 |
| 4 | 契约检查：把生成的 `SKILL.md` 摆成 `skills/ping-ledger/` 结构，调 `check_skill` | ✅ 0 error，0 warning |

## 结论

生成器与契约检查器均未发现 bug，本次无代码修改，仅提交本报告。

## 环境

- Python 3.12.3（仓库 CI 覆盖 3.9/3.11/3.13；生成器仅用标准库）
- Ubuntu 24.04（VM）
- 无 `lp` 真实环境（不影响本次自检项）
