# PRD-047/T2：插件包整理与上架前置检查报告

> 对应 trend #223；输入为 T1 方案 `docs/plans/2026-10-17-skillsh-plan.md` §4 检查清单。
> 结论：5 项全过；修了 1 个包装层问题；无阻塞性遗留问题。
>
> **重要修正（2026-10-17 浏览器实测）**：skills.sh（The Agent Skills Directory，Vercel 运营）
> **没有传统提交流程**——无提交表单、无需提 PR、无投稿邮箱、无人工审核。
> 收录靠自动索引：GitHub 公开仓库含 SKILL.md，当用户跑 `npx skills add <owner>/<repo>`
> 且开启匿名 telemetry 时，ingestion pipeline 自动索引；排名按去重安装量 telemetry；
> 合作方安全审计结果公开在详情页，仅全部审计挂掉才移除；免费、无需账号。
> 因此 T1 方案里的"提交流程验证"改为 **"无提交动作，靠安装 telemetry 自动收录"**，
> 上架前置条件相应改为：`npx skills add zhanglunet/livepowers` 可安装、
> SKILL.md frontmatter（含 name/description）规范、README 齐全、可选加 `skills.sh.json`。
> `vercel-labs/skills` 仓库只用于 hidden/redirect 管理，不是提交入口。

## 1. 校准后的 5 插件元数据（按实际 skill 内容写，非占位）

| 插件 | 一句话描述（校准版） | 版本 | 许可证 | skills |
|---|---|---|---|---|
| livepowers-core | 核心工作流：System 1 优先查表、带证据探索、固化成可测试能力（含 using-livepowers 路由器） | 1.5.0 | MIT | system1-first、explore-with-evidence、crystallize-to-system1、ontology-grounded-spec、using-livepowers |
| livepowers-ontology | 本体工作：环境扫描、知识演进、本体变更提案、数字角色规约与活展示面 | 1.5.0 | MIT | env-scan-ontology、ontology-evolution、digital-role-spec、living-surface |
| livepowers-delivery | 交付与安全：独立验收门、FDE 现场交付、结果账本、操作安全、可审计通信、异常接管 | 1.5.0 | MIT | acceptance-gates、fde-delivery、outcome-ledger、oltp-action-safety、auditable-agent-comms、takeover-handling |
| livepowers-night | 夜间循环：夜间作业规划与晨间固化评审（含 /lp-nightly、/lp-morning 命令） | 1.5.0 | MIT | night-loop-planning、nightly-crystallization-review |
| livepowers-tooling | 工具：agent harness 封装指南与 skill 编写指南 | 1.5.0 | MIT | agent-harness-for-tools、writing-livepowers-skills |

> 版本口径：5 个 `plugin.json` 的 version 均为 1.5.0，与仓库 `package.json` 一致。
> 纠正 T1 文档 §3 的一处不准确："tooling（含 gen_harness）"——`scripts/gen_harness.py`
> 实际位于仓库根 `scripts/` 下，是仓库级工具，不在 livepowers-tooling 插件包内。

## 2. 检查清单逐项结果

- [x] **5 个插件目录结构完整**：`plugins/livepowers-*/` 均含 `skills/`（各 skill 有 SKILL.md，共 19 个）、`.claude-plugin/plugin.json`、`README.md`、`LICENSE`，以及 P1-1 修复时打进的运行时资产（core：scripts/lp.py、templates×3、commands/lp-route.md、hooks/；night：templates/job-contract.json、commands×2；ontology：templates×3；tooling：templates/tool-card.md；delivery：无外部资产依赖）。
- [x] **每个插件 README 含安装说明**：5 个 README 均有 `/plugin marketplace add` + `/plugin install <name>@livepowers-marketplace`，外加依赖与推荐安装组合说明。
- [x] **版本号与仓库 release 一致**：5× `plugin.json` version = 1.5.0 = `package.json` version；且与 `.claude-plugin/marketplace.json` 各条目一致。
- [x] **许可证声明清晰**：5× `plugin.json` 的 `license: MIT`，5× `LICENSE` 文件为 MIT 全文。
- [x] **无损坏链接/缺失引用**：全插件 md 文件的相对链接逐条解析，`${CLAUDE_PLUGIN_ROOT}/…` 与 `templates/…` 引用逐条核对——仅发现 1 处（见 §3，已修）。

## 3. 修复的问题（1 个，均为包装层）

1. `plugins/livepowers-tooling/skills/writing-livepowers-skills/SKILL.md` 提到 `scripts/eval_triggers.py`，
   但该脚本未打进插件包。核查：它是仓库级开发工具（依赖仓库根 `tests/triggers/` 用例集与完整目录结构，
   单插件内跑不起来），不适合打包。修复：在 `plugins/livepowers-tooling/README.md` 增加说明，
   明确其为"仓库级开发工具，需在完整仓库中使用，不在单插件安装范围内"。skill 内容未动。

## 4. 遗留问题

无阻塞性遗留。两点备注（非阻塞）：

- `scripts/eval_triggers.py` 等仓库级开发脚本天然不在插件包内——这是设计使然（插件包只含 agent 运行时资产），
  已在 tooling README 写明。
- skills.sh 实测结论（见文首）：无提交流程、无人工审核，收录靠 `npx skills add` 的安装 telemetry
  自动索引。本 T2 未做、也无需做任何"提交"动作；"上架"已转化为"可被索引"的准备状态（见 §5）。

## 5. skills.sh.json 评估与提案

- **要不要加**：建议加。livepowers 有 19 个 skills，默认按安装量排序的列表不好扫；
  按 5 个插件主题分组（Core / Ontology / Delivery / Night / Tooling）正是官方文档写的典型用法。
  成本为零风险：文件只影响 skills.sh 上的展示，不影响 CLI 安装、不改 SKILL.md；
  格式无效或缺失时自动回退默认列表。
- **本 PR 已附提案文件**：仓库根 `skills.sh.json`（5 个分组，19 个 skill 名与 `skills/` 目录逐一核对过；
  slug 取目录名/skill 名，匹配不区分大小写、未知名会被忽略，所以即使索引后的 slug 有出入也不会坏事）。
- **生效条件**：需有人跑过 `npx skills add zhanglunet/livepowers`（telemetry 开启）后，
  pipeline 在后台读取默认分支的该文件；页面有缓存，变更不会立刻显示。用户拍板合并后，
  自己跑一次安装即可触发收录。
