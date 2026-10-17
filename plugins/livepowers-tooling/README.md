# livepowers-tooling

工具：agent harness 与 skill 编写指南。Tooling: agent harness for tools and the guide to writing livepowers skills.

版本跟随 livepowers 主版本（当前 1.5.0）。

## 包含的 skills

- `agent-harness-for-tools`
- `writing-livepowers-skills`

## 安装

```
/plugin marketplace add zhanglunet/livepowers
/plugin install livepowers-tooling@livepowers-marketplace
```

skill 内容与仓库根 `skills/` 全量入口保持一致（只搬目录，不改内容）。

## 自带运行时资产

`templates/tool-card.md`，单装即可工作。

## 依赖与推荐安装

本插件独立可用（harness 与 skill 编写指南），无跨插件依赖。
