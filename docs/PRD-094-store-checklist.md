# PRD-094/T1：官方插件收录标准反向 checklist v1（定稿）

> 状态：**定稿（final），2026-10-20 用户确认（Q1–Q9 全按稿内建议）**。其中 Q1、Q2、Q4、Q5 按稿内建议执行；Q3、Q6、Q7、Q8、Q9 五项经用户 2026-10-20 拍板"维持现状定案"，逐条结论见"决策记录"节。Q1–Q9 至此全部定案。
> 对应任务：zhanglunet/livepowers#56（PRD-094/T1）；PRD 原文：zhanglunet/trend `adopted/PRD-094-livepowers-store-checklist.md`
> 起草日期：2026-10-20；定稿日期：2026-10-20

## 用途

把 Anthropic 官方插件目录（claude-plugins-official）与 Cursor 插件市场的收录/质量标准拆成可逐项打分的 checklist，给 livepowers 的 skills 做一次"用考官的卷子给自己判卷"的自查：每个 skill、每个插件逐项过条目，打分留证据，不达标项进 T4 待办清单。

- 打分对象分三层：**skill 级**（每个 skill 单独打分，进 T3 全量打分矩阵）、**插件级**（每个主题插件 + 根插件各打一次）、**仓库级**（marketplace 清单整体，只打一次）。每条条目标注适用层级。
- 本 checklist 只定条目和口径，不做工具；打分表模板（skill × 条目矩阵、汇总公式）是 T2 的事，本文只留汇总口径接口（见"汇总口径"节）。
- 与 PRD-078 的呼应：PRD-078 是选题审计，看"该做什么"；PRD-003 已按官方市场格式把 5 个插件发了出去，解决"格式对不对"；本 checklist 呼应 PRD-078 的审计思路，把尺子换成官方收录标准，回答"质量分够不够"。

## 相关门禁（选题 → 瘦身 → 工程门禁 → 收录）

本 checklist（收录）是最后一道闸；收录之前还有三道（谁在哪个阶段拦什么）：

| 阶段 | 门禁 | 拦什么 | 位置 |
|---|---|---|---|
| 选题 | PRD-078 选题审计（已收官，事后抽查） | 翻车点不成立、证据纯构造的选题（19 张审计卡 + 待办清单，成果在 trend 仓库） | [PRD-078 总报告](https://github.com/zhanglunet/trend/blob/main/adopted/PRD-078-final-report.md) |
| 瘦身 | PRD-148 瘦身门 | 新提案 / 大改"这需要存在吗、能否并入已有 skill"——无决策记录不可标 published | [`docs/slim-gate/README.md`](slim-gate/README.md) |
| 工程门禁 | PRD-147 工程标准 checklist | 测试 / 文档 / 示例 / 安全四类 19 条——阻断级不过不出发布 PR | [`docs/engineering-checklist/README.md`](engineering-checklist/README.md) |
| 收录 | **PRD-094 收录 checklist（本门，C-01–C-31）** | 官方目录视角"收不收"：结构 / 元数据 / 质量分 | 本文 |

收录打分以 published 为前提。工程门（PRD-147）与本文的字段映射见
[`docs/engineering-checklist/prd-094-mapping.md`](engineering-checklist/prd-094-mapping.md)；
结构 / 元数据类 C 条目不在工程门重复打分（见映射文档的反向覆盖表）。

## 来源清单（标准版本标）

官方标准没有统一版本号，本 checklist 以"来源 + 抓取日期"作为版本标（对应 PRD 风险节"checklist 标注标准版本号，T5 复核"）。全部条目均出自下列原文，2026-10-20 抓取：

| 编号 | 来源 | 链接 | 备注 |
|---|---|---|---|
| A1 | anthropics/claude-plugins-official 仓库 README | https://github.com/anthropics/claude-plugins-official | 官方目录结构、外部插件提交与质量/安全标准、名称不可变规则 |
| A2 | Claude Code 官方文档《Create a marketplace》 | https://code.claude.com/docs/en/plugin-marketplaces | 页面标注 Updated 2026-10-01；条目命名、相对路径、validate 报错范围、官方保留名 |
| A3 | Claude Code 官方文档《Plugin manifest reference》 | https://code.claude.com/docs/en/plugins-reference | plugin.json 字段表、必填/警告规则、目录展示字段、路径规则 |
| A4 | Claude Code 官方文档《Extend Claude with skills》 | https://code.claude.com/docs/en/skills | SKILL.md frontmatter 规范、Agent Skills 六字段可移植集、正文写作要求 |
| C1 | Cursor 官方文档《Plugins》 | https://cursor.com/docs/plugins | 人工审核、必须开源、本地测试流程、提交入口 |
| C2 | Cursor 官方文档《Plugins reference》 | https://cursor.com/docs/reference/plugins | .cursor-plugin/plugin.json 与 marketplace.json 字段表、提交清单（submission checklist）原文 |
| L1 | livepowers 仓库内标准《SKILL-TEST-SPEC.md》 | 仓库 `docs/SKILL-TEST-SPEC.md` | **内部标准，非官方来源**；仅在官方标准未覆盖的"测试分层"处用作证据口径，条目中单独标注 |

> 说明：A1 的 README 只写"External plugins must meet quality and security standards for approval"，细则不在 README 里；可操作的细则主要来自 A2/A3/A4 的字段与校验规则和 C2 的提交清单原文。下文每条"要求原文"均为简摘，判定以链接原文为准。

## livepowers 现状速览（2026-10-20 只读核查，HEAD `9cd242f`）

打分时对照用，先摆事实，不预设分数：

- `skills/` 下 **20 个** skill 目录（acceptance-gates、agent-harness-for-tools、auditable-agent-comms、crystallize-to-system1、digital-role-spec、env-scan-ontology、explore-with-evidence、fde-delivery、generalizing-skills、living-surface、night-loop-planning、nightly-crystallization-review、oltp-action-safety、ontology-evolution、ontology-grounded-spec、outcome-ledger、system1-first、takeover-handling、using-livepowers、writing-livepowers-skills）。**注意：PRD 与 T3/T5 原写 19 个**——v1.6.0 新增 generalizing-skills 后已是 20 个；定稿按 20 个打分，T3/T5 口径同步改 20/20（决策记录 Q1，已确认）。单个 skill 目录目前只含 SKILL.md（如 using-livepowers，10725 字节）。
- 仓库根 `.claude-plugin/` 有 plugin.json（name=livepowers、version=1.6.0、description、author、homepage、repository、license=MIT、keywords 9 个）与 marketplace.json（5 个主题插件条目，字段含 name/description/version/source/author/license/keywords/category/homepage）。
- `plugins/` 下 5 个主题插件（core / ontology / delivery / night / tooling），各自含 `.claude-plugin/`、README.md、LICENSE、skills/ 等，与 marketplace.json 的 source 一一对应。
- `.cursor-plugin/` **只有 plugin.json（690 字节），没有 marketplace.json**（见条目 C-04；计分地位见决策记录 Q3：正式计分）。
- `docs/SKILL-TEST-SPEC.md` 定义了 L1 契约 / L2 示例 / L3 反例三层测试；`tests/<skill-name>/test_examples.py` 与 skills 一一对应。
- 仓库根有 LICENSE（MIT）、README.md、CHANGELOG.md；另有 skills.sh 分发渠道（根目录 skills.sh.json），不在官方两目录标准覆盖内（是否另加自有条目见决策记录 Q8：v1 不另加）。

## 条目表

打分标准统一为 0/1/2 三档：2 = 完全满足，1 = 部分满足（有但不全/不规范），0 = 缺失或违反。判定条件逐条写死，避免打分时自由裁量。每条"证据要求"写明打分时要看的文件/字段/命令输出，T3 打分时证据链接到具体位置。

### 一、结构（5 条）

| 编号 | 要求（原文简摘） | 出处 | 打分标准（2 / 1 / 0） | 证据要求 | 适用 |
|---|---|---|---|---|---|
| C-01 | 每个 skill 独立目录、含 SKILL.md："Each subdirectory containing a `SKILL.md` file"（Cursor 自动发现规则）；官方目录结构中 skills/ 为 Skill definitions 存放处 | C2、A1 | 2：`skills/<name>/SKILL.md` 存在且目录只承载该 skill；1：SKILL.md 存在但不在独立目录（如散落在根目录）；0：缺 SKILL.md | `skills/<name>/` 目录清单 | skill |
| C-02 | 插件标准布局：`.claude-plugin/plugin.json` 必备（required）；其余组件文件放插件根，不得放进 `.claude-plugin/`："Put every other plugin file at the plugin root, not inside `.claude-plugin/`" | A1、A3 | 2：plugin.json 在 `.claude-plugin/` 下，skills/、commands/、hooks/ 等在插件根；1：plugin.json 存在但有组件误置于 `.claude-plugin/` 内；0：缺 plugin.json | 插件根目录清单 + `.claude-plugin/` 清单 | 插件 |
| C-03 | `.claude-plugin/marketplace.json` 存在且合法：含 name、owner（必填，缺失 validate 报 `owner: Invalid input`）、plugins 数组；每条目 source 为相对路径、自 marketplace 根起算、不含 `..`、指向真实目录 | A2 | 2：文件存在、必填字段齐、全部 source 可达；1：文件存在但有条目字段缺失或个别 source 路径写法不规范但可达；0：文件缺失，或有 source 指向不存在的目录/含 `..` | `.claude-plugin/marketplace.json` 全文 + 逐条目核对目标目录 | 仓库 |
| C-04 | Cursor 侧清单齐备：根有 `.cursor-plugin/plugin.json`；多插件仓库另需 `.cursor-plugin/marketplace.json` 且插件名唯一（提交清单原文："Cursor multi-plugin repositories have `.cursor-plugin/marketplace.json` at the repo root with unique plugin names"） | C2 | 2：两个文件都在、marketplace 内插件名无重复；1：只有 plugin.json、无 marketplace.json（单插件形态可装，多插件分发不完整）；0：两个都缺 | `.cursor-plugin/` 目录清单 | 仓库 |
| C-05 | marketplace 命名不冒用官方保留名：官方名（如 `claude-plugins-official`）在添加时会被拒绝："The name '<name>' is reserved for official Anthropic marketplaces" | A2 | 2：名称为自有名称、不含官方保留名；1：（无中间档，命中即 0）；0：使用或仿冒官方保留名 | `.claude-plugin/marketplace.json` 的 name 字段 | 仓库 |

### 二、元数据（14 条）

| 编号 | 要求（原文简摘） | 出处 | 打分标准（2 / 1 / 0） | 证据要求 | 适用 |
|---|---|---|---|---|---|
| C-06 | plugin.json `name` 是唯一必填字段："Plugin identifier, required. Use kebab-case."；不得触保留名规则（以 `claude-`、`anthropic-` 等开头或整体冒充官方为 error） | A3 | 2：name 存在、kebab-case、不触保留名；1：name 存在但非 kebab-case（validate 给 warning）；0：缺 name 或触保留名 error | plugin.json 的 name 字段 | 插件 |
| C-07 | marketplace 条目名与 plugin.json 的 manifest 名必须一致："Keep the entry name and the manifest name the same"，不一致时按 manifest 名安装会报 not found | A2 | 2：逐条目比对全部一致；1：（无中间档，不一致即 0 分条目，但按条目逐个判）；0：任一条目两名不一致 | marketplace.json 各条目 name × 对应 plugin.json name 对照表 | 插件 |
| C-08 | 已发布插件名不可变："The `name` field in a marketplace entry is an **immutable slug**"；改名须走 `displayName` 改展示名，或在 marketplace.json 顶层 `renames` 里加旧名→新名映射 | A1 | 2：自首次发布以来未改名，或改名已配 renames 映射；1：改过名且已补 renames 但曾有版本未配（历史断裂已修复）；0：改名无 renames 映射 | git 历史中 marketplace.json 的 name 变更记录 + renames 字段 | 仓库 |
| C-09 | `version` 存在且口径一致：Claude 侧缺 version 是 validate warning；Cursor 侧要求语义化版本（"Semantic version (e.g., `1.0.0`)"）；plugin.json 与 marketplace 条目的版本号应一致 | A3、C2 | 2：两处都有 version、为语义化版本且一致；1：有 version 但两处不一致，或非语义化写法；0：任一处缺 version | plugin.json 与 marketplace.json 条目的 version 字段对照 | 插件 |
| C-10 | `description` 说清用途：Cursor 提交清单原文 "`description` clearly explains the plugin's purpose"；Claude 侧它是用户在 `/plugin` 浏览时看到的那一行，缺失为 validate warning | C2、A2、A3 | 2：plugin.json 与 marketplace 条目都有 description，一句话说清"给谁、解决什么"；1：有 description 但只写口号/范式词、看不出具体用途，或只有一处有；0：两处都缺 | 两处 description 原文 | 插件 |
| C-11 | `author` 完整：Claude 侧 author 为对象、`name` 必填（缺失为 validate warning）；Cursor 侧同样 "Author info: `name` (required), `email` (optional)" | A3、C2 | 2：plugin.json 与 marketplace 条目都有 author.name；1：只有一处有，或只有 name 无任何联系方式且条目间写法不一；0：两处都缺 | 两处 author 字段 | 插件 |
| C-12 | `license` 为 SPDX 标识且与 LICENSE 文件一致："SPDX identifier such as `MIT` or `Apache-2.0`"；官方目录要求看每个插件自己的 LICENSE 文件 | A3、A1 | 2：plugin.json/marketplace 条目 license 字段与插件目录内 LICENSE 文件一致；1：有 license 字段但插件目录内无 LICENSE 文件（或反之）；0：无 license 字段且无 LICENSE 文件 | license 字段 + 插件目录 LICENSE 文件 | 插件 |
| C-13 | `keywords` 供发现：Claude 侧 "Discovery tags"；Cursor 侧 "Tags for discovery and categorization" | A3、C2 | 2：plugin.json 与 marketplace 条目都有 keywords，覆盖该插件的核心场景词；1：只有一处有，或词与内容明显不相关；0：两处都缺 | 两处 keywords 字段 | 插件 |
| C-14 | `homepage` 必须可解析为 URL："Must parse as a URL, or the plugin fails to load"；`repository` 指向源码仓库 | A3 | 2：homepage/repository 均为合法 URL 且指向本项目；1：只填了 repository 未填 homepage（不阻断加载，但目录展示缺链接）；0：homepage 填了非法 URL（阻断加载）或指向无关站点 | 两字段原文（必要时实际打开验证） | 插件 |
| C-15 | 目录展示字段（icon/logo 等）：Anthropic 目录 listing 读取 plugin.json 的 `icon`、`documentationUrl`、`supportUrl`、`privacyPolicyUrl`、`termsOfServiceUrl`；Cursor 侧 `logo` 要求"commit the logo to your repo and use a relative path" | A3、C2 | 2：有 icon/logo（仓库内相对路径）且至少 documentationUrl 或文档链接齐备；1：有 logo 或文档链接其一；0：都没有 | plugin.json 相关字段 + 资产文件是否存在 | 插件 |
| C-16 | SKILL.md 必须带可解析的 YAML frontmatter：frontmatter 须是文件第一行起的 `---` 块；"If the YAML between the markers doesn't parse, the skill still loads with no fields set"——即解析失败等于元数据全丢、无法靠 description 匹配触发 | A4 | 2：frontmatter 存在且 YAML 可解析；1：（无中间档）；0：无 frontmatter 或 YAML 解析失败 | SKILL.md 头部原文；可用仓库契约测试 `tests/_contract/run_contract.py` 的解析结果作证 | skill |
| C-17 | skill `name` 规范：小写 kebab-case（Cursor 原文 "Skill identifier (lowercase, kebab-case)"）；Claude 侧含零宽空格、控制字符、`<`/`>` 等字符的名会被拒载；内部契约另要求 name 与目录名一致 | C2、A4、L1 | 2：name 存在、kebab-case、无禁用字符、与目录名一致；1：name 合法但与目录名不一致；0：缺 name 或含禁用字符 | SKILL.md frontmatter name × 目录名 | skill |
| C-18 | skill `description` 写明"做什么 + 何时用"：官方推荐字段（"Only `description` is recommended so Claude knows when to use the skill"）；关键用例写在前面，description 与 when_to_use 合计在列表里截断于 1,536 字符 | A4 | 2：description 存在，同时交代用途与触发场景，关键信息在前 1,536 字符内完整；1：有 description 但只有用途没有触发场景（或反之），或关键信息被截断；0：缺 description | SKILL.md frontmatter description 原文 + 字符数 | skill |
| C-19 | frontmatter 字段集可移植：离开 Claude Code 的分发路径（claude.ai 上传、Skills API、`package_skill.py` 打包）只允许六字段 `name`、`description`、`license`、`compatibility`、`metadata`、`allowed-tools`，多一个字段即硬报错（"packaging or upload fails with a hard error"）；`compatibility` 若填须 ≤500 字符 | A4 | 2：只用六字段；1：用了 Claude Code 扩展字段（Q2 已定 (a) 严判：扩展字段即记 1 分，不设"只走 Claude Code 分发"的豁免，见决策记录 Q2）；0：字段名拼写错误等导致字段被静默忽略（Claude Code 对未知字段 "ignores a field it doesn't recognize without reporting an error"） | SKILL.md frontmatter 全字段清单 | skill |

### 三、文档（2 条）

| 编号 | 要求（原文简摘） | 出处 | 打分标准（2 / 1 / 0） | 证据要求 | 适用 |
|---|---|---|---|---|---|
| C-20 | 每个插件有 README 且写明用法与配置：Cursor 提交清单原文 "`README.md` documents usage and any configuration"；官方目录标准结构中 README.md 为 Documentation | C2、A1 | 2：插件根有 README，含用途、安装、用法、配置说明；1：有 README 但只有介绍、缺用法或配置；0：无 README | 插件根 README.md | 插件 |
| C-21 | marketplace 条目展示信息完整：条目除 name/source 外应有 description、category、keywords 等供浏览与检索的字段（Cursor 条目字段表含 category、tags；Claude 侧条目 description 是浏览页展示行） | C2、A2 | 2：5 个条目展示字段齐备且与插件实际内容相符；1：条目齐但个别条目缺 category/keywords；0：条目只有 name+source | marketplace.json 各条目字段清单 | 仓库 |

### 四、质量（4 条）

| 编号 | 要求（原文简摘） | 出处 | 打分标准（2 / 1 / 0） | 证据要求 | 适用 |
|---|---|---|---|---|---|
| C-22 | `claude plugin validate` 通过："`claude plugin validate` is the authoritative check for a manifest"；它报告 JSON 语法错误、必填缺失、命名违规、含 `..` 的 source、未知字段警告 | A3、A2 | 2：Validation passed（无警告）；1：Validation passed with warnings；0：Validation failed | 对仓库根与各插件目录运行 validate 的输出记录（T3 打分时实跑一次并存档） | 插件/仓库 |
| C-23 | 上架前本地实测安装：Claude 侧 "install from the marketplace on your own machine before you share it"；Cursor 侧把插件放 `~/.cursor/plugins/local` 重载后在 Customize 确认组件出现，提交清单含 "Plugin has been tested locally" | A2、C1、C2 | 2：有本地安装/加载实测记录且组件（skills/commands）按预期出现；1：装过但无记录可查；0：从未本地实测 | 实测记录（ devlog/reports 中的记载或 T3 时补测记录） | 插件 |
| C-24 | SKILL.md 正文简洁可执行："Keep the body itself concise… State what to do rather than narrating how or why"；内部契约参考线：正文超 500 行给 warning | A4、L1 | 2：正文以步骤/约束/判定条件为主，无大段背景叙述，≤500 行；1：正文可执行但混有成段叙述，或超 500 行；0：正文主要是理念阐述、找不到可执行步骤 | SKILL.md 正文（行数 + 人工判读） | skill |
| C-25 | 引用完整性：正文里引用的文件、其他 skill 必须真实存在；出现的命令（如 `lp <cmd>`）须同段给出退出码/语义说明（内部契约 L1 的检查项）；Cursor 提交清单对应项 "All included components have valid files and frontmatter" | L1、C2 | 2：引用全部可达、命令均有语义说明；1：个别引用失效或个别命令缺说明；0：多处引用失效 | SKILL.md 引用清单 × 仓库文件核对（契约测试输出可作证） | skill |

### 五、安全（4 条）

| 编号 | 要求（原文简摘） | 出处 | 打分标准（2 / 1 / 0） | 证据要求 | 适用 |
|---|---|---|---|---|---|
| C-26 | 开源与审核前提：Cursor 侧 "All plugins must be open source"，且 "Every plugin is manually reviewed before it's listed… we review each update before publishing"；Claude 侧外部插件 "must meet quality and security standards for approval"，目录页顶部有信任警告 | C1、A1 | 2：仓库公开、LICENSE 在根目录、内容与公开状态一致（无只在私有渠道分发的同名异版）；1：公开但 LICENSE 缺失或位置不规范；0：仓库非公开或含未声明来源的第三方内容 | 仓库可见性 + 根 LICENSE | 仓库 |
| C-27 | 凭据不入库：Claude validate 对 MCP 配置中 "a header value that looks like a literal credential" 给警告；Cursor 原文 "Do not put secret values in the plugin repo"，机密只能用 `${VAR}` 占位并在 manifest 的 variables 里声明名 | A3、C2 | 2：全仓无字面凭据，MCP/hook 配置中的机密均为占位符且有声明；1：无真实凭据，但有疑似占位符未在 variables/文档中声明；0：发现字面 token/密钥 | 对 `.mcp.json`、hooks、scripts 的凭据模式扫描记录 | 插件/仓库 |
| C-28 | manifest 路径全部相对且不逃逸：Cursor 提交清单原文 "All paths in manifest are relative and valid (no `..`, no absolute paths)"；Claude 侧路径缺失或逃逸插件根是 Validation failed 级问题 | C2、A3 | 2：plugin.json/marketplace.json 所有路径字段为相对路径且目标存在；1：路径合法但有个别目标缺失（不阻断加载的组件路径）；0：出现绝对路径、`..` 或关键组件路径指向不存在 | 两个 manifest 的路径字段逐项核对 | 插件 |
| C-29 | `allowed-tools` 与实际需要匹配（引申条目）：`allowed-tools` 是"该 skill 激活时无需询问即可用的工具"清单——官方未给"最小授权"的直接条文，本条由该字段语义引申，已纳入正式打分（见决策记录 Q7） | A4 | 2：声明了 allowed-tools 且与正文实际用到的工具一致；1：未声明 allowed-tools（走默认询问，不算违规但少一层明确边界），或声明与实际有出入；0：声明了与正文无关的高危工具（如与任务无关的任意 shell/写权限） | SKILL.md frontmatter × 正文命令核对 | skill |

### 六、测试（2 条）

> 说明：官方标准对"每个 skill 要有独立验收测试"没有直接条文，只有 C2 提交清单的 "All included components have valid files and frontmatter" 与 "Plugin has been tested locally" 两条兜底。livepowers 自己的 SKILL-TEST-SPEC 已把测试定成三层契约，这两条以内部标准为判定口径、官方条文为依据下限，T5 验收的"复核一致性"也靠它兜底。按内部标准计分，已定案（见决策记录 Q8）。

| 编号 | 要求（原文简摘） | 出处 | 打分标准（2 / 1 / 0） | 证据要求 | 适用 |
|---|---|---|---|---|---|
| C-30 | 每个 skill 有独立验收测试且分层：`tests/<skill-name>/test_examples.py` 与 skills 一一对应，覆盖 L1 契约（frontmatter/引用/退出码文档）、L2 示例、L3 反例；"缺目录 = 测试缺失 = CI 打回" | L1、C2 | 2：测试目录存在且三层齐备、CI 中实际运行；1：有测试但缺某一层（如无 L3 反例）；0：无测试目录 | `tests/<skill-name>/` 清单 + 测试文件内容 | skill |
| C-31 | 示例可复现、反例不误触发：L2 测"skill 里的断言性例子可复现"，L3 测"不该触发的场景明确不触发"；需真实环境的 L2 用例须显式 skipIf 标注而非假绿 | L1 | 2：L2/L3 用例最近一次 CI 全绿（skip 项有明确标注）；1：有用例但长期未跑或 skip 无标注；0：用例存在但实际失败未处理 | CI 运行记录或本地 `python3 -m unittest discover -s tests` 输出 | skill |

## 汇总口径（给 T2 打分表留的接口）

T2 做打分表模板时按以下口径实现汇总公式，本文只定口径、不做表：

1. **条目得分**：每条 0/1/2；不适用的条目标 N/A，不计入分母，打分时必须写明不适用理由。
2. **skill 得分率** = 该 skill 适用条目实得分之和 ÷（适用条目数 × 2）。skill 级条目共 10 条：C-01、C-16、C-17、C-18、C-19、C-24、C-25、C-29、C-30、C-31（以条目表"适用"列为准，T2 模板按适用列分列）。
3. **插件得分率** = 插件级条目同理单独计算（C-02、C-06～C-15、C-20、C-22、C-23、C-27、C-28 中适用插件层者）；**仓库级条目**（C-03、C-04、C-05、C-08、C-21、C-26）单独成段报告，不并入任何 skill/插件分数。
4. **条目达标**：得 2 分为达标；1 分为部分达标、0 分为不达标，1 分和 0 分都进 T4 待办清单（0 分优先）。
5. **达标判定（Q4、Q5 已确认，见决策记录）**：达标率 = 达标（2 分）条目数 ÷ 适用条目总数。单 skill 达标 = 适用条目无 0 分且达标率 ≥ 90%；插件、仓库两层各自同理判定，skill、插件、仓库三层分开报，不折算一个总百分比（Q4）。整体验收（T5）另沿用 PRD 口径：覆盖率全量（skill 20/20，Q1）+ 抽查 5 个 skill 的打分复核一致性 ≥ 80%。
6. **证据强制**：每条打分必须附证据（文件路径 + 字段/行号，或命令输出存档位置）；无证据的打分视为未打分。存疑项标"待复核"，计入 T5 抽查池。
7. **标准版本标**：打分表抬头须抄录本 checklist 的来源清单与抓取日期；T5 验收时按 PRD 风险节复核官方标准是否有更新，有更新先升 checklist 版本再复核分数。
8. **计分地位定案（决策记录 Q3、Q6、Q7、Q8，2026-10-20 用户确认）**：C-04、C-15、C-29、C-30、C-31 全部正式计分——照常打分留证据，一律计入达标率分母，达标率只用单一算法，不再另出剔除版；skills.sh 渠道 v1 不另加自有条目（Q8）。

## 决策记录（2026-10-20 用户确认）

Q1–Q9 全部已定案。稿内有明确"建议"字样或既定口径的按结论执行（Q1、Q2、Q4、Q5）；稿内仅二选一提问或开放式征询、无建议结论的（Q3、Q6、Q7、Q8、Q9），用户于 2026-10-20 拍板"维持现状定案"，逐条结论如下。

- **Q1 打分对象 19 还是 20**：稿内建议"按 20 个打分，T3/T5 口径同步改 20/20"。结论：按建议执行——定稿打分对象为 20 个 skills，T3（#58 全量打分）与 T5（#60 验收覆盖率）口径同步为 20/20。
- **Q2 frontmatter 字段集（C-19）**：稿内建议 (a) Agent Skills 六字段严判（理由：仓库同时走 Cursor/skills.sh 分发）。结论：按 (a) 执行，C-19 判定已改为"用了 Claude Code 扩展字段即记 1 分"，无豁免。
- **Q3 C-04（Cursor 侧 marketplace.json）计分地位**：稿内无明确建议（仅给出"若只主攻 Claude 官方目录，可把 C-04 降为观察项"的条件式假设）。结论：维持现状定案（2026-10-20 用户确认）——C-04 正式计分，计入达标率分母，不降为观察项（汇总口径第 8 条）。
- **Q4 三层分开算分**：稿内既定口径为 skill/插件/仓库三层分开报、不折算总分，问题问的是"是否接受"该口径。结论：接受，按既定口径定稿（汇总口径第 3、5 条），不设折算权重。
- **Q5 达标线**：稿内建议"单 skill 适用条目无 0 分且达标率 ≥ 90%；整体验收沿用 PRD 的覆盖率全量 + 抽查 5 个复核一致性 ≥ 80%"。结论：按建议执行，已落入汇总口径第 5 条。
- **Q6 C-15（icon/logo/目录展示字段）计分地位**：稿内无明确建议（"正式条目 / 加分备注"二选一，双向理由并列）。结论：维持现状定案（2026-10-20 用户确认）——C-15 正式计分，计入达标率分母，不作加分备注（汇总口径第 8 条）。
- **Q7 C-29（allowed-tools 匹配度）保留与否**：稿内无明确建议（"保留 / 删掉"二选一）。结论：维持现状定案（2026-10-20 用户确认）——C-29 保留并正式计分，计入达标率分母。
- **Q8 测试类条目内部标准计分 + skills.sh 条目**：稿内无明确建议（两问均为开放式确认）。结论：维持现状定案（2026-10-20 用户确认）——C-30/C-31 按本文的内部标准口径正式计分，计入达标率分母；skills.sh 渠道 v1 不另加自有条目。
- **Q9 条目总量 31 条**：稿内无明确建议（开放式征询删补，仅举例）。结论：维持现状定案（2026-10-20 用户确认）——条目总量维持 31 条，不删不补。

---

起草说明：本文所有"要求原文"均于 2026-10-20 从来源清单所列页面/仓库原文简摘，未用二手转述；livepowers 现状数据来自同日对仓库的只读核查（HEAD `9cd242f`）。两个拿不到更细原文的点如实标注：A1 的 README 未给"quality and security standards"的细则清单（细则以 A2/A3/A4 + C2 拼成）；Cursor 的 marketplace/publish 提交页为表单页，未抓取，提交要求以 C1/C2 文档原文为准。
