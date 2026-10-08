# 对比：Livepowers 与 Superpowers 及同类产品

> 更新于 2026-10-07，对应 Livepowers v1.2.0、Superpowers 6.3.0。对比对象的信息来自各自的仓库、文档与公开文章（文末附来源）；若与其最新版本不符，请提 Issue 指正。

## 一句话定位

- **Livepowers**：业务智能体的"活产品"工作方法。Agent + Ontology + Harness；System 1（已固化能力）优先，System 2（Agent 探索）留证据，成功路径固化为经测试的能力，独立验收；白天探索、夜间固化、早晨采纳。
- **Superpowers**：编码智能体的软件开发方法论。brainstorm → plan → 子 Agent TDD 实现 → 评审 → 收尾，技能是强制工作流。

两者可以同时安装：Livepowers 决定"做什么、要不要固化、算不算完成"，Superpowers 负责"固化代码怎么写好"。Livepowers 的仓库结构、SessionStart 注入、"技能即强制工作流"和"用压力情境写技能"都借鉴自 Superpowers。

## Superpowers 的技能（6.3.0，14 个）

| 分组 | 技能 | 用途 |
|---|---|---|
| 入口 | `using-superpowers` | 会话启动注入；"有 1% 可能适用就必须用技能"；红旗表反合理化 |
| 元 | `writing-skills` | 用 TDD 写技能：先让子 Agent 在压力场景下失败，再写最小技能，再堵漏 |
| 协作 | `brainstorming` | 创造性工作前必用；分 spike / bounded / architectural；人类批准设计前不得写代码 |
| 协作 | `writing-plans` | 有规格后写实施计划：小步骤、精确路径、TDD |
| 协作 | `executing-plans` | 在独立会话中按计划执行，带人工检查点 |
| 协作 | `subagent-driven-development` | 每任务派一个子 Agent 实现 + 两段评审 + 最终全分支评审 |
| 协作 | `dispatching-parallel-agents` | 多个独立问题并行派 Agent |
| 协作 | `requesting-code-review` | 合并前派评审子 Agent，按严重度处理 |
| 协作 | `receiving-code-review` | 收到评审先核实再实现；禁止表演性同意 |
| 协作 | `using-git-worktrees` | 功能工作前确保隔离工作区 |
| 协作 | `finishing-a-development-branch` | 跑全量测试 → merge / PR / keep → 清理 |
| 测试 | `test-driven-development` | 没有失败测试就没有生产代码 |
| 调试 | `systematic-debugging` | 先找根因再修；四阶段流程 |
| 调试 | `verification-before-completion` | 声称完成前必须新鲜运行验证命令 |

## Livepowers vs Superpowers 逐项对比

| 维度 | Livepowers 1.2.0 | Superpowers 6.3.0 |
|---|---|---|
| 目标用户 | 做企业业务软件、数据分析、交易系统、现场交付的业务 Agent 及其运营者；技能正文中文 | 用 Claude Code / Codex / Cursor 等写代码的开发者；英文 |
| 技能数与分组 | 18 个：入口、本体 ×3、System 1 ×2、System 2、固化、验收、安全、接管、夜间 ×2、协作、交付、价值 ×2、元 | 14 个：入口、元、协作 ×9、测试、调试 ×2 |
| 入口机制 | SessionStart 钩子注入 `using-livepowers` 全文；三个斜杠命令 `/lp-route` `/lp-nightly` `/lp-morning` | SessionStart 钩子注入 `using-superpowers` 全文；无斜杠命令 |
| 运行时状态 | 有：`lp.py`（证据、注册表、看板、台账、资产、夜间产物、金丝雀、晨报）、`agent_switch.py`、`scan_sqlite.py`，数据落在项目 `.livepowers/` | 几乎没有；产物是 `docs/superpowers/plans/*.md` 和 specs |
| 业务本体 | 核心：扫描生成本体草稿与环境指纹、漂移检测；规格按变化层级分类；本体按候选 → 已校验 → 已确认 → 已发布演进；"不在本体之外操作"是铁律 | 无本体概念，语义停留在 spec / plan 文档 |
| System 1 / System 2 路由 | `lp registry find` 先查已固化能力（中文可不分词），命中直接执行，未命中才探索；定义去固化信号 | 无；每次任务都由 LLM 走完整流程 |
| 证据与固化 | `lp evidence add` 每轮记录；F-V-S-R 评分（V=0 一票否决）+ 盈亏平衡 `n* = (K+M)/(c2′−c1)` 决定是否固化；固化物是带测试、版本和元数据的能力包 | "证据"指验证命令的输出，不跨会话记录；技能由人工提炼，无候选 / 评分 / 注册表 |
| 验收门禁 | 四道门（形式检查 → 契约测试 → 独立对抗审查 → 人工采纳）；派工 / 执行 / 验证 / 采纳 / 运营五种职责分离；脚本强制：看板拒绝非法迁移与自验，`registry add` 要求生成者 ≠ 采纳人，写操作缺测试拒绝注册 | 两段子 Agent 评审 + 终审；brainstorming 的人类批准门；"新鲜证据"规则。约束靠提示词，无持久化校验 |
| 多 Agent 协作 | 按信任域选直连 / 交换机中转 / 旁路日志；`agent_switch.py` 哈希链防篡改、策略拦截、回放、审计 | harness 原生子 Agent；无消息审计 / 回放 |
| 夜间 / 长程任务 | `night-loop-planning`（DAG、按模型可稳定时长切段、交接契约、止损）+ `nightly-crystallization-review`（候选、复核、金丝雀、晨报）+ 早晨人工采纳 | 无夜间概念；SDD 可连续执行数小时，但无切段 / 交接 / 晨报 |
| 异常接管 | `takeover-handling`：止损后冻结、诊断包、归因、换人重开、接管成本入账 | 无（遇阻即停，交给人） |
| 交付方法 | `fde-delivery`：先白盒 → 再契约 → 后证据闭环；资产四道门与回流率；`digital-role-spec` 数字岗位 | `finishing-a-development-branch`：merge / PR / keep |
| 价值度量 | `outcome-ledger`：先登记基线；验收任务平均成本、首次价值交付时间、ΔV = B × u | 无 |
| 测试方式 | `unittest`：脚本行为、技能结构、三平台钩子输出、npm 安装器、示例流程；技能行为按压力情境人工做 | 按 harness 分目录的集成测试；技能行为用 drill eval 框架 |
| 安装 | `npx livepowers install`（Claude / Cursor / Codex / agents，个人或项目级，可卸载）；Claude Code 插件市场；Codex / Cursor 插件清单 | 官方插件市场；README 列出 15+ 个 harness 的安装方式 |
| 许可证 | MIT | MIT |

## 三种串联用法

**串法 A：固化流水线**
`nightly-crystallization-review` 挑出候选 → `crystallize-to-system1` 的 F-V-S-R / n* 判定通过 → 把能力包的实现交给 Superpowers：`brainstorming`（bounded）→ `writing-plans` → `subagent-driven-development` + `test-driven-development` 写确定性代码与评测 → `verification-before-completion` → 产物登记 `lp pending add` → 早晨 `/lp-morning` 走 `acceptance-gates` → `lp registry add --generated-by <agent> --accepted-by <人>`。

**串法 B：业务需求首响**
`system1-first`（`lp registry find`）MISS → `ontology-grounded-spec` 产出带不变量与验收样例的规格（作为 `writing-plans` 的输入）→ `explore-with-evidence` 设轮次 / 预算 → 探索中要改代码就用 `systematic-debugging` + `using-git-worktrees` → 每轮 `lp evidence add --system S2`。

**串法 C：验收与去固化闭环**
Superpowers 的 `requesting-code-review` 评审子 Agent 充当 `acceptance-gates` 第三道门"独立对抗审查"；`verification-before-completion` 的"新鲜命令输出"正对应 Livepowers 的"回执优先于声明"。运行期 `lp registry review --current-model` 发现连续失败或换模型 → 去固化 → `systematic-debugging` 修复 → `lp registry verify` 复验。

## 与其他同类产品

| 产品 | 定位 | 核心机制 | 与 Livepowers 最像的点 | Livepowers 独有 / 缺失 |
|---|---|---|---|---|
| **Agent Skills 标准 + anthropics/skills** | 开放的技能格式（SKILL.md + frontmatter + 资源）与官方示例库 | 格式与分发，不规定工作流 | Livepowers 完全遵循该格式，这是它能装进多个客户端的基础 | 独有：整套业务方法论与运行时。缺失：skill-creator 式的触发率自动评测 |
| **GitHub spec-kit** | 规格驱动开发工具包 | constitution → specify → plan → tasks → implement → converge；任务有稳定 ID | constitution ≈ 七条铁律 + 本体不变量；converge ≈ 验收门 | 独有：System 1 路由、证据台账、固化经济学、夜间循环。缺失：每特性一个目录的产物链与任务 ID |
| **BMAD-METHOD** | 角色化 Agile AI 开发框架（12+ 角色代理） | 分析 → 规划 → 方案 → 实现；顺序交接 / Party Mode | 多角色分工 ≈ `digital-role-spec` + 五种职责分离 | 独有：本体、固化、价值台账、可审计通信。缺失：完整的 PRD / 架构 / Story 模板体系 |
| **Agent OS（buildermethods）** | 把代码库的编码规范提取并注入编码 Agent | 声明式 standards + profiles，按需注入 | "从环境提取标准" ≈ `env-scan-ontology` | 独有：扫的是业务语义而非代码风格；有门禁。缺失：代码惯例的自动发现 |
| **claude-flow / Ruflo** | 企业级多 Agent 编排平台 | 向量记忆、从成功轨迹学习、信任评分、自动路由 | "从成功轨迹学习 + 路由" ≈ System 1 优先 + 固化 | 独有：固化物是可测试的确定性代码，有人工采纳门，显式算盈亏。缺失：向量检索、自动学习、信任评分量化 |
| **Palantir AIP / Ontology** | 商业企业平台，本体即语义层 + 动能层 | Action Types 走审批与审计；Agent 用本体工具 | Agent + Ontology 公式本身；原子行动 + 审计 ≈ `oltp-action-safety` | 独有：开源、零依赖、装进任意编码 Agent。缺失：真正的本体运行时（对象存储、权限传播、行动引擎） |
| **Devin Playbooks / Knowledge** | 可复用的多步流程 prompt 与组织知识 | Playbook 含后置条件与禁止动作；Knowledge 按触发词匹配 | Playbook ≈ 工具卡 + 剧本；Knowledge 自动建议 ≈ 固化候选 | 独有：固化物是代码而非 prompt，有评分、独立验收、台账。缺失：从会话自动生成 playbook 的产品化流程 |
| **Voyager 式自增长技能库**（continuous-learning、MUSE-Autoskill、Trace2Skill、SkillRL） | 自动从轨迹蒸馏技能并评估 | hook 观测 → 抽取模式 → 置信度评分 → 提升 | 最像"探索留证据 → 固化"；v1.3 起同样用 hook 自动采集证据并给能力算置信度 | 独有：显式经济学 n*、生成者 ≠ 采纳人、去固化信号、固化物是代码。缺失：从轨迹自动生成技能草稿（Livepowers 的夜间生成仍由 Agent 按技能执行） |
| **skills.sh / Cursor rules 生态** | 技能与规则的分发渠道 | `npx skills` 市场；`.cursor/rules/*.mdc` | `npx livepowers install` 与 `npx skills add` 对应这些渠道 | 支持 skills.sh 安装 18 个技能；为 Cursor 生成 `.mdc` 入口规则 |

## Livepowers 的差异化

1. **把"是否固化"做成显式经济学决策**：F-V-S-R 评分 + 盈亏平衡 n*，`lp score` 用退出码给结论。同类产品要么没有固化概念，要么自动学习但不算账。
2. **固化物是可测试的确定性代码（System 1），不是 prompt 或记忆**：能力包必须带实现与评测，写操作缺测试拒绝注册；反模式明确反对"把整段探索对话存成技能"。
3. **验收与职责分离由脚本强制**：看板状态机拒绝非法迁移与自验，注册要求生成者 ≠ 采纳人，夜间产物清单拒绝自我验收。
4. **业务本体是一等公民，且以开源形式与 Agent Skills 格式结合**：MIT、零依赖，带环境指纹与漂移检测。
5. **完整的运营闭环**：夜间固化 → 晨报 → 早晨人工采纳；异常接管有技能；可审计多 Agent 通信；结果台账先基线再承诺。

## 值得借鉴、已列入路线图

每项对应一个可领取的 Issue，见 [路线图总览](https://github.com/zhanglunet/livepowers/issues/10)。

- ~~hook 自动采集证据，给能力加随成功 / 失败升降的置信度（借 continuous-learning v2）。~~ v1.3.0 已做。
- 技能触发率自动评测，替代纯手工压力情境（借 Anthropic skill-creator / superpowers-evals）。
- ~~意图同义词表~~ v1.4.0 已做（确定性、可审计的别名表；不引入向量检索，保持零依赖）。语义检索仍在路线图。
- 规格产物链与稳定任务 ID，让夜间 DAG 直接引用（借 spec-kit）。
- 工具卡补后置条件与禁止动作字段（借 Devin Playbook）。
- ~~上架 skills.sh；为 Cursor 生成 `.mdc` 入口规则。~~ 已支持。

## 来源

- https://github.com/obra/superpowers
- https://github.com/anthropics/skills · https://agentskills.io
- https://github.com/github/spec-kit
- https://github.com/bmad-code-org/BMAD-METHOD
- https://buildermethods.com/agent-os/concepts
- https://github.com/ruvnet/claude-flow
- https://palantir.com/docs/foundry/ontology/overview · https://www.palantir.com/docs/foundry/agent-studio/overview
- https://docs.devin.ai/product-guides/creating-playbooks
- https://skills.sh/oldwinter/skills/continuous-learning · https://arxiv.org/html/2603.25158v1 · https://arxiv.org/pdf/2602.20867 · https://github.com/aiming-lab/SkillRL
- https://vercel.com/docs/agent-resources/skills · https://github.com/ikhare/awesome-cursorrules
