# PRD-363/T1：上架审批收件箱设计（扫完/渲染完之后等人拍的统一出口）

> trend issue #1642。对应 PRD-363（2026-11-11 日报第 6 条，用户「继续」按既定流水线立项）。
> 设计日：2026-11-11 · 目标仓库：zhanglunet/livepowers
> 状态：T1 设计草案，待评审。仅设计文档（纯加法 .md）；收件箱内核（T2）、批阅闸门（T3）、划界断言（T4）、全链验收（T5）按本设计后续落地。
> 示例全部虚构占位，不出现真实主机名、IP、账号、密钥。

## 0. 红线

| # | 红线 | 落地方式 |
|---|---|---|
| R1 | **收件箱零自动执行** | approve/reject 只改条目状态留痕——**零上架写、零 skillpack 变更**：approved 只是「人已拍板」记录，上架动作走既有发布流程；INBOX_AUTO_EXEC_ATTEMPT 拒绝动作载荷 |
| R2 | **只读汇聚** | 统一收口三类待人工项：插件安检「需人工复核」项（PRD-247/253/255）、生成式 UI 属性白名单 dropped 复核（PRD-335 genui_gate）、市场收录边界案例——安检线继续进池先扫 |
| R3 | **每项带证据** | 逐条 `{item_id, kind, source_ref, report_ref（安检报告/genui 产物 ref）, diff_digest?, reason, state}` 缺一拒绝入箱 |
| R4 | **账本 append-only + 拒绝留痕** | reject 留 by/at/reason |
| R5 | 占位符纪律 | T5 检查覆盖本文件 |
| R6 | 实现类 PR 只开不合并 | 等用户 review |

## 1. 借鉴对象、许可证与不复用红线

backnotprop/plannotator（Apache-2.0，实测）+ pingdotgg/t3code（MIT，实测）——只借鉴「人工拍板收件箱」控制面形态；条目 schema 按本仓上架域自研，零代码复用，不引入原仓依赖。

## 2. 与既有机制划界

| 维度 | PRD-363（本条） | 安检线（247/253/255） | PRD-335 genui_gate |
|---|---|---|---|
| 管什么 | 待批项**统一出口** | 进池先扫 | 渲染判定 |
| 操作语义 | 人批/拒（零自动） | 拦截 | 丢弃显形 |
| 关系 | 消费扫描/判定产物 | 被消费 | 被消费 |

## 3. 收件箱设计

### 3.1 schema（T2 预埋）

```json
{"schema": "listing-inbox/v1",
 "items": [{"item_id": "item-001",
   "kind": "security_manual_review|dropped_props_review|market_edge_case",
   "source_ref": "genui-product/v1#dropped[0]（占位）",
   "report_ref": "安检报告 digest sha16:…（占位）",
   "diff_digest": "sha16:…（可空）",
   "reason": "白名单外属性 hack_attr 丢弃待复核（占位）",
   "state": "pending|approved|rejected", "decided_by": null, "decided_at": null}]}
```

### 3.2 状态机（确定性）

collect（三源只读汇聚）→ pending；人 approve/reject 留痕；重复裁决/未知 id 显形拒绝。approved 是「人已拍板」记录——上架走既有流程。

## 4. 失败闸门（T3 落地）

| 错误码 | 触发 | 行为 |
|---|---|---|
| INBOX_ITEM_INCOMPLETE | 证据缺一 | 拒绝入箱 |
| INBOX_DOUBLE_DECIDE | 重复裁决 | 显形拒绝 |
| INBOX_AUTO_EXEC_ATTEMPT | 条目携带上架/skillpack 写载荷 | 拒绝（R1） |

- kind 词表封闭三项。

## 5. 衔接

T2 内核；T3 闸门（三码+R1 零上架写 AST）；T4 划界（与 247/253/255/335 划界钉值）；T5 样例回放+文档无密钥。

## 6. 开放问题

1. dropped_props_review 通过后的出口（复核通过=属性白名单增补走 PRD-335 词表扩容评审 vs 放行本例——倾向只记定性，增补走既有评审，待 T2 裁决）；
2. 边界案例的立案标准（什么算 market_edge_case——倾向安检报告里带「边界」标记的自动入箱，待 T2）。
