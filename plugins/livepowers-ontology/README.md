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
