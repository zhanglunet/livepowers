---
name: night-loop-planning
description: Use when a task must run for hours or overnight, should use idle off-peak compute, needs a strong model to plan and cheaper models to execute, or must be split into resumable concurrent jobs. 规划夜间 / 长程任务时使用。
---

# 夜间作业 Loop 规划

**节律：**白天提需求、定规格、交互探索；夜间跑可延后的长程任务与固化；早晨交付可审核的成果。

## 1. 判断是否适合夜间

适合：知识加工（图谱、文档抽取）、批量数据治理与血缘更新、模型训练 / 评测、"实现—测试—修复"循环、固化候选生成与回归测试、金丝雀评测、环境漂移扫描。
不适合：需要人即时等结果的交互请求；需要白天业务确认的写操作。

## 2. 强模型规划，便宜模型执行，上下文不出智能体

- **规划**：强模型把目标分解为任务图，写清每个节点的输入、产物与验收。
- **执行**：在**同一个**智能体框架内按节点切换到便宜模型或自有模型的子 Agent。
- **上下文入仓库**：PRD、意图、计划、进度、交接全部写入 git 或共享知识库；子 Agent 从文件读上下文。**不要在一个工具里讨论方案、再把一句话目标丢进另一个工具执行**——中间的上下文会全部丢失。
- 会话压缩或关闭前，把有价值的个人记忆总结进共享知识库。

## 3. 按"可稳定时长"切段

每个模型在当前 Harness 下有一个**可稳定完成的时长 H**（先实测：同类任务连续跑，记录多长时间后质量明显下降）。

- 节点预计时长 ≤ H；超过就再切。约 **2–30 分钟**的均质小段最稳。
- 在作业文件里声明 `model_horizon_minutes`，`lp job validate` 会拒绝超过 H 的节点。
- 优先用框架内置的图分解 + 循环检查来拆，不靠人工硬拆（人工拆容易割裂上下文）。

## 4. 交接契约：写实际终态，不写"预期已完成"

每个节点的 `handoff` 必填：

- `actual_end_state`：前一段**实际**终态的位置（分支、提交、产物清单、失败列表）；
- `checker`：独立的完成度检查者（另一个 Agent 或测试），防止"声称完成但做得很浅"；未达标就返工，不往下游传。

## 5. Graph Engineering：DAG

- 节点 = 可独立调度的原子任务；边 = 依赖与产物传递。
- 无依赖的节点并行；共享接口先约定契约再并行实现。
- 需要同时启动的节点（多卡训练、并行解析组）标为一个 gang。

## 6. Loop Engineering：每个循环装刹车

- **收敛条件**：什么算通过（测试全绿、指标 ≥ 阈值、引用校验 ≥95%）；
- **最大迭代次数**；
- **止损条件**：超预算、超时、连续 N 次同类失败 → 停止并交付可诊断记录。
- 单任务设 Token 与时长预算，超限熔断。核心指标是**每完成任务成本**，不是"用了多强的模型"——便宜模型 + 强 Harness 往往更优。

## 7. 统一作业契约

每个节点一份（`templates/job-contract.json`），必填：

`job_id, tenant, stage_id, dependency, priority, deadline, model_capability, resources, max_cost, retry_limit, stop_condition, checkpoint, preemptible, resume_policy, data_classification, acceptance, handoff, expected_minutes`

```bash
lp job validate jobs.json   # 必填字段、悬空依赖、环、单段时长、交接契约
```

## 8. 检查点与抢占

- 产物写入可复用位置（git 分支、对象存储），**不依赖一个一直活着的 Agent 进程保存上下文**。
- 可被高优先级任务抢占的节点标 `preemptible: true`，从检查点恢复。
- 参考优先级：在线推理 ＞ 交互研发 ＞ 知识数据批 ＞ 模型训练 ＞ 仿真探索。

## 9. 多角色协同

派单 / 执行 / 审查三角色分离，issue 驱动：每个节点一个 issue，执行者提交变更，审查者独立验收（`acceptance-gates`）。角色间通信走 `auditable-agent-comms`。

## 10. 次日交付物

- 代码变更（待人审）与测试证据；知识条目与引用校验结果；候选模型与评测报告；
- 失败与剩余风险清单；
- 本夜 Token / GPU 时 / 成本；
- `lp report` 晨报（含固化候选与能力复核）。
- **轻量、高频、多出小结果**：人类次日花 20–30 分钟评审并补入真实世界反馈，比一夜憋一个大结果更有效。

## 反模式

- 一个大目标、一个 Agent、跑一整夜、没有中间产物。
- 没有止损条件的循环。
- 规划和执行在两个不共享上下文的工具里。
- 交接里写"上一步应该已经完成"。
