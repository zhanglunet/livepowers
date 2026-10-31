# PRD-255/T5 验收试运行记录：收录样例全流程

- 日期：2026-10-28
- trend issue：[zhanglunet/trend#1279](https://github.com/zhanglunet/trend/issues/1279)
- PRD：adopted/PRD-255-livepowers-skillspector-market-gate.md（zhanglunet/trend）
- 设计：livepowers `docs/plans/2026-10-28-prd-255-market-gate.md`（T1，§3.4 样本 + §6 验收标准）
- 分支：`trend/prd-255-t5-acceptance`（自 `trend/prd-255-t4-whitelist` 切出）
- 前置链：T1 #111 → T2 #113（`market_gate_scan.py` 7 例）→ T3 #115（`market_gate_flow.py` 6 例）→ T4 #117（`market_whitelist.py` 12 例）
- 状态：实现类 PR 只开不合并，等用户 review

## 1. 验收标准（PRD 原文口径）

> HIGH 不收录；报告随清单；无密钥

设计 §6 展开为五条：① N-1…N-4 全部不收录（HIGH），P-1 收录通过；② 每个收录条目的清单带 `gate_*` 字段，报告本体随清单归档可回放；③ 白名单放行 N 类误报演示：`gate_whitelist` 留痕 + 白名单文件签字齐全；④ N-4 license 声明与实测不符被拦（许可证红线断言）；⑤ 报告/清单/白名单密钥扫描 0 命中。

## 2. 验收方式

新增 `tests/test_prd255_acceptance.py`（12 例），按 §3.4 正负样本清单**回放 T2 夹具**，走 T3 单一入口 `admission_flow`，覆盖 T4 白名单与归档回放，全部断言走真实扫描/流程输出（零 mock、零网络，license 实测值按接口约定由调用方传入）。

运行方式：`tests/` 目录下 `python3 -m unittest test_prd255_acceptance -v`。

## 3. 用例对照（验收标准 → 用例）

| 验收标准 | 用例 | 结果 |
|---|---|---|
| P-1 收录通过 | `test_p1_clean_admitted_with_checklist_six_fields`：LOW/100 分，清单六字段齐全且 `gate_decision=admitted` | ok |
| N-1 隐藏指令不收录 | `test_n1_hidden_instruction_blocked`：M-1 命中，HIGH blocked | ok |
| N-2 过度授权不收录 | `test_n2_overreach_blocked`：M-2 命中，HIGH+（本夹具叠 M-3-02 达 CRITICAL）blocked | ok |
| N-3 凭据触碰不收录 | `test_n3_credential_blocked_floor_high`：M-3-01+M-3-02，floor HIGH blocked | ok |
| ④ N-4 license 红线 | `test_n4_license_redline_blocked`：声明 MIT 实测 NONE → M-4-02 HIGH blocked | ok |
| 拒绝态清单隔离 | `test_blocked_checklist_never_admitted`：`gate_decision` 恒 blocked | ok |
| ③ 白名单误报放行留痕 | `test_false_positive_pardon_traceable`：单条规则放行后 admitted，报告 `whitelist_applied` 与清单 `gate_whitelist` 逐条一致，白名单落盘文件 reason+reviewer 签字齐全 | ok |
| ② 报告随清单归档 | `test_report_archived_and_replayable`：按 `gate_report_ref` 落盘、重载后 `checklist_mapping` 回放与清单逐字段一致 | ok |
| ⑤ 密钥扫描（报告/清单） | `test_no_secret_hits_in_report_and_checklist`：含占位密钥样例的 N-3 归档物四类密钥模式 0 命中，证据 `<REDACTED>` 占位 | ok |
| ⑤ 密钥扫描（白名单） | `test_whitelist_artifacts_carry_no_secret`：白名单落盘文件 0 命中 | ok |
| 幂等（普通流） | `test_repeated_flow_identical`：同目录重复收录/拒绝流结果逐字段一致 | ok |
| 幂等（白名单态） | `test_whitelist_flow_idempotent`：同一白名单状态重复流结果一致 | ok |

## 4. 真实运行输出

```
$ cd tests && python3 -m unittest test_prd255_acceptance -v
test_blocked_checklist_never_admitted ... ok
test_n1_hidden_instruction_blocked ... ok
test_n2_overreach_blocked ... ok
test_n3_credential_blocked_floor_high ... ok
test_n4_license_redline_blocked ... ok
test_false_positive_pardon_traceable ... ok
test_p1_clean_admitted_with_checklist_six_fields ... ok
test_repeated_flow_identical ... ok
test_report_archived_and_replayable ... ok
test_no_secret_hits_in_report_and_checklist ... ok
test_whitelist_artifacts_carry_no_secret ... ok
test_whitelist_flow_idempotent ... ok
----------------------------------------------------------------------
Ran 12 tests in 0.052s

OK
```

全量回归（含 T2 `test_market_gate_scan` 7 例、T3 `test_market_gate_flow` 6 例、T4 `test_market_whitelist` 12 例）：

```
$ python3 -m unittest discover -s tests
----------------------------------------------------------------------
Ran 566 tests in 196.178s

OK (skipped=2)
✅ 发行就绪检查：全部 published 包成员 acceptance 状态合规
```

（2 跳过为既有环境条件跳过，与 T4 分支基线一致；554 → 566 = 基线 554 + 本任务 12 例，零回归。）

## 5. 结论

- **HIGH 不收录**：N-1…N-4 四类样本全部被硬闸门拦截，P-1 干净样本收录通过——红线达成；
- **报告随清单**：收录条目清单带 `gate_*` 六字段，报告本体按 `gate_report_ref` 归档可回放，重放清单逐字段一致——红线达成；
- **白名单可审计**：误报单条规则放行后收录，`gate_whitelist`/`whitelist_applied` 双侧留痕，白名单文件签字齐全——达成；
- **无密钥**：报告/清单/白名单三类归档物密钥扫描 0 命中，密钥证据一律 `<REDACTED>` 占位——红线达成。

验收通过（试运行口径），等用户 review；只开不合并。

## 6. 借鉴划界与虚构纪律

- 借鉴 [NVIDIA/SkillSpector](https://github.com/NVIDIA/SkillSpector)（实测 Apache-2.0）仅取"安检先行、分数门槛、白名单"模式，不复制代码/规则表/文案；
- 样本技能内容、复核人全虚构；密钥样例为占位形态（`sk-` 前缀拼接构造）；零宽字符用 `\u200b` 转义；不含真实主机名、IP、账号、密钥；全程零网络。
