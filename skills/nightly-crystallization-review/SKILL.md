---
name: nightly-crystallization-review
description: Use at end of day, when a nightly job starts, or when asked "what can be crystallized today" or "is the product getting more skilled". 收工 / 夜间回顾证据、挑固化候选、出晨报时使用。
---

# 夜间固化评审

白天探索，夜间固化，早晨验收。活产品每天醒来都应该比昨天更熟练一点。

## 步骤

1. **看全局。**
   ```bash
   lp evidence stats
   ```
   看 System 2 占比的**周趋势**：应随时间下降。若上升，要么新需求变多，要么固化能力在失效——都要在晨报里说明。

2. **挑候选。**
   ```bash
   lp candidates --min-count 3
   ```
   对每个候选：读 `.livepowers/explorations/` 对应记录，合并同义意图；用 `lp score` 过 F-V-S-R 与盈亏平衡；写操作候选标"需 oltp-action-safety"。

3. **夜间生成。**对通过门禁的候选，按 `crystallize-to-system1` 生成测试、实现与能力包草稿，在隔离环境运行测试。**不要在夜间注册**——注册要等早晨人工采纳。产物放分支或 `.livepowers/pending/<intent>/`。

4. **复核已固化能力。**
   ```bash
   lp registry review --idle-days 60 --verify-days 30 --current-model <当前模型>
   ```
   - 连续失败（去固化信号）；
   - 受环境漂移或本体升级影响（来自 `env-scan-ontology` 的夜间扫描、`ontology-evolution` 的发布记录）；
   - 长期无人调用（考虑退役，避免能力库变成新的"死软件"）；
   - 久未复验（重跑测试集后 `lp registry verify <id>`）；
   - 验证模型与当前模型不一致（重跑基准，见 `agent-harness-for-tools`）。

5. **金丝雀评测。**固定一组小样例，每晚用当前模型跑，与历史结果比较，发现模型隐性降质或 Token 异常增长。

6. **出晨报。**
   ```bash
   lp report --current-model <当前模型>
   ```
   在 `.livepowers/reports/morning-<日期>.md` 末尾补充：
   - 每个待验收产物：意图、评分、n*、测试结果、分支位置、需要谁签字；
   - 建议退役 / 复核的能力及原因；
   - 金丝雀结果；本夜资源消耗。

7. **早晨采纳后**：通过的 `lp registry add ... --generated-by <夜间Agent> --accepted-by <采纳人>`；不通过的写明原因回到 System 2。

## 汇报口径

"昨夜评审了 N 个候选，生成 M 个固化产物待验收（其中 K 个为写操作）；建议退役 1 个能力（口径变化）；金丝雀无回归。System 2 占比本周从 x% 降到 y%。"

## 提醒

自动固化并不可靠——已有研究表明从交互轨迹自动生成技能可能迁移失败、不如简单频率基线。夜间产出的永远是"草稿 + 测试证据"，最终决定权在人。
