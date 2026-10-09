# 场景 5 隔离走查记录

使用合成 SQLite CRM（两个对象、一个外键、两条商机），实际运行只读扫描、注册表路由与基线登记。以下是执行回执，日期 2026-10-09。没有客户数据或生产系统。

```text
python3 scripts/scan_sqlite.py <isolated-workspace>/crm.sqlite --fingerprint <isolated-workspace>/fp.json
exit=0
# 本体草稿（scan_sqlite.py 自动生成）——须业务确认后才能晋升为 ontology.yaml
source: sqlite:<isolated-workspace>/crm.sqlite
ontology_version: 0.1.0-draft
objects:
  - name: accounts
    description: ""   # TODO(需业务确认) 业务含义
    identity: ['id']
    row_count: 1
    attributes:
      - {name: id, type: INTEGER, nullable: true}
      - {name: name, type: TEXT, nullable: true}
  - name: opportunities
    description: ""   # TODO(需业务确认) 业务含义
    identity: ['id']
    row_count: 2
    attributes:
      - {name: id, type: INTEGER, nullable: true}
      - {name: account_id, type: INTEGER, nullable: true}
      - {name: stage, type: TEXT, nullable: true}  # 候选状态字段，抽样取值 ['closed', 'open']：请定义状态机
      - {name: amount, type: REAL, nullable: true}
relations:
  - {from: opportunities.account_id, to: accounts.id, cardinality: many_to_one, evidence: foreign_key}
rules: []        # TODO(需业务确认) 口径、阈值、约束；每条写来源、适用范围、生效时间
permissions: []  # TODO(需业务确认) 角色与可见范围
actions: []      # TODO 原子行动（见 templates/action.yaml）
```

```text
python3 scripts/lp.py registry find 现场交付试点
exit=2
MISS —— 未命中已固化能力 → 转 System 2 探索（记得记录证据）
```

```text
python3 scripts/lp.py outcome baseline --scenario crm-pilot --metric delivery-hours --value 10 --target 5 --direction lower --owner business-owner
exit=0
已登记基线 crm-pilot/delivery-hours = 10.0
```

```text
python3 scripts/lp.py outcome report
exit=0
### 场景 crm-pilot
- delivery-hours: 基线 10.0 → 目标 5.0
- 归集成本 0.00（）
- 通过验收任务 0，未通过 0；验收任务平均成本 = —（暂无通过验收的任务）
```

扫描生成对象、外键与环境指纹；注册表 MISS，后续按 FDE 选试点和结果台账登记基线。基线是合成测试输入，不能声明真实价值改善。

业务确认门保持待办：对象含义、状态机、金额口径及权限须由业务责任人确认后，才能将草稿升为本体 0.1.0。本走查没有冒充业务确认、独立审查或生产采纳。后续发布前按 acceptance-gates 检查 OLAP 七项，写动作按 oltp-action-safety 八项检查；资产需依次过四道门并在第二环境验证。

引用走查：差异三分在 env-scan-ontology，OLAP 清单在 acceptance-gates，OLTP 在 oltp-action-safety，生长与同类交付下降指标及岗位经济账在 outcome-ledger。fde-delivery 从原 94 行缩为 65 行，减少 30.9%。
