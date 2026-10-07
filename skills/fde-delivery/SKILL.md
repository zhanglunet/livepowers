---
name: fde-delivery
description: Use when delivering a domain Live Product at a customer site as a forward-deployed engineer (FDE), for brownfield retrofit or greenfield build — checks base assets, picks value-based pilot scenarios, maps the ontology and customer differences, generates the initial app through the harness, validates and releases, and pushes field innovations back through four asset gates with measured backflow. 把领域产品交付到客户现场时使用。
---

# FDE 交付

FDE 的每一次现场工作都有两种产出：交付给客户的**功能**，以及回流给产品的**资产**。只有前者，FDE 就退化成了服务业务。判断标准：项目结束后留下了什么——只留一套系统是外包；带回经验却无法复用是项目制；沉淀为 Skill、模板与产品能力才是 FDE；显著降低下一个同类客户的交付成本，才是可规模化的 FDE。

## 开工前：五类底座资产

- [ ] 领域本体包（对象、关系、状态、指标、规则、词汇）
- [ ] 本体孪生与数据契约（OLAP / OLTP 规范表与视图、映射方式）
- [ ] 原子行动与 CLI（每项声明输入输出、权限、前置条件、效果）
- [ ] 领域 Harness（技能、规格模板、界面组件、仿真与测试环境、工具注册、运行观测）
- [ ] 验收样例（典型问题、预期结果、边界与错误案例）

缺哪项，先向产品团队要，不要在现场从零造。

## 落地三步：先白盒，再契约，后证据闭环

1. **先白盒。**选一个有代表性的场景，把交付拆成可见步骤，标注对象、状态、产物和责任主体，找出反复返工的原因。
2. **再契约。**把关键语义、不变量、权限和完成标准做成版本化约定，接入自动检查与场景回放，先让一项稳定任务可靠运行。
3. **后证据闭环。**建立独立审查和业务采纳机制，把执行记录、异常与修复回写到本体、契约库、工具、Skill 与场景集，再扩大复用。

试点至少展示**一次完整转化**：Agent 处理已有能力无法覆盖的需求 → 形成经确认的本体与候选能力 → Harness 验证并发布 → 下一次同类任务直接使用固化成果。

## 第 1 步：从业务价值确定首批场景

- 每个场景四项齐全才开工：**业务负责人、当前基线、目标结果、验收样例**（`lp outcome baseline`）。
- **双轨选点**：一个降本 / 提效场景 + 一个增收场景；每轮 3–5 个可量化闭环。
- 优先"基数大、提升比例小也显著"的场景，以及"高频 + 可验证 + 痛点明确"的场景（它们也最快能固化）。

## 第 2 步：本体映射与客户差异

1. 运行 `env-scan-ontology`（存量改造先扫描，新建再造从预置本体出发）。
2. 差异三分：可参数化 → 客户配置；规则不同 → 客户级扩展；核心对象缺失 → 本体版本变更（`ontology-evolution`）。
3. 每项资产标归属：客户所有 / 供方沉淀 / 共创。
4. **映射验收用真实样例**，不是只验证"连上了"。

## 第 3 步：通过 Harness 生成初始应用

1. 每个场景走 `ontology-grounded-spec`。
2. `system1-first`：领域产品已有的能力直接复用。
3. 缺的走 `explore-with-evidence`；OLTP 动作过 `oltp-action-safety`。
4. FDE 的主要工作是**主持业务对象与行动边界的确认、修正业务语义与结果**，不是逐页手写应用。Agent 辅助拟定契约，人确认业务含义与授权，机器验证契约，人在证据上采纳结果。

## 第 4 步：验证发布，建立生长机制

1. 先在本体孪生或隔离环境验证，再用客户样例业务验收（`acceptance-gates`）。
   - OLAP 看：口径、粒度、关联、金额、权限、时效、预算。
   - OLTP 看：前提、并发、幂等、事务、审批、异常恢复。
2. 通过后 `crystallize-to-system1` 组装能力包、注册、发布到客户实例。
3. 打开证据采集，安排 `nightly-crystallization-review`，让产品在现场继续生长；交付运营与接管方案。
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

| 维度 | 指标 |
|---|---|
| 效率 | 首次价值交付时间；单个新功能从提出到验收的时间；专属开发量 |
| 质量 | 验收 / 回归通过率；指标核对通过率（OLAP）；幂等与事务测试通过率（OLTP）；门禁覆盖率；返工与回撤轮次 |
| 生长 | System 2 占比变化；新增固化能力数；人工接管比例 |
| 资产化 | 资产回流率；跨客户资产复用率；第二个同类客户的交付周期下降 `1 − T₂/T₁` 与边际成本下降 `1 − C₂/C₁` |
| 经济 | 验收任务平均成本（`outcome-ledger`） |
| 业务 | 场景目标结果的实际改善 |

FDE 考核用双指标：**业务结果增量 + 对产品的资产贡献**。

**警示信号：**功能生成很快，但本体映射反复返工、交易行为难以复核；或第十个同类客户仍需要和第一个一样多的人月——都说明还没有形成可规模化的交付能力。

## 节奏建议

现场嵌入是"脚手架"不是"房子"：设限时冲刺的上线目标，控制人力投入与收入的比例上限，每个周期把现场定制回收为可复用的配置与模板；产品平台把 FDE 当作"第二用户"。
