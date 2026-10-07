---
name: nightly-crystallization-review
description: Use at end of day, when a nightly job starts, or when asked "what can be crystallized today" or "is the product getting more skilled". 收工 / 夜间回顾证据、挑固化候选、出晨报时使用。
---

# 夜间固化评审

白天探索，夜间固化，早晨验收。活产品每天醒来都应该比昨天更熟练一点。

## 步骤

1. **先清自动补记。**晨报"自动采集待确认"列出钩子补记的 `partial` 证据：能判断结论的，补一条带 `--outcome` 的显式记录；判断不了的留着，它们不计入成功率但计入频率。
2. **看全局。**
   ```bash
   lp evidence stats
   ```
   看 System 2 占比的**周趋势**：应随时间下降。若上升，要么新需求变多，要么固化能力在失效——都要在晨报里说明。

3. **挑候选。**
   ```bash
   lp candidates --min-count 3
   ```
   先合并同义意图，否则同一件事会被几个名字稀释、凑不够次数：
   ```bash
   lp intents suggest                 # 列出"长得像"的意图对，附登记命令
   lp intents alias "<规范意图>" "<别名>" --by <你>   # 人工确认后登记；历史证据读取时自动归并
   ```
   再对每个候选：读 `.livepowers/explorations/` 对应记录；用 `lp score` 过 F-V-S-R 与盈亏平衡；写操作候选标"需 oltp-action-safety"。

4. **夜间生成。**对通过门禁的候选，按 `crystallize-to-system1` 生成测试、实现与能力包草稿，在隔离环境运行测试。**不要在夜间注册**——注册要等早晨人工采纳。产物放分支或 `.livepowers/pending/<意图>/`，并登记清单：
   ```bash
   lp pending add --intent "<意图>" --score <评分> --n-star <n*> --tests "<测试命令>" --result pass|fail|partial \
     --location "<分支或目录>" --generated-by <夜间Agent> [--writes-state] --model <模型>
   ```
   没有登记的产物不会出现在晨报里，早晨也不会被验收。

5. **复核已固化能力。**
   ```bash
   lp registry review --idle-days 60 --verify-days 30 --current-model <当前模型>
   ```
   - 连续失败（去固化信号）；
   - 受环境漂移或本体升级影响（来自 `env-scan-ontology` 的夜间扫描、`ontology-evolution` 的发布记录）；
   - 长期无人调用（考虑退役，避免能力库变成新的"死软件"）；
   - 久未复验（重跑测试集后 `lp registry verify <id>`）；
   - 验证模型与当前模型不一致（重跑基准，见 `agent-harness-for-tools`）。

6. **金丝雀评测。**固定一组小样例（每个能力包的 `evals:` 里挑 3–5 个，加上几条跨能力的综合样例），每晚用当前模型跑一遍并记录：
   ```bash
   lp canary record --name <套件名> --model <当前模型> --pass <通过数> --total <总数> --tokens <总token>
   lp canary compare            # 通过率下降 >10% 或 token 上升 >30% → exit 5
   ```
   回归时先核对样例本身是否过期，再判断是模型降质还是能力失效；不要在夜间自动换模型。

7. **出晨报。**
   ```bash
   lp report --current-model <当前模型>
   ```
   晨报会自动汇总 `lp pending` 清单、证据候选、金丝雀比较、能力复核、看板与台账。在 `.livepowers/reports/morning-<日期>.md` 末尾只需补充：建议退役 / 复核的能力及原因、本夜资源消耗、需要谁签字。

8. **早晨采纳后**：通过的 `lp registry add ... --generated-by <夜间Agent> --accepted-by <采纳人>` 并 `lp pending done "<意图>" --by <采纳人> --accepted`；不通过的 `lp pending done "<意图>" --by <采纳人> --reason "<原因>"`，回到 System 2。`pending done` 会拒绝生成者给自己验收。

## 汇报口径

"昨夜评审了 N 个候选，生成 M 个固化产物待验收（其中 K 个为写操作）；建议退役 1 个能力（口径变化）；金丝雀无回归。System 2 占比本周从 x% 降到 y%。"

## 提醒

自动固化并不可靠——已有研究表明从交互轨迹自动生成技能可能迁移失败、不如简单频率基线。夜间产出的永远是"草稿 + 测试证据"，最终决定权在人。
