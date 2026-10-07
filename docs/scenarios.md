# 场景清单与应用案例

每个场景写清：触发 → 走哪些技能 → 关键命令 → 产出。示例一律用虚构的通用业务对象（商机、订单、合同、工单）。想亲手跑一遍，看文末的"五分钟 demo"。

## 1. 周报类查询第一次来：注册表未命中

**触发**：业务问"各地区上周收入多少"，之前没做过。

**走法**：`system1-first` → MISS → 会话级小请求不建任务 → `explore-with-evidence`。

```bash
lp registry find "各地区上周收入"            # exit 2 → MISS
# Agent 在本体范围内写 SQL，小样本、带 LIMIT，用已知数字核对
lp evidence add --intent "weekly revenue by region" --system S2 --outcome success \
  --cost 0.9 --verifiable --note "exploration: .livepowers/explorations/2026-10-07-weekly-revenue.md"
```

**产出**：答案 + 一条证据 + 一份别人能接手的探索记录。第 3 次同样的请求时，Agent 会在回复末尾提示"该路径已满足固化候选条件"。

## 2. 同一件事第三次探索成功：固化为 System 1

**触发**：`lp candidates` 列出 `weekly revenue by region` 已 3 次成功、可验证。

**走法**：`nightly-crystallization-review` → `crystallize-to-system1`（TDD）→ 夜间登记产物 → 早晨 `acceptance-gates` → 注册。

```bash
lp score --freq 30 --verifiable 2 --stability 2 --c2 0.9 --c1 0.001 --K 20 --M 5 --p 0.8 --h 5   # exit 0 建议固化
# 夜间：先写测试，再写参数化 SQL / CLI，组装能力包
lp pending add --intent "weekly revenue by region" --score 9 --n-star 11.1 \
  --tests "pytest tests/weekly_revenue -q" --result pass --location branch:night/weekly-revenue --generated-by night-agent
# 早晨：人工过四道门后
lp registry add --name "Weekly revenue" --kind sql --intents "weekly revenue by region,各地区周收入" \
  --entry "python tools/weekly_revenue.py --region {region}" --tests "pytest tests/weekly_revenue -q" \
  --generated-by night-agent --accepted-by analytics-owner
lp pending done "weekly revenue by region" --by analytics-owner --accepted
```

**产出**：一项带测试、版本、生成者与采纳人的能力；之后同样的请求几乎零 Token。

## 3. 请求命中已固化能力：几乎零成本执行

**触发**：业务再问"华东上周收入"。

```bash
lp registry find "华东上周收入"    # exit 0 → HIT：cap_weekly_revenue v1.0.0 (sql)
# 核对前置条件覆盖当前请求 → 按 entry 调用
lp evidence add --intent "weekly revenue by region" --system S1 --outcome success --capability cap_weekly_revenue
```

**产出**：确定性结果；证据里 S1 占比上升。健康的活产品，S2 占比随时间下降。

## 4. 写操作：把逾期的重点商机转给主管

**触发**：销售运营要"把 30 天没有有效跟进的重点商机自动转给区域主管"。

**走法**：`system1-first` → MISS → `lp task new` → `ontology-grounded-spec`（"有效跟进"的定义是本体层变化 → `ontology-evolution`）→ `oltp-action-safety`（八项检查，先预演）→ `explore-with-evidence` 只预演 → `acceptance-gates` → 注册时 `--writes-state` 必须带测试。

```bash
lp outcome baseline --scenario stale-opps --metric "逾期重点商机数" --value 40 --target 10 --direction lower
T=$(lp task new --title "逾期重点商机移交" --intent "transfer stale opportunity" --max-loops 5 --budget 20)
lp task move $T spec --by sales-ops --reason "口径：逾期 = 30 天无有效跟进（Delta 已提）"
# 按 templates/action.yaml 填原子行动：前提、权限、事务、幂等、并发、审批、审计、补偿 + 九项测试
lp registry add --name "转交逾期商机" --kind cli --intents "transfer stale opportunity,转交逾期商机" \
  --entry "crm opp transfer-stale --days {days}" --writes-state --tests "pytest tests/test_transfer.py" \
  --generated-by agent-a --accepted-by reviewer-b
lp outcome measure --scenario stale-opps --metric "逾期重点商机数" --value 22
```

**产出**：一项写操作能力 + 台账里"逾期数 40 → 22，ΔV 为正"。

## 5. 接入一个存量 CRM：先知道自己在哪里

**触发**：进客户现场，对方有一套用了八年的 CRM。

**走法**：`env-scan-ontology`（只读扫描 → 环境指纹 → 本体草稿）→ 业务确认 → `fde-delivery` 选试点场景 → `outcome-ledger` 登记基线。

```bash
python3 scripts/scan_sqlite.py crm.sqlite --fingerprint .livepowers/env/fp-1.json > .livepowers/ontology.draft.yaml
# 业务逐个确认对象含义、状态机、指标口径 → ontology/ontology.yaml 0.1.0
```

**产出**：环境指纹、本体草稿、确认后的本体 0.1.0；非 SQLite 的库按同样结构查 `information_schema`。

## 6. 夜里发现环境变了：漂移检测与去固化

**触发**：夜间扫描发现 `opportunities.stage` 出现新取值 `on_hold`。

```bash
python3 scripts/scan_sqlite.py crm.sqlite --fingerprint .livepowers/env/fp-2.json > /dev/null
python3 scripts/scan_sqlite.py --diff .livepowers/env/fp-1.json .livepowers/env/fp-2.json   # exit 5 → 有漂移
lp registry review                      # 列出受影响、连续失败、闲置、久未复验的能力
lp registry retire cap_转交逾期商机 --reason "状态机新增 on_hold，转交规则待确认"
```

**产出**：晨报里的复核项；能力退役回到 System 2，`ontology-evolution` 提 Delta 后再固化新版本（`--supersedes`）。

## 7. 探索三轮没收敛：止损与接管

**触发**：任务 `--max-loops 3`，第 4 次 `task move ... explore` 被脚本止损（exit 4）。

**走法**：`takeover-handling`：执行者冻结并交付诊断包 → 接管人归因（规格不清）→ 回到规格或换人重开 → 接管成本入账。

```bash
lp task show t_x                                         # 轮次 3/3，看每轮假设
lp task move t_x spec --by lead --reason "缺'有效跟进'定义"
lp task move t_x explore --by agent-b --reason "口径已补，换做法" --reset-loops
lp outcome cost --scenario stale-opps --kind takeover --amount 1.5 --note "task=t_x"
```

**产出**：诊断记录、规格补丁、重开的任务；台账里接管成本不丢。

## 8. 换模型了：Harness 还值不值

**触发**：把执行模型从 model-a 换成更便宜的 model-b。

**走法**：`agent-harness-for-tools`（重跑 10 次基准；消融不再需要的约束）+ 金丝雀。

```bash
lp canary record --name core --model model-b --pass 9 --total 10 --tokens 12000
lp canary compare                                        # 通过率降 >10% 或 token 升 >30% → exit 5
lp registry review --current-model model-b               # Skill 类能力：验证模型不一致 → 待复验
lp registry verify cap_xxx --model model-b
```

**产出**：模型切换的回归结论；哪些剧本约束可以去掉（去 Harness 化）。

## 9. 多个 Agent 协作：派工、执行、评审分开且可审计

**触发**：夜间固化由 supervisor 派工、executor 实现、reviewer 评审。

**走法**：`auditable-agent-comms`：同一任务 id + 契约版本；消息经交换机或旁路日志；评审看回执不看声明。

```bash
python3 scripts/agent_switch.py serve --port 8787 --log .livepowers/comms.jsonl &
python3 scripts/agent_switch.py send --from sup --to exe --type task --body "固化 weekly revenue" --trace t1 --task t_x --contract c@1 --url http://127.0.0.1:8787
python3 scripts/agent_switch.py send --from exe --to rev --type result --body "done" --ref git:abc --trace t1 --url http://127.0.0.1:8787
python3 scripts/agent_switch.py verify --log .livepowers/comms.jsonl     # 哈希链完整
python3 scripts/agent_switch.py audit  --log .livepowers/comms.jsonl     # 被拒消息、无产物引用的"完成"
```

**产出**：可回放、防篡改的通信记录；"声称完成却无回执"会被审计点名。

## 10. 把一个岗位交给"人 + 智能体团队"

**触发**：合同审核岗要用智能体承担初审。

**走法**：`digital-role-spec`（任务归属 auto / agent / handoff / human；接管条件；KPI）+ `outcome-ledger`（岗位经济账）。

**产出**：按 `templates/digital-role.yaml` 填好的岗位规格；接管比例高就先固化、先补 Harness，再谈规模。

## 11. 跨夜的长程任务：知识加工 500 份文档

**触发**：要在夜里把 500 份合同抽取成结构化字段。

**走法**：`night-loop-planning`：强模型拆 DAG，按便宜模型可稳定运行的时长切段，每段写作业契约（实际终态、独立检查者、止损）。

```bash
lp job validate jobs/contracts-night.json     # 必填字段、悬空依赖、环、单段时长
```

**产出**：可恢复的并发作业；早晨的交付物与晨报。

## 12. 向客户说明价值：按结果计价

**触发**：客户问"这套东西到底帮我省了什么"。

**走法**：`outcome-ledger`：基线 → 测量 → 成本归集（含失败、返工、接管）→ 验收任务平均成本、首次价值交付时间、ΔV。

```bash
lp outcome report
# 逾期重点商机数: 基线 40 → 目标 10；当前 22（-45%）；增量价值 ΔV = B×u
# 验收任务平均成本 = 全部归集成本 ÷ 通过验收的任务数
```

**产出**：一份可对账的价值报告；没有基线的价值不算价值。

---

## 五分钟 demo

仓库自带 `examples/walkthrough.sh`，用一个虚构的商机数据库完整走一遍场景 1 → 4 → 6：

```bash
git clone https://github.com/zhanglunet/livepowers && cd livepowers
bash examples/walkthrough.sh
```

它依次做：环境扫描 → 登记基线 → 路由 MISS → 三轮探索留证据 → 评分 → 任务看板 → 独立验收 → 注册 → 路由 HIT → 结果台账 → 环境漂移 → 晨报。真实输出见网站的"五分钟 demo"板块。
