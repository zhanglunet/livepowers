# Changelog

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## [1.4.0] - 2026-10-07

### 新增

- **意图同义词表** `lp intents alias / list / suggest`：`.livepowers/intents.json` 存规范意图与别名。
  - `evidence add`、`task new`、`pending add` 与钩子自动采集：别名落盘为规范名，原话保留在 `intent_raw`。
  - `evidence stats`、`candidates`、晨报：读取时按规范名归并，历史记录无需改写。
  - `registry find`：查询命中任何同义词时按整组同义词打分，别名也能 HIT。
  - `suggest` 用英文词集 Jaccard / 中文二元组重叠找相似意图对，只建议不自动合并。
- `nightly-crystallization-review` 的"合并同义意图"、`system1-first` 与 `explore-with-evidence` 的意图命名改为使用这些命令。

## [1.3.0] - 2026-10-07

### 新增

- **钩子自动采集证据**（Claude Code 插件）：`hooks/evidence-capture.sh` 注册为 `PostToolUse`（Bash）与 `Stop` 钩子，调用 `lp hook post-tool | stop`。
  - `lp registry find` 命中后，每次调用该能力 entry 的命令自动记一条 S1 证据（exit 非 0 或有 stderr 记 fail），能力的 `calls / fails` 随之更新。
  - 未命中且本轮结束前没有 `lp evidence add`，补记一条 S2 证据：`outcome partial`、`auto: true`，token 从 transcript 累加。
  - 显式记录优先；未 `lp init` 的项目不写任何文件；任何异常都不外溢（记到 `.livepowers/hook-errors.log`）；`LP_HOOK_CAPTURE=0` 关闭。
- 能力置信度 =（成功 + 1）/（调用 + 2）：`registry find / list` 显示；`registry review` 对 ≥3 次调用且置信度 < 0.6 的能力提复核。
- `evidence stats` 统计自动采集与待确认数；晨报新增"自动采集待确认"段；`nightly-crystallization-review` 第一步先清这些记录。

## [1.2.0] - 2026-10-07

独立评审（只读仓库、实跑 60 多条命令；并调研 Superpowers 与 9 个同类产品）之后的修正与补强。决策记录见 [docs/devlog.md](docs/devlog.md)。

### 修复

- 任务看板：`takeover` 不能再直接迁到 `running`（必须经 待验证 → 已注册）；`closed` 为终态；接管后重开须显式 `task move <id> explore --reset-loops` 或 `--extend-budget <金额> [--max-loops N]`，否则止损条件仍成立。
- 结果台账：`outcome baseline --direction lower|higher`，越低越好的指标（逾期数、时长）不再算出负的增量价值；`outcome cost` 须已有基线。
- 注册表：`registry add --supersedes <旧id>` 发新版本并自动退役旧版、记录 `superseded_by`；修正 `crystallize-to-system1` 与脚本矛盾的"旧版本保留"说法。
- 17 个技能的 `description` 改为只写触发条件；`test_frontmatter` 现在会拒绝破折号接流程摘要、流程动词和超过 400 字符的描述。
- `using-livepowers` 的工作循环与 `system1-first` 一致（先 `registry find`，MISS 且功能级以上才建任务；证据每轮一条）；`templates/action.yaml` 的测试项与八项检查一一对应；`acceptance-gates` 门 1 不再把 `lp job validate` 当通用形式检查；文档写出 F-V-S-R 合成公式。
- 网站 Codex / Cursor 安装改用 npm 安装器，不再 `cat AGENTS.md >>`。

### 新增

- 技能 `takeover-handling`（18 个技能）：止损后冻结并交付诊断包、七类主因只选一个、换人重开 / 重定规格 / 关闭、接管成本入账；进入路由表与晨报待办。
- `lp pending add / list / done`：夜间固化产物清单（意图、评分、n*、测试命令与结果、位置、生成者）；晨报自动汇总；`done` 拒绝生成者给自己验收。
- `lp canary record / compare / list`：金丝雀评测记录与比较（通过率下降 >10% 或 token 上升 >30% 算回归，exit 5）；晨报含金丝雀段。
- `lp --help` 为所有子命令与参数提供说明。
- `using-livepowers`：三种安装方式下 `lp` 与模板位置的对照表、项目目录约定表、冷启动说明；npm 安装器把 `templates/` 装到 `using-livepowers/templates/`。
- 文档：`docs/scenarios.md`（12 个场景与五分钟 demo）、`docs/comparison.md`（与 Superpowers 逐项对比、三种串联用法、9 个同类产品）、`docs/devlog.md`（开发日志）；Issue 模板新增"使用反馈 / 问题"；开启 Discussions。
- 网站：首屏放安装命令与"两种死"；新增场景、demo（真实输出）、对比、FAQ、开发日志、反馈入口板块与页内导航。

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
