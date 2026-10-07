---
name: writing-livepowers-skills
description: Use when creating a new Livepowers skill, editing an existing one, or turning a team's recurring practice into a skill. 新建或修改 Livepowers 技能时使用。
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

```bash
python -m unittest discover -s tests -v    # 含技能结构检查：名称、描述长度、路由表覆盖
```

## 固化的类比

技能本身也是能力：被反复使用、判据稳定的技能步骤，应考虑固化为脚本（交给 `crystallize-to-system1`），技能里只保留需要判断的部分。
