# livepowers-night

夜间循环：夜间计划与晨间固化评审。Night loops: nightly planning and morning crystallization review.

版本跟随 livepowers 主版本（当前 1.6.0）。

## 包含的 skills

- `night-loop-planning`
- `nightly-crystallization-review`

## 安装

```
/plugin marketplace add zhanglunet/livepowers
/plugin install livepowers-night@livepowers-marketplace
```

skill 内容与仓库根 `skills/` 全量入口保持一致（只搬目录，不改内容）。

## 自带运行时资产

`templates/job-contract.json`、`commands/lp-nightly.md`、`commands/lp-morning.md`。

## 依赖与推荐安装

`nightly-crystallization-review` 晨报里的"自动采集待确认"列依赖 `livepowers-core` 的证据钩子（单装本插件无自动采集，需手动 `lp evidence add`）；`/lp-morning` 的验收环节会引用 `livepowers-delivery` 的 `acceptance-gates` / `takeover-handling`（缺失时相关验收步骤需手动执行）。

推荐：`livepowers-night` + `livepowers-core` 一起装。
