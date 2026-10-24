# 相似 skill 检测首跑基线（PRD-148/T3）

> trend issue #742。工具：`scripts/skill_similarity.py`（只读、零依赖、只提示不判定）。
> 本文件是 T1 §6「重复度」指标的首跑基线存档，也是 T3 验收样例（**样例能提示可能重复**）。
> 复跑命令：`python3 scripts/skill_similarity.py --top 0 --format markdown`。

## 首跑记录（2026-10-23，21 个存量 skill）

- 两两 210 对；阈值 0.60 提示 / 0.80 强提示（T1 §5）。
- **重复度指标（≥0.60 的对数）：2**；强提示：0。
- 得分 = name / 英文触发段 / 中文一句话 / 正文标题四字段 `difflib.SequenceMatcher`
  相似度的最大值（主相似字段标注在表内）；排序：得分降序、同分按名字字典序（可复现）。

| 强提示 | skill A | skill B | 得分 | 主相似字段 | 重叠触发词 |
|---|---|---|---|---|---|
| — | `using-livepowers` | `writing-livepowers-skills` | 0.68 | name | livepowers |
| — | `delivery-chain` | `fde-delivery` | 0.62 | name | delivery |

## 逐对解读（提示 ≠ 判定，处置归瘦身门 Q2/Q3 人工终审）

- `using-livepowers` × `writing-livepowers-skills`（0.68）：两个都是"关于 livepowers 自身"
  的元技能——前者是路由表（找技能），后者是写作规范（造技能）。名字相近但翻车点不同，
  属 T1 §4 先例口径的**引用 ≠ 重叠**：维持现状，不合并；若 Q3 复核，改写触发条件即可。
- `delivery-chain` × `fde-delivery`（0.62）：一个管交付链路全景、一个管 FDE 交付动作，
  触发词 delivery 重叠但层级不同。同样只提示：后续有提案触碰任一时，Q2 逐案对照。

## 阈值下参考（未达 0.60，不进指标，仅供 Q2 复核时对照）

- `crystallize-to-system1` × `nightly-crystallization-review`（0.46，重叠触发词
  crystallization / nightly / review）：PRD-078 总报告三处重叠定夺之一——已裁"都留、
  引用关系"（夜间评审挑候选、固化技能落实现）。词法相似度不高恰恰因为分工不同，
  本基线如实记录，供先例引用。
- `delivery-chain` × `takeover-handling`（0.58）、`generalizing-skills` ×
  `writing-livepowers-skills`（0.55）：均在提示线之下，无动作。

## 口径说明

- 词法相似 ≠ 语义重复：本工具不做模型调用/语义嵌入（T1 §5 明确不做），得分只用于
  排序与提示；Q2 判定要对照"翻车点"与先例（`docs/plans/2026-10-23-skill-slim-gate.md`
  第 4 节三先例）。
- 本工具与 `scripts/slim_gate.py` 不强耦合，可独立运行；不做 CI 门禁（退出码恒 0），
  不自动删除、不自动修改任何已发布 skill（PRD 非目标红线）。
- 指标跟踪（T1 §6）：重复度连续两个版本不降的高分组 → 进人工复核清单；每次发版前
  重跑一次，与本文件对比增减。

---

变更记录：2026-10-23 首跑基线（21 skills，重复度 2）。
