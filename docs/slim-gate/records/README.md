# 瘦身门（PRD-148）：记录目录

一条决策记录一个文件：`<YYYYMMDD>-<skill-slug>.md`（如 `2026-10-23-demo-skill.md`），
内容按 `templates/slim-gate-record.md` 模板（T1 §3 字段级定义）。

- `scripts/slim_gate.py` 枚举本目录做发布检查：基线外（见 `../baseline-2026-10-23.md`）
  的 skill 三处登记（published）而无 `decision: approved` 记录 → CI 失败。
- 记录有效性：必填 `record` / `skill` / `decision`；decision 五值枚举；
  `proposer` 不得与 `reviewer` 相同；同一 skill 取 date 最大的一条。
- `rejected` / `merged` / `downgraded` 为终态不可逆，翻案须新开记录并引用旧记录 ID。
- 当前有 1 条**示范样例**：[`2026-10-23-slim-gate-demo-skill.md`](2026-10-23-slim-gate-demo-skill.md)
  （虚构 skill、构造证据、provisional，PRD-148/T5 验收演示；对应 skill 不在 `skills/`，
  对发布检查零影响）。案例全过程见 [`../demo-2026-10-23.md`](../demo-2026-10-23.md)；
  首个真实记录仍由下一个新 skill 提案产生。
