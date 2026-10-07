---
description: 收工 / 夜间固化评审：看证据趋势、挑候选、生成草稿与测试、复核能力、出晨报
---
使用 `nightly-crystallization-review` 技能执行今晚的固化评审。不要直接注册任何能力；每个产物放到 `.livepowers/pending/<意图>/` 并用 `lp pending add` 登记（评分、n*、测试命令与结果、位置、生成者）；跑金丝雀并 `lp canary record`；最后运行 `lp report` 并告诉我晨报位置。
