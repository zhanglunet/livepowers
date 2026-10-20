# livepowers-core

核心工作流：先查固化能力（System 1 first）、带证据探索、把验证过的路径固化成可测试能力。Core workflow: System 1 first, explore with evidence, crystallize proven paths into tested capabilities.

版本跟随 livepowers 主版本（当前 1.6.0）。

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

## 快速上手

1. 按上节安装插件；Claude Code 会话启动时自动注入 `using-livepowers` 路由。
2. 在项目目录初始化数据区，并试一次 System 1 路由：

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/lp.py init
python ${CLAUDE_PLUGIN_ROOT}/scripts/lp.py registry find "weekly revenue by region"  # 退出码 2 = MISS → 转 explore-with-evidence
```

3. 探索结束记一条证据（钩子漏记时手动补）：

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/lp.py evidence add --intent "weekly revenue by region" \
  --system S2 --outcome success --domain OLAP
```

非 Claude Code 环境：用仓库根 `scripts/lp.py`，或 `npm i -g livepowers` 后直接用 `lp`。

## 配置项

| 配置 | 位置 | 说明 |
|---|---|---|
| `LIVEPOWERS_HOME` | 环境变量 | 数据区位置，默认项目下 `.livepowers/` |
| `verbose: true` | `$LIVEPOWERS_HOME/config.yaml` | 持久全量输出；临时用 `LIVEPOWERS_VERBOSE=1 <命令>`（见各 skill 的简洁输出规范） |
| `LP_HOOK_CAPTURE=0` | 环境变量 | 关闭钩子自动补记证据 |
| `LP_CURRENT_MODEL` | 环境变量 | 证据 / 金丝雀记录里的当前模型标识 |
