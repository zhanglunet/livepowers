---
name: system1-first
description: Use when handling any business request (query, report, dashboard, business operation, routine task), before reasoning it out from scratch. 收到任何业务请求、准备动手前使用。
---

# System 1 优先

**为什么：**一次确定性执行的成本比一次大模型推理低几个数量级，而且可测试、可审计。同一件事做一千次，就不该推理一千次。

## 流程

1. **规范化意图。**把请求改写成简短、稳定、不含参数值的意图：
   - "帮我看看华东上周收入掉了多少" → `weekly revenue by region`（参数：region=华东，weeks=1）
   - "把超过 30 天没跟进的重点商机转给区域主管" → `transfer stale opportunity`
   先 `lp intents list` 看已有的规范意图与别名；用户的说法是已登记的别名时，直接用规范名。`lp registry find` 会按整组同义词匹配，所以别名也能命中。
2. **查注册表。**
   ```bash
   lp registry find "<规范化意图 + 关键词>"     # 退出码 0 = HIT，2 = MISS
   ```
3. **HIT → 执行 System 1。**
   - 核对能力的前置条件、权限、适用范围是否覆盖当前请求；不覆盖视为 MISS。
   - 按 `entry` 调用。不要"顺手改进"已固化代码——改动走 `crystallize-to-system1` 发新版本。
   - 若是写操作能力（标 `[写操作]`），执行仍需过 `oltp-action-safety` 的执行阶段步骤（确认点、幂等键）。
   - 记录证据（Claude Code 插件的钩子会在你调用 entry 时自动记一条；其他客户端手动记）：
     ```bash
     lp evidence add --intent "<意图>" --system S1 --outcome success --capability <id> --cost <成本>
     ```
   - 报错或用户指出结果不对：记 `--outcome fail`，然后看下文"去固化信号"。
4. **MISS → 转 System 2。**进入 `explore-with-evidence`。功能级以上的需求先走 `ontology-grounded-spec`。
5. **建任务（功能级以上）。**`lp task new --title "<...>" --intent "<意图>" --max-loops 5 --budget <预算>`，让后续探索有轮次和预算上限。

## 去固化信号

任一出现，说明 System 1 能力可能已不适应环境：

- 同一能力连续失败 ≥ 2 次（`lp registry review` 会列出）；
- 用户纠正了口径；
- `env-scan-ontology` 报告相关表、字段或状态取值发生变化；
- 依赖的本体版本已升级而能力未复验。

处理：本次改走 System 2 完成；在晨报中标记待复核；确认失效后 `lp registry retire <id> --reason "<原因>"`。去固化不是失败，是活产品在适应环境。

## 汇报方式

一句话说明走了哪条路径，例如："已用固化能力 `cap_weekly_revenue_by_region` v1.2 直接生成（未调用大模型推理）。"
