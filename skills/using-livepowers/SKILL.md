---
name: using-livepowers
description: Use when starting any conversation that touches business software, data analysis, transactional systems, ontology, agent product delivery, long-running jobs or multi-agent work, before any response or action. 开始任何企业业务软件 / 数据分析 / 交易系统 / 本体 / 智能体交付 / 长程任务 / 多智能体工作前使用。
---

# Using Livepowers

Livepowers 让智能体按「活产品（Live Product）」范式工作：

> **Agentic AI = Agent + Ontology + Harness**
> Agent 提供开放能力，Ontology 定义业务语义，Harness 规范工程约束。
> 高频、可验证、稳定的事交给 **System 1**（已固化的代码 / CLI / SQL / 工作流，CPU，便宜、确定）；
> 新需求、低频、环境变化交给 **System 2**（Agent + 大模型探索，GPU，昂贵、概率性）。
> 探索必留证据；满足判据的成功路径**固化**回 System 1；固化失效就**去固化**。
> 白天探索，夜间固化，早晨验收。

<EXTREMELY-IMPORTANT>
只要有 1% 的可能某个 Livepowers 技能适用，你就必须先读它再行动。技能是强制工作流，不是建议，也不能用"这次很简单"跳过。
</EXTREMELY-IMPORTANT>

## 七条铁律

1. **先检查技能。**任何任务开始前，先按下面的路由表找到适用技能。
2. **先 System 1，后 System 2。**业务请求先 `lp registry find "<意图>"`；命中就调用已固化能力，不重新推理。
3. **没有证据的探索等于没发生。**每次探索结束都 `lp evidence add`。
4. **不在本体之外操作。**缺对象、缺口径就提 Ontology Delta（`ontology-evolution`），不用一段脚本掩盖模型缺口。
5. **写操作必过安全门禁。**前提、权限、事务、幂等、并发、审批、审计、补偿，缺一不可（`oltp-action-safety`）。
6. **生成者不评审自己。**验收标准和基准用例不能由生成方修改；完成与否由验收条件决定，智能体的自我声明只是待检查信息（`acceptance-gates`）。
7. **没有基线的价值不算价值。**承诺业务结果前先登记基线（`outcome-ledger`）。

## 路由表

| 场景 | 技能 |
|---|---|
| 接入新环境 / 新数据库 / 新系统；需要"知道自己在哪里"；环境可能变了 | `env-scan-ontology` |
| 有一个业务需求要实现（报表、看板、命令、流程） | `ontology-grounded-spec` |
| 需要新增或修改对象、关系、状态、指标口径、规则 | `ontology-evolution` |
| 收到业务请求，准备动手 | `system1-first` |
| 没有现成能力，需要 Agent 探索 | `explore-with-evidence` |
| 某条路径被反复探索成功，考虑变成代码 / CLI / 能力包 | `crystallize-to-system1` |
| 接口已有，但业务 Agent 用不稳；或要换模型 | `agent-harness-for-tools` |
| 任何候选能力要进入生产；任何"我做完了"需要被确认 | `acceptance-gates` |
| 任何写生产状态的动作 | `oltp-action-safety` |
| 跨小时 / 跨夜任务、多模型分工、利用夜间算力 | `night-loop-planning` |
| 收工或夜间：回顾证据、挑固化候选、复核能力、出晨报 | `nightly-crystallization-review` |
| 多个 Agent 互相通信，需要可审计、可回放 | `auditable-agent-comms` |
| 把领域产品交付到客户现场（存量改造或新建） | `fde-delivery` |
| 要衡量业务结果、核算单位成本、论证价值 | `outcome-ledger` |
| 要把一个岗位的工作交给"人 + 智能体团队"共同承担 | `digital-role-spec` |
| 新建或修改 Livepowers 技能本身 | `writing-livepowers-skills` |

## 工具

技能包自带脚本（纯 Python 3.9+ 标准库，位于插件的 `scripts/`）：

- `lp.py`：证据、能力注册表与 System 1 路由、F-V-S-R 评分与盈亏平衡、固化候选、任务看板状态机、结果台账、资产回流、作业契约校验、能力复核、晨报。
- `agent_switch.py`：智能体交换机（中转 / 旁路记录、哈希链、回放、审计）。
- `scan_sqlite.py`：环境扫描示例（本体草稿、环境指纹、漂移比对）。

首次在项目中使用：`python <plugin>/scripts/lp.py init`，创建 `.livepowers/`（建议纳入 git）。下文用 `lp` 代指 `python <plugin>/scripts/lp.py`。

## 三层架构的落点

| 层 | 承载什么 | 不要放什么 |
|---|---|---|
| Ontology | 对象、关系、状态、指标、规则、权限、行动契约（版本化） | 某次会话的临时理解 |
| 工具（Tool） | 确定性计算、查询、事务、业务行动 | 开放式判断 |
| 技能（Skill） | 完成一类任务的方法、适用条件、所需证据、工具用法、停止与恢复规则 | 本应确定执行的计算与事务 |

多智能体只在任务确有分工、并行或责任隔离需要时使用；简单任务用单个 Agent + 若干技能即可。

## 一次标准工作循环

```
业务请求 ──► system1-first：lp registry find
  ├─ HIT  → 核对前置条件 → 执行已固化能力 → lp evidence add --system S1
  └─ MISS → 功能级以上：lp task new（看板：待澄清）→ ontology-grounded-spec（必要时 ontology-evolution）
            → explore-with-evidence（看板：探索；有轮次与预算上限；**每轮结束 lp evidence add --system S2**）
            → acceptance-gates（看板：待验证）→ 交付
            └─ 超轮次 / 超预算 → 止损（看板：异常接管）→ takeover-handling
夜间 ──► nightly-crystallization-review：lp candidates → crystallize-to-system1（草稿 + 测试，写 pending 清单）
早晨 ──► 人工采纳：lp registry add（看板：已注册 → 生产运行）；不通过写明原因
运行 ──► 失败 / 口径变化 / 环境漂移 → 去固化（看板：回到探索）
```

会话级的小请求（一次性查询）不建任务，直接探索并记证据。

## 反模式（看到自己在这样想就停下）

| 念头 | 现实 |
|---|---|
| "这个我很熟，直接写" | 先查注册表和技能。 |
| "这次只是临时查一下，不用记证据" | 临时查询正是判断频率的数据来源。 |
| "模型答对了，注册成能力吧" | 没有测试、没有独立验收的路径不能固化。 |
| "把整段探索对话存成一个 Skill" | 固化物是最小、可测试的确定性代码，外加简短使用说明。 |
| "两个 Agent 直接互相调用更快" | 除非在可信沙箱内，否则走交换机或旁路日志。 |
| "Agent 说它完成了" | 看回执、看验收条件，不看自我声明。 |
| "用户随口说的想法就照做" | 不确定的想法是**假设**，不是指令；先澄清再执行。 |
| "多加几个 Agent 显得更先进" | 没有分工需要就用单 Agent。 |
