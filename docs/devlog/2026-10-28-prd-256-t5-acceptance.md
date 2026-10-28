# PRD-256/T5 验收试运行记录：样例任务走三角色

- 日期：2026-10-28
- trend issue：[zhanglunet/trend#1284](https://github.com/zhanglunet/trend/issues/1284)
- PRD：adopted/PRD-256-livepowers-pi-subagents-template.md（zhanglunet/trend）
- 设计：livepowers `docs/plans/2026-10-28-prd-256-pi-subagents-template.md`（T1，§6 T5 验收标准）
- 分支：`trend/prd-256-t5-acceptance`（自 `trend/prd-256-t4-boundary-doc` 切出）
- 前置链：T1 #112（设计）→ T2 #114（模板包 + `validate_handoff.py` 8 例）→ T3 #116（example-walkthrough 5 例）→ T4 #118（boundary-vs-112 3 例）
- 状态：实现类 PR 只开不合并，等用户 review

## 1. 验收标准（PRD 原文口径）

> 交接合同齐全；无密钥；只借形态无违规拷贝

设计 §6 展开为五条：① 示范任务三角色走通，全部交接合同过 `handoff.schema.json` 校验；② 合同三要素（input/expect/result）齐全，acceptance 逐条有 evidence；③ 演示含一次 verify 打回→implement 修复→重新派发的完整流转（rejected 留痕）；④ 主会话汇总由合同 result 对照呈现（无需额外报告文件）；⑤ 模板包与示范零密钥；与上游 pi-subagents 逐段比对确认零文案拷贝。

## 2. 验收方式

新增 `tests/test_prd256_acceptance.py`（11 例），对 T3 示范走查（example-walkthrough.md 内联合同）做端到端回放 + 对 T2/T4 交付物做结构与红线核查。全部零 mock、零网络。

**零拷贝比对的取样说明**：上游关键短语抽样自 [nicobailon/pi-subagents](https://github.com/nicobailon/pi-subagents) main 分支（2026-10-23 实测取样：`README.md`、`agents/scout.md`、`agents/worker.md`、`agents/reviewer.md` 共 14 条 verbatim 片段），固化为离线夹具写入测试文件，断言这些上游原文短语在本模板包任一文件**零命中**——测试本身零网络、可重放。

运行方式：`tests/` 目录下 `python3 -m unittest test_prd256_acceptance -v`。

## 3. 用例对照（验收标准 → 用例）

| 验收标准 | 用例 | 结果 |
|---|---|---|
| ① 三角色走通 + 合同全过 schema | `test_all_inline_contracts_pass_schema_with_three_elements`：走查 5 份内联合同逐个过 handoff.schema.json（内置退化校验） | ok |
| ② 合同三要素齐全 + evidence 逐条 | `test_acceptance_items_backed_by_evidence`：input/expect/result 齐全、constraints 派发必带、终态合同 evidence 非空 | ok |
| ③ 三角色最终 done | `test_three_roles_final_done` | ok |
| ③ rejected 打回流转闭环 | `test_rejected_flow_closed_loop`：verify rejected（留失败条目证据）→ implement 修复 done → verify 复验 done | ok |
| ③ 重派引用原 task_id | `test_retry_contracts_reference_original_task_ids`：新 task_id + retries 引用原 task_id，修复重派落在 implement | ok |
| ④ 汇总对照呈现 | `test_summary_section_compares_three_results`：汇总节对照三份最终合同 task_id 与 result.status，无额外报告文件 | ok |
| ⑤ 零文案拷贝（关键短语抽样） | `test_upstream_key_phrases_absent_from_pack`：上游 14 条抽样短语在模板包 7 个文件零命中 | ok |
| ⑤ 只借形态（角色体系不复用） | `test_upstream_role_system_not_reused`：角色页仅本仓原创 explore/implement/verify；合同 to 枚举不含上游 scout/worker/reviewer/oracle/researcher/delegate/evidence-auditor | ok |
| ⑤ 零密钥 | `test_no_secret_hits_in_template_pack`：模板包全文件五类密钥模式 0 命中 | ok |
| 结构完整 | `test_all_deliverables_in_place`：README/三角色页/schema/走查/边界文档/校验入口在位 | ok |
| 结构完整（校验入口可用） | `test_validator_cli_accepts_walkthrough_contract`：`validate_handoff.py` 对走查合同 CLI 判 0（valid handoff-v1） | ok |

## 4. 真实运行输出

```
$ cd tests && python3 -m unittest test_prd256_acceptance
----------------------------------------------------------------------
Ran 11 tests in 0.195s

OK
```

全量回归（含 T2 `test_prd256_handoff_template` 8 例、T3 `test_prd256_walkthrough` 5 例、T4 `test_prd256_boundary_doc` 3 例）：

```
$ python3 -m unittest discover -s tests
----------------------------------------------------------------------
Ran 556 tests in 190.528s

OK (skipped=3)
✅ 发行就绪检查：全部 published 包成员 acceptance 状态合规
```

（3 跳过均为既有环境条件：jsonschema 未安装 / LP_DENYLIST / PG DSN，与 T4 分支基线一致；545 → 556 = 基线 545 + 本任务 11 例，零回归。）

## 5. 结论

- **交接合同齐全** ✅：示范 5 份内联合同全部过 `handoff.schema.json`，三要素齐全、constraints 必带、acceptance 逐条有 evidence；
- **无密钥** ✅：模板包（含示范与边界文档）密钥扫描 0 命中；
- **只借形态无违规拷贝** ✅：上游（实测 MIT）14 条关键短语抽样零命中；角色体系不复用（本仓原创 explore/implement/verify vs 上游 scout/worker/reviewer/oracle 体系）；示范与角色文案全本仓原创；
- 打回流转闭环：verify rejected 留痕 → implement 新 task_id 重派修复 → verify 复验 done；主会话汇总以合同 result 对照呈现。

验收通过（试运行口径），等用户 review；只开不合并。

## 6. 借鉴划界与虚构纪律

- 上游 [nicobailon/pi-subagents](https://github.com/nicobailon/pi-subagents) License API 实测 **MIT**（日报原标注"未核实"，T1 已实测修正）；仅借鉴"探索/实现/验证三角色 + 交接合同"形态，不复制其角色文案、模板文件与代码；角色边界、`handoff-v1` 字段、示范走查为本仓原创；
- 走查任务（示例 CLI `examples/echo-cli`）、路径、命令、输出全虚构；不含真实主机名、IP、账号、密钥；全程零网络。
