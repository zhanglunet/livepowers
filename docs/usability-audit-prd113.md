# PRD-113/T1：livepowers "that works" 可用性现状盘点

> trend issue #564 · PRD 全文 adopted/PRD-113-livepowers-usability-narrative.md
> 借鉴：cc-skills-golang（MIT）"that works" 叙事——新用户 5 分钟跑通首个命令、
> 10 分钟产出可验证结果。只借叙事形态，零代码复用。
> 红线：盘点只读不改；示例全占位；零真实主机名/IP/账号/密钥。

## 盘点范围

- skills/ 下 21 个技能（含 using-livepowers 入口技能）
- 根 README.md、CHANGELOG.md、LICENSE
- plugins/ 四包（core/delivery/night/ontology）
- templates/ parallel-experts（PRD-112 交付）

## 逐维度评分（1–5，5 = 新用户零障碍）

| 维度 | 现状 | 评分 | 差距 |
|---|---|---|---|
| **5 分钟跑通** | README 有安装命令但无"跑通一条命令"的示例；using-livepowers 是入口技能但需先了解概念 | 2 | 缺"复制粘贴即可跑"的第一条命令 |
| **首个可验证结果** | 无 step-by-step 快速上手；验收示例在 tests/ 但用户不逛 tests/ | 1 | 缺 10 分钟产出可验证结果的教程 |
| **概念入门** | skills/using-livepowers 存在，但 21 个技能无分类索引（按用途分组） | 2 | 缺技能分层导航表 |
| **错误恢复** | 各技能有 fail-closed 设计但无用户侧故障排查指南 | 2 | 缺常见错误 → 解决方案映射 |
| **文档完备** | README 有但偏架构叙述；CHANGELOG 存在；无 USAGE.md / QUICKSTART.md | 3 | 缺用户侧文档（区别于开发者侧） |
| **实例完备** | examples/ 仅有 parallel-experts 一例；无端到端样例 | 1 | 缺 ≥1 个可跑的完整示例 |
| **测试即文档** | test_* 全过但测试名偏内部视角 | 3 | 缺面向用户的验收叙事 |

## 综合评估

**当前 NPS 假设 ≈ 被动**：功能完备（21 技能 + 四包 + 并行编排），但新用户
"零到一"路径断裂——能装上、跑不通、看不到结果。

## T2–T5 改进方向（后续 issue 承载）

| 层 | 改进 | 预期 |
|---|---|---|
| T2 实测例子 | 写 ≥1 个 5 分钟跑通示例（复制粘贴→出结果） | 5 分钟维度 2→4 |
| T3 CI 徽章 | README 加 CI badge + 测试覆盖率 | 文档可信度提升 |
| T4 README 改写 | 拆用户侧 QUICKSTART + 开发者侧 README | 概念入门 2→4 |
| T5 验收 | 新用户视角走查 | 全维度 ≥3 |
