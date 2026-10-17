# PRD-003/T4：官方插件市场收录材料准备

> 状态：材料准备完成，**未做任何提交动作**。提交目标仓库与流程待用户拍板后执行。
> 前置：PRD-003 T1（marketplace.json 对齐官方格式）+ T2（5 插件拆分）+ T3（安装链路验证）均已合并。

## 1. 五个插件的英文一句话描述（提交用）

按各插件实际 skill 内容编写，面向官方市场审核者：

| 插件 | 英文描述 | 建议分类 |
|---|---|---|
| livepowers-core | Core agent workflow for business tasks: check the capability registry first (System 1), explore with evidence, and crystallize proven paths into tested, reusable capabilities. Ships the using-livepowers router, session/evidence hooks, and the lp CLI. | productivity |
| livepowers-ontology | Ontology tooling for agents: scan environments into structured ontologies, evolve them via deltas, and define digital roles and living surfaces for business operations. | development |
| livepowers-delivery | Delivery and safety guardrails for agents: independent acceptance gates, field-delivery workflow, outcome ledger, action-safety rules, auditable agent communications, and takeover handling. | deployment |
| livepowers-night | Night loops for agents: plan overnight work, crystallize results in a morning review, and track pending items — built for unattended compute windows. | automation |
| livepowers-tooling | Tooling for building on livepowers: the agent harness for wrapping tools as capabilities, plus the guide to writing livepowers skills. | development |

分类依据 `anthropics/claude-plugins-official` 的 category 体系（development / productivity / deployment / automation 等），与 `marketplace.json` 中已填的 `category` 字段一致。

## 2. 提交材料清单

- **仓库地址**：https://github.com/zhanglunet/livepowers（公开仓库）
- **marketplace.json**：`.claude-plugin/marketplace.json`（含 `$schema: https://anthropic.com/claude-code/marketplace.schema.json`，与官方格式对齐）
- **各插件 plugin.json**：`plugins/<name>/.claude-plugin/plugin.json`（name / version / description / author / license / keywords）
- **各插件主页链接**：
  - https://github.com/zhanglunet/livepowers/tree/main/plugins/livepowers-core
  - https://github.com/zhanglunet/livepowers/tree/main/plugins/livepowers-ontology
  - https://github.com/zhanglunet/livepowers/tree/main/plugins/livepowers-delivery
  - https://github.com/zhanglunet/livepowers/tree/main/plugins/livepowers-night
  - https://github.com/zhanglunet/livepowers/tree/main/plugins/livepowers-tooling
- **许可证声明**：MIT。仓库根 `LICENSE` + 每个插件目录内附带 `LICENSE` 拷贝；`marketplace.json` 与各 `plugin.json` 均声明 `license: MIT`。
- **版本口径**：5 个插件版本号跟随仓库主版本（当前 1.5.0）。
- **安装方式**（供审核者验证）：
  ```text
  /plugin marketplace add zhanglunet/livepowers
  /plugin install livepowers-core@livepowers-marketplace
  ```
  安装链路已有 CI 可重复的静态验证（`tests/test_marketplace_install.py`，PRD-003/T3）。

## 3. 待办（本次不做）

- [ ] **TODO：截图 / demo 链接**——需真机录制（Claude Code 客户端内 `marketplace add` → `install` → skill 触发全过程），本次未做。
- [ ] **TODO：提交 PR 的目标仓库与流程**——按官方惯例，向 `anthropics/claude-plugins-official` 提 PR（在其 `marketplace.json` 中追加条目）；**待用户拍板后执行，本次绝不提交**。
- [ ] 提交前复核：5 个英文描述与当时 `main` 分支的 skill 内容一致（若 skill 有新增/改名，同步更新）。

## 4. 合规说明

- 借鉴对象 `anthropics/claude-plugins-official` 为 Apache-2.0，本仓库仅复用其**文件格式约定**（字段名与目录布局），未复制其代码与文本，不存在许可证冲突。
- 本仓库全部内容为原创（MIT），无第三方代码混入插件目录。
