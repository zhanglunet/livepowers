# livepowers-role-hr —— 人力/合规角色包

面向人力角色的一键安装 skill 包：把「数字岗位规格：任务归属与人在回路 → 信任域分级与可审计协作」加通用方法底座打包发行。纯 Markdown + JSON，无构建依赖；企业可按 README 自行建立私有市场。

## 用途

- 岗位与流程数字化先定规格：`digital-role-spec` 明确任务归属、授权边界与人在回路点；
- 招聘/流程合规涉及多 Agent 协作时，走 `auditable-agent-comms` 的信任域分级与留痕；
- 日常方法底座与全仓一致：先查固化能力、带证据探索、验收收口。

## 安装

插件市场形态（整仓克隆或 fork 后在本仓库根执行）：

```
/plugin marketplace add <本仓库本地路径或 <企业内部仓库地址>>
/plugin install livepowers-role-hr@livepowers-marketplace
```

仅技能形态：把 `skills/` 下各技能目录复制进客户端技能目录即可，无需市场。

## 快速上手

1. 收到业务请求，先 `lp registry find "<规范化意图>"`：退出码 0 = HIT 走固化能力，2 = MISS 转 `explore-with-evidence`；
2. 新岗位/新流程先用 `digital-role-spec` 定任务归属与人在回路；
3. Agent 间通信经 `auditable-agent-comms` 留痕，不私下直连；
4. 每次交付收口过 `acceptance-gates` 四道门，价值记入 `outcome-ledger`。

## 包内技能表

| 技能 | 桶 | 必含/选含 | 对抗验收状态 |
|---|---|---|---|
| `using-livepowers`（入口） | entry | 必含 | pending |
| `system1-first` | G | 必含 | pending |
| `explore-with-evidence` | G | 必含 | pending |
| `ontology-grounded-spec` | G | 必含 | pending |
| `acceptance-gates` | G | 必含 | pending |
| `outcome-ledger` | G | 必含 | pending |
| `digital-role-spec` | H | 必含 | pending |
| `auditable-agent-comms` | H | 必含 | pending |

## 验收状态与补偿规则

- **pending** = 对抗验收（PRD-171：作者≠验收者、三态记录）尚未跑完；本包状态为 `draft`，转 `published` 须门禁全过（发行清单 `../manifest.json` 为单一真值源）；
- **补偿规则**：`using-livepowers` 路由表中未随包安装的技能视为未启用，命中即按 MISS 走 `explore-with-evidence`，不改入口正文。

许可：MIT（见仓库根 LICENSE）。
