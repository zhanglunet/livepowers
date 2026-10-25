# PRD-172/T1：19 skill 角色分组与发行清单

> trend issue #860。对应 PRD-172（中央仓库 zhanglunet/trend）。
> 状态：草案，供评审。分组定稿后 T2（#861）才开工；本文只定分组方案与发行清单 schema，不落包文件、不改市场清单。
> 现状基线：2026-10-25，livepowers main `be00d9d`（10-23 批次 PRD-147/148 已合并）。

## 1. 借鉴对象与许可证

借鉴对象：[anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins)（**Apache-2.0**，观测 commit `33d3dea41a34`，2026-10-25 实测）。借鉴形态而非内容：

1. **角色即发行单元**：上游顶层按职业角色分目录（sales、finance、human-resources、marketing、operations、legal…），一角色一个插件，市场一键安装——本 PRD 的角色包沿用"按角色切发行"的形态；
2. **每包组件约定**：上游每个角色插件含 `.claude-plugin/plugin.json` + `skills/` + `README.md`（另有 CONNECTORS.md 与 `.mcp.json`，见下方红线）——本仓角色包对齐该组件约定；
3. **包装的是"方法与文档"而非代码**：纯 Markdown + JSON、无构建，企业可自建私有市场——与本仓"领域知识产品化"方向一致。

全部为按本仓现状另写的自研表述，本 T1 未复制上游任何文件，故不附 LICENSE/NOTICE；T2/T3 落包同样自写内容，若未来拷贝上游文件，须附 Apache-2.0 LICENSE 并在 NOTICE 写明来源仓库与钉扎 commit。**红线：上游各角色包的 `.mcp.json` 含第三方服务端点与凭据配置，任何情况下不整份拷贝；本仓角色包零 MCP 依赖。**

## 2. 现状衔接与口径校准

### 2.1 "19 个"的口径关闭（21 = 19 + 2）

PRD 写"19 个 skill"，main 实际 **21 个**（v1.6.0 增 generalizing-skills、其后 delivery-chain 入列；契约 `EXPECTED_SKILL_COUNT = 21`）。本设计按如下口径对齐 PRD 数字，分组表不多不少覆盖 19 个：

| 不计入分组的 2 个 | 理由 | 处置 |
|---|---|---|
| `using-livepowers` | 入口技能（七条铁律 + 路由表），是"怎么用"不是"某角色的方法" | 作为**每包必含入口**随包发行（原样拷贝），不占分组名额 |
| `writing-livepowers-skills` | 作者元技能，消费者是 skill 作者不是角色使用者 | **不进任何角色包** |

### 2.2 两轴切分：功能轴不动，角色轴新增

| 维度 | 功能轴（现有，不动） | 角色轴（本 PRD 新增） |
|---|---|---|
| 切分依据 | 按 livepowers 体系职能（core / ontology / delivery / night / tooling） | 按**使用者职业角色**（销售 / 财务 / 人力） |
| 载体 | 5 个主题插件，`.claude-plugin/marketplace.json` 已登记 | `role-packs/` 下每角色一包 |
| 归属 | 每 skill 恰好属于一个功能插件主体 | 同一 skill **可进多个角色包**（拷贝发行） |
| 渠道 | 插件市场 / npm / skills.sh / 网页 zip | 先接插件市场形态（T2/T3）；`skills.sh.json` groupings 与 npm 安装器本期不动 |

### 2.3 门禁衔接

- **PRD-171 对抗验收（T4 硬门禁）**：发行清单每个 skill 条目挂验收状态（§4 字段），非 confirmed 且无有效豁免不得进 published 包；
- **PRD-147 工程门**：E-T04"插件拷贝逐字节一致"的机检模式扩展到 `role-packs/`（T4 落）；
- **PRD-094 收录门**：角色包作为新插件对象，按既有 C 条目（插件级）打分，口径不变。

## 3. 角色分组方案（19 个）

**分组原则（写死，评审按此裁争议）**：

1. 按角色日常工作流（找答案 → 按规矩做 → 写回去 → 收台账）匹配 skill 的强制工作流，不按行业名词硬凑；
2. 每 skill 恰好一个**主桶**（primary bucket）；适用角色可多值，标注**必含/选含**；
3. 工程/作者向、不面向业务角色的进**未分组桶 U**（PRD 风险节预留）；
4. 护栏类（验收、写操作安全）进通用桶；角色包涉写操作（CRM 录入、凭证写入）时护栏必含。

**分组表（5 桶 19 行）**：

| 桶 | skill | 适用角色（必含/选含） | 说明 |
|---|---|---|---|
| G 通用方法与护栏（8） | `system1-first` | 通用·必含 | 先查固化能力，所有角色的第一步 |
| G | `explore-with-evidence` | 通用·必含 | 未固化需求的探索与证据 |
| G | `ontology-grounded-spec` | 通用·必含 | 把业务诉求问成规格 |
| G | `acceptance-gates` | 通用·必含 | 四道门收口，所有交付必过 |
| G | `oltp-action-safety` | 销售/财务·涉写必含 | 先仿真后执行的写操作护栏 |
| G | `outcome-ledger` | 通用·必含 | 基线与增量价值台账 |
| G | `night-loop-planning` | 财务·选含（月结/夜间批量） | 强规划弱执行 |
| G | `nightly-crystallization-review` | 财务·选含 | 夜间固化复盘与晨报 |
| S 销售与交付（3） | `fde-delivery` | 销售·必含 | 现场交付五类底座资产 |
| S | `delivery-chain` | 销售·必含 | 五段链编排（扫描→规格→探索→验收→台账） |
| S | `takeover-handling` | 销售·必含 | 止损冻结、诊断包与换人重开（跟单接手） |
| F 财务与口径（2） | `env-scan-ontology` | 财务·必含 | 数据环境盘点 = 科目/口径梳理的入口 |
| F | `ontology-evolution` | 财务·必含 | 口径变更流程（候选→已发布、历史重算） |
| H 人力与合规（2） | `digital-role-spec` | 人力·必含 | 数字岗位规格：任务归属与人在回路 |
| H | `auditable-agent-comms` | 人力·必含 | 信任域分级与可审计协作（招聘/流程合规） |
| U 未分组·工程向（4） | `crystallize-to-system1` | —（作者向） | 固化门禁是 skill 生产者的事 |
| U | `agent-harness-for-tools` | —（工程向） | 工具卡与硬约束，面向搭建者 |
| U | `generalizing-skills` | —（作者向） | skill 泛化，面向作者 |
| U | `living-surface` | —（工程向） | 展示面技术形态，非业务角色日常工作流 |

**角色包构成（T2 三包，最小发行）**：

| 包 | 构成 | skill 数 |
|---|---|---|
| `livepowers-role-sales` 销售/交付包 | `using-livepowers`（入口）+ G 必含 5 + `oltp-action-safety`（CRM 写入）+ S 3 | 10 |
| `livepowers-role-finance` 财务包 | `using-livepowers` + G 必含 5 + `oltp-action-safety`（凭证写入）+ F 2 + `night-loop-planning`（选含） | 10 |
| `livepowers-role-hr` 人力包 | `using-livepowers` + G 必含 5 + H 2 | 8 |

**争议处理**：分组异议按原则 1–4 裁；裁不动的进 U 桶留痕（记录异议与理由），不阻塞 T2 开工——U 桶是合法出口不是落选堆。

## 4. 角色包结构与发行清单 schema

### 4.1 目录形态（T2 建，本 T1 只定结构）

```
role-packs/
├── manifest.json                       # 发行清单（单一真值源，§4.2 schema）
├── livepowers-role-sales/
│   ├── .claude-plugin/plugin.json      # name/version/description/author/license 对齐 C-06/09/10 口径
│   ├── README.md                       # 快速上手 + 包内技能表 + 验收状态列
│   └── skills/<每包技能>/SKILL.md       # 从根 skills/ 拷贝，原样不裁剪
├── livepowers-role-finance/            # 同构
└── livepowers-role-hr/                 # 同构
```

设计决策（三条，写明理由）：

1. **物理拷贝而非引用**：marketplace `source` 必须指向真实目录（C-03）；拷贝分叉风险由契约测试兜底——沿用 `tests/test_plugin_sync` 的逐字节比对模式扩展到 `role-packs/`（T4 落，对齐 E-T04）；
2. **包内技能一律原样拷贝，不裁剪正文**：裁剪会制造正文分叉，违反工程门同步口径；包 README 声明补偿规则——"路由表中未随包安装的技能视为未启用，命中即按 MISS 走探索"，不改 `using-livepowers` 正文；
3. **版本**：包从 `0.1.0` 起（semver，内容版本）；包版本独立于仓库 minor 版本，升级由 manifest 统一记。

### 4.2 发行清单 `role-packs/manifest.json`（字段级）

```json
{
  "schema_version": 1,
  "updated": "2026-10-25",
  "skill_source": "../skills/",
  "acceptance_gate": "docs/plans/2026-10-25-adversarial-acceptance.md",
  "packs": [
    {
      "pack_id": "livepowers-role-sales",
      "title": "销售/交付角色包",
      "version": "0.1.0",
      "status": "planned",
      "entry_skill": "using-livepowers",
      "skills": [
        {
          "name": "system1-first",
          "bucket": "G",
          "inclusion": "required",
          "acceptance": {
            "state": "pending",
            "evidence": "tests/adversarial/system1-first/findings.json",
            "exempt_ref": null
          }
        }
      ],
      "marketplace_entry": true
    }
  ],
  "ungrouped": ["crystallize-to-system1", "agent-harness-for-tools", "generalizing-skills", "living-surface"]
}
```

字段口径：

| 字段 | 取值与规则 |
|---|---|
| `packs[].status` | `planned` → `draft`（包文件就位）→ `published`（可安装 + 门禁全过）；`published` 是唯一可进 marketplace 条目的状态 |
| `skills[].acceptance.state` | `pending`（未跑对抗验收）/ `confirmed` / `exempt`（必须带 `exempt_ref`，指向 `docs/engineering-checklist/exemptions.md` 的 EX- ID）/ `blocked`（存在 rejected 且未修复） |
| `skills[].inclusion` | `required` / `optional`（选含项进包与否由包决定，manifest 如实记） |
| **硬门禁（T4 落）** | `state ≠ confirmed 且无有效豁免` 的 skill，所在包 `status` 不得为 `published`；safety 类用例 rejected 的 skill 直接 `blocked`，不可豁免（沿用 PRD-171 §5 禁令） |

`marketplace_entry: true` 的包在 T2/T3 由清单**生成**根 `.claude-plugin/marketplace.json` 追加条目（source `./role-packs/<pack>`，字段与既有 5 条目同构）；清单是输入、市场清单是产物，避免两处手改漂移。

## 5. 私有市场说明（T3 范围预告）

- **路径一（整仓 fork/vendored）**：企业拷贝本仓 → 自有 `.claude-plugin/marketplace.json` 的 source 相对路径指向所需角色包目录（相对路径、不含 `..`，沿用 C-03 禁令）→ `/plugin marketplace add <企业内部仓库>`。角色包自带 MIT LICENSE 与 README，不依赖上游市场存在。
- **路径二（单包技能分发）**：只取 `role-packs/<pack>/skills/` 复制进客户端技能目录（对齐 README"仅技能"安装形态），无需市场。
- **红线**：私有市场文档示例一律占位符（`<企业内部仓库地址>`、`<TOKEN>` 等），不出现真实主机名/IP/账号/密钥；不引入 CONNECTORS/`.mcp.json` 类第三方端点配置。

## 6. 下一步

确认后进 T2（#861）：销售/财务/人力三包最小发行——按 §3 构成落 `role-packs/` 三目录 + `manifest.json`（§4.2 schema，验收状态初值 `pending`）+ 根 marketplace.json 追加 3 条目 + 每包 README（含技能表与验收状态列）；验收口径"三包可安装"。

---

变更记录：v0.1（2026-10-25）草案。
