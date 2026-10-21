# livepowers-delivery

交付与安全：独立验收门、现场交付、结果账本、操作安全与可审计通信。Delivery & safety: acceptance gates, FDE delivery, outcome ledger, action safety.

版本跟随 livepowers 主版本（当前 1.6.0）。

## 包含的 skills

- `acceptance-gates`
- `fde-delivery`
- `outcome-ledger`
- `oltp-action-safety`
- `auditable-agent-comms`
- `takeover-handling`
- `delivery-chain`

## 安装

```
/plugin marketplace add zhanglunet/livepowers
/plugin install livepowers-delivery@livepowers-marketplace
```

skill 内容与仓库根 `skills/` 全量入口保持一致（只搬目录，不改内容）。

## 依赖与推荐安装

本插件可独立使用（验收门、现场交付、结果账本），无运行时资产依赖。`livepowers-core` 的路由表会引用 `acceptance-gates`；`livepowers-night` 的 `/lp-morning` 命令验收环节会用到 `acceptance-gates` 与 `takeover-handling`。

## 快速上手

1. 按上节安装插件。
2. 让 Agent 按 `acceptance-gates` 走四道门验收一个候选能力：

> "用 acceptance-gates 验收本次交付：依次过形式检查 → 契约测试 → 独立对抗审查 → 人工采纳。"

3. 装有 `livepowers-core` 时，立项先登记价值基线（没有基线不开始探索）：

```bash
lp outcome baseline --scenario "商机跟进" --metric "逾期率" --value 0.32 --direction lower
```

## 配置项

| 配置 | 位置 | 说明 |
|---|---|---|
| `SWITCH_MAX_BODY` | 环境变量（默认 4000） | `auditable-agent-comms` 交换机单条协调消息最大字符数，超限被拒绝，大块内容走 `--ref` 引用 |
| `LIVEPOWERS_HOME` | 环境变量 | 结果台账等数据位置，默认 `.livepowers/`（需装 `livepowers-core` 的 `lp`） |
| `LIVEPOWERS_VERBOSE=1` / `config.yaml` 的 `verbose: true` | 环境变量 / 配置文件 | 全量输出开关（见各 skill 的简洁输出规范） |
