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

## 快速上手

1. 按上节安装插件。
2. 给一个已有工具写一张工具卡：按 `templates/tool-card.md` 逐项填写——用途一句话、何时用 / 何时不要用、输入输出、前置与后置条件、禁止动作、常见错误 → 下一步动作、一个最小调用示例（见 `agent-harness-for-tools`）。
3. 新建 skill 按 TDD 来：先跑 2–3 个压力情境记录无技能时 Agent 的失败（RED），再写最小 skill（GREEN），重跑情境验证（REFACTOR）；触发样例写进 `tests/triggers/<name>.jsonl`（仓库级目录，评测见仓库根 `scripts/eval_triggers.py`，见 `writing-livepowers-skills`）。

## 配置项

本插件无用户可调配置项：三个 skill 均为纯流程文档，唯一的模板 `templates/tool-card.md` 是填写格式而非开关；全仓库通用的输出开关（`LIVEPOWERS_VERBOSE=1`，或 `$LIVEPOWERS_HOME/config.yaml` 写 `verbose: true`）同样适用。
