# livepowers 技能包分层总登记册（REGISTRY）

> PRD-227/T3（trend #1137）落地。机读权威源：[`registry.json`](registry.json)（4 包 / 21 技能）；本文件由其生成——生成命令 `python3 scripts/skill_registry.py --render > REGISTRY.md`，**禁止手改本文件**，两载体不一致即漂移（规范 §7，测试机判）。
>
> 技能包分层规范：skill-pack-layering-spec@1.0.0（docs/plans/2026-10-26-skill-pack-layering-spec.md，评审通过后定版）。本登记册为包归属与检索的单一事实源（规范 §7）；人读 REGISTRY.md 由本文件生成。
>
> 「分层 + 总登记册」组织形态借鉴 AgriciDaniel/claude-seo（MIT License，Copyright (c) Daniel Agrici，https://github.com/AgriciDaniel/claude-seo）：只复用形态，未复用其代码与文本。

检索：`python3 scripts/skill_registry.py <触发词…>`（例：`交付`、`验收`、`本体`、`夜巡`）。

## livepowers-delivery — 交付域：端到端交付链、FDE 实施路径与可持续演进的活页面交付面

version 0.1.0 ｜ spec_version 1.0.0

| skill | 触发词（frontmatter description 原文） | 验收例 |
|---|---|---|
| **delivery-chain** | Use when a business request must be delivered end-to-end as one pipeline (scan the environment and ontology, ground a spec, explore with evidence, pass the acceptance gates, then record the outcome in the ledger), or when such a delivery stopped at the human acceptance gate and must be resumed. 一条业务请求需要端到端交付（扫描→规格→探索→验收→台账）、或交付停在人工验收门需要续跑时使用。 | 按 skills/delivery-chain/SKILL.md 执行，产出满足 metadata.output：交付链路核对记录 |
| **fde-delivery** | Use when delivering a domain Live Product at a customer site as a forward-deployed engineer, for a brownfield retrofit or a greenfield build, or when field innovations must flow back into the product. 把领域产品交付到客户现场时使用。 | 按 skills/fde-delivery/SKILL.md 执行，产出满足 metadata.output：现场交付（FDE）执行记录 |
| **living-surface** | Use when a business application shows fixed pages and the user asks the embedded agent for an analysis or chart that no fixed page covers, when the user wants a one-off result kept as a permanent page, or when a new derived table, view or metric should become part of the fixed structure. 活软件里出次抛分析展示、或把次抛长成固化表结构与固定页时使用。 | 按 skills/living-surface/SKILL.md 执行，产出满足 metadata.output：活页面固化方案 |

## livepowers-governance — 治理与安全域：验收门、写操作安全边界、人机接管与可审计通信

version 0.1.0 ｜ spec_version 1.0.0

| skill | 触发词（frontmatter description 原文） | 验收例 |
|---|---|---|
| **acceptance-gates** | Use when any candidate capability, ontology change, spec implementation or agent-produced result is about to enter production, or whenever an agent or person says "done" and that claim needs to be confirmed. 报表上线、注册前需要独立审查验收，候选能力进入生产、或任何"已完成"需要被确认时使用。 | 按 skills/acceptance-gates/SKILL.md 执行，产出满足 metadata.output：验收门清单与逐门判定记录 |
| **auditable-agent-comms** | Use whenever two or more agents (dispatcher / executor / reviewer, or agents across teams or organizations) exchange messages and the exchange must be logged, auditable, replayable or metered. 多个 Agent 互相通信时使用。 | 按 skills/auditable-agent-comms/SKILL.md 执行，产出满足 metadata.output：可审计通信记录格式 |
| **oltp-action-safety** | Use before exploring, crystallizing or executing any action that writes production state (create, update, transfer, approve, bill, push configuration), including on legacy systems without transactions. 任何写生产状态的动作之前使用。 | 按 skills/oltp-action-safety/SKILL.md 执行，产出满足 metadata.output：OLTP 写操作安全检查清单 |
| **takeover-handling** | Use when a task has been stopped by the loop or budget limit and moved to takeover, when an agent keeps failing on the same step, when a person is asked to take over from an agent, or when the morning report lists tasks in takeover. 任务被止损转入异常接管、Agent 反复失败、人要从 Agent 手里接手时使用。 | 按 skills/takeover-handling/SKILL.md 执行，产出满足 metadata.output：异常接管操作记录 |

## livepowers-methodology — 方法论域：技能写作规范、结晶泛化与本体锚定的规格与演化

version 0.1.0 ｜ spec_version 1.0.0

| skill | 触发词（frontmatter description 原文） | 验收例 |
|---|---|---|
| **agent-harness-for-tools** | Use when CLIs / MCP tools / APIs already exist but business agents use them unreliably, when a weaker or different model must take over a workflow, or right after a model upgrade lands. 接口已有但 Agent 用不稳、或要换模型时使用。 | 按 skills/agent-harness-for-tools/SKILL.md 执行，产出满足 metadata.output：工具 harness 配置与包装说明 |
| **crystallize-to-system1** | Use when an intent has been explored successfully several times, when the user says "do it this way from now on", or when the nightly review has selected a crystallization candidate. 把探索成功的路径固化为 System 1 能力包时使用。 | 按 skills/crystallize-to-system1/SKILL.md 执行，产出满足 metadata.output：System 1 能力包草稿 |
| **digital-role-spec** | Use when a job role or recurring function is to be carried by humans plus an agent team (a "digital role"), or when someone asks which parts of a position can be automated and what it would cost. 把一个岗位的工作交给"人 + 智能体团队"时使用。 | 按 skills/digital-role-spec/SKILL.md 执行，产出满足 metadata.output：数字角色规格文档 |
| **generalizing-skills** | Use when a skill only works in the project it was written for (hard-coded files, columns, thresholds, templates or channels), when the same kind of skill is rewritten for each new project, or when a generalized skill is first used in a new workspace or its environment may have changed. 把只能在单个项目用的 skill 改成跨项目复用、或在新 workspace 首次使用时使用。 | 按 skills/generalizing-skills/SKILL.md 执行，产出满足 metadata.output：跨项目通用化改造说明 |
| **ontology-evolution** | Use when a task needs an object, relation, state, metric definition or rule the ontology does not have, when two definitions conflict, or when a business rule changes (new policy, new threshold, new effective date). 需要新增或修改本体定义、规则变更时使用。 | 按 skills/ontology-evolution/SKILL.md 执行，产出满足 metadata.output：本体演进条目 |
| **ontology-grounded-spec** | Use before implementing any business feature, report, dashboard, query, transactional command or workflow, and whenever a request is ambiguous about scope, definitions or acceptance. 实现任何业务功能之前使用。 | 按 skills/ontology-grounded-spec/SKILL.md 执行，产出满足 metadata.output：本体对齐规格（含输出物章节） |
| **system1-first** | Use when handling any business request (query, report, dashboard, business operation, routine task), before reasoning it out from scratch. 收到业务请求准备动手，或想先找注册表里的现成固化能力时使用。 | 按 skills/system1-first/SKILL.md 执行，产出满足 metadata.output：System 1 现成固化能力检索 |
| **writing-livepowers-skills** | Use when creating a new Livepowers skill, editing an existing one, or turning a team's recurring practice into a skill. 新建或修改 Livepowers 技能时使用。 | 按 skills/writing-livepowers-skills/SKILL.md 执行，产出满足 metadata.output：skill 编写规范与骨架 |

## livepowers-ops — 运行域：环境扫描、循证探索、夜巡规划复盘与结果台账

version 0.1.0 ｜ spec_version 1.0.0

| skill | 触发词（frontmatter description 原文） | 验收例 |
|---|---|---|
| **env-scan-ontology** | Use when onboarding a new database, business system, API set or customer site, when starting a brownfield or greenfield delivery, or whenever schema / interface drift is suspected. 接入新环境、扫描库表生成本体、检测环境漂移时使用。 | 按 skills/env-scan-ontology/SKILL.md 执行，产出满足 metadata.output：环境扫描本体对照表 |
| **explore-with-evidence** | Use when the capability registry misses, when a request is new, rare or the environment has changed, and the agent must reason it out with the LLM (write SQL, analyze, trial-and-error, orchestrate tools). 注册表未命中、需要 Agent 自主探索时使用。 | 按 skills/explore-with-evidence/SKILL.md 执行，产出满足 metadata.output：带证据引用的探索记录 |
| **night-loop-planning** | Use when a task must run for hours or overnight, should use idle off-peak compute, needs a strong model to plan and cheaper models to execute, or must be split into resumable concurrent jobs. 规划夜间 / 长程任务时使用。 | 按 skills/night-loop-planning/SKILL.md 执行，产出满足 metadata.output：夜间/长程任务计划 |
| **nightly-crystallization-review** | Use at end of day, when a nightly job starts, or when asked "what can be crystallized today" or "is the product getting more skilled". 收工 / 夜间回顾证据、挑固化候选、出晨报时使用。 | 按 skills/nightly-crystallization-review/SKILL.md 执行，产出满足 metadata.output：固化候选与晨报 |
| **outcome-ledger** | Use when committing to a business outcome, choosing pilot scenarios, reporting value, comparing delivery approaches, or preparing outcome- or workflow-based pricing. 衡量业务结果、核算单位成本、论证价值时使用。 | 按 skills/outcome-ledger/SKILL.md 执行，产出满足 metadata.output：业务结果台账与价值论证 |
| **using-livepowers** | Use when starting any conversation that touches business software, data analysis, transactional systems, ontology, agent product delivery, long-running jobs or multi-agent work, before any response or action. 开始任何企业业务软件 / 数据分析 / 交易系统 / 本体 / 智能体交付 / 长程任务 / 多智能体工作前使用。 | 按 skills/using-livepowers/SKILL.md 执行，产出满足 metadata.output：路由决策：指向最适合当前任务的能力包 |

版本政策：全库 lockstep 0.1.0（规范 §6.3 允许的本地政策；包内 skill 增删或定位变更至少升 MINOR）
