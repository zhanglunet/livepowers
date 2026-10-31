---
name: <与目录名一致>
description: Use when <触发条件>... <中文一句话>
allowed-tools: Bash, Read, Write, Edit
license: MIT
metadata:
  when_not_to_use: 非 skill 编写任务不适用
  output: skill 编写规范与骨架
  compatibility: 需 Read 工具
---

# 编写 Livepowers 技能

**写技能就是对流程文档做 TDD。**没看过 Agent 在没有技能时如何失败，就不知道技能教的是不是对的东西。

## 什么值得写成技能

- 不直观、会跨项目反复用、能让其他团队受益的做法。
- **不写**：一次性解法；项目私有约定（放项目的 AGENTS.md / CLAUDE.md）；能用脚本或校验强制执行的机械约束（写成脚本，技能里只留判断）。

## RED → GREEN → REFACTOR

1. **RED：先跑基线。**设计 2–3 个压力情境（时间压力、沉没成本、"用户说这次特殊"、"模型已经答对了"），让一个没有该技能的 Agent 去做，逐字记录它跳过了什么、用了什么借口。
2. **GREEN：写最小技能。**只针对记录到的违规写规则；把借口写进"反模式"表，逐条反驳。
3. **再跑同样的情境**，确认 Agent 现在会遵守。
4. **REFACTOR：堵漏洞。**发现新的借口 → 补规则 → 重新验证。

## 格式要求

```
skills/<kebab-case-name>/SKILL.md
---
name: <与目录名一致>
description: Use when <触发条件>... <中文一句话>
---
```

- `description` 只写**何时使用**（触发条件与症状），不要概括流程——否则 Agent 会读完描述就以为自己会了，跳过正文。≤1024 字符。
- 正文：为什么 → 步骤 → 命令 → 反模式 / 红线。用表格承载判据，用代码块承载命令。
- 引用其他技能写名字（如 `acceptance-gates`），不要复制其内容。
- 不写具体组织、人员、客户、项目名称；示例用通用业务对象（订单、商机、合同、工单）。
- 新技能要加进 `using-livepowers` 的路由表和 README 的技能表。

## 验证

每个技能必须在 `tests/triggers/<name>.jsonl` 提供至少 3 条正例与 2 条反例（`{"prompt": "...", "expect": ["<name>"], "reject": ["..."]}`），并在 CI 中验证确定性打分排序。也可以运行评测脚本 `scripts/eval_triggers.py` 测量触发率与混淆表现。

```bash
python -m unittest discover -s tests -v    # 含技能结构检查与 tests/triggers/ 触发率用例集
python scripts/eval_triggers.py           # 输出所有技能的触发率与混淆评估
```


## 固化的类比

技能本身也是能力：被反复使用、判据稳定的技能步骤，应考虑固化为脚本（交给 `crystallize-to-system1`），技能里只保留需要判断的部分。

## 简洁输出规范

人类可读输出遵循三段式：**结论**（一句话，≤50 字）/ **关键信息**（≤5 条，每条 ≤30 字）/ **详情**（折叠，需要时展开）。`--json`、退出码、机器协议逐字节不动。
全量输出：`LIVEPOWERS_VERBOSE=1 <命令>`（临时）；`<LIVEPOWERS_HOME>/config.yaml` 写 `verbose: true`（持久）。
- `eval_triggers.py` 结论首行：`总体 Top-2 触发率 x%（a/b）`；关键信息：混淆最严重的 Top 5；明细表格折叠（"总计正例"行保留原文）。
- 新 skill 的 SKILL.md 必须包含"简洁输出规范"节（见 `templates/skill.md`）。
