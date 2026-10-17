# PRD-047/T1：livepowers 上架 skills.sh 方案（草稿）

> 状态：草稿，待确认后进 T2（插件包整理）
> 前置：PRD-003 T1（#31）+ T2（#32）已合并，5 个插件已按官方市场格式备好

## 1. skills.sh 提交流程（待 T1 确认前实测）

> 以下为按公开信息整理的初版，T2 动手前需实测验证每一步。

1. **入口**：skills.sh 是 skill 包的聚合目录站（text-to-cad 在列）。提交方式通常为 GitHub 仓库提 PR
  （新增条目文件）或站内表单——T2 开工前先打开 skills.sh 确认当前流程并截图留档。
2. **审核**：关注审核标准（skill 质量、文档完整度、许可证声明）。
3. **生效**：审核通过后条目上线，可被检索。

## 2. 与官方 marketplace.json 的差异核对表

| 检查项 | 官方 market 格式（PRD-003 已有） | skills.sh 要求（待实测） | 差异处理 |
|---|---|---|---|
| $schema | `https://anthropic.com/claude-code/marketplace.schema.json` | 待确认 | 有差异则补适配文件 |
| 插件元数据 | name/description/version | 待确认 | 缺字段则补 |
| 许可证声明 | Apache-2.0/MIT（livepowers 仓库已定） | 待确认 | 按要求格式声明 |
| 安装方式 | 一键安装命令 | 待确认 | 与 T4 冷启动验证对齐 |

## 3. 五个插件的元数据（初版，T2 校准）

| 插件 | 一句话描述 | 版本口径 | 备注 |
|---|---|---|---|
| livepowers-core | 核心能力：通用执行与编排 | 跟仓库 release 对齐 | T2 核对 |
| livepowers-ontology | 本体/知识相关 skills | 同上 | T2 核对 |
| livepowers-delivery | 交付流水线 skills | 同上 | T2 核对 |
| livepowers-night | 夜间/定时任务 skills | 同上 | T2 核对 |
| livepowers-tooling | 工具链 skills（含 gen_harness） | 同上 | T2 核对 |

> 版本号、描述文案以 T2 实际盘点 `plugins/livepowers-*/` 目录为准，本表为占位。

## 4. 上架前置条件检查清单（T2 执行）

- [ ] 5 个插件目录存在且结构完整（SKILL.md + scripts/ + references/）
- [ ] 每个插件有独立 README（含安装说明）
- [ ] 版本号与仓库 release 一致
- [ ] 许可证声明清晰
- [ ] 无损坏链接/缺失引用

## 5. 冷启动验证计划（T4）

- 找一个没接触过本项目的 agent，按 skills.sh 的安装方式安装任一插件。
- 验证：skill 可被触发 → 正确执行 → 输出符合 PRD-046 规范（如已落地）。
- 记录问题并修复；安装链路无人工干预才算过。

## 6. 下一步

确认本方案后，T2（#223）实测 skills.sh 提交流程并整理 5 个插件包。
