# PRD-172/T5 发行验收走查记录

> trend issue #864。验收标准：三包安装演示；清单与验收状态一致；无密钥。
> 走查范围（发行面）：`role-packs/`（销售/财务/人力三包 + `manifest.json`）、
> 根 `.claude-plugin/marketplace.json` 角色包条目、
> `docs/role-packs-private-marketplace.md`（T3 手册）。
> 术语与双语口径对照 PRD-102（双语写作规范：slogan 式中文 + 英文技术描述）。
> 机检复现：`python3 -m unittest tests.test_role_packs_t5 -v`（20 用例）。
> 本文与发行面全量无真实主机名 / IP / 账号 / 密钥（机检 + 阳性对照，见 §4）。

## 1. 三包安装演示（栏目可浏览）

### 1.1 市场形态（整仓 + 市场条目）

市场栏目恰好列出三个角色包（source 均为相对路径 `./role-packs/<pack>`、不含
`..`，收录门 C-03 口径），逐包核对：

| 包 | 版本 | 市场条目 | plugin.json | README | LICENSE (MIT) | skills/ |
|---|---|---|---|---|---|---|
| livepowers-role-sales | 0.1.0 | ✅ 可解析 | ✅ name/version 一致 | ✅ | ✅ | 10 技能 |
| livepowers-role-finance | 0.1.0 | ✅ 可解析 | ✅ name/version 一致 | ✅ | ✅ | 10 技能 |
| livepowers-role-hr | 0.1.0 | ✅ 可解析 | ✅ name/version 一致 | ✅ | ✅ | 8 技能 |

安装命令（占位符示例，与本仓 README 口径一致）：

```
/plugin marketplace add <本仓库本地路径或 <企业内部仓库地址>>
/plugin install livepowers-role-sales@livepowers-marketplace
```

### 1.2 仅技能形态（无市场）

每包 `skills/` 下全部技能目录带 `SKILL.md`，frontmatter `name` 与目录名一致
（`TestInstallDemo.test_skills_only_form_installable`）；包内拷贝与根 `skills/`
逐字节一致由 T2 机检（`tests/test_role_packs.py`，工程门 E-T04 模式）持续兜底。

### 1.3 私有市场照做演示（T3 手册 replay）

按 `docs/role-packs-private-marketplace.md` 模板在临时目录搭「企业最小仓库」并
安装销售包（`TestInstallDemo.test_private_marketplace_manual_replay`）：

1. 抽取手册内嵌的企业 `marketplace.json` 模板（占位符 `<企业市场名>` 等均为合法
   JSON 字符串，可照抄）；
2. 拷贝 `role-packs/livepowers-role-sales/` → `<企业仓库根>/role-packs/`；
3. 清单只保留所需条目，`name` 换企业市场名；
4. 验证：清单合法、`source` 解析到真实目录、`plugin.json` name 与条目一致、
   LICENSE=MIT、入口技能 `using-livepowers` 在位、包内无 `.mcp.json`。

全过——手册「可照做」成立。

## 2. 清单与验收状态一致

**现状**：三包 `status=draft`，全部成员 `acceptance.state=pending`；
`tests/adversarial/` 下无任何打包技能的 `findings.json`（已入对抗程序的
`system1-first` / `acceptance-gates` 仅有冻结用例清单，亦无 findings）。

**双向机检**（`TestManifestAcceptanceConsistency`）：

- `state=pending` ⇔ `tests/adversarial/<skill>/findings.json` 不存在——不漏记
  （跑完验收不得滞留 pending）也不虚报（无 findings 不得标 confirmed/exempt/blocked）；
- 非 `pending` 须有可过机检的 findings 支撑：confirmed=过门（gate PASS）、
  exempt=exempt_ref 在工程门豁免台账登记且对象为该 skill、blocked=存在 rejected；
- `evidence` 路径格式统一为 `tests/adversarial/<skill>/findings.json`；
- T4 硬门禁（`scripts/check_release_readiness.py`）真实仓库冒烟 exit 0
  （`✅ 发行就绪检查：全部 published 包成员 acceptance 状态合规`）；
- 负向对照：published 包带 pending 成员 → 违规「非 confirmed 不可 published」
  （故意失败被拦）。

**T4 脚本两处口径修正**（bug fix，不改判定语义）：

1. 违规标签改取 manifest 实际字段 `pack_id`（原取 `name`，真实清单上显示 `?`）；
2. 清单 schema 的 `exempt` 状态（带有效 `exempt_ref`）放行——对齐 T1 §4.2 硬门禁
   口径「state ≠ confirmed 且无有效豁免不得 published」（原脚本只认 confirmed，
   会把合规的 exempt 成员误拒）；`needs_validation` 写法保留兼容。

## 3. 术语统一（对照 PRD-102 双语验收口径）

**术语表**（发行面统一用词，`TestBilingualAndTerms` 机检）：

| 术语 | 指代 | 混杂变体（0 命中） |
|---|---|---|
| 角色包 | role pack，发行单元 | 角色插件包 / 岗位包 / 职业包 / 知识包 |
| 发行清单 | `role-packs/manifest.json`（输入） | — |
| 市场清单 | `.claude-plugin/marketplace.json`（产物） | — |
| 对抗验收 | PRD-171 动态证伪程序 | — |
| 私有市场 | 企业自建市场 | — |

**双语成对**（PRD-102「中文 + 英文技术描述」口径）：三包 `plugin.json` 与市场
条目 description 均为中文句（含「角色包」）+ 英文技术句（含 role pack），如
`角色包：销售/交付。Role pack for sales/delivery: …`。

**技能名可解析**：四份 README 中反引号连字符 token（17 个）全部为真实 skill 名
或包名/市场名，无笔误（如 `system-first` 类变体 0 命中）。

**回环地址说明**：发行面唯一的 IPv4 形态是 `127.0.0.1:7070`（HR 包
`auditable-agent-comms` 拷贝内）——这是 `scripts/agent_switch.py` 的本地回环
默认端口（`--host 127.0.0.1 --port 7070`），非真实内网地址；包内拷贝与根
`skills/` 逐字节一致（E-T04），本验收不改其正文。

## 4. 无密钥 / 内网信息

- 扫描覆盖：`role-packs/` 全部文件（含包内技能拷贝、LICENSE、plugin.json、
  manifest.json）+ `docs/role-packs-private-marketplace.md`；
- 口径：AWS/GitHub/通用 API key 形态、Bearer、password/token 赋值、私钥块、
  ssh user@、**非回环 IPv4**（回环 127.0.0.1 显式放行，见 §3）——0 命中；
- 阳性对照：构造 AWS key 样例确认扫描器有效（拼接写入测试源码，避免自伤）；
- 角色包零 MCP 依赖：无 `.mcp.json` / `CONNECTORS` 文件、JSON 无 `mcpServers`；
- 文档示例一律占位符（`<企业内部仓库地址>`、`<企业市场名>`、`<企业/团队名>`）。

## 5. 验收标准逐条结论（trend #864）

| 标准 | 结论 | 证据 |
|---|---|---|
| 三包安装演示 | ✅ | §1：市场形态三包条目可浏览且 source 可解析；仅技能形态 SKILL.md 齐全；T3 手册 replay 安装成立 |
| 清单与验收状态一致 | ✅ | §2：三包 draft + 全员 pending 与 tests/adversarial/ 现实双向一致；T4 硬门禁 exit 0、pending 成员负向被拦 |
| 栏目可浏览 | ✅ | §1.1：市场栏目恰好列出三个角色包，字段同构（name/version/source/license） |
| 术语统一 | ✅ | §3：术语表统一、双语成对、技能名反引号全可解析 |
| 无密钥 / 内网信息 | ✅ | §4：发行面全量扫描 0 命中（阳性对照）、零 MCP、示例全占位符 |

## 6. 复现与不影响面

- 复现：`python3 -m unittest tests.test_role_packs_t5 -v`；全量
  `python3 -m unittest discover -s tests`；
- 不改 T1–T4 已合并交付的行为：包文件、manifest、市场清单、私有市场手册零改动；
  仅 `scripts/check_release_readiness.py` 两处口径修正（§2，回归测试覆盖）；
- 不触碰其他 open PR 的文件域。

---

变更记录：v0.1（2026-10-27）PRD-172/T5 验收走查记录。
