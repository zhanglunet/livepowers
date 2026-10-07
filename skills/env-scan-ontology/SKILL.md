---
name: env-scan-ontology
description: Use when onboarding a new database, business system, API set or customer site, starting a brownfield or greenfield delivery, or when schema / interface drift is suspected — scans read-only, builds an environment fingerprint and an ontology draft, aligns it with a preset domain ontology, and runs nightly drift detection. 接入新环境、扫描库表生成本体、检测环境漂移时使用。
---

# 环境感知与本体沉淀

**目标：**让 Agent "知道自己在哪里"。活产品的第一个能力是感知环境、初始化自己的业务世界；环境变了能发现并调整。

## 两种起点

| 起点 | 特征 | 做法 |
|---|---|---|
| **存量改造**（brownfield） | 已有大量系统、数据、接口、制度 | 先扫描"考古" → 环境指纹 → 围绕当前任务提出最小本体 → 映射 → 业务确认。原系统继续作为权威记录（System of Record） |
| **新建再造**（greenfield） | 无存量包袱 | 带预置领域本体、常用规则、原子行动出厂 → 按客户任务、样例、制度逐项确认 → 生成数据模型、工具、Skill、界面 |

两者可以组合：先加载预置骨架，再扫描补全映射与扩展。新建场景的参考指标：**从需求到第一个可演示版本的时间**。

## 步骤

1. **只读扫描。**用只读账号。SQLite 示例：
   ```bash
   python <plugin>/scripts/scan_sqlite.py <db> --fingerprint .livepowers/env/fp-$(date +%F).json \
     > .livepowers/ontology.draft.yaml
   ```
   其他数据库按同样结构查询 `information_schema`（表、列、类型、主键、外键、行数）。接口类系统读取 OpenAPI / MCP 工具清单；同时记录权限、制度文件与关键依赖。
2. **识别候选语义。**
   - 身份：主键、业务唯一键。
   - 关系：外键；`*_id` 命名推断（标 `evidence: name_inferred`，须确认）。
   - 状态：`status/state/stage` 字段 → 抽样取值 → 候选状态机。
   - 时间：事件时间还是快照时间？
   - 指标：金额、数量 → 问口径（含税？去重？确认收入还是收款？）。
3. **抽样核对，不要猜。**对候选状态字段 `select distinct`；对关系做连接计数确认基数。相同字段名只是映射线索，关键定义要有制度依据和责任人确认。
4. **与预置本体对齐**（如有），输出三类差异：
   - **可参数化**：阈值、术语、口径参数 → 客户配置；
   - **规则不同**：领域已有对象但规则不同 → 客户级扩展；
   - **对象缺失**：核心对象或状态结构缺失 → 本体版本变更（`ontology-evolution`）。
5. **标注资产归属。**每项产物标 `client`（客户数据、规则、本体实例、凭证）/ `vendor`（参考本体、模板、Harness、基准集）/ `joint`（按约定）。客户所有的内容不得进入公共参考库。
6. **补全描述面。**每个对象写一句业务含义；无法确定的标 `TODO(需业务确认)`，不要编造。
7. **评审与晋升。**经业务负责人确认后，从 `ontology.draft.yaml` 晋升为 `ontology.yaml`，写 `ontology_version`，提交 git。
8. **记录证据。**`lp evidence add --intent "env scan <系统名>" --system S2 --outcome success --verifiable`。

## 漂移检测（运行期）

把扫描注册为 System 1 能力并排入夜间作业：

```bash
python scan_sqlite.py <db> --fingerprint .livepowers/env/fp-today.json > /dev/null
python scan_sqlite.py --diff .livepowers/env/fp-yesterday.json .livepowers/env/fp-today.json   # 有漂移 exit 5
```

新表、删表、列类型变化、状态新取值 → 写入晨报，把依赖它们的已固化能力标为待复核（`system1-first` 的去固化信号）。

## 红线

- 扫描只读；绝不在扫描阶段写库。
- 敏感字段（证件号、手机号、银行卡、密码等）只记字段名与类型，不抽样、不写日志（脚本已自动跳过）。
- 推断出的关系和口径必须标"推断"，确认后才能被 Harness 使用。
- 孪生要记录数据更新时间与同步方式，不能默认是真实系统的实时完整副本。
