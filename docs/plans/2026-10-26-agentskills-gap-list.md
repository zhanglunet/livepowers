# PRD-199/T1：agentskills 规范差距清单（21 skills frontmatter 逐项对照）

> trend issue #995。对应 PRD-199（中央仓库 zhanglunet/trend，`adopted/PRD-199-livepowers-agentskills-alignment.md`）。
> 状态：草案，供评审。T1 只产出差距清单，不改任何 SKILL.md；批量对齐是 T2（#996），校验进发布门是 T3（#997），四工具可发现性实测是 T4（#998）。
> 现状基线：2026-10-26，livepowers main `7fc9e8e`。计数口径：根 `skills/` 21 个 skill 为准；`plugins/*/skills/` 是逐字节同步拷贝，不重复计数（同步由既有测试保证）。
> 对齐规范：Agent Skills 开放规范（agentskills.io/specification，2025-12 发布为开放标准；本文查证日期 2026-10-26）。借鉴声明：该规范协议未核实，本文只借鉴其规范形态（字段与约束），未复用其代码或原文表述，下表为对照转述。

## 1. 对照口径

规范定义的 frontmatter 字段共 6 个：

| 字段 | 必填 | 约束（转述） |
|---|---|---|
| `name` | 是 | ≤64 字符；仅小写字母、数字、连字符；不得以连字符开头或结尾；不得有连续连字符；须与父目录名一致 |
| `description` | 是 | 1–1024 字符，非空；写清「做什么 + 何时用」；配套指南建议同时写明不适用场景，帮助 agent 排除误触发 |
| `license` | 否 | 许可证名称，或指向随 skill 打包的许可证文件 |
| `compatibility` | 否 | ≤500 字符；环境要求（目标产品、所需系统包、网络访问等），多数 skill 不需要 |
| `metadata` | 否 | 字符串到字符串的任意键值映射（如 author、version、tags） |
| `allowed-tools` | 否（实验性） | 空格分隔的字符串，列出该 skill 预批准可用的工具；各工具支持程度不一 |

PRD 点名的五个对照维度是 `name`、`description`（触发描述）、适用场景、输入、输出。其中规范**没有**为「适用场景 / 输入 / 输出」设独立字段：适用场景由 `description` 承载；输入与输出规范未定义专门字段。本清单的判定方式：

- **适用场景**：看 `description` 是否写明触发场景与边界（只有场景、没有不适用边界的，记「部分对齐」）。
- **输入 / 输出**：看 `description` 是否声明、或正文是否有固定落点章节（散见正文叙述的，记「缺失（无结构化落点）」）；承载方式留待 T2 统一决定（见 §5）。

判定词汇：**已对齐** / **部分对齐** / **缺失** / **形态不符**。

## 2. 现状总览（量化）

| 维度 | 结果 | 说明 |
|---|---|---|
| skill 总数 | 21 | PRD 写「19+」，以仓库现状为准 |
| `name` | 已对齐 21/21 | 全部与目录名一致，长度 12–30 字符，无连字符首尾/连续问题 |
| `description` 存在性与长度 | 已对齐 21/21 | 143–344 字符，全部以 `Use when` 开头（触发句）+ 中文一句；无一条超 1024 上限 |
| 适用场景 | 部分对齐 21/21 | 场景都写在 description 内，但 0 条写明不适用场景（否定触发） |
| 输入 | 缺失 21/21 | description 与正文均无结构化输入声明 |
| 输出 | 缺失 20/21、部分对齐 1/21 | 仅 `ontology-grounded-spec` 正文有「输出物」章节；其余产物只散见正文叙述 |
| `allowed-tools` | 形态不符 20/21、缺失 1/21 | 现状为逗号分隔（`Bash, Read`），规范为空格分隔字符串；`delivery-chain` 整项缺失 |
| `license` | 缺失 21/21 | 仓库根与各插件有 MIT 许可，但 skill 级 frontmatter 未声明 |
| `compatibility` | 缺失 21/21 | 环境要求（如需 Bash、需数据库连接）未在 frontmatter 声明 |
| `metadata` | 缺失 21/21 | 版本号现由插件级 `plugin.json` 承载（如 livepowers-core 1.6.0），skill 级无 version/author/tags |
| 模板 | 同步缺失 | `templates/skill.md` 的 frontmatter 骨架也只有 `name` + `description` 两项，新 skill 会继续复制上述缺口 |

现有 frontmatter 惯例（长处，T2 应保留）：必填两项全齐；description 统一「英文触发句 + 中文一句」双语形态，规范不限语言，不视为不符；`skills.sh.json` 的 groupings 与 5 插件划分一致，发现面在包一级是完整的，缺口集中在 skill 一级字段。

## 3. 逐 skill 清单

`license` / `compatibility` / `metadata` 三项为全仓统一缺失（见 §2），逐行不重复标注；下表只记个体差异。`allowed-tools` 一列：除注明外均为「形态不符（逗号分隔）」。

| skill | name | description（字符数） | 适用场景 | 输入 | 输出 | allowed-tools | 个体备注 |
|---|---|---|---|---|---|---|---|
| acceptance-gates | 已对齐 | 已对齐（251） | 部分对齐 | 缺失 | 缺失 | 形态不符 | description 含引号文本，T2 若改为引号包裹写法需注意转义 |
| agent-harness-for-tools | 已对齐 | 已对齐（211） | 部分对齐 | 缺失 | 缺失 | 形态不符 | — |
| auditable-agent-comms | 已对齐 | 已对齐（210） | 部分对齐 | 缺失 | 缺失 | 形态不符 | — |
| crystallize-to-system1 | 已对齐 | 已对齐（211） | 部分对齐 | 缺失 | 缺失 | 形态不符 | 与 nightly-crystallization-review 场景相邻，边界靠正文区分（见 §4-4） |
| delivery-chain | 已对齐 | 已对齐（344） | 部分对齐 | 缺失 | 缺失 | **缺失** | 编排型 skill（串联五阶段）；补齐还是登记例外，见 §5 例外草案 EX-02 |
| digital-role-spec | 已对齐 | 已对齐（221） | 部分对齐 | 缺失 | 缺失 | 形态不符 | 工具面含 Write（`Read, Write`），与其余只读型不同 |
| env-scan-ontology | 已对齐 | 已对齐（206） | 部分对齐 | 缺失 | 缺失 | 形态不符 | 有真实环境要求（数据库/接口访问），是 compatibility 的首要候选 |
| explore-with-evidence | 已对齐 | 已对齐（229） | 部分对齐 | 缺失 | 缺失 | 形态不符 | 与 system1-first 相邻（未命中才探索），边界靠正文区分 |
| fde-delivery | 已对齐 | 已对齐（217） | 部分对齐 | 缺失 | 缺失 | 形态不符 | description 含内部术语，跨工具发现时可读性待 T2 评估（不属字段差距，仅记录） |
| generalizing-skills | 已对齐 | 已对齐（334） | 部分对齐 | 缺失 | 缺失 | 形态不符 | — |
| living-surface | 已对齐 | 已对齐（320） | 部分对齐 | 缺失 | 缺失 | 形态不符 | — |
| night-loop-planning | 已对齐 | 已对齐（207） | 部分对齐 | 缺失 | 缺失 | 形态不符 | 工具面最宽（含 Task 子代理调度） |
| nightly-crystallization-review | 已对齐 | 已对齐（160） | 部分对齐 | 缺失 | 缺失 | 形态不符 | 与 crystallize-to-system1 相邻，见上 |
| oltp-action-safety | 已对齐 | 已对齐（217） | 部分对齐 | 缺失 | 缺失 | 形态不符 | 安全前置型 skill，触发面宽系有意（与 using-livepowers 同类，见 EX-01 说明） |
| ontology-evolution | 已对齐 | 已对齐（236） | 部分对齐 | 缺失 | 缺失 | 形态不符 | — |
| ontology-grounded-spec | 已对齐 | 已对齐（196） | 部分对齐 | 缺失 | **部分对齐** | 形态不符 | 正文有「输出物」章节，是全仓唯一的输出落点，可作 T2 输出章节的形态参考 |
| outcome-ledger | 已对齐 | 已对齐（188） | 部分对齐 | 缺失 | 缺失 | 形态不符 | — |
| system1-first | 已对齐 | 已对齐（169） | 部分对齐 | 缺失 | 缺失 | 形态不符 | 与 explore-with-evidence 相邻，见上 |
| takeover-handling | 已对齐 | 已对齐（274） | 部分对齐 | 缺失 | 缺失 | 形态不符 | — |
| using-livepowers | 已对齐 | 已对齐（266） | 部分对齐 | 缺失 | 缺失 | 形态不符 | 入口/路由 skill，宽触发为设计意图，见例外草案 EX-01 |
| writing-livepowers-skills | 已对齐 | 已对齐（143） | 部分对齐 | 缺失 | 缺失 | 形态不符 | 工具面含 Edit；T2 改模板时须与本 skill 的写作规范同步 |

## 4. 共性缺口汇总

1. **可选字段整片空白，且模板在持续复制缺口。** `license` / `compatibility` / `metadata` 21/21 全缺：跨工具按 frontmatter 做发现时，拿不到许可证、环境要求与版本信息；`templates/skill.md` 骨架同样只有两项，不先改模板，T2 补完存量、新 skill 还会再缺一轮。
2. **输入 / 输出无声明、无统一落点。** description 只回答「何时用」，不回答「吃什么、产什么」；正文里产物说明散见叙述（仅 1 个 skill 有固定章节）。跨工具编排按 frontmatter 预判 skill 输入输出时无据可依。规范本身没给这两项设字段，承载方式需要本仓自己定标准（见 §5 第 4 步），这也是本 PRD 作为「标准对齐四件套共用口径源头」要输出的关键决策。
3. **`allowed-tools` 形态与覆盖不一致。** 规范为空间分隔字符串，现状 20 个为逗号分隔、1 个缺失。分隔符差异是否影响各工具解析，静态对照无法定论，必须与 T4 的四工具实测联动核对后再全量改，避免改出新的不兼容。
4. **不适用场景（否定触发）全缺。** 0/21 在 description 写明边界；相邻 skill 对（system1-first ↔ explore-with-evidence、crystallize-to-system1 ↔ nightly-crystallization-review）的区分靠正文。现有缓解是触发测试（`tests/triggers/<name>.jsonl` 已要求 ≥3 正例 ≥2 反例），T2 补否定触发时应与反例集对齐，避免两处口径打架。
5. **版本信息只在插件一级。** skill 级无 version，单个 skill 修订时跨工具无从判断新旧；是否借 `metadata.version` 补齐、与 `plugin.json` 版本如何联动，T2 需定规则（只定必填最小集，其余留扩展，避免口径过重）。

## 5. 例外清单草案（待评审定稿）

| 编号 | 对象 | 例外内容 | 理由 |
|---|---|---|---|
| EX-199-01 | `using-livepowers`（及同类的 `oltp-action-safety`） | description 保持宽触发，不按相邻 skill 的方式收窄 | 入口路由 / 安全前置的职责就是「先于一切触发」，收窄会破坏路由与安全门语义；其误触发成本由正文的分流规则承担 |
| EX-199-02 | `delivery-chain` | `allowed-tools` 可不声明，工具面由被编排的各阶段 skill 各自声明 | 编排型 skill 本身不直接执行工具；若评审认为声明更利于发现，可改为 T2 直接补齐并撤销本例外 |
| EX-199-03 | 全部 | description 保留「英文触发句 + 中文一句」双语形态 | 规范对 description 语言无限制；双语是本仓既有惯例，兼顾跨工具发现与中文用户可读性，不视为形态不符 |

例外登记的落位建议复用既有豁免台账惯例（`docs/engineering-checklist/exemptions.md` 的 EX- 编号规则），不另立系统；是否复用请评审定。

## 6. T2 批量对齐建议顺序

1. **先改模板**：`templates/skill.md`（及 tooling 插件内拷贝）补齐可选字段骨架与 `allowed-tools` 空格分隔写法，止住新 skill 复制缺口；同步 `writing-livepowers-skills` 的相关表述。
2. **批量补可选字段**：`license` 全量补（指向仓库 MIT）；`metadata` 只补最小集（version/author，规则先行）；`compatibility` 只给有真实环境要求的 skill 填（如 env-scan-ontology），其余留空不硬填。
3. **`allowed-tools` 统一形态**：先小样本核对 Claude / Cursor / Codex / Pi 四工具的实际解析（与 T4 联动），确认分隔符口径后再全量改；同时处理 delivery-chain（补齐或走 EX-199-02）。
4. **description 增补**：先定输入/输出承载方式（建议二选一并全仓统一：description 尾句声明，或正文固定「输入 / 输出」章节——后者已有 ontology-grounded-spec 的「输出物」先例）；再为相邻易混 skill 补不适用场景一句。此步改动触发词，须保留旧触发词别名（PRD 风险项），并与 `tests/triggers` 反例集对齐。
5. **按插件分批落地**：core → ontology → delivery → night → tooling，每批跑全量测试（含触发测试）确认不回归，再进下一批；根 `skills/` 与插件拷贝的同步照旧由既有测试守住。

## 7. 范围与非目标

- 本清单只对照 frontmatter（及输入/输出在正文的落点有无）；不评估正文质量，不动任何 SKILL.md。
- 不写校验脚本（T3）、不做四工具实测（T4）；`allowed-tools` 分隔符的最终口径以 T4 实测为准，本清单只登记形态差异。
- 对齐版本写明：Agent Skills 开放规范，2025-12 发布版（查证 2026-10-26）。规范仍在演进，后续若规范字段变更，本清单需按新版本重跑对照。
