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
