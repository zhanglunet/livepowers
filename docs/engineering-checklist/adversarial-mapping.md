# PRD-171/T4：对抗验收 findings 与工程/收录 checklist 字段映射

> trend issue #858。三份清单各自为政会让人对「一个 skill 到底卡在哪道门」来回翻
> 文档；本映射把三态 findings 条目、工程门禁 E 条目、收录 C 条目对到同一张表上，
> 供发布裁决时一次看全。上游：`scripts/adversarial_verify.py`（PRD-171/T2）。

## 字段映射（findings 条目 → checklist 关联）

| findings 字段 | 类型 | 对应工程门（E）/ 收录门（C） | 说明 |
|---|---|---|---|
| `skill` | TEXT | E-D04 三处登记 / C-01 目录 | 同一 skill 名，双门共享主键 |
| `case_id` | TEXT | E-T02 触发用例 | 用例须能在触发清单里指认（AC- 锚点强制） |
| `class` | POS-EX/POS-TR/NEG-TR/NEG-RED | E-T02 正/反例 | NEG-RED 恒 safety=true |
| `verdict` | confirmed/needs_validation/rejected | E 级别映射见下表 | 三态判据见 adversarial_verify §5 |
| `evidence` | TEXT | E-T01 三层标记 | 证据须指向真实输出/锚点 |
| `exempt_ref` | TEXT? | 工程门豁免台账 `EX-` ID | needs_validation 的机器锚点（T2 增设） |

## verdict → 门禁级别映射

| verdict | 工程门（E）含义 | 收录门（C）含义 | published |
|---|---|---|---|
| confirmed | 对应 E 条目按 2 分计 | 收录面可引用其证据 | ✅ 可（core 全 confirmed） |
| needs_validation | 对应条目按 1 分 + 豁免台账 EX-（须 `exempt_ref`） | 收录暂缓，标注「验收中」 | ⚠️ 常规门可（≥90%），阻断门不可 |
| rejected | 对应条目 0 分且不可豁免 | 不得进收录清单 | ❌ 不可 |

## 边界

- 本映射是**读侧对照**，不改两个门禁脚本各自的判定（写侧仍各走各的）。
- safety 条目在两门均不可豁免（PRD-171 §5 硬规则）。
- 映射一致性由 `tests/test_adversarial_mapping.py` 机检：双侧 ID 存在性 + 行数。
