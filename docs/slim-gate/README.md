# 瘦身门（PRD-148/T2）：发布前强制项

> 问题清单与决策记录模板见 PRD-148/T1（trend issue #740；草案见 PR #87 的
> `docs/plans/2026-10-23-skill-slim-gate.md`）。本目录是 T2/T3 落地物：发布门检查、
> 基线清单、决策记录目录与模板、相似检测首跑基线。

## 规则

**无瘦身门决策记录，不可标为 published。** published 的锚点是三处登记（与 PRD-147
条目 E-D04 同一处）：

1. `using-livepowers` 路由表（`skills/using-livepowers/SKILL.md`）
2. 根 README 技能表（`README.md`）
3. 插件拷贝（`plugins/<name>/skills/<skill>/`）

三处齐 = published。基线外（新增 / 大改后发布）的 skill 必须先在
`records/` 留下 `decision: approved` 的决策记录（模板：`templates/slim-gate-record.md`），
否则 `scripts/slim_gate.py` 报告失败，CI 打回。

## 用法

```bash
python3 scripts/slim_gate.py             # 全量检查：违规退出 1
python3 scripts/slim_gate.py --report-only
```

CI（`.github/workflows/test.yml`）每次 push / PR 都跑硬检查。

## 存量基线

`baseline-2026-10-23.md` 记录启用日的 21 个存量 skill（与
`tests/test_marketplace_install.py` 的 `EXPECTED_SKILL_COUNT = 21` 同源口径，增减同步）。
存量不要求补记录——PRD-078 已做一轮事后全量审计；存量的大改（改名、触发条件变更、
正文 ≥1/3 重写）同样触发本门（`trigger: major-revision`）。

## 红线（不砍护栏）

涉及安全、写操作审计、独立验收的 skill（`oltp-action-safety`、`acceptance-gates`、
`auditable-agent-comms`、`takeover-handling`）不因瘦身门被合并或拒绝：跳 Q3 并在
记录里标 `safety_exempt: true`。本门不自动删除、不自动修改任何已发布 skill
（相似检测只提示不判定，是 T3 的事）。

## 相似 skill 检测（T3，供 Q2/Q3 参考）

```bash
python3 scripts/skill_similarity.py              # 全库 Top 20（阈值 0.60 提示 / 0.80 强提示）
python3 scripts/skill_similarity.py --top 0 --format markdown
```

- 词法相似度（`difflib`，name/英文触发段/中文一句话/正文标题四字段取最大值），
  **只提示、不判定、不自动删**；与 `slim_gate.py` 不强耦合、可独立运行、退出码恒 0
  （不做 CI 门禁）。
- 首跑基线：`similarity-baseline-2026-10-23.md`（21 skills，重复度指标 = ≥0.60 的
  2 对；T1 §6 的"重复度"指标以此为首跑存档，发版前重跑对比）。
- 提示 ≠ 判定：Q2（能否并入）/Q3（触发边界）的处置仍走决策记录人工终审。
