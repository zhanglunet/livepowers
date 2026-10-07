---
description: 早晨验收：逐项过晨报中的固化候选与复核项，由人决定注册、退役或返工
---
读取 `.livepowers/reports/` 下最新的晨报，按 `acceptance-gates` 技能逐项列出待我采纳的固化产物（意图、评分、n*、测试结果、证据位置）和能力复核项。一次只问我一个决定；我确认后再执行 `lp registry add` / `lp registry retire` / `lp registry verify`，并确保 `--generated-by` 与 `--accepted-by` 不同。
