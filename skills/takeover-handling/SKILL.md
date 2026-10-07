---
name: takeover-handling
description: Use when a task has been stopped by the loop or budget limit and moved to takeover, when an agent keeps failing on the same step, when a person is asked to take over from an agent, or when the morning report lists tasks in takeover. 任务被止损转入异常接管、Agent 反复失败、人要从 Agent 手里接手时使用。
---

# 异常接管

止损不是失败，是活产品在说"这条路我走不通，换人换法"。接管的目标是**把探索花掉的钱变成可复用的诊断**，并决定下一步走哪条路——而不是换个人继续撞同一堵墙。

## 什么时候进入接管

- `lp task move <id> explore` 超过轮次或预算，脚本自动转入"异常接管"（exit 4）；
- 同一步骤连续失败 ≥ 2 次，或两次生成给出互相矛盾的结果；
- 用户或运营者明确要求人工接手；
- 写操作预演失败、审批被拒、或触发了 `digital-role-spec` 里的 `takeover_when` 条件。

进入接管后，**执行 Agent 停止一切重试**。

## 步骤

1. **冻结并交付诊断包。**执行者把下列内容写到 `.livepowers/explorations/<日期>-<意图>-takeover.md`：
   - 任务 id、意图、已花费轮次与成本（`lp task show <id>`）；
   - 每轮的假设、做法、结果，哪一步开始偏离；
   - 已确认的事实与来源；未经核验的中间结果单独列出；
   - 怀疑的原因（见第 2 步分类）和建议。
   没有诊断包的接管不接受——这是本次探索唯一能回收的价值。

2. **归因，只选一个主因。**

   | 主因 | 典型迹象 | 下一步 |
   |---|---|---|
   | 规格不清 | 每轮都在猜口径；用户的说法前后不一 | 回到 `ontology-grounded-spec`：`lp task move <id> spec --reason "<缺哪条口径>"` |
   | 本体缺口 | 需要的对象、关系或规则不存在 | `ontology-evolution` 提 Delta；任务停在接管直到 Delta 确认 |
   | 环境漂移 | 表、字段、状态取值变了 | `env-scan-ontology` 比对指纹；受影响能力标记复核 |
   | 已固化能力失效 | S1 命中却反复出错 | `lp registry retire`（去固化），本次改走 S2 |
   | 预算定得太低 | 方向正确，只是轮次不够 | 重开并追加预算（第 3 步） |
   | 工具 / 权限故障 | 报错来自接口、超时、无权限 | 修工具或申请权限，不改业务逻辑 |
   | 任务本身不该做 | 价值不成立、风险过高 | 关闭：`lp task move <id> closed --reason "<原因>"` |

3. **决定并记录。**接管人（不能是原执行者）三选一：
   ```bash
   # 返工：换执行者重开，轮次与花费归零，或追加预算
   lp task move <id> explore --by <接管人> --reason "<主因 + 新做法>" --reset-loops
   lp task move <id> explore --by <接管人> --reason "<主因>" --extend-budget <金额> --max-loops <新上限>
   # 重定规格 / 回到澄清
   lp task move <id> spec --by <接管人> --reason "<缺什么>"
   # 关闭
   lp task move <id> closed --by <接管人> --reason "<原因>"
   ```
   不带 `--reset-loops` 或 `--extend-budget` 的重开会再次触发止损——这是故意的，重开必须是显式决定。接管后的任务**仍要经待验证 → 已注册**才能进入生产，不能从接管直接上线。

4. **记接管成本。**
   ```bash
   lp outcome cost --scenario <场景> --kind takeover --amount <人工 + 返工成本> --note "task=<id>"
   ```
   接管成本计入验收任务平均成本（`outcome-ledger`），不得遗漏——接管比例高本身就是要先固化、先补 Harness 的信号（`digital-role-spec`）。

5. **把教训变成规则。**同一主因第二次出现时：补进规格的不变量、工具卡的"何时不用"（`agent-harness-for-tools`）、或本技能的归因表；若是 Agent 行为问题，按 `writing-livepowers-skills` 补技能规则。

## 晨报与汇报口径

晨报"处理异常接管中的任务"一项，逐条写：任务、主因、决定、追加预算（如有）、谁接管。

"任务 t_x 三轮未收敛，主因是规格缺少'有效跟进'的定义；已回到规格确认，补口径后由 agent-b 重开，预算从 20 追加到 35；接管成本 1.5 人时已入账。"

## 反模式

- 换个 Agent 用同样的提示词再跑一遍。
- 手改 `tasks.json` 把状态改回探索。
- 接管人就是原执行者。
- 从接管直接进入生产运行。
- 接管成本不记账，台账里只剩"成功"的任务。
