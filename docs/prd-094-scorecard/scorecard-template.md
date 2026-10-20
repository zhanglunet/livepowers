# PRD-094/T2：打分表模板（checklist v1 定稿配套）

> 对应：zhanglunet/livepowers#57（PRD-094/T2）；条目与口径以《PRD-094/T1 官方插件收录标准反向 checklist v1（定稿）》为准，本模板不另立标准。
> 配套文件：`scorecard-template.csv`（同一数据模型的长表版，一行 = 一个对象 × 一个条目，与本文第三节登记表同构）、`汇总公式说明.md`（公式与算例）。
> 标准版本标（定稿汇总口径第 7 条）：来源 A1 anthropics/claude-plugins-official README、A2/A3/A4 Claude Code 官方文档、C1/C2 Cursor 官方文档、L1 仓库 docs/SKILL-TEST-SPEC.md，抓取日期 2026-10-20。

## 填写信息

| 项 | 内容 |
|---|---|
| 打分日期 |  |
| 打分人 |  |
| checklist 版本 | v1 定稿（2026-10-20） |
| 仓库 HEAD |  |

## 填写规则（速览，细则见《汇总公式说明》）

- 每格填 0 / 1 / 2，或 N/A（不适用，必须在备注或登记表写明理由，N/A 不计入分母）。
- 每条打分必须在第三节登记表附证据（文件路径 + 字段/行号，或命令输出存档位置）；无证据视为未打分。
- 存疑项在登记表"待复核"列标"是"，进 T5 抽查池。
- 得 1 分 / 0 分的条目全部进 T4 待办清单（0 分优先），在第四节登记。
- 全部条目（含 C-04、C-15、C-29、C-30、C-31）照常打分留证据并计入分母；达标率按《汇总公式说明》的单一算法计算（Q3/Q6/Q7/Q8 已于 2026-10-20 定案，见定稿决策记录）。

## 一、skill 级矩阵（20 个 skill × 10 条）

条目图例：

- C-01：skill 独立目录含 SKILL.md
- C-16：frontmatter 存在且可解析
- C-17：skill name 规范（kebab-case、与目录名一致）
- C-18：description 写明做什么+何时用
- C-19：frontmatter 六字段可移植集（Q2 严判）
- C-24：SKILL.md 正文简洁可执行
- C-25：引用完整性
- C-29：allowed-tools 与实际需要匹配（正式计分，见定稿决策记录 Q7）
- C-30：独立验收测试三层齐备（正式计分，见定稿决策记录 Q8）
- C-31：示例可复现、反例不误触发（正式计分，见定稿决策记录 Q8）

| 对象 | C-01 | C-16 | C-17 | C-18 | C-19 | C-24 | C-25 | C-29 | C-30 | C-31 | 得分率 | 达标率 | 达标判定（Q5） |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| acceptance-gates |  |  |  |  |  |  |  |  |  |  |  |  |  |
| agent-harness-for-tools |  |  |  |  |  |  |  |  |  |  |  |  |  |
| auditable-agent-comms |  |  |  |  |  |  |  |  |  |  |  |  |  |
| crystallize-to-system1 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| digital-role-spec |  |  |  |  |  |  |  |  |  |  |  |  |  |
| env-scan-ontology |  |  |  |  |  |  |  |  |  |  |  |  |  |
| explore-with-evidence |  |  |  |  |  |  |  |  |  |  |  |  |  |
| fde-delivery |  |  |  |  |  |  |  |  |  |  |  |  |  |
| generalizing-skills |  |  |  |  |  |  |  |  |  |  |  |  |  |
| living-surface |  |  |  |  |  |  |  |  |  |  |  |  |  |
| night-loop-planning |  |  |  |  |  |  |  |  |  |  |  |  |  |
| nightly-crystallization-review |  |  |  |  |  |  |  |  |  |  |  |  |  |
| oltp-action-safety |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ontology-evolution |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ontology-grounded-spec |  |  |  |  |  |  |  |  |  |  |  |  |  |
| outcome-ledger |  |  |  |  |  |  |  |  |  |  |  |  |  |
| system1-first |  |  |  |  |  |  |  |  |  |  |  |  |  |
| takeover-handling |  |  |  |  |  |  |  |  |  |  |  |  |  |
| using-livepowers |  |  |  |  |  |  |  |  |  |  |  |  |  |
| writing-livepowers-skills |  |  |  |  |  |  |  |  |  |  |  |  |  |

## 二、插件级矩阵（6 个插件对象 × 15 条）

对象名按 `plugins/` 目录与仓库根填写；打分时以各插件 `plugin.json` 的 name 为准。

条目图例：

- C-02：插件标准布局
- C-06：plugin.json name 规范
- C-07：条目名与 manifest 名一致
- C-09：version 语义化且两处一致
- C-10：description 说清用途
- C-11：author 完整
- C-12：license SPDX 且与 LICENSE 文件一致
- C-13：keywords 供发现
- C-14：homepage/repository 合法 URL
- C-15：目录展示字段 icon/logo（正式计分，见定稿决策记录 Q6）
- C-20：插件 README 写明用法与配置
- C-22：claude plugin validate 通过
- C-23：本地实测安装有记录
- C-27：凭据不入库
- C-28：manifest 路径相对且不逃逸

| 对象 | C-02 | C-06 | C-07 | C-09 | C-10 | C-11 | C-12 | C-13 | C-14 | C-15 | C-20 | C-22 | C-23 | C-27 | C-28 | 得分率 | 达标率 | 达标判定（Q5） |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 根插件（livepowers） |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 主题插件 core |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 主题插件 ontology |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 主题插件 delivery |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 主题插件 night |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 主题插件 tooling |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |

## 三、证据登记表（与 csv 长表同构，逐条登记）

| 层级 | 对象 | 条目 | 分数 | 证据链接/位置 | 待复核 | 备注 |
|---|---|---|---|---|---|---|
| skill | using-livepowers | C-17 | 2 | 【示例行，正式打分时删除】skills/using-livepowers/SKILL.md frontmatter name 字段 = 目录名 | 否 | 示例 |
|  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |

## 四、待办移交登记（T4 接口：1 分与 0 分条目，0 分在前）

| 对象 | 条目 | 分数 | 问题一句话 | 影响×成本初判 |
|---|---|---|---|---|
|  |  |  |  |  |

## 五、仓库级清单（全仓只打一次）

| 条目 | 名称 | 分数 | 证据链接/位置 | 备注 |
|---|---|---|---|---|
| C-03 | .claude-plugin/marketplace.json 存在且合法 |  |  |  |
| C-04 | Cursor 侧 marketplace.json 齐备 |  |  | 正式计分，见定稿决策记录 Q3 |
| C-05 | marketplace 命名不冒用官方保留名 |  |  |  |
| C-08 | 已发布插件名不可变（改名配 renames） |  |  |  |
| C-21 | marketplace 条目展示信息完整 |  |  |  |
| C-26 | 开源与审核前提（仓库公开、根 LICENSE） |  |  |  |
| C-22 | validate 仓库根整体运行 |  |  | 双层适用：插件级已逐插件打分，此行为仓库整体核查 |
| C-27 | 全仓凭据模式扫描 |  |  | 双层适用：插件级已逐插件打分，此行为仓库整体核查 |

## 六、汇总结果（三层分开报，Q4 口径，不折总分）

| 层级 | 对象 | 得分率 | 达标率 | 达标判定（Q5） |
|---|---|---|---|---|
| skill | （逐个列，20 行） |  |  |  |
| 插件 | （逐个列，6 行） |  |  |  |
| 仓库 | 仓库整体 |  |  |  |
