---
description: 早晨验收：逐项过晨报中的固化候选与复核项，由人决定注册、退役或返工
---
读取 `.livepowers/reports/` 下最新的晨报（或直接 `lp pending list`），按 `acceptance-gates` 技能逐项列出待我采纳的固化产物（意图、评分、n*、测试结果、位置、生成者）、能力复核项、金丝雀回归和异常接管中的任务（按 `takeover-handling` 给出主因与建议）。一次只问我一个决定；我确认后再执行 `lp registry add` + `lp pending done --accepted`、`lp registry retire`、`lp registry verify` 或 `lp task move`，并确保 `--generated-by` 与 `--accepted-by` 不同。
