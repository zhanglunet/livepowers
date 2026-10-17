# PRD-051/T1：livepowers 定位语候选 + 竞品对标

> 对应 trend issue #236。T1 只出候选，不改 README（T2 才改）。需用户拍板选定一条后，T2 才开工。

## 一、定位语候选（5 条）

### 候选 1：借 Superpowers（主推）

> **业务智能体版 Superpowers：19 个强制工作流技能，决定"做什么、要不要固化、算不算完成"。**

- **讲清了什么**：是什么（19 个强制工作流技能）、给谁用（业务智能体，区别于 Superpowers 的 coding agents）、跟什么对标（Superpowers）。
- **适用场景**：懂 Superpowers 的技术用户。README 已写明"结构借鉴 obra/superpowers，两者可以同时安装"，这句定位语与现有文档口径一致，零解释成本。
- **套路**：学 VoiceStudio 借 ElevenLabs——借已有认知度的竞品名声，一句话讲清自己和差异。

### 候选 2：品类定义

> **一套让业务智能体按"活产品"范式工作的开源技能包：能复用的先复用，缺口才探索，用得越多越熟练。**

- **讲清了什么**：是什么（开源技能包）、方法论（活产品范式）、核心价值（复用优先、用得越多越熟练）。
- **适用场景**：不了解 Superpowers 的用户，直接讲品类和价值，不依赖外部认知。
- **弱点**："活产品范式"是自创词，第一次听需要 3 秒消化；不如候选 1 借力打力。

### 候选 3：痛点/省钱

> **别为已解决的问题付 GPU 的钱：把成功路径固化成经过测试的确定性能力。**

- **讲清了什么**：痛点（GPU 账单）、解法（固化成功路径）、信任状（经过测试）。
- **适用场景**：强调经济价值，呼应 System 1（便宜确定）vs System 2（昂贵概率）的核心设计。适合在"token 经济学"语境下传播（如 caveman 那类讨论）。
- **弱点**：没讲清"给谁用"，偏口号，信息密度不如候选 1。

### 候选 4：极简版（学 text-to-cad）

> **Give your business agent a live-product mindset.**

- **讲清了什么**：极简，一句话 + 一个品类词（live-product）。
- **适用场景**：英文传播、海报、徽章。套路直接抄 text-to-cad 的 "Give your agent CAD superpowers"。
- **弱点**：中文用户需要翻译；"mindset"偏虚，不如"19 个技能"实在。

### 候选 5：技术完整版

> **Agentic AI = Agent + Ontology + Harness：19 个技能让智能体在业务本体里行动、复用固化能力、独立验收。**

- **讲清了什么**：公式（三块地基）、数量（19 技能）、闭环（行动→复用→验收）。
- **适用场景**：技术深度用户，README 现有英文 summary 就是这个口径。
- **弱点**：偏长，5 秒测试可能读不完；Ontology/Harness 是术语，新用户要查。

## 二、竞品/品类对标表

| 项目 | 定位语（原文） | 套路分析 | 可借鉴点 |
|---|---|---|---|
| [debpalash/VoiceStudio](https://github.com/debpalash/VoiceStudio) | "open-source, fully-local ElevenLabs alternative" | **借竞品**：直接点名 ElevenLabs（竞品名声）+ 两个差异化定语（open-source, fully-local） | 借已有认知度的名字，一句话讲清"我是谁、跟谁像、哪里不一样" |
| [earthtojake/text-to-cad](https://github.com/earthtojake/text-to-cad) | "Give your agent CAD superpowers." | **极简动词短语**：Give your agent X + 品类词（superpowers）；首屏 logo + 这一句，无多余解释 | 定位语越短越好记；品类词（superpowers）本身就是传播 |
| [obra/superpowers](https://github.com/obra/superpowers) | "a complete software development methodology for your coding agents, built on top of a set of composable skills" | **品类定义**："complete X methodology"（完整方法论）+ 受众（your coding agents）+ 实现方式（composable skills） | 用"methodology"抬升品类（不只是工具，是方法论）；受众限定词（coding agents）划清边界 |
| [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) | "A curated directory of high-quality plugins for Claude Code." | **精选目录**：curated（精选）+ high-quality（质量背书）+ 受众（for Claude Code） | 官方/精选类项目用"curated"建立信任；livepowers 是技能包而非目录，此套路不适用 |

**共性结论**：好定位语 = 受众限定词 + 品类/竞品锚点 + 一句差异化。VoiceStudio 和 text-to-cad 证明"短"本身就是竞争力。

## 三、推荐首选

**主推候选 1**（业务智能体版 Superpowers），理由：

1. **借力最大**：Superpowers 在 agent 圈已有认知度，VoiceStudio 借 ElevenLabs 的打法已被验证有效。
2. **与现有文档一致**：README 已写"结构借鉴 obra/superpowers，两者可以同时安装：Livepowers 决定'做什么、要不要固化、算不算完成'，Superpowers 负责'固化代码怎么写好'"——定位语是这句话的压缩版，不用改口径。
3. **差异化清晰**：Superpowers = coding agents 的 software development methodology；livepowers = business agents 的"做什么/固化/验收"。一句话划清边界，避免被当成"又一个 superpowers 翻版"。
4. **备选**：如果用户觉得"版"字有山寨感，可退到候选 2（品类定义），信息完整但需要多解释 3 秒。

## 四、下一步（T2 前置）

- 用户拍板选定一条（或给修改意见）→ T2 按选定语重写 README 首屏（≤5 行：定位语 + 一句话补充 + GIF 位）。
- 本 PR 只含本文档，不改 README，不动插件代码。
