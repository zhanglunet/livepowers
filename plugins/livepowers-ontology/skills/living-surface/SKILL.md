---
name: living-surface
description: Use when a business application shows fixed pages and the user asks the embedded agent for an analysis or chart that no fixed page covers, when the user wants a one-off result kept as a permanent page, or when a new derived table, view or metric should become part of the fixed structure. 活软件里出次抛分析展示、或把次抛长成固化表结构与固定页时使用。
---

# 活软件的生长面

活软件同时承载三类需求：**存量固化**（固定页，CPU 按公式算）、**新增固化**（从次抛长出来、验收后变成新的固化结构）、**次抛**（当场分析，用完即弃）。次抛不算生长；能把语义需求长成新的表结构和固定页才算。长出来的东西仍然是固化的——准确、快、便宜，不靠模型每次"想"。

面向具体业务，准确性、安全性、确定性的要求比通用对话高得多：**数字必须来自确定性查询，写操作不经过展示面，新结构不经验收不上线。**

## 先查固定页

先走 `system1-first`。命中的能力带"固定页"时直接打开它，不要重新分析。未命中再做次抛。

## 次抛：一次性分析展示

1. 按 `templates/surface.json` 写展示面描述，`tier: ephemeral`。只写组件（kpi / table / bar / line / filter）和数据源；**每个数据源都带只读查询**，只引用本体里的表、视图或只读能力。数字由数据库算，模型只负责编排查询和挑组件。
2. 校验，不通过不展示：
   ```bash
   lp surface validate <surface.json>     # 格式、组件、本体引用、只读查询、无可执行代码、不引用写操作能力
   ```
3. 宿主按 query 计算数据并渲染，界面上标"次抛，未经验收"。宿主支持 A2UI 的，用 `lp surface a2ui <surface.json> --db <sqlite>` 转成 A2UI v0.9.1 消息下发。
4. 记录（同时写一条 S2 证据）：
   ```bash
   lp surface record <surface.json> --intent "<规范化意图>" [--db <sqlite>]
   ```
   只落盘元数据：查询与参数、行数、结果哈希、数值列合计。**明细行不进 git**；宿主要缓存明细，放进 `.livepowers/cache/`（`lp init` 已把它排除在 git 外），会话结束即删。

## 生长：把次抛长成固化结构

用户说"以后就看这个"、或同一意图反复次抛（`lp candidates` 会列出），就申请固化：

```bash
lp surface promote <记录文件> --by <申请人>     # 建看板任务，进入固化候选（排在候选最前）
```

然后按顺序：

| 步骤 | 做什么 | 依赖 |
|---|---|---|
| 1 规格 | 把次抛的口径、粒度、维度写成规格 | `ontology-grounded-spec` |
| 2 本体 | 新视图 / 新表 / 新指标先进本体（`views:` 或 `objects:`），升版本 | `ontology-evolution` |
| 3 生成 | 写 DDL（视图或物化表）、回滚脚本、固化展示面（`tier: fixed`，数据源指向新结构）、测试 | `crystallize-to-system1` |
| 4 孪生 | `lp surface deploy <fixed> --env twin --twin --db <孪生库> --ddl <sql> --rollback <sql>` | |
| 5 对账 | `lp surface reconcile <记录文件> <fixed> --db <孪生库>`：按记录的查询重算，与新结构逐项比行数、哈希、合计；不一致必须解释并修正 | |
| 6 验收 | 四道门，采纳人不能是生成者 | `acceptance-gates` |
| 7 生产 | `lp surface deploy <fixed> --env prod --by <执行人> --db ... --ddl ... --rollback ...`；失败自动回滚。非 SQLite 用自己的迁移工具执行后 `--external --verified-by <核验人>` 记回执 | |
| 8 注册 | `lp registry add --kind view --ui <fixed> ...`；只认 `--env prod` 且展示面内容与部署时一致的回执，否则拒绝 | |

注册后 `lp pages list` 就会列出这页，下次同类请求直接走 System 1。

## 去固化

口径变化、环境漂移、连续失败时 `lp registry retire`，固定页自动从目录下线，回到次抛（`nightly-crystallization-review`）。

## 红线

- 展示面里出现脚本、事件处理器、内嵌结果数据——拒绝。展示面只传数据与组件描述。
- 次抛用写库账号，或展示面上放"转交""审批"之类按钮——写操作走 `oltp-action-safety`。
- 孪生对账通过就注册——`lp registry add` 只登记，不建表；没有生产回执的固定页背后是空的。
- 把次抛结果当正式口径导出或引用。

## 反模式

| 借口 | 反驳 |
|---|---|
| "模型已经算出来了，直接展示数字" | 数字必须来自有查询文本的确定性计算，模型写出来的数字不可追溯 |
| "这个次抛用户很满意，先挂成固定页再补验收" | 未经对账和验收的固定页会被当成正式口径；先走完生长步骤 |
| "明细一起存下来，方便以后对账" | 对账靠重跑记录的查询；明细进 git 就永久留在历史里 |
| "新视图很简单，不用进本体" | 不在本体里的对象展示面校验不过；缺对象就提本体变更，不用脚本掩盖 |
