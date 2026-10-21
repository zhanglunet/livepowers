# livepowers-ontology

本体：环境扫描、知识演进、数字角色规约。Ontology: environment scan, knowledge evolution, digital role specs.

版本跟随 livepowers 主版本（当前 1.6.0）。

## 包含的 skills

- `env-scan-ontology`
- `ontology-evolution`
- `digital-role-spec`
- `living-surface`

## 安装

```
/plugin marketplace add zhanglunet/livepowers
/plugin install livepowers-ontology@livepowers-marketplace
```

skill 内容与仓库根 `skills/` 全量入口保持一致（只搬目录，不改内容）。

## 自带运行时资产

`templates/`（digital-role.yaml、ontology-delta.yaml、surface.json），单装即可工作。

## 依赖与推荐安装

本插件可独立使用（本体扫描、演进、数字角色规约）。`livepowers-core` 的路由表会引用本插件的 `env-scan-ontology` / `ontology-evolution`，两者搭配效果最好。

## 快速上手

1. 按上节安装插件；建议搭配 `livepowers-core`（本体演进后的固化走 `crystallize-to-system1`）。
2. 让 Agent 按 `env-scan-ontology` 只读接入一个数据库：

> "用 env-scan-ontology 接入 ./data/orders.sqlite：扫描生成环境指纹，产出 `.livepowers/ontology.draft.yaml` 本体草稿。"

3. 做次抛展示面：按 `templates/surface.json` 写展示描述（`tier: ephemeral`，数据源只带只读查询），用 `lp surface validate <surface.json>` 校验通过后再展示（`lp` 来自 `livepowers-core`）。

## 配置项

本插件无专用环境变量或配置文件。它的"配置"以填写模板的形式存在：

| 项 | 说明 |
|---|---|
| `templates/ontology-delta.yaml` | 本体演进提案的填写格式（候选 → 已校验 → 已确认 → 已发布四态） |
| `templates/digital-role.yaml` | 数字岗位规格的填写格式（职责归属 auto / agent / human / handoff） |
| `templates/surface.json` | 展示面描述的填写格式（组件 + 只读查询） |
| `LIVEPOWERS_HOME` | 环境变量，数据区位置，默认 `.livepowers/`（全仓库通用） |
| `LIVEPOWERS_VERBOSE=1` / `config.yaml` 的 `verbose: true` | 全量输出开关（全仓库通用，见各 skill 的简洁输出规范） |
