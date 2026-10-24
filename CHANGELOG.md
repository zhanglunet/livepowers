# Changelog

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增

- **瘦身门 T5 验收演示与案例留档**（PRD-148/T5，trend #744）：`docs/slim-gate/demo-2026-10-23.md`（虚构新 skill 在测试夹具完整走门：未登记不拦 → 三处登记无记录 CI 拒 exit 1 → 补决策记录过 exit 0，含 merged 变体与度量快照）+ `docs/slim-gate/records/2026-10-23-slim-gate-demo-skill.md`（「拒绝 → 补记录 → 通过」示范决策记录，虚构 skill、构造证据、provisional）；`tests/test_slim_gate_t5.py` 机检复现三阶段并断言留档记录被采信且不破坏真实门禁。
- **工程标准 checklist 本体入库**（PRD-147/T5，trend #739）：`docs/engineering-checklist/checklist.md`（v0.1，四类 19 条 + 公共约定 + 豁免规则），条目与 `scripts/eng_checklist.py` 的登记表逐条一致（`tests/test_eng_checklist_t5.py` 断言）；根 README 新增「发布门禁」节（发布前过工程门禁的口径与命令），另附 T5 验收记录与密钥扫描断言（金样例报告与门禁文档 0 命中，带阳性对照）。
- **并行专家骨架一键生成**（PRD-112/T2）：`python3 scripts/gen_harness.py --parallel-experts -o . examples/parallel-experts/page-review.yaml` 按 `templates/parallel-experts/` 的目录与专家/汇总契约，把编排规格铺成 `harness/<name>/`。不扩展 `capability.yaml`，也不新增运行器或技能。
- **并行专家编排模板**（PRD-112/T1，`templates/parallel-experts/`）：只读专家同一轮派发、合并后经人工门才派发唯一写入者。只有模板与契约测试，不含运行器与新技能。
- **链式 skill 使用指南**（`docs/chained-skills-guide.md`）：面向使用者写清如何运行一条链（校验/运行/人工门采纳续跑/状态/段独立调用/跳段与退出码全表）、如何编排新链（`chain.yaml` 字段逐项与校验规则）、元数据与兼容性口径、链上架 checklist。
- **最小链示例** `skills/delivery-chain/examples/minimal-chain/`：示范链前两段（环境扫描 → 规格）组成的两段链，无人工门、一次跑通，附说明与试跑命令；`livepowers-delivery` 插件拷贝已同步。

### 修复

- 各技能 `tests/<skill>/test_examples.py` 的 L2 用例不再用 `shutil.which("lp")` 找命令：macOS 自带 CUPS 打印命令 `/usr/bin/lp`，会被误当成 Livepowers 的 `lp`，导致 16 项用例在本机失败并真的调用打印命令。改用 `tests/helpers.py` 的 `find_livepowers_lp()`：优先用仓库内 `scripts/lp.py`，仓库脚本缺失时才用 PATH 里 `lp --version` 输出 `lp X.Y.Z` 的命令；`run_lp()` 在临时目录执行，不往仓库写 `.livepowers/`。
- **安装提示指向不存在的插件**：`npx livepowers install`（`--target claude`）结束时的提示和官网安装区 Claude Code 页签仍写 `/plugin install livepowers@livepowers-marketplace`，但插件市场自 v1.6.0 起只有 5 个主题插件，照做会失败。现改为先装 `livepowers-core`、其余主题插件按需安装，并列出全部 5 条命令，与 README 一致。
- **`livepowers-core` 插件内的 `lp.py` 落后于仓库根**：缺 PRD-046/T3 简洁输出等改动。现与根 `scripts/lp.py` 同步，并补上它依赖的 `lp_output.py`（之前只同步 `lp.py` 会在启动时 `ModuleNotFoundError`）。

### 测试

- `tests/test_plugin_sync.py`：插件内的 `scripts/*.py` 必须与根 `scripts/` 同名文件逐字节一致。
- `tests/test_marketplace_install.py`：插件 `scripts/` 里 import 的兄弟模块必须随插件一起提供；README、安装器、官网与插件 README 中的 `/plugin install <名>@livepowers-marketplace` 只能指向 marketplace.json 中存在的插件。
- `tests/test_npm.py`：断言安装提示含 `livepowers-core@livepowers-marketplace`，且不再出现 `livepowers@`。

## [1.6.0] - 2026-10-20

这一版的主角是新技能 **`generalizing-skills`**：把只能在一个项目里用的 skill，改造成换个项目只写一份绑定就能复用的 skill。同时，19 个技能拆成 5 个可单独安装的主题插件，每个技能都有了独立验收测试，命令行输出默认改为简洁模式。

### 新增

- **技能 `generalizing-skills`**（技能总数 19 → 20，归入 `livepowers-tooling` 插件）。解决的问题：同一种月报、稽核 skill 在每个项目各写一份，路径、列名、阈值、模板全写死，换个项目就得重写。
  - **三层拆分**：业务本体（对象、关系、规则模式）/ 方法（步骤、校验、交互）/ 环境实例（数据源、列、规则取值、模板、渠道）。用"变化分层"判断每句话归哪层。
  - **本体契约**：skill 只按 ID 引用规则，规则正文留在项目或企业本体里，不另造一份真值；规则模式进本体，规则取值进绑定。
  - **先判断值不值得泛化**：同类 skill ≥ 2 份、周期性、结果可自动核对、规则模式稳定；不可验证的不泛化。
  - **首次初始化**：在新 workspace 发现环境、生成环境指纹、确认实例参数与产物、试跑，写绑定 `.livepowers/bindings/<skill>.yaml`（含本体版本、指纹、确认人）。
  - **复用前比对**：指纹一致才直接跑；关键列出现新取值（如多了一种订单状态）时停下来问，不静默计算；运行时再做一次覆盖检查。
  - **验收**：原项目回归一致、第二个 workspace 只写绑定不改代码就跑通、护栏用例通过，生成者不验收自己；通过后进能力注册表并登记意图别名。
  - 按 RED / GREEN / REFACTOR 写成，对照结论见 `docs/devlog.md`。
- **`docs/lightweight.md` 轻量接入**：只想借概念、不搭全套时，按目标挑最小技能组合、只装需要的主题插件、只用几条命令，以及什么时候再升级。
- **5 个主题插件**：`livepowers-core` / `livepowers-ontology` / `livepowers-delivery` / `livepowers-night` / `livepowers-tooling`，可以只装需要的部分（`/plugin install livepowers-<主题>@livepowers-marketplace`）；插件市场清单对齐官方格式。插件内的技能是仓库根 `skills/` 的逐字节拷贝，测试保证不漂移。
- **每个技能的独立验收测试**：`tests/<skill>/test_examples.py`，分契约（L1）、示例（L2）、反例（L3）三层；规范见 `docs/SKILL-TEST-SPEC.md`。
- **简洁输出（默认开启）**：命令行输出改为"结论 / 关键信息 / 详情折叠"三段式，`--json` 与退出码不变。5 个典型场景的输出 token 合计下降约 67%（`scripts/token_compare.py` 可复现）。需要全量输出时设 `LIVEPOWERS_VERBOSE=1`，或在 `.livepowers/config.yaml` 写 `verbose: true`。
- **harness 生成器原型** `scripts/gen_harness.py`：读 `capability.yaml`，生成带 `--json` 与错误码的 `cli.py` 和对应 `SKILL.md`（设计见 `docs/HARNESS-DESIGN.md`）。
- 上架 skills.sh：`npx skills add zhanglunet/livepowers`。

### 改进

- `using-livepowers` 路由表与项目目录约定新增 `generalizing-skills` 与 `.livepowers/bindings/`。
- 几个技能之间补了调用关系说明（`digital-role-spec`、`fde-delivery`、`nightly-crystallization-review` 等）。
- README 首屏与官网重写定位与愿景，加 GIF 演示；官网新增 `generalizing-skills` 卡片与"只借概念"FAQ。

### 已知问题

- macOS 自带打印命令 `/usr/bin/lp`，各技能 `tests/<skill>/test_examples.py` 用 `shutil.which("lp")` 会找到它，导致 16 项 L2 用例在 macOS 本机失败（CI 的 Linux 环境不受影响）。修复进行中。
- Claude Code 插件 `livepowers-core` 自带的 `scripts/lp.py` 比仓库根目录的旧，尚未包含简洁输出；通过 npm 或仓库直接使用 `lp` 不受影响。

## [1.5.0] - 2026-10-12

### 新增

- **在线演示接入模型的通道（不绑定具体模型）**：`functions/api/agent.js`（Cloudflare Pages Function）调用任何兼容 OpenAI Chat Completions 的接口，由环境变量配置；限流用 D1 单条 upsert 原子计数（未绑定或计数出错时默认拒绝）。模型只输出展示面 JSON，页面按 `web/surface-rules.js`（与 `lp surface validate` 同一套规则，外加禁止递归查询、`SELECT *`、敏感字段，组件字段类型检查）校验后才执行，执行后再检查结果列不含敏感字段。未配置时退回预置展示面；预置匹配改为覆盖度 ≥ 60%，不再答非所问。配置方法见 `examples/living_app/README.md`。
- **活软件生长面**（#21，PRD 见 `docs/prd-living-surface.md`）：
  - 展示面描述 `templates/surface.json`（结构与数据分离，对齐 A2UI 思路，不传可执行代码）；组件 kpi / table / bar / line / filter。
  - `lp surface validate`：格式、组件、数据引用在本体内、只读单语句查询、无可执行代码、不内嵌结果数据、不引用写操作能力。
  - `lp surface record`：次抛只记元数据（查询、行数、结果哈希、数值合计）并写 S2 证据；明细不进 git，`lp init` 生成 `.livepowers/.gitignore` 排除 `cache/`。
  - `lp surface promote`：申请固化，建看板任务，`lp candidates` 把它排在最前。
  - `lp surface reconcile`：按记录的查询重算，与固化结构逐项比行数、哈希、合计。
  - `lp surface deploy`：先校验展示面（不通过则不执行任何 DDL 或查询），再执行 DDL、核验结构与查询、失败自动回滚，写部署回执（含展示面内容指纹）；`--twin` 演练，`--external --verified-by` 记录外部迁移。
  - `lp registry add --ui`：只认 `--env prod`、且展示面内容与部署时一致的回执，否则拒绝注册；注册后展示面文件被改，固定页自动下线；`lp registry find` 命中时提示固定页；`lp pages list` 输出固定页目录。
  - 新技能 `living-surface`；能力包增加 `ddl`、`rollback`、`materialization`、`deployment` 字段，`ui` 指向固化展示面。
  - `lp surface a2ui`：把展示面转成 A2UI v0.9.1 消息流（createSurface / updateComponents / updateDataModel；Column / Row / Card / Text / Button 同 A2UI 基础组件，图表、表格、KPI、筛选为自定义组件库）。
  - 参考宿主 `examples/living_app/`（零依赖：`http.server` + 原生 JS）：对话式页面，智能体回答以 A2UI 展示面嵌在对话里，「申请固化」是 A2UI Button 事件，「模拟生长」运行 `grow.sh`；walkthrough 增加活软件一段。
  - 网站新增在线演示页 `/demo/`（`docs/demo/index.html`，由 `examples/living_app/build_site.py` 生成）：对话式页面，浏览器内 SQLite（sql.js，带 SRI 校验）跑真实查询，演示次抛 → 申请固化 → 生长 → 命中固定页。

- **零依赖语义匹配**（#19）：`lp registry find --semantic` 在未严格命中时给出 MAYBE HIT 候选（exit 3），概念组存于 `.livepowers/concepts.json` 可审阅；严格路由与 `intents suggest` 不受影响，MAYBE 不会自动当作 HIT。
- **PostgreSQL / MySQL 扫描**（#15）：`scripts/scan_sql.py --dsn` 只读查询 `information_schema`，输出与 `scan_sqlite.py` 同构的本体草稿与指纹，可跨脚本 `--diff`。
- **证据自动采集扩展到 Cursor / Codex**（#17）：Cursor 用 `hooks/hooks-cursor.json`；Codex 等无钩子客户端用 `lp hook watch --transcript` 从会话记录补采。
- **规格产物链与稳定任务 ID**（#14）：规格模板带任务 ID（如 T001），`lp task new --spec --spec-task` 关联规格任务，并校验 ID 存在且不重复；示例见 `examples/spec-task-chain.md`。
- **技能触发率评测**（#16）：`scripts/eval_triggers.py` 按 `tests/triggers/*.jsonl` 评测触发与混淆，可记录金丝雀并与上次比较；测试要求每个技能至少 3 条正例、2 条反例。
- **Cursor 项目级入口规则**（#12）：项目级安装生成 `.cursor/rules/livepowers.mdc`，不覆盖用户自己的规则。
- **工具卡补后置条件与禁止动作**（#11）：`templates/tool-card.md` 与 `agent-harness-for-tools`。
- **skills.sh 安装**（#18）：文档补充 `npx skills add zhanglunet/livepowers`。

### 变更

- `fde-delivery` 瘦身（#13）：只保留交付流程，验收、台账、角色规格的细则回到对应技能。

### 修复

- `oltp-action-safety` 的 frontmatter 不是合法 YAML，skills CLI 会漏装（#20）；测试禁止描述里出现 `: ` 与 ` #`。
- 参考宿主 `grow.sh` 在 macOS 的 bash 上报变量未绑定（#25）。
- `fde-delivery` 引用的 `docs/paradigm.md` 在 npm / ZIP 安装后不存在（#6）：五类底座资产细项、节奏建议与警示信号移到随技能安装的 `skills/fde-delivery/cadence.md`；新增测试，技能目录内的文件不得引用 `docs/`，引用的同目录附属文件必须存在。

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
