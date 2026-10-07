# Changelog

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## [1.1.0] - 2026-10-07

### 新增

- 发布 npm 包 `livepowers`（零依赖，Node 18+）：
  - `npx livepowers install`：把技能装进 Claude Code（`.claude/skills`）、Cursor（`.cursor/skills`）、Codex 及其他 Agent Skills 客户端（`.agents/skills`）；支持个人或项目级（`--project`）、`--force`、`--dry-run`；写入安装清单，`uninstall` 只删除自己装的技能。
  - `--target codex|agents --project` 会把入口说明合并进项目的 `AGENTS.md`（带标记，重复安装只替换、卸载时移除）。
  - `livepowers list` / `livepowers path`。
  - `lp` 命令：全局安装后直接可用，转发到自带的 `scripts/lp.py`（需要 Python 3.9+）。
- 官网 <https://livepowers.pages.dev>，安装说明新增 npm 方式。

### 改进

- 测试读文件、请求 HTTP 时及时关闭句柄，不再刷屏 `ResourceWarning`；`agent_switch.py` 读日志同样处理。
- 新增 `tests/test_npm.py`；版本一致性检查纳入 `package.json`；CI 安装 Node。

## [1.0.0] - 2026-10-07

首个公开发布版本，在 0.9 试用版的基础上迭代。

### 新增技能

- `acceptance-gates`：四道质量门禁（形式检查 → 契约测试 → 独立对抗审查 → 人工采纳）；用回执代替声明；五种职责分离（派工、执行、验证、采纳、运营）；门禁力度与风险成正比；一周迭代节奏。
- `ontology-evolution`：本体按 候选 → 已校验 → 已确认 → 已发布 演进；分参考本体与本体孪生两层；按变化率决定知识放在哪里；大小调整走两条通道；规则频繁更新时的版本、生效时间与双向互证。
- `outcome-ledger`：价值闸门（可量化、可归因、可复现、可经营）；先登记基线；验收任务平均成本、首次价值交付时间、跨客户复用率、增量价值 ΔV = B × u。
- `digital-role-spec`：数字岗位规格（角色、职责、智能体团队、本体范围、技能、工具、权限、KPI、升级路径、人在回路）与岗位经济账。
- `writing-livepowers-skills`：用 RED → GREEN → REFACTOR 编写技能；描述只写触发条件。

### 增强的技能

- `using-livepowers`：铁律从六条增加到七条（加入"没有基线的价值不算价值"）；新增三层架构落点（本体 / 工具 / 技能）；反模式表加入"自我声明"与"把假设当指令"；路由表覆盖全部 17 个技能。
- `env-scan-ontology`：区分存量改造与新建两种起点；加入环境指纹与漂移比对；资产归属标注；孪生须记录数据时效。
- `ontology-grounded-spec`：变化分层改为 界面 / 参数 / 功能 / 本体 / 会话 五层；加入防迎合规则（不确定的说法记为假设）；加入业务不变量与保留测试集。
- `explore-with-evidence`：探索前设定轮次与预算，超限自动止损；产物要能被他人接手。
- `crystallize-to-system1`：新增能力包（本体版本、规格、实现、Skill、界面、评测、依赖、维护主体绑定在一起）；在产品内发布，不必整版升级；注册时记录生成者与采纳人。
- `agent-harness-for-tools`：换模型时重跑基准；模型升级后做消融，不再需要的约束就去掉（去 Harness 化）；加入金丝雀样例。
- `oltp-action-safety`：先仿真后执行的高风险闭环；审批后重新校验；超时先查状态；存量系统缺少事务时的适配边界。
- `night-loop-planning`：按模型可稳定时长切段；交接契约写实际终态并指定独立检查者；单任务熔断；"轻量、高频、多出小结果"。
- `nightly-crystallization-review`：能力复核（连续失败、闲置、久未复验、模型变化）；金丝雀评测。
- `auditable-agent-comms`：消息信封增加共享任务标识、契约版本和内容引用；新增 receipt 类型；加入审计要点。
- `fde-delivery`：落地三步（先白盒、再契约、后证据闭环）；双轨选点；资产四道门与回流率；客户所有的资产不入库；双指标考核。

### 脚本

- `lp.py`
  - 新增 `task`：任务看板状态机，会拒绝非法迁移，迁移必须写明理由，超出轮次或预算自动止损，生成者不能自验。
  - 新增 `outcome`：结果台账。
  - 新增 `asset`：资产四道门与回流率。
  - 新增 `registry verify / review`：能力复验与复核。
  - `evidence add` 增加 `--task`、`--model` 参数，并自动累计能力调用次数。
  - `registry add` 增加能力包、验证模型、生成者与采纳人字段；写操作能力缺测试时拒绝注册。
  - `job validate` 检查单段时长和交接契约。
  - `score` 用退出码表示结论；晨报加入复核、看板与台账。
- `agent_switch.py`：新增 `audit` 子命令；消息带任务标识、契约版本与引用；超长消息体会被拒绝；新增 `receipt` 消息类型。
- `scan_sqlite.py`：以只读方式打开数据库；对状态字段的取值抽样；跳过敏感字段；新增 `--fingerprint` 与 `--diff` 做漂移检测。
- 新增 `package-skills.sh`。

### 仓库

- 仓库结构参照 obra/superpowers：带 Claude Code、Codex、Cursor 三种插件清单；钩子按平台输出不同字段；新增 `commands/`、`examples/`、`tests/`、CI 和 issue 模板。
- 新增自动化测试，覆盖评分与盈亏平衡、路由、看板规则、止损、台账、资产门、作业契约、扫描与漂移、交换机的中转 / 拒绝 / 回放 / 篡改 / 审计、技能结构、钩子输出和示例。
- 全面脱敏：去除所有具体组织、人员、客户、项目与会议信息，示例一律使用虚构的通用业务场景。
- 采用 MIT 许可。

## [0.9.0] - 试用版

12 个技能、3 个脚本、5 个模板；SessionStart 自动注入。
