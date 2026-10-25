# role-packs —— 职业角色 skill 包发行

按职业角色（销售 / 财务 / 人力）重组发行 skill 包（PRD-172）。纯 Markdown +
JSON、无构建依赖；企业可建立私有市场。分组方案与发行清单 schema 见
docs/plans/2026-10-25-role-skill-pack.md（PRD-172/T1，trend issue #860）；
私有市场照做手册见 [docs/role-packs-private-marketplace.md](../docs/role-packs-private-marketplace.md)。

## 目录约定

```
role-packs/
├── README.md                       # 本文件：目录约定与验收状态推进流程
├── manifest.json                   # 发行清单（单一真值源）
├── livepowers-role-sales/          # 销售/交付角色包
│   ├── .claude-plugin/plugin.json  # name / version / description / author / license
│   ├── README.md                   # 快速上手 + 包内技能表 + 验收状态列
│   ├── LICENSE                     # MIT，与仓库根 LICENSE 一致（包自带，可独立分发）
│   └── skills/<skill>/SKILL.md     # 从根 skills/ 原样拷贝（不裁剪正文）
├── livepowers-role-finance/        # 同构
└── livepowers-role-hr/             # 同构
```

约定（T1 §4 定稿）：

1. **manifest.json 是单一真值源**：包构成、版本、状态、验收状态以它为准；
   `marketplace_entry: true` 的包在根 `.claude-plugin/marketplace.json` 有同构
   条目（source `./role-packs/<pack>`，相对路径、不含 `..`，沿用收录门 C-03）
   ——清单是输入、市场清单是产物，不得两处手改漂移；
2. **包内技能一律原样拷贝**：裁剪会制造正文分叉，同步由
   `tests/test_role_packs.py` 逐字节比对兜底（工程门 E-T04 模式）；
3. **每包自带 LICENSE 与 README**：不依赖上游仓库存在即可独立分发
   （整包 vendored / 单包拷贝都成立）；
4. **零 MCP 依赖**：角色包不含 `.mcp.json`、CONNECTORS 类文件，不引用
   第三方服务端点与凭据。

## 包状态机与验收状态推进流程

包状态（`manifest.json` 的 `packs[].status`）：

| 状态 | 含义 | 推进条件 |
|---|---|---|
| `planned` | 立项、包文件未就位 | — |
| `draft` | 包文件就位（plugin.json / README / LICENSE / skills 拷贝齐全） | 目录与 manifest 一致 |
| `published` | 可安装 + 门禁全过，可作企业内采信来源 | 见下 |

`draft → published` 的推进流程（全部走 PR 留痕，manifest 单点改动）：

1. **跑对抗验收**（PRD-171）：独立 verifier 会话按 `tests/adversarial/<skill>/`
   用例执行并写 `findings.json` 三态记录（作者会话不可自签；evidence 可复算）；
2. **更新验收状态**：把 manifest 里对应 `skills[].acceptance.state` 从
   `pending` 改为——
   - `confirmed`：findings 判定 confirmed；
   - `exempt`：needs_validation 经人工豁免，`exempt_ref` 填工程门豁免台账
     （docs/engineering-checklist/exemptions.md）登记的 EX- ID；**safety 用例
     一律不可豁免**（沿用 PRD-171 §5 禁令）；
   - `blocked`：存在 rejected 且未修复；修复回 skill 跟踪，修复后重验再转 confirmed；
3. **标 published**：包内全部 skill 达到 `confirmed` 或有效 `exempt` 后，把包
   `status` 改为 `published` 并同步 marketplace 条目 version。**存在任一
   `pending` / `blocked` 即不得标 published**——硬门禁由 T4（trend #863）接
   findings.json 联动机检，当前由 `tests/test_role_packs.py` 做清单侧判定；
4. **留痕**：状态变更 PR 中写明谁验（verifier）、谁批（批准人 ≠ 实现者）、
   evidence 路径。

回退规则：`published` 包新增 / 修改 skill 时，受影响 skill 回 `pending`、
包回 `draft`，重走验收后再 `published`，包版本按 semver 递增。

## 版本

包版本为内容 semver，从 `0.1.0` 起，独立于仓库 minor 版本；升级由 manifest
统一记，marketplace 条目 version 与之同步。

## 私有市场

两条路径（整仓 fork/vendored + 私有市场、单包技能分发）的分步手册与验证清单：
**docs/role-packs-private-marketplace.md**。文档示例一律占位符，不出现真实
主机名 / IP / 账号 / 密钥。
