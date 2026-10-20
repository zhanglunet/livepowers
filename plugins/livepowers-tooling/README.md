# livepowers-tooling

工具：agent harness 与 skill 编写指南。Tooling: agent harness for tools and the guide to writing livepowers skills.

版本跟随 livepowers 主版本（当前 1.6.0）。

## 包含的 skills

- `agent-harness-for-tools`
- `generalizing-skills`
- `writing-livepowers-skills`

## 安装

```
/plugin marketplace add zhanglunet/livepowers
/plugin install livepowers-tooling@livepowers-marketplace
```

skill 内容与仓库根 `skills/` 全量入口保持一致（只搬目录，不改内容）。

## 自带运行时资产

`templates/tool-card.md`，单装即可工作。

> 说明：`writing-livepowers-skills` 中提到的 `scripts/eval_triggers.py`（触发率评测）是仓库级开发工具，
> 依赖仓库根的 `tests/triggers/` 用例集与完整目录结构，需在完整仓库中使用，不在单插件安装范围内。

## 依赖与推荐安装

本插件独立可用（harness 与 skill 编写指南），无跨插件依赖。
