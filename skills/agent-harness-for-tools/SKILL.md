---
name: agent-harness-for-tools
description: Use when CLIs / MCP tools / APIs already exist but business agents use them unreliably, when a weaker or different model must take over a workflow, or right after a model upgrade lands. 接口已有但 Agent 用不稳、或要换模型时使用。
---

# 用工具办事的 Harness（Agent Harness）

- **Coding Harness（造工具）**：约束 Agent 生成确定性代码，见 `crystallize-to-system1`。
- **Agent Harness（用工具办事）**：约束 Agent 使用已有工具完成业务。本技能。

很多系统已有大量 CLI / MCP / API，却缺后者，于是强模型能办成、弱模型十次只成七八次。

## 产出一：工具卡（每个工具一张）

用 `templates/tool-card.md`：

- 用途一句话；**何时用 / 何时不要用**（后者更重要）
- 输入参数（类型、取值来源于哪个本体对象）、输出结构
- 前置条件、权限、副作用（写状态？发通知？可撤销？）
- 常见错误 → 下一步动作
- 一个最小调用示例

## 产出二：业务剧本（每个高频业务一份）

写成有决策点的步骤，不是一条固定路线：

```
剧本：转交逾期重点商机
目标：...（引用规格编号与契约版本）
步骤：
  1. crm opp list --filter "key=true,last_followup_days>30"   → 候选
  2. 对每个候选：crm opp get <id> 确认 status=open（前置条件）
     决策点：owner 已离职 → 转剧本《离职交接》，本剧本不处理
  3. crm org manager --region <r>   → 区域主管
  4. [确认点] 汇总清单给用户确认（写操作前必须）
  5. crm opp transfer <id> --to <mgr> --reason <..> --idempotency-key <..>
  6. 失败：409 冲突 → 重新读取后重试一次；403 → 停止并报告；超时 → 先查执行状态再决定是否重试
证据：每步写入 lp evidence；保留工具回执
```

## 产出三：硬约束（在 Harness 里执行，不写在提示里祈祷）

- 写操作前的确认点与幂等键；
- 按安全、权限设置的强制决策点：Agent 可以动态调整路线，但不能跳过硬约束；
- 调用次数、Token、时长上限，超限熔断。

能用脚本检查的约束就写成脚本（如调用前的前置条件校验 CLI）。**约束力度与动作风险成正比**，不要一刀切。

## 验证

用目标模型（尤其是较弱或自有模型）把每份剧本的验收样例跑 10 次，成功率应 ≥95%。达不到时优先：把决策点前的判断固化成 CLI（让模型少做判断），而不是写更长的提示。

## 模型变化时

Harness 与模型是匹配的：在一个模型上调好的 Harness，换到另一个模型上效果可能下降。

1. **换模型就重跑基准**；把通过的模型写进能力的 `--validated-model`，`lp registry review --current-model <新模型>` 会列出未复验的 Skill 类能力。
2. **每次模型升级做一次消融**：去掉某条 Harness 约束或某段剧本后，是否仍达标？仍达标就"去 Harness 化"——删掉它，减少维护成本。这与"去固化"对称：能力和约束都应随环境增减。
3. 固定一组**金丝雀样例**，夜间跑，检测模型的隐性降质（`nightly-crystallization-review`）。

## 与固化的关系

剧本执行得足够多、决策点足够稳定，它本身就是固化候选：整体固化为一个复合命令（`crystallize-to-system1`），Agent 在这件事上进一步退化为"一次调用"。

## 分层自优化顺序

先优化 Skill（沉淀经验）→ 再优化流程编排 → 最后才动系统提示词。让 Agent "自己造工具"保持谨慎，由 Coding Harness 与独立验收把关。
