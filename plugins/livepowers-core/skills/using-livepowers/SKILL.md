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
| 注册表未命中、且需求是功能级以上（报表、看板、命令、流程） | `ontology-grounded-spec` |
| 需要新增或修改对象、关系、状态、指标口径、规则 | `ontology-evolution` |
| 收到业务请求，准备动手（**先走这一行**） | `system1-first` |
| 没有现成能力，需要 Agent 探索 | `explore-with-evidence` |
| 某条路径被反复探索成功，考虑变成代码 / CLI / 能力包 | `crystallize-to-system1` |
| 业务应用里要出一次性分析展示，或把次抛长成新的固化表结构与固定页 | `living-surface` |
| 接口已有，但业务 Agent 用不稳；或要换模型 | `agent-harness-for-tools` |
| 任何候选能力要进入生产；任何"我做完了"需要被确认 | `acceptance-gates` |
| 任何写生产状态的动作 | `oltp-action-safety` |
| 任务被止损转入异常接管、Agent 反复失败、人要从 Agent 手里接手 | `takeover-handling` |
| 跨小时 / 跨夜任务、多模型分工、利用夜间算力 | `night-loop-planning` |
| 收工或夜间：回顾证据、挑固化候选、复核能力、出晨报 | `nightly-crystallization-review` |
| 多个 Agent 互相通信，需要可审计、可回放 | `auditable-agent-comms` |
| 把领域产品交付到客户现场（存量改造或新建） | `fde-delivery` |
| 要衡量业务结果、核算单位成本、论证价值 | `outcome-ledger` |
| 要把一个岗位的工作交给"人 + 智能体团队"共同承担 | `digital-role-spec` |
| 新建或修改 Livepowers 技能本身 | `writing-livepowers-skills` |

## 工具

技能包自带脚本（纯 Python 3.9+ 标准库，位于插件的 `scripts/`）：

- `lp.py`：证据、能力注册表与 System 1 路由、F-V-S-R 评分与盈亏平衡、固化候选、任务看板状态机、结果台账、资产回流、夜间产物清单、金丝雀评测、作业契约校验、能力复核、晨报；活软件展示面（`lp surface validate / record / promote / reconcile / deploy`、`lp pages list`）。
- `agent_switch.py`：智能体交换机（中转 / 旁路记录、哈希链、回放、审计）。
- `scan_sqlite.py`：环境扫描示例（SQLite 本体草稿、环境指纹、漂移比对）。
- `scan_sql.py`：环境扫描通用实现（PostgreSQL / MySQL information_schema 查询、指纹与漂移比对）。


技能正文里的 `lp` 和 `templates/` 按安装方式对应到：

| 安装方式 | `lp` 是什么 | 脚本与模板在哪 |
|---|---|---|
| Claude Code 插件 | `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/lp.py`（启动钩子已告知路径） | `${CLAUDE_PLUGIN_ROOT}/scripts/`、`${CLAUDE_PLUGIN_ROOT}/templates/` |
| npm（`npx livepowers install`） | `npm i -g livepowers` 后直接 `lp`；或 `npx livepowers path` 取根目录 | `$(livepowers path)/scripts/`；模板同时装在本技能目录 `using-livepowers/templates/` |
| 仅复制技能 | 克隆仓库后 `alias lp='python3 /path/to/livepowers/scripts/lp.py'` | 仓库的 `scripts/`、`templates/` |

需要 Python 3.9+。找不到 `lp` 时先 `lp --help` 确认，不要凭记忆拼命令。

**证据自动采集（Claude Code 插件）。**插件的 `PostToolUse` / `Stop` 钩子会观测你的 Bash 命令：`lp registry find` 命中后每次调用该能力的 entry 都自动记一条 S1 证据（exit 非 0 或有 stderr 记 fail）；未命中而本轮结束前没有 `lp evidence add`，钩子会补记一条 S2 证据，结论标 `partial`、带 `auto: true`。**这只是兜底**：显式 `lp evidence add` 更准（有 verifiable、cost、note），探索结束仍要自己记；自动补记的记录会出现在晨报"自动采集待确认"里。能力的置信度 =（成功 + 1）/（调用 + 2），随 S1 调用升降，`registry find / list` 显示，低于 0.6 会进复核。`LP_HOOK_CAPTURE=0` 关闭采集。

首次在项目中使用：`lp init`，创建 `.livepowers/`。

## 项目目录约定

| 位置 | 放什么 | 入 git |
|---|---|---|
| `.livepowers/` | 证据、注册表、看板、台账、资产、金丝雀记录、晨报（`reports/`）、探索记录（`explorations/`）、环境指纹（`env/`）、夜间产物（`pending/<意图>/`） | 是（本仓库自己的 `.gitignore` 忽略它，你的项目不要照抄） |
| `.livepowers/ontology.draft.yaml` | `env-scan-ontology` 生成的本体草稿 | 是 |
| `ontology/ontology.yaml` | 已确认的本体（按 `templates/ontology.yaml`），版本号写在文件里 | 是 |
| `ontology/deltas/` | 本体变更提案（`ontology-evolution`） | 是 |
| `specs/<feature>.md` | 规格（`ontology-grounded-spec`） | 是 |
| 能力实现与测试 | 项目自己的代码目录；能力包清单路径写进 `lp registry add --package` | 是 |

冷启动：还没有确认本体时，用草稿本体（版本记为 `0.1.0-draft`）走通第一个任务；规格里引用草稿的对象名，待本体确认后升版。

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
