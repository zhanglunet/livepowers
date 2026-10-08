# 开发日志

按日期记录做了什么、为什么、放弃了什么。版本变更的条目清单见 [CHANGELOG](../CHANGELOG.md)；这里写决策。

## 2026-10-08 · 活软件生长面（未发版）

做了什么：把"次抛展示 + 语义生成固化结构"落成 `lp surface` / `lp pages` 命令、`living-surface` 技能和一个零依赖参考宿主（#21）。

- 展示面只传数据与组件描述：选了"声明式描述 + 宿主渲染"，和 A2UI 同一取向。代价是组件只有五种；好处是不会有智能体代码跑在客户端。
- 次抛只记元数据：行数、哈希、合计。对账靠重跑记录的查询，而不是保存的明细——明细一旦进 git 就删不掉。
- 注册前必须有生产部署回执：`lp registry add` 只登记信息，不建表；没有回执就注册，固定页背后会是空的。孪生回执不算。
- 本体解析按行读 YAML（只取 `objects` 的 name / table 和 `views`），保持零依赖；复杂本体请把可引用的视图列进 `views:`。
- A2UI：内部格式保持 `livepowers-surface/1`（便于校验与对账），由 `lp surface a2ui` 转成 A2UI v0.9.1 消息下发。基础组件库没有图表，KPI / 表格 / 柱状图 / 折线图 / 筛选放在自定义组件库 `urn:livepowers:a2ui-catalog:surface:1`；协议还在演进（v1.0 候选中），转换器集中在一处，跟版本时只改这里。

## 2026-10-07 · v1.4.0：意图同义词表

**问题。**`lp registry find` 靠字符串和中文二元组匹配，同一件事换个说法（"各地区周收入"、"按区域的每周营收"、"weekly revenue by region"）就 MISS，于是重复探索；证据也被分散到几个名字下，固化候选迟迟凑不够 3 次。夜间技能要求"合并同义意图"，但没有工具，而证据日志是追加式的、不能改。

**做法。**`.livepowers/intents.json` 存"规范意图 → 别名"。`lp intents alias` 登记（别名若本身是规范意图，整组并入；别名不能再当规范名），`lp intents list` 看归并后的证据数，`lp intents suggest` 用词集 Jaccard / 二元组重叠找相似意图对，附上登记命令。全链路生效：`evidence add`、`task new`、`pending add`、钩子自动采集落盘时写规范名（原话留在 `intent_raw`）；`evidence stats`、`candidates`、晨报读取时归并——旧记录不改；`registry find` 查询命中任何同义词时把整组并入打分。

**取舍。**不做自动合并：`suggest` 只建议，人确认——合错口径的代价比多探索一次高。不做向量检索：零依赖、确定性、可审计，和"固化物是确定性代码"一致；语义检索留在路线图。

## 2026-10-07 · v1.3.0：钩子自动采集证据

**问题。**证据全靠 Agent 主动 `lp evidence add`，而技能触发本身是概率性的：忘了、被打断、或觉得"这次很简单"，这一轮就没留痕。频率统计、固化候选、S2 占比趋势全建立在证据上——漏记一次，固化晚一天；系统性漏记，产品就学不会。这是对比调研里 Voyager 式技能库（continuous-learning v2）明显领先的一点。

**做法。**Claude Code 插件加两个钩子，逻辑都在 `lp hook`：

- `PostToolUse`（只看 Bash）：看到 `lp registry find` 就记下意图与命中结果；命中后每次调用该能力 entry 的固定前缀，自动记一条 S1 证据（exit 非 0 或有 stderr 记 fail）；看到 `lp evidence add` 就标记"本轮已显式记录"。
- `Stop`：若本轮有 MISS 且没有显式记录，补记一条 S2 证据，结论 `partial`、`auto: true`，token 从 transcript 里累加本轮 assistant 消息的 usage。
- 置信度 =（成功 + 1）/（调用 + 2），随自动采集的 S1 成功 / 失败升降；≥3 次调用且低于 0.6 进复核——这样自动采集直接推动去固化。

**取舍。**

- 自动补记 vs 只提醒：选了补记并标 `partial`。理由是频率不能漏；代价是"只问了一句没探索"也会记一条，但 note 写明 auto、晨报单列"自动采集待确认"、`stats` 单独计数，不计入成功率。
- 显式记录永远优先：自动记录没有 verifiable / cost / note，技能里明确写"这只是兜底"。
- 钩子永不阻塞：异常全吞、总是 exit 0、未 `lp init` 的项目不创建任何文件、`LP_HOOK_CAPTURE=0` 可关。`PostToolUse` 同步（要保证顺序，耗时毫秒级），`Stop` 异步。
- 客户端适配：Claude Code 用 `PostToolUse` / `Stop`；Cursor 配置 `afterCommand` / `sessionEnd` 并由 `lp hook` 兼容平铺字段；Codex 与无钩子客户端提供 `lp hook watch --transcript <path>` 轮询，亦可回合结束显式记。
- entry 匹配用"参数占位符之前最多三个 token"的前缀：简单、可解释；误判的代价只是多一条 S1 记录。

## 2026-10-07 · v1.2.0：独立评审后的修正与补强

**起因。**v1.1.0 发布后做了一次独立评审（一个评审 Agent 只读仓库、实跑 60 多条命令；另一个调研 Superpowers 与 9 个同类产品）。评审的总评是"思想自洽、脚本与技能匹配度高"，但挑出了几处真正的矛盾。

**修了什么，为什么。**

- *17 个技能的 description 都违反了仓库自己的规则。*`writing-livepowers-skills` 说"只写何时使用，不要概括流程，否则 Agent 读完描述就以为自己会了"，但每个描述都在破折号后接了一段流程摘要，而测试检不出来。现在只保留触发条件，测试会拒绝破折号接流程、流程动词和超过 400 字符的描述。
- *任务看板有两个漏洞。*`takeover` 可以直接迁到 `running`，绕过待验证和已注册两道门，和铁律 6 矛盾；止损后轮次不重置，接管后"重开"永远再次止损，只能手改 `tasks.json`。现在 takeover 只能去澄清 / 规格 / 探索 / 关闭，重开必须显式 `--reset-loops` 或 `--extend-budget`；`closed` 成为终态。
- *结果台账对"越低越好"的指标算出负的增量价值。*示例场景全是这类（逾期数、时长）。`baseline` 加了 `--direction lower`。
- *"发新版本旧版保留"在脚本里做不到。*`registry add` 对同名 active 能力直接拒绝。加了 `--supersedes <旧id>`：自动退役旧版并记录取代关系。
- *非插件安装下技能跑不动。*技能正文写 `python <plugin>/scripts/lp.py` 和 `templates/...`，npm 和"仅复制技能"的用户找不到这些位置。入口技能现在有一张"安装方式 → lp 在哪、模板在哪"的表，安装器把模板装到 `using-livepowers/templates/`。

**补了什么。**

- `takeover-handling`：循环里唯一"有状态无技能"的环节。止损后该冻结、交付诊断包、归因、换人重开、记接管成本——之前没人告诉 Agent 这些。
- `lp pending`：夜间产物清单。晨报原来承诺列出"评分、n*、测试结果、位置"，实际只能列证据候选，承诺落空。现在夜间 Agent 用 `lp pending add` 登记，晨报汇总，`pending done` 拒绝生成者给自己验收。
- `lp canary`：三个技能都提到"金丝雀评测"，但没有落盘格式和比较命令。现在有了记录与比较（通过率降 >10% 或 token 升 >30% 算回归）。
- 入口技能的"项目目录约定"表和冷启动说明；`lp --help` 给每个子命令和参数写了说明。
- 网站：首屏放安装命令、"两种死"说清为什么、场景清单、五分钟 demo 的真实输出、对比、FAQ、开发日志、反馈入口。

**放弃或推迟了什么。**

- hook 自动采集证据、意图同义词表、技能触发率自动评测、spec-kit 式任务 ID、Cursor `.mdc` 规则、上架 skills.sh：都有价值，但每个都是独立的小项目，放进路线图而不是塞进这个版本。
- 评审建议把 `fde-delivery` 拆分瘦身：它确实复述了别的技能，但拆分会改变路由表语义，等有现场反馈再动。

## 2026-10-07 · v1.1.0：npm 安装包

- `npx livepowers install` 把技能装进 Claude Code、Cursor、Codex 及其他 Agent Skills 客户端；写安装清单，`uninstall` 只删自己装的；Codex 项目级安装会把入口说明合并进 `AGENTS.md`（带标记，可卸载）。
- `lp` 命令随包安装，转发到自带的 Python 脚本。选择不用 Node 重写脚本：Python 标准库零依赖、测试齐全，Node 只负责分发。
- 网站上线 livepowers.pages.dev（Cloudflare Pages，推送即发布）。
- 顺手清掉了测试里的 `ResourceWarning`。

## 2026-10-07 · v1.0.0：首个公开版本

- 17 个技能、3 个零依赖脚本、8 个模板、Claude Code / Codex / Cursor 插件清单、测试与 CI、MIT。
- 在 0.9 试用版基础上加了验收门、本体演进、结果台账、数字岗位、技能编写五个技能；脚本加了任务看板状态机、结果台账、资产四道门、能力复核。
- 仓库结构借鉴 obra/superpowers：技能是强制工作流，会话启动时注入入口技能。
- 全面脱敏：示例一律使用虚构的通用业务场景。
