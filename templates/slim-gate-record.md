# 瘦身门决策记录模板（PRD-148/T1 §3）

> 用法：复制为 `docs/slim-gate/records/<YYYYMMDD>-<skill-slug>.md`（如
> `2026-10-23-demo-skill.md`），按尖括号提示填空后删掉本行。一个 skill 一条记录；
> 五问逐问必填，不许跳格；梯子停在第一个命中的动作（Q1→Q5）。
> 红线：`oltp-action-safety`、`acceptance-gates`、`auditable-agent-comms`、
> `takeover-handling` 不因瘦身门被合并或拒绝——直接跳 Q3 并把 `safety_exempt`
> 标 `true`。

---
record: SG-<日期>-<两位序号>            # 如 SG-20261023-01
skill: <提案名，kebab-case>             # merged 时填被并入的提案名
proposer: <提案人>                      # 不得与 reviewer 相同（生成者 ≠ 采纳人）
reviewer: <人工终审人>
date: <YYYY-MM-DD>
trigger: new-proposal | major-revision
ladder:
  q1_exist: pass | rejected | downgraded
  q2_merge: pass | merged               # merged 时括注目标：<目标skill>#<节名>
  q3_boundary: pass | reworded
  q4_worth: pass | rejected | deferred
evidence:
  type: real-record | reproducible-case | constructed
  link: <证据位置；本仓内相对路径或 issue 链接>
decision: approved | merged | rejected | downgraded | deferred
target: <仅 merged：目标 skill 与节名>
changes: []                             # 并入/改名后的变更清单，逐条一行
safety_exempt: false                    # 红线类 skill 标 true，跳过 Q2
cross_ref:
  audit: <PRD-078 审计卡链接；无则留空>
  engineering: <PRD-147 checklist 打分记录；发布前补填>
metrics_snapshot:
  skill_count_before: 21
  skill_count_after: 21                 # approved 且确为新 skill 时 +1
status: provisional | final             # constructed 证据 → provisional
---

## 结论

<一句话：本提案的终态是什么、为什么。>

## 五问判定

- **Q1 这需要存在吗**：<≤3 句，写翻车点与证据档位>
- **Q2 能否并入已有 skill**：<≤3 句；引用 ≠ 重叠，先例见 T1 §4>
- **Q3 触发边界是否冲突**：<≤3 句>
- **Q4 值得固化吗**：<F/V/S/R 四值 + 预估依据一句话>
- **Q5 通过**：<全 pass 才写 approved>

## 跳过了什么、有什么风险

<明确写出没问的问题 / 没核的证据 / 带病点，不许留白（借 ponytail 的披露习惯）。>
