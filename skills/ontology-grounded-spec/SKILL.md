---
name: ontology-grounded-spec
description: Use before implementing any business feature, report, dashboard, query, transactional command or workflow — clarifies one question at a time, classifies the change as interface / parameter / feature / ontology level, treats uncertain user statements as hypotheses, and compiles an ontology-grounded spec with invariants and machine-checkable acceptance samples. 实现任何业务功能之前使用。
---

# 本体接地的规格（规格编译）

**原则：**先本体、后代码。生成的功能要有明确的完成标准，"能跑起来"不算交付。规格是把自然语言意图编译成可执行约定的地方。

## 第一步：苏格拉底式澄清（一次只问一个问题）

能从本体或上下文查到的不要问用户。依次确认：

1. 要改善的业务结果是什么？业务负责人是谁？当前基线是多少？（没有基线 → 先 `outcome-ledger`）
2. 涉及哪些本体对象？口径在本体里是否已定义、是哪个版本？
3. 只读（OLAP）、写生产状态（OLTP），还是两者兼有（HTAP）？
4. 结果给谁看、多久一次？（决定频率 → 是否值得固化）
5. 有没有已知正确答案的样例可核对？

**防迎合：**用户的不确定说法（"可能按签约算吧""大概 30 天"）记为**假设**并标出来，不当作指令；关键假设必须由有权主体确认后才写进规格。规格模糊时，先澄清再执行，不要"先做一版看看"。

## 第二步：判断变化落在哪一层

| 层 | 例子 | 发布路径 |
|---|---|---|
| 界面 / 展示 | 看板样式、列顺序 | 改界面配置，轻量审批 |
| 参数 | 阈值、口径参数在授权范围内调整 | 改客户配置 + 回归 |
| 功能 | 新查询、新命令、新流程，只用已有对象与行动 | 写规格 → 实现 → `acceptance-gates` → `lp registry add` |
| 本体 | 新对象、新关系、新状态结构、口径含义变化 | 先 `ontology-evolution` → 升本体版本 → 再写规格 |
| 会话 | 一次性、个人化、用完即弃 | 直接 `explore-with-evidence`，不写正式规格 |

**不要把所有变化都翻译成重新编码；也不要用一段脚本掩盖模型缺口。**

## 第三步：写规格

用 `templates/spec.md`，至少包含：

- 目标对象与本体版本；契约版本
- 输入 / 输出（字段、类型、粒度、时间边界、货币）
- 数据来源（规范表 / 视图 / 原子行动）
- 业务规则与口径（引用本体规则 ID；新规则写入 Delta）
- **业务不变量**（例："审批未完成的合同不得生效"）
- 权限：谁在什么条件下可以对哪个对象做什么
- 前置条件、执行效果、失败处理（OLTP 必填）
- 界面要求
- **验收样例**：≥3 正常 + 2 边界 + 1 错误，每个带预期结果与自动核对方式；另留一组保留测试集给独立审查者
- 频率预估（每月次数）

## 第四步：自检

- 每个字段、每条口径都能在本体里找到出处吗？
- 验收样例能被机器自动核对吗？（不能的话将来无法固化，要注明）
- OLTP 规格列了并发、幂等、审批、异常恢复吗？没有就转 `oltp-action-safety`。
- 还有标为"假设"未确认的条目吗？有就不能进入实现。

## 输出物

- `specs/<feature>.md`
- `ontology/deltas/<id>.yaml`（如有本体级变更）

分段给用户确认（每段 200–300 字），确认后再实现；看板 `lp task move <id> spec --by <你> --reason "规格确认"`。
