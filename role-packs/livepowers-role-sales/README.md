# livepowers-role-sales —— 销售/交付角色包

面向销售/交付角色的一键安装 skill 包：把「先查固化能力 → 带证据探索 → 五段交付链 → 跟单接手 → 写操作护栏」打包发行。纯 Markdown + JSON，无构建依赖；企业可按 README 自行建立私有市场。

## 用途

- 每天从业务请求开始：先查注册表（System 1），命中直接用固化能力，MISS 才探索；
- 现场交付与跟单：五段交付链（扫描 → 规格 → 探索 → 验收 → 台账）、止损冻结与换人重开；
- 涉及 CRM 录入等写操作时，先仿真后执行。

## 安装

插件市场形态（整仓克隆或 fork 后在本仓库根执行）：

```
/plugin marketplace add <本仓库本地路径或 <企业内部仓库地址>>
/plugin install livepowers-role-sales@livepowers-marketplace
```

仅技能形态：把 `skills/` 下各技能目录复制进客户端技能目录即可，无需市场。

## 快速上手

1. 收到业务请求，先 `lp registry find "<规范化意图>"`：退出码 0 = HIT 走固化能力，2 = MISS 转 `explore-with-evidence`；
2. 交付工作按 `fde-delivery` 五类底座资产与 `delivery-chain` 五段链编排；
3. 跟单接手/止损按 `takeover-handling`；
4. 任何写操作先过 `oltp-action-safety` 的执行阶段步骤（确认点、幂等键）；
5. 每次交付收口过 `acceptance-gates` 四道门，价值记入 `outcome-ledger`。

## 包内技能表

| 技能 | 桶 | 必含/选含 | 对抗验收状态 |
|---|---|---|---|
| `using-livepowers`（入口） | entry | 必含 | pending |
| `system1-first` | G | 必含 | pending |
| `explore-with-evidence` | G | 必含 | pending |
| `ontology-grounded-spec` | G | 必含 | pending |
| `acceptance-gates` | G | 必含 | pending |
| `outcome-ledger` | G | 必含 | pending |
| `oltp-action-safety` | G | 必含（涉写） | pending |
| `fde-delivery` | S | 必含 | pending |
| `delivery-chain` | S | 必含 | pending |
| `takeover-handling` | S | 必含 | pending |

## 验收状态与补偿规则

- **pending** = 对抗验收（PRD-171：作者≠验收者、三态记录）尚未跑完；本包状态为 `draft`，转 `published` 须门禁全过（发行清单 `../manifest.json` 为单一真值源）；
- **补偿规则**：`using-livepowers` 路由表中未随包安装的技能视为未启用，命中即按 MISS 走 `explore-with-evidence`，不改入口正文。

许可：MIT（见仓库根 LICENSE）。
