# livepowers-core

核心工作流：先查固化能力（System 1 first）、带证据探索、把验证过的路径固化成可测试能力。Core workflow: System 1 first, explore with evidence, crystallize proven paths into tested capabilities.

版本跟随 livepowers 主版本（当前 1.5.0）。

## 包含的 skills

- `system1-first`
- `explore-with-evidence`
- `crystallize-to-system1`
- `ontology-grounded-spec`
- `using-livepowers`

## 安装

```
/plugin marketplace add zhanglunet/livepowers
/plugin install livepowers-core@livepowers-marketplace
```

skill 内容与仓库根 `skills/` 全量入口保持一致（只搬目录，不改内容）。

## 自带运行时资产

`scripts/lp.py`、`templates/`（capability-package.yaml、ontology.yaml、spec.md）、`commands/lp-route.md`、`hooks/`（SessionStart / PostToolUse / Stop），单装即可工作。

## 依赖与推荐安装

`using-livepowers` 的路由表会引用其他插件的 skill：`env-scan-ontology`、`ontology-evolution`（livepowers-ontology），`acceptance-gates`（livepowers-delivery），`night-loop-planning`（livepowers-night）。单装本插件时这些路由不可用。

推荐：`livepowers-core` + `livepowers-ontology` 起步，按需加装 delivery / night / tooling；或一次装全 5 个。
