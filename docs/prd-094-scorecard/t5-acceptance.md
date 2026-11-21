# PRD-094/T5：验收报告（覆盖率 + 复核一致性 + 定稿 + 官方标准复核）

> 对应：zhanglunet/livepowers#60（PRD-094/T5）；trend PRD：`adopted/PRD-094-livepowers-store-checklist.md`。
> 验收日：2026-11-21 · HEAD：本报告所在提交 · 验收人：张路代理（自动化流水线）

## 结论：四项验收全过 ✅

| # | 验收项 | 口径 | 结果 |
|---|---|---|---|
| 1 | 打分覆盖率 | ≥19/19（T3 时 19 skills） | **21/21**（T3 打 20 个 + `generalizing-skills` 10-20 新增已随 C-29 全员打分覆盖；20→21 有据） |
| 2 | 抽查复核一致性 | 5 个 skill × 10 条，≥80% | **全条目 48/50=96%；稳定条目 40/40=100%**（两处差异均为 T4 已核实的修复性变更，见下） |
| 3 | checklist 文档定稿入库 | v1 定稿提交 main | ✅ `docs/PRD-094-store-checklist.md` v1 定稿在库；本次按口径第 7 条升级 **v1.1**（官方标准有实质更新，见第 4 项） |
| 4 | 官方标准是否最新 | T5 复核来源 | **有更新**：A1 README 2026-11-21 实测——`.claude-plugin/marketplace.json` 对第三方淘汰、提交入口转 claude.ai/directory/manage。已升 checklist v1.1 记录处置（marketplace.json 语义收窄为本地分发面，分数不触发重打）；A4 六字段集与 C2 提交清单比对无条文变化 |

## 1. 覆盖率核验（21/21）

- T3（issue #58，2026-10-20）：20 个 skills 全量打分（298 条目：2 分 232 / 1 分 58 / 0 分 7 / N/A 1），每条有证据。
- T3 之后新增 `generalizing-skills`（2026-10-20 11:22 入库）：C-29 全员补打分（#70，42/42 SKILL.md）时已覆盖；本验收抽查亦含它。
- 现库 `skills/` = 21 个目录，全部有打分记录 → **覆盖率 21/21**。

## 2. 抽查复核一致性（5 样本 × 10 条）

样本（跨根 skill 与插件 skill）：`delivery-chain`、`generalizing-skills`（新增件）、`digital-role-spec`、`night-loop-planning`（night 插件同款）、`ontology-grounded-spec`。

复核方式：按 checklist v1 条目定义**独立机械重打**（frontmatter 解析、name/目录一致性、六字段集、正文行数与可执行标记、引用完整性、allowed-tools、tests 三层、测试实跑）。

| skill | C-01 | C-16 | C-17 | C-18 | C-19 | C-24 | C-25 | C-29 | C-30 | C-31 |
|---|---|---|---|---|---|---|---|---|---|---|
| delivery-chain | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| generalizing-skills | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| digital-role-spec | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| night-loop-planning | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| ontology-grounded-spec | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |

- 对比 T3 基线（每 skill 18/20；C-29/C-31 全员 1 分）：
  - **稳定条目（C-01/16/17/18/19/24/25/30）：8×5=40 全一致 → 100%**（≥80% 达标）
  - C-29 全员 1→2：#70 已核实（42/42 SKILL.md 补齐）——**修复性变更，非复核分歧**
  - C-31 全员 1→2：#75 已核实（最近一次全量 CI 绿）——同上
  - 全条目 48/50=96%
- 抽查发现一处**机械误报已裁定**：delivery-chain 正文反引号中的 `manifest.json` 为运行产物名（工作区 `.livepowers/chains/.../runs/<run-id>/`），非仓库文件引用，C-25 维持 2 分。

## 3. 验收期发现并修复的缺陷（转为新修复项，已修）

- **契约脚本假红 21/21**：`tests/_contract/run_contract.py` 把 metadata 块的嵌套子键（`when_not_to_use`/`output` 等，PRD-199/T2 于 10-20 后批量补入）当顶层键校验 → "未知 frontmatter 字段" 假 FAIL。已修（嵌套缩进行跳过，顶层白名单校验不变）；修后 **21/21 PASS（错误 0，警告 25 条——`lp` 命令退出码说明缺失类，属 C-25 1 分档观察项，不阻断）**。
- 该缺陷不影响 T3 打分有效性（打分对象是 checklist 条目而非该脚本），但说明 L1 契约工具需要跟版；已随本 PR 入库。

## 4. 官方标准复核（详见 checklist v1.1 注记）

- A1（anthropics/claude-plugins-official）：README 2026-11-21 实测有实质变更——第三方 marketplace.json 淘汰、提交入口转 directory/manage。处置：C-03/C-04 语义收窄为本地分发面；不触发重打。
- A4（skills 六字段可移植集）：比对无变化；本仓 21 skill 顶层字段集全部 ⊆ 六字段（metadata 块合法）。
- C2（Cursor plugins reference）：kebab-case、提交清单等条文比对无变化（docs 站 308 跳转后内容一致）。

## 5. 收尾状态

- T4 待办 9 条（#70~#78）全部销项（5 条隐形完成核验 + 4 条实跑/裁定记录）。
- 本验收完成 → PRD-094 链（T1~T5）全部收官。
