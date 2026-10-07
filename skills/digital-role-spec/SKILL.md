---
name: digital-role-spec
description: Use when a job role or recurring function is to be carried by humans plus an agent team (a "digital role") — specifies responsibilities, ontology scope, skills, tools, permissions, KPIs, escalation paths and human-in-the-loop points, marks which tasks are automated versus human-owned, and tracks the human-to-digital ratio and role economics. 把一个岗位的工作交给"人 + 智能体团队"时使用。
---

# 数字岗位规格

把"上一个智能体"变成"设一个岗位"：岗位有职责、边界、考核和升级路径，才能被管理、被计量、被信任。

## 模板

用 `templates/digital-role.yaml`：

```
岗位 = 角色 + 职责 + 智能体团队 + 本体范围 + 技能 + 工具 + 权限 + KPI + 升级路径 + 人在回路
```

## 步骤

1. **列任务清单。**把岗位一周内实际做的事列成任务（来自工单、日志、访谈），每项标频率、耗时、是否写生产状态。
2. **逐项标注归属：**
   - `auto`：由已固化能力（System 1）完成；
   - `agent`：由 Agent 探索或按剧本完成，结果需抽检；
   - `human`：必须人做（授权、裁定、对外承诺、无法验证的判断）；
   - `handoff`：Agent 起草、人确认。
3. **划边界。**本体范围（能看哪些对象）、工具清单（能调用什么）、权限（能做哪些动作、额度上限）、预算（Token / 时长）。
4. **定人在回路。**哪些节点必须确认；谁来接管；接管的触发条件（失败次数、金额、置信度、例外类型）。
5. **定 KPI。**沿用 `outcome-ledger`：业务结果指标 + 验收任务平均成本 + 人工接管比例。
6. **定升级路径。**`agent` 任务被反复成功执行 → 进入固化候选；`human` 任务出现稳定模式 → 评估能否改为 `handoff`。
7. **跟踪人工 : 数字配比**随时间的变化，以及每个任务的归属迁移。

## 岗位经济账（供决策参考）

- 数字岗位总成本 = Token + 工具 + 运维 + 接管人工 + 摊销。
- 只有当 **数字岗位总成本 < 价格 < 同等人工岗位全成本** 时，岗位化交付对双方都成立：客户节省 = 人工成本 − 价格；供方毛利 = 价格 − 数字岗位总成本。
- 接管比例高的岗位，先降接管比例（固化、补 Harness），再谈规模。

## 红线

- 数字岗位不拥有超出岗位定义的权限；派工者不得自行扩大授权。
- 对外承诺、不可逆动作、法律与合规裁定保留给人。
- 岗位规格本身版本化；改权限等同于改本体级约束，走 `acceptance-gates`。
