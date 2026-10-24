---
record: SG-20261023-01
skill: slim-gate-demo-skill
proposer: demo-proposer
reviewer: demo-reviewer
date: 2026-10-23
trigger: new-proposal
ladder:
  q1_exist: pass
  q2_merge: pass
  q3_boundary: pass
  q4_worth: pass
evidence:
  type: constructed
  link: docs/slim-gate/demo-2026-10-23.md
decision: approved
changes: []
safety_exempt: false
cross_ref:
  audit: ""
  engineering: "虚构演示未实际打分；正式提案发布前按 docs/engineering-checklist/checklist.md 补打分记录"
metrics_snapshot:
  skill_count_before: 21
  skill_count_after: 21
status: provisional
---

> **示范样例（虚构，PRD-148/T5 验收演示）**：本记录对应的 skill 只存在于测试夹具
> （`tests/test_slim_gate_t5.py`），不在 `skills/` 正式目录；proposer / reviewer 均为
> 占位符，不是真实账号。案例全过程见 [`../demo-2026-10-23.md`](../demo-2026-10-23.md)。
> 构造证据 → 按 T1 §3 规则只能 `provisional`；真实首例记录由下一个真实提案产生。

## 结论

虚构提案 `slim-gate-demo-skill` 走完瘦身门全流程：三处登记（published）后无决策记录被
CI 口径拒绝（`scripts/slim_gate.py` 退出码 1）；按模板补本记录（五问全 pass）后复检通过
（退出码 0）。演示路径为「拒绝 → 补记录 → 通过」，留档即本文件。

## 五问判定

- **Q1 这需要存在吗**：pass。虚构提案仅为演示走门，翻车点取"新 skill 发布前无人问过该不该存在"（PRD-148 背景）；证据档位 constructed（夹具构造，无真实使用记录）。
- **Q2 能否并入已有 skill**：pass。相似检测（`scripts/skill_similarity.py`，只提示不判定）对夹具运行提示其与已有 skill 无 ≥0.60 相似对；触发条件"演示走门"不与任何存量 skill 冲突（引用 ≠ 重叠，T1 §4）。
- **Q3 触发边界是否冲突**：pass。description 写明"夹具演示走门用"，与存量 21 个 skill 的触发段无重叠（演示变体：近重复提案会收到相似提示，处置见案例文档第 4 节）。
- **Q4 值得固化吗**：F=构造（无真实频率）、V=2（门禁退出码可自动核对）、S=2（夹具口径稳定）、R=0（只读检查）。演示不计入真实固化候选。
- **Q5 通过**：全 pass，decision=approved（仅对夹具生效；`skills/` 不新增目录，技能数 21→21）。

## 跳过了什么、有什么风险

跳过项：未跑真实夜间评测（虚构 skill 无真实调用量）；`cross_ref.engineering` 未回填实际
打分记录（虚构对象无从打分，发布前补填的口径已写入字段值）。风险：本记录会被
`scripts/slim_gate.py` 采信为有效记录（格式合规），但对应 skill 不存在于 `skills/`，
对发布检查零影响；防止误读为真实批准的责任由本节与文首示范声明承担。
