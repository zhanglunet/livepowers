# PRD-147/T5 验收记录（2026-10-23）

> 对应 trend issue [#739](https://github.com/zhanglunet/trend/issues/739)。
> 验收标准（PRD 任务表 T5 行）：**checklist 入库；发布文档引用门禁；无密钥入报告**。
> 本记录随 T5 PR 入库；T1–T4 已在 main（PR #86 / #88 / #89 / #91–#94 系）。

## 逐条验收结论

| # | 验收标准 | 结论 | 证据 |
|---|---|---|---|
| 1 | checklist 入库 | 通过 | 本体 [`checklist.md`](checklist.md)（v0.1，四类 19 条 + 公共约定 + 豁免规则）；本目录全套：`README.md`（台账）、`exemptions.md`、`prd-094-mapping.md`（T3）、`samples/` 金样例 ×2。条目编号/类别/级别与 `scripts/eng_checklist.py` 的 ITEMS 一致，由 `tests/test_eng_checklist_t5.py::TestChecklistInRepo` 断言 |
| 2 | 发布文档引用门禁 | 通过 | 根 `README.md` 新增「发布门禁（发版前必过）」节：工程门禁命令、过门口径（阻断级全 2 分且常规级达标率 ≥90%）、豁免边界与瘦身门串联说明；由 `tests/test_eng_checklist_t5.py::TestReleaseDocsReferenceGate` 断言 |
| 3 | 无密钥入报告 | 通过 | `tests/test_eng_checklist_t5.py::TestNoSecretsInReportsAndDocs` 用 `scripts/eng_checklist.py` 的同源模式（字面密钥赋值 / AWS AccessKey / 私钥文件头 / GitHub token / 私有网段 IP）对本目录全部文档（含金样例报告、映射表、验收记录）做扫描断言 0 命中，并带阳性对照（构造泄漏样例必须被模式命中，防止断言空转） |

## 复核命令

```bash
python3 scripts/eng_checklist.py --plugin livepowers-night   # 金样例插件回归：判定 PASS
python3 -m unittest tests.test_eng_checklist_t5 -v           # T5 验收断言
python3 -m unittest discover -s tests                        # 全量回归
```

## 边界说明

- E-S05 占位符规约的人工抽查面（`<HOST>`/`<TOKEN>`/保留域）不在机检范围，本记录只覆盖
  可机检的密钥/私有网段模式；金样例报告为脚本原样输出存档（`samples/`），不改写。
- CI 仍以 report-only 接入工程门禁（硬门禁开关是后续发版节奏的决定，见 `README.md` 用法节），
  不在本验收标准内。
