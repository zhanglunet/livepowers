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

## 快速上手

1. 按上节安装插件；建议同时装 `livepowers-core`——晨报"自动采集待确认"列依赖核心的证据钩子，单装需手动 `lp evidence add`。
2. 收工时跑夜间评审：

> `/lp-nightly` —— 看证据趋势、挑固化候选（`lp candidates --min-count 3`）、登记 `lp pending add`、跑金丝雀并 `lp report` 出晨报。

3. 早晨逐项验收：

> `/lp-morning` —— 按 `acceptance-gates` 决定注册 / 退役 / 返工，一次只做一个决定。

## 配置项

| 配置 | 位置 | 说明 |
|---|---|---|
| `templates/job-contract.json` | 作业契约文件 | 夜间作业的真实配置面：`model_horizon_minutes`（各档模型可稳定时长）；每 job 的 `model_capability` / `earliest_start` / `deadline` / `max_cost` / `retry_limit` / `checkpoint` + `resume_policy`；用 `lp job validate <file>` 校验（需 `livepowers-core` 的 `lp`） |
| `LIVEPOWERS_HOME` | 环境变量 | 数据区位置，默认 `.livepowers/` |
| `LIVEPOWERS_VERBOSE=1` / `config.yaml` 的 `verbose: true` | 环境变量 / 配置文件 | 全量输出开关（见各 skill 的简洁输出规范） |
