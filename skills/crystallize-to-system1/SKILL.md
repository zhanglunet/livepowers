---
name: crystallize-to-system1
description: Use when an intent has been explored successfully several times, when the user says "do it this way from now on", or when the nightly review has selected a crystallization candidate. 把探索成功的路径固化为 System 1 能力包时使用。
---

# 固化到 System 1

固化让 Agent 在这条能力上从"探索者"转为"执行者"，把昂贵的推理留给真正需要它的地方。

## 第一步：过门禁（F-V-S-R + 盈亏平衡）

```bash
lp score --freq <每月次数> --verifiable 0|1|2 --stability 0|1|2 [--writes-state] \
  --c2 <S2单次成本> --c1 <S1单次成本> --K <固化成本> --M <维护成本> --p <S2成功率> --h <失败兜底成本>
# 建议固化 exit 0；否则 exit 3
```

- **F 频率**：<4 次/月 = 0；4–19 = 1；≥20 = 2
- **V 可验证**：0 = 无法自动核对；1 = 有样例可核对；2 = 有断言 / 对账可全自动核对。**V=0 一票否决。**
- **S 稳定**：0 = 口径或接口常变；1 = 偶尔变；2 = 稳定
- **R 风险**：写生产状态时加 `--writes-state`（收益最大，测试要求最严）

合成分 = F×2 + V×1.5 + S×1 + R×1，满分 10（`lp score` 会打印分项）。

盈亏平衡：`n* = (K + M) / (c2′ − c1)`，其中 `c2′ = c2/p + (1−p)·h/p`。**成功率越低，固化越划算；夜间空闲算力能摊薄 K；口径常变会抬高 M。**评分 ≥5 且预计调用次数 > n* 才继续。把输出贴进变更说明。

## 第二步：测试先于实现（TDD）

1. 从规格与 `explorations/` 取出验收样例写成测试（RED：先确认会失败）。
2. OLTP 能力加入 `oltp-action-safety` 要求的八项测试。
3. 写实现（GREEN），再精简（REFACTOR）。

## 第三步：实现规范

- **确定性**：关键计算和事务不得调用大模型。需要语义理解的部分留在 System 2 或 Skill 里。
- **参数化**：把探索中写死的值（地区、周期、阈值）提成参数，取值范围来自本体。
- **类型化接口**：明确的参数与退出码；结构化输出；错误信息写成"下一步该怎么修"，让调用它的 Agent 能自我纠正。
- **最小化**：一个能力做一件事。不要把整段探索对话存成 Skill。

## 第四步：组装能力包

能力不是一段孤立的代码。用 `templates/capability-package.yaml` 把以下内容绑定在一起，任何一项变化都能定位影响范围：

- 本体版本与引用的规则 ID
- 规格（含验收样例）
- 实现（工具 / 查询 / 工作流）与入口
- Skill（何时用、何时不要用、需要什么证据、何时停止或升级）
- 界面或输出组件（如有）
- 评测集（正常 / 边界 / 错误 / 保留测试集）
- 依赖、维护主体、刷新或运行计划
- 适用范围（领域共性 / 客户扩展 / 运行配置）

## 第五步：独立验收

走 `acceptance-gates` 的四道门：形式检查 → 契约测试 → 独立对抗审查 → 人工采纳。用真实样例对比 System 2 历史结果与 System 1 新结果，差异须解释。OLTP 能力需业务负责人签字。

## 第六步：注册与发布

```bash
lp registry add --name "<名称>" --kind cli|sql|script|skill|view|mcp|workflow \
  --intents "<意图1>,<意图2>" --entry "<调用方式>" \
  --inputs "<...>" --outputs "<...>" --preconditions "<...>" --permissions "<...>" \
  [--writes-state] --tests "<测试命令>" --version 1.0.0 --owner <维护主体> \
  --ontology-version <版本> --package <能力包清单路径> \
  --generated-by <生成者> --accepted-by <采纳人>   # 两者必须不同
```

- 意图关键字覆盖用户常见说法（中英文都写），否则 `system1-first` 找不到它。
- 夜间生成、等早晨验收的产物，用 `lp pending add` 登记（见 `nightly-crystallization-review`），不要直接注册。
- **在产品内发布，不必整版升级。**探索态对终端用户不可见；通过验收后以新工具、新 Skill、新流程或新看板的形式上线。
- 被业务 Agent 调用的能力，转 `agent-harness-for-tools` 补工具卡与剧本。

## 版本与退役

- 修改已注册能力 = 发新版本：`lp registry add --id <新id> --version 2.0.0 --supersedes <旧id> ...`。旧版本自动退役并记录 `superseded_by`，注册表仍能查到它供调用方迁移；同一 id 不能重复注册。
- 口径变化或连续失败 → `lp registry retire <id> --reason ...`，回到 System 2。
- 已提交的业务动作通过有记录的补偿行动纠正；代码回退只控制后续执行。

## 反模式

- 模型答对一次就注册。
- 固化代码里藏着一次 LLM 调用。
- 没有测试的"固化"——那只是把概率性换了个位置。
- 生成者自己签字验收。
