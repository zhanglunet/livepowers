# 角色包私有市场照做手册（PRD-172/T3）

> 适用对象：想在企业内部自建 livepowers 角色包私有市场的使用者。
> 范围：私有市场目录约定、两条安装路径、安装后验证清单。
> **本文示例一律使用占位符**（`<企业内部仓库地址>`、`<企业市场名>`、`<企业/团队名>`），
> 不出现真实主机名 / IP / 账号 / 密钥。

## 前置：角色包是什么

`role-packs/<pack>/` 每包自包含：`.claude-plugin/plugin.json` + `README.md` +
`LICENSE`（MIT）+ `skills/`（从根 skills/ 原样拷贝）。零 MCP 依赖、无构建
步骤，整包拷走即可独立分发。包构成、版本与验收状态以
`role-packs/manifest.json` 为单一真值源（目录约定与推进流程见
role-packs/README.md）。

## 目录约定（企业侧最小结构）

企业仓库只需要以下结构（可只取所需角色包）：

```
<企业仓库根>/
├── .claude-plugin/
│   └── marketplace.json        # 企业自有市场清单（模板见下）
└── role-packs/
    └── livepowers-role-sales/  # 整包拷贝（含 .claude-plugin/、README、LICENSE、skills/）
```

企业自有 `marketplace.json` 模板（字段与本仓同构，`name` 换成企业市场名）：

```json
{
  "name": "<企业市场名>",
  "owner": { "name": "<企业/团队名>" },
  "plugins": [
    {
      "name": "livepowers-role-sales",
      "description": "销售/交付角色包（来源 livepowers，MIT）",
      "version": "0.1.0",
      "source": "./role-packs/livepowers-role-sales",
      "license": "MIT"
    }
  ]
}
```

约束（沿用收录门 C-03 口径）：`source` 必须是相对路径、自 marketplace 根起算、
**不含 `..`**、指向真实存在的目录；一个条目一个包，`name` 与包目录内
`.claude-plugin/plugin.json` 的 `name` 一致。

## 路径一：整仓 fork / vendored + 私有市场

1. 把本仓 fork 或 vendored 快照放进企业内部仓库 `<企业内部仓库地址>`
   （也可只取 `role-packs/` 与 `.claude-plugin/` 组成最小仓库）；
2. 按上文模板改 `.claude-plugin/marketplace.json`：只保留所需角色包条目，
   `name` 写企业市场名；
3. 客户端添加市场并安装：

   ```
   /plugin marketplace add <企业内部仓库地址>
   /plugin install livepowers-role-sales@<企业市场名>
   ```

4. 更新：同步上游快照后，对照 `role-packs/manifest.json` 的版本与验收状态
   （推进流程见 role-packs/README.md）决定是否跟进。

## 路径二：单包技能分发（无市场）

只要技能、不要插件形态时：

1. 把 `role-packs/<pack>/skills/` 下的技能目录复制进客户端技能目录；
2. 无需 marketplace.json 与 plugin.json；包 README 的补偿规则适用——
   `using-livepowers` 路由表中未随包安装的技能视为未启用，命中即按 MISS 走
   `explore-with-evidence` 探索，不改入口正文；
3. 分发物保留包内 `LICENSE`（MIT）与 `README.md`，许可与来源可追溯。

## 安装后验证清单

- [ ] `/plugin` 列表能看到 `<企业市场名>` 与所装角色包；
- [ ] 包内技能出现在技能列表（入口 `using-livepowers`、方法技能如
      `system1-first`）；
- [ ] 触发入口技能，按路由表走一轮 HIT / MISS（System 1 命中或转探索）；
- [ ] 私有化环境核对：包内无 `.mcp.json`、无第三方服务端点引用；
- [ ] 分发物保留 LICENSE 与 README。

## 红线

1. 文档、示例与企业市场配置一律占位符，不写入真实主机名 / IP / 账号 / 密钥；
   密钥只放环境变量，从不写入仓库；
2. 不引入 CONNECTORS / `.mcp.json` 类第三方服务端点与凭据配置（本仓角色包
   零 MCP 依赖）；
3. `source` 相对路径、不含 `..`（C-03）；清单（manifest.json）是输入、市场
   清单是产物，不要两处手改漂移。
