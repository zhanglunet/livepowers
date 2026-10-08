# Livepowers · 活产品范式技能包

[![test](https://github.com/zhanglunet/livepowers/actions/workflows/test.yml/badge.svg)](https://github.com/zhanglunet/livepowers/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![npm](https://img.shields.io/npm/v/livepowers)](https://www.npmjs.com/package/livepowers)
[![网站](https://img.shields.io/badge/网站-livepowers.pages.dev-f38020)](https://livepowers.pages.dev)

**官网：<https://livepowers.pages.dev>**（介绍与安装）

**Livepowers 是一套给智能体用的工作方法。**它让业务智能体按「活产品（Live Product）」范式工作：在本体划定的业务世界里行动；能复用的直接复用；不能复用的先探索，并留下证据；把成功路径固化成经过测试的能力；所有成果都要过独立验收。用得越多，产品越熟练。

> **Agentic AI = Agent + Ontology + Harness**
>
> Agent 提供开放能力，Ontology 定义业务语义，Harness 规范工程约束。
> 高频固化（System 1：代码 / CLI / SQL，跑在 CPU 上，便宜、确定），低频探索（System 2：Agent + 大模型，跑在 GPU 上，昂贵、概率性）。
> 探索留证据，成功路径固化，失效就去固化。白天探索，夜间固化，早晨验收。

*English summary: Livepowers is a skills library that turns coding/business agents into "live products": work inside an ontology, reuse crystallized deterministic capabilities first (System 1), explore with LLM reasoning only for gaps (System 2) while recording evidence, crystallize proven paths into tested capability packages, and accept everything through independent gates. Skill bodies are in Chinese; descriptions are bilingual.*

结构借鉴 [obra/superpowers](https://github.com/obra/superpowers)：技能是强制工作流，会话启动时自动注入入口技能。两者可以同时安装：Livepowers 决定"做什么、要不要固化、算不算完成"，Superpowers 负责"固化代码怎么写好"。

## 全景：它是怎么运转的

![Livepowers 全景：一个请求的旅程、三块地基、一天的节律与四道护栏](https://livepowers.pages.dev/panorama.svg)

- **一个请求的旅程**：先翻工具箱（已固化的能力），找到了就直接用、几乎不花钱；没找到才让探索者（Agent + 大模型）去想办法——先说清要什么，只在业务地图范围内摸索，做完过质检。每一步留工作日志；走不通就到预算止损、换人接手。
- **三块地基**：业务地图（本体）回答"业务里有什么、怎么算、谁能做"；工具箱装反复成功后做成"按钮"的能力，每个带测试和责任人；操作手册是 18 个技能，会话一开始就自动翻开。
- **一天的节律**：白天用和探索，夜里翻日志把反复成功的做法做成新工具（先算值不值），早晨人来验收，通过的放进工具箱——明天的请求更多走"找到了"。四道护栏贯穿全程：质检、写操作安全、账本、现场交付的资产回流。

在线版（可缩放）见[官网全景板块](https://livepowers.pages.dev/#pano)。

## 工作方式

```
业务请求
  └─ system1-first：lp registry find
        ├─ HIT  → 执行已固化能力（几乎零 Token）→ 记证据
        └─ MISS → ontology-grounded-spec → explore-with-evidence（有轮次与预算上限）
                  → acceptance-gates → 交付 → 记证据
夜间：nightly-crystallization-review → crystallize-to-system1（草稿 + 测试，不注册）
早晨：人工采纳 → lp registry add（生成者 ≠ 采纳人）
运行：连续失败 / 口径变化 / 环境漂移 / 换模型 → 复核或去固化
```

健康的活产品，System 2 调用占比随时间下降，能力库随时间增长，而面对新问题仍保有探索能力。

## 技能（18 个）

| 分组 | 技能 | 作用 |
|---|---|---|
| 入口 | `using-livepowers` | 七条铁律、路由表、工作循环（会话启动时自动注入） |
| 本体 | `env-scan-ontology` | 存量改造 / 新建两种起步；只读扫描 → 环境指纹 → 本体草稿 → 漂移检测 |
| 本体 | `ontology-grounded-spec` | 一次只问一个问题；判断变化落在哪一层；防迎合；带不变量与验收样例的规格 |
| 本体 | `ontology-evolution` | 候选 → 已校验 → 已确认 → 已发布；来源、适用范围、生效时间、历史重算 |
| System 1 | `system1-first` | 先查注册表，命中即执行；去固化信号 |
| System 2 | `explore-with-evidence` | 探索边界、预算与止损、样例核对、可接手的产物、证据 |
| 活软件 · NEW | `living-surface` | 三类需求并存：固定页 / 次抛展示 / 从次抛长出新的固化结构；展示面只传数据与组件描述，只读查询，孪生对账，生产回执后才注册（`lp surface`、`lp pages`） |
| 固化 | `crystallize-to-system1` | F-V-S-R 门禁与盈亏平衡 → TDD → 确定性实现 → 能力包 → 注册（Coding Harness） |
| System 1 | `agent-harness-for-tools` | 工具卡、带决策点的剧本、硬约束；换模型重跑基准、去 Harness 化（Agent Harness） |
| 验收 | `acceptance-gates` | 四道门：形式检查、契约测试、独立对抗审查、人工采纳；回执优先于声明；五种职责分离 |
| 安全 | `oltp-action-safety` | 先仿真后执行；八项检查与对应测试；存量系统的适配边界 |
| 夜间 | `night-loop-planning` | 强规划弱执行、按模型可稳定时长切段、交接写实际终态、DAG、止损、作业契约 |
| 夜间 | `nightly-crystallization-review` | S2 占比趋势、固化候选、能力复核、金丝雀评测（`lp canary`）、夜间产物清单（`lp pending`）、晨报 |
| 接管 · NEW | `takeover-handling` | 止损后冻结并交付诊断包；归因七类主因只选一个；换人重开（`--reset-loops` / `--extend-budget`）、重定规格或关闭；接管成本入账 |
| 协作 | `auditable-agent-comms` | 信任域分级、协调线 / 内容线、共享任务标识、哈希链、回放与审计 |
| 交付 | `fde-delivery` | 五类底座资产、先白盒再契约后证据闭环、双轨选点、资产四道门与回流率 |
| 价值 | `outcome-ledger` | 先登记基线；验收任务平均成本、首次价值交付时间、增量价值 ΔV = B × u |
| 价值 | `digital-role-spec` | 数字岗位规格：任务归属（auto / agent / handoff / human）、人在回路、岗位经济账 |
| 元 | `writing-livepowers-skills` | 先看 Agent 失败再写技能；描述只写触发条件；结构测试 |

## 脚本（纯 Python 3.9+ 标准库，零依赖）

| 脚本 | 能做什么 |
|---|---|
| `scripts/lp.py` | 证据记录（含钩子自动采集）、意图同义词表（别名归并、按整组同义词路由、相似意图建议）、能力注册表与 System 1 路由（支持中文无空格匹配、置信度）、F-V-S-R 评分与盈亏平衡 n*、固化候选、**任务看板状态机**（非法迁移、止损、接管重开、生成者不能自验）、**结果台账**、**资产四道门与回流率**、夜间产物清单、金丝雀评测、作业契约校验、**能力复核**、晨报、**活软件展示面**（`lp surface`：校验、次抛记录、申请固化、对账、带回滚的部署回执、转 A2UI 消息；`lp pages list` 固定页目录） |
| `scripts/agent_switch.py` | 智能体交换机：HTTP 中转 / 旁路记录、策略拦截（未知类型、超长消息、拦截词）、哈希链防篡改、回放、审计 |
| `examples/living_app/` | 活软件参考宿主（零依赖）：对话式页面，智能体回答以 A2UI v0.9.1 展示面嵌在对话里；固定页目录、申请固化、模拟生长；`python3 examples/living_app/server.py` |
| `scripts/scan_sqlite.py` | 环境扫描示例：本体草稿、状态取值抽样、敏感字段跳过、环境指纹、漂移比对 |
| `scripts/package-skills.sh` | 把每个技能打成单独 zip，便于在网页端上传 |
| `bin/livepowers.js` · `bin/lp.js` | npm 包的命令：`livepowers install / uninstall / list / path` 安装器，`lp` 转发到 `scripts/lp.py` |

数据全部落在项目的 `.livepowers/` 下，建议纳入 git。

## 安装

**npm（一键安装，推荐）**

```bash
npx livepowers install                            # 装到 ~/.claude/skills（默认 --target claude）
npx livepowers install --target cursor            # 或 codex / agents
npx livepowers install --target codex --project   # 装到当前项目，并合并 AGENTS.md 入口说明
npm i -g livepowers                               # 全局安装后可直接用 lp 命令（需要 Python 3.9+）
```

`livepowers list` 查看已安装位置，`livepowers uninstall`（参数同 install）只删除自己装的技能。同名技能已存在时默认跳过，加 `--force` 覆盖；加 `--dry-run` 只预览。

**Claude Code（插件）**

```text
/plugin marketplace add zhanglunet/livepowers
/plugin install livepowers@livepowers-marketplace
```

插件自带 `SessionStart` 钩子，自动注入 `using-livepowers`；`PostToolUse` / `Stop` 钩子自动采集证据（命中能力后的每次调用记 S1；探索后忘了记的补一条 `partial` 的 S2，晨报列为待确认；`LP_HOOK_CAPTURE=0` 关闭）；另带三个命令：`/lp-route`、`/lp-nightly`、`/lp-morning`。

**Claude Code（仅技能）**：把 `skills/*` 复制到 `~/.claude/skills/`（个人）或项目的 `.claude/skills/`（团队）。

**Codex**：仓库带 `.codex-plugin/plugin.json`，可作为插件安装；或把 `skills/*` 复制到 `~/.agents/skills/`。Codex 插件不带会话启动钩子，请把本仓库 `AGENTS.md` 的内容合并进项目根目录的 `AGENTS.md`，让 Agent 在开始时读取 `using-livepowers`。无钩子环境下可通过 `lp hook watch --transcript <path>` 轮询自动采集证据，或在回合结束时显式运行 `lp evidence add`。

**Cursor**：仓库带 `.cursor-plugin/plugin.json` 与 `hooks/hooks-cursor.json`（支持 `sessionStart` 初始化、`afterCommand` 命令后自动采集与 `sessionEnd` 兜底补记）。

**其他支持 Agent Skills 标准的客户端**：把 `skills/*` 放进客户端的技能目录。

**网页端**：运行 `scripts/package-skills.sh`，在设置的技能页逐个上传 `dist/skills/*.zip`（也可以直接从 Releases 下载）。

## 五分钟体验

```bash
git clone https://github.com/zhanglunet/livepowers && cd livepowers
bash examples/walkthrough.sh
```

示例用一个虚构的商机数据库，完整走一遍：环境扫描 → 路由未命中 → 三轮探索留证据 → 评分 → 任务看板 → 独立验收 → 注册 → 路由命中 → 结果台账 → 环境漂移 → 晨报。

常用命令：

```bash
npm i -g livepowers   # 或在仓库里：lp() { python /path/to/livepowers/scripts/lp.py "$@"; }
lp init
lp registry find "各地区的周收入"                   # HIT → exit 0；MISS → exit 2
lp evidence add --intent "weekly revenue by region" --system S2 --outcome success --cost 0.9 --verifiable
lp score --freq 20 --verifiable 2 --stability 2 --c2 0.9 --c1 0.001 --K 30 --M 10 --p 0.8 --h 5
lp task new --title "逾期商机移交" --max-loops 5 --budget 20
lp outcome baseline --scenario stale-opps --metric "逾期商机数" --value 40 --target 10
lp registry review --current-model <当前模型>
lp report
```

## 固化门禁：F-V-S-R 与盈亏平衡

| 维度 | 含义 | 取值 |
|---|---|---|
| **F** 频率 | 每月预计调用次数 | <4 → 0；4–19 → 1；≥20 → 2 |
| **V** 可验证 | 结果能否被样例 / 断言自动核对 | 0 / 1 / 2；**V=0 一票否决** |
| **S** 稳定 | 口径、输入结构、接口是否稳定 | 0 / 1 / 2 |
| **R** 风险 | 是否写生产状态 | 写操作收益最大，但须过八项检查 |

合成分 = F×2 + V×1.5 + S + R（满分 10，≥5 且预计调用次数 > n* 才建议固化）。

```
n* = (K + M) / (c2′ − c1)        c2′ = c2 / p + (1 − p) · h / p
```

K 是固化成本，M 是维护成本，c1 和 c2 是单次执行成本，p 是 System 2 的成功率，h 是失败后的人工兜底成本。**成功率越低，固化越划算。夜间空闲算力能摊薄 K。口径常变会抬高 M。**

## 建议的落地顺序

1. **先白盒**：选一个有代表性的分析场景，只启用 `using-livepowers`、`system1-first`、`explore-with-evidence`、`outcome-ledger`，先记基线、记证据，建立统一的意图命名。
2. **再契约**：把关键口径写进本体与规格，开启 `acceptance-gates` 与 `nightly-crystallization-review`，每天早晨人工验收，观察 System 2 占比曲线。
3. **后证据闭环**：扩到写操作场景（`oltp-action-safety`、`agent-harness-for-tools`），长程任务接入 `night-loop-planning`，多 Agent 协作接入 `auditable-agent-comms`；交付统一走 `fde-delivery`，把资产回流率纳入评价。

## 文档

- [官网 livepowers.pages.dev](https://livepowers.pages.dev)：图文说明页（含场景、demo、对比、FAQ、开发日志）
- [docs/paradigm.md](docs/paradigm.md)：范式要点（一页纸）
- [docs/scenarios.md](docs/scenarios.md)：12 个场景与应用案例，每个带命令与产出
- [docs/comparison.md](docs/comparison.md)：与 Superpowers 逐项对比、三种串联用法、9 个同类产品
- [docs/devlog.md](docs/devlog.md)：开发日志（做了什么、为什么、放弃了什么）
- [docs/testing.md](docs/testing.md)：如何测试脚本与技能
- [CHANGELOG.md](CHANGELOG.md)：版本记录

## 反馈与参与

这个项目靠使用反馈迭代。用了之后哪里别扭、不清楚、Agent 绕过了规则、想要什么场景，都欢迎提 Issue：

- [使用反馈 / 问题](https://github.com/zhanglunet/livepowers/issues/new?template=feedback.md)：哪里不清楚、期望什么
- [问题报告](https://github.com/zhanglunet/livepowers/issues/new?template=bug_report.md)：技能没触发、脚本出错、规则被绕过
- [技能提议](https://github.com/zhanglunet/livepowers/issues/new?template=skill_proposal.md)：先写下没有这个技能时 Agent 怎么失败
- [Discussions](https://github.com/zhanglunet/livepowers/discussions)：场景交流、落地经验
- [路线图](https://github.com/zhanglunet/livepowers/issues?q=is%3Aissue+is%3Aopen+label%3Aroadmap)：每项都是可独立领取的小项目，从[总览](https://github.com/zhanglunet/livepowers/issues/10)开始

提 PR 前请先读 `skills/writing-livepowers-skills/SKILL.md`，并运行：

```bash
python -m unittest discover -s tests -v
```

## 致谢

仓库结构与"技能即强制工作流"的设计借鉴自 [obra/superpowers](https://github.com/obra/superpowers)（MIT）。

## 许可

[MIT](LICENSE)
