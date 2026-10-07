---
name: outcome-ledger
description: Use when committing to a business outcome, choosing pilot scenarios, reporting value, comparing delivery approaches, or preparing outcome- or workflow-based pricing — registers a baseline before any work, measures deltas, allocates all costs (including failures, rework and takeover) to accepted tasks, and reports cost per accepted task, time to first value and incremental value. 衡量业务结果、核算单位成本、论证价值时使用。
---

# 结果台账

**没有基线的价值不算价值。**感知提效、生成提效与完整交付提效要分别测量；经济账以**通过验收的任务**为分母。

## 价值闸门：四个"可"

一项能力要进入规模化，必须同时满足：

1. **可量化**：有基线、目标、增量；
2. **可归因**：增量能落到具体任务或决策节点，而不是"整体变好了"；
3. **可复现**：换一个组织单元、区域或客户仍成立；
4. **可经营**：能进入续用、扩容或计费决策。

缺任何一条，只能算演示。

## 步骤

1. **立项先登记基线**（没有基线不开始探索）：
   ```bash
   lp outcome baseline --scenario <场景> --metric <指标> --value <基线值> \
     --target <目标值> --base <业务基数B> --owner <业务负责人> --confirmed-at <范围确认时间>
   ```
2. **定义"什么算完成"。**写清完成判定、重开、失败与人工接管如何计。这一步同时决定将来能不能按结果计价。
3. **归集全部成本**（失败任务的成本也要算）：
   ```bash
   lp outcome cost --scenario <场景> --kind human|inference|tool|rework|ops|amortization|takeover --amount <金额>
   ```
   推理成本也可在 `lp evidence add --note "scenario=<场景>"` 中自动归集。
4. **记录采纳**：
   ```bash
   lp outcome accept --scenario <场景> --task <任务id> --by <采纳人> [--first] [--rejected]
   ```
   `--first` 标记首个生产任务被采纳，用于计算首次价值交付时间。
5. **定期测量与报告**：
   ```bash
   lp outcome measure --scenario <场景> --metric <指标> --value <当前值>
   lp outcome report
   ```

## 指标定义

| 指标 | 定义 |
|---|---|
| 验收任务平均成本 | 同一周期全部归集成本 ÷ 通过约定验收的任务数。按复杂度与风险分层；比较时验收标准一致；失败与接管成本不得遗漏 |
| 首次价值交付时间 | 从客户正式确认任务范围，到首个生产任务被采纳。数据接入、授权等待、异常处理分别记录，同时保留总时长 |
| 跨客户资产复用率 | 按事先固定的功能点或工作量，来自其他项目、完成适配并**重新验证**的资产占比。复制代码或改名不算复用 |
| 增量价值 | ΔV = 业务基数 B × 提升率 u。基数大时，小比例提升也显著 |
| 配套记录 | 门禁覆盖率、返工与回撤轮次、人工接管比例、采纳主体 |

## 北极星

不是"部署了多少个智能体"，而是：**每轮学习后，下一单位业务价值是否被更快、更便宜、更可信地创造出来。**产品的学习速度应快于客户自行内化的速度。

## 计价光谱（供讨论，不是推荐）

按资源（Token / 调用量）→ 订阅 → 额度 / 积分 → 按工作流 → 按结果 → 按岗位。越往右，供方承担的风险越大，越依赖上面的台账：可靠完成的任务决定可计费量，复用与低返工决定单位成本。几种模式长期分层共存。

## 红线

- 不把模型给出的解释当作因果证据；变化分解只提供构成证据，因果判断另需研究设计。
- 不只统计成功调用的费用。
- 不在验收标准变化后直接与旧数据比较。
