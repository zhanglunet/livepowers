---
name: fde-delivery
description: Use when delivering a domain Live Product at a customer site as a forward-deployed engineer, for a brownfield retrofit or a greenfield build, or when field innovations must flow back into the product. 把领域产品交付到客户现场时使用。
---

# FDE 交付

FDE 的每一次现场工作都有两种产出：交付给客户的**功能**，以及回流给产品的**资产**。只有前者，FDE 就退化成了服务业务。判断标准：项目结束后留下了什么——只留一套系统是外包；带回经验却无法复用是项目制；沉淀为 Skill、模板与产品能力才是 FDE；显著降低下一个同类客户的交付成本，才是可规模化的 FDE。

## 开工前：五类底座资产
开工前向产品团队核对五类底座资产，避免在现场从零造：领域本体包、本体孪生与数据契约、原子行动与 CLI、领域 Harness、验收样例。

## 落地三步：先白盒，再契约，后证据闭环

1. **先白盒**：选代表性场景拆解为可见步骤，标注对象、状态、产物与责任主体。
2. **再契约**：关键语义、不变量、权限与完成标准版本化约定，接入自动检查。
3. **后证据闭环**：独立审查与业务采纳，将执行记录、异常与修复回写本体、契约库、工具、Skill 与场景集。

试点展示至少一次完整转化：未覆盖需求 → 产生本体与候选能力 → Harness 验证发布 → 下次直接复用。

## 第 1 步：从业务价值确定首批场景

- 每个场景四项齐全才开工：**业务负责人、当前基线、目标结果、验收样例**（`lp outcome baseline`）。
- **双轨选点**：一个降本 / 提效场景 + 一个增收场景；每轮 3–5 个可量化闭环。
- 优先"基数大、提升比例小也显著"的场景，以及"高频 + 可验证 + 痛点明确"的场景（它们也最快能固化）。

## 第 2 步：本体映射与客户差异

1. 运行 `env-scan-ontology`（存量改造先扫描，新建再造从预置本体出发）。
2. 差异三分：可参数化、规则不同、核心对象缺失，分别按 `env-scan-ontology` 与 `ontology-evolution` 处理。
3. 每项资产标归属：客户所有（`client`）/ 供方沉淀（`vendor`）/ 共创（`joint`）。
4. **映射验收用真实样例**，不是只验证"连上了"。

## 第 3 步：通过 Harness 生成初始应用

每个场景走 `ontology-grounded-spec` → `system1-first`；缺能力走 `explore-with-evidence`，写动作走 `oltp-action-safety`。FDE 主持业务对象、行动边界和结果确认；人确认业务含义与授权，机器验证契约，人在证据上采纳。

## 第 4 步：验证发布，建立生长机制

1. 先在本体孪生或隔离环境验证，再用客户样例业务验收，OLAP 清单见 `acceptance-gates`，OLTP 八项检查见 `oltp-action-safety`。
2. 通过后 `crystallize-to-system1` 组装能力包、注册、发布到客户实例。
3. 打开证据采集，安排 `nightly-crystallization-review`，让产品在现场继续生长；交付运营与接管方案（`takeover-handling`）。
4. 成熟能力按约定**移交客户内化**。

## 资产回流：四道门
现场创新必须**依次**通过才进入公共参考库：
| 门 | 判据 |
|---|---|
| 可抽象 | 去掉客户特有内容后仍有意义；已脱敏 |
| 可版本化 | 有版本、依赖与兼容性说明 |
| 可评测 | 有独立评测集，能在其他环境重新验证 |
| 可复用 | 在第二个环境完成适配并通过验证 |

```bash
lp asset add --name "<名称>" --kind skill --origin field --ownership vendor
lp asset gate <id> abstractable --by <评审人> --evidence <...>   # 依次 versioned / evaluated / reusable
lp asset reuse <id> --project <项目代号> --verified
lp asset list    # 资产回流率 = 入库现场创新 / 现场创新总数
```

客户数据、凭证、专有制度永远不入库：标为 `--ownership client` 的资产可以登记，但 `lp asset gate` 会拒绝它过门。能力组合定期评审，每项结论只能是：**扩大 / 保留 / 重设计 / 淘汰**。

## 交付评价

指标核算与基线管理遵循 `outcome-ledger`（首次价值交付时间、验收任务平均成本、跨客户资产复用率、增量价值 ΔV 等）。现场交付考核采用双指标：**业务结果增量 + 对产品的资产贡献**（资产回流率 `lp asset list`）。现场交付的节奏建议与警示信号见 `docs/paradigm.md`。
