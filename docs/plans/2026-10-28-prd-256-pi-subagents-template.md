# PRD-256/T1：pi-subagents 式子代理分工模板设计（三角色 + 交接合同）

- 日期：2026-10-28
- 来源：2026-10-27 趋势日报 livepowers 第 2 条，用户当日拍板采纳
- trend issue：[zhanglunet/trend#1280](https://github.com/zhanglunet/trend/issues/1280)
- 中央 PRD：`trend/adopted/PRD-256-livepowers-pi-subagents-template.md`
- 状态：T1 设计稿，待评审；实现类任务（T2–T4）只开 PR 不合并

## 1. 目标与非目标

**目标**：为 pi 会话内提供一套子代理分工**模板包**（Markdown/JSON，非代码框架）：探索 / 实现 / 验证三角色 + 交接合同（输入、产物、验收三要素固定字段）；会话内分工、结果回主会话汇总。

**非目标**：
- 不做编排引擎——没有调度器/进程管理，模板只是给主会话 agent 的**结构化指令与格式约定**；
- 不替代 PRD-112 并行专家编排——112 是跨会话的专家 agent 编排（有基础设施），本条是**pi 会话内的轻量分工**；边界说明归 T4；
- 不绑定 pi 特有私有 API——模板全部用 pi 的公开会话机制（子代理派发 + 结果回传）表达。

## 2. 与既有能力的划界

| 既有能力 | 关系 |
|---|---|
| PRD-112 并行专家编排 | 112 = 专家 agent 编排（基础设施级）；256 = 会话内分工模板（零基础设施）。T4 出选用指引：有跨会话持久需求走 112，单会话内分工走 256 |
| 既有角色包机制（role-skill-pack 系） | 角色包定义"我是谁"；256 定义"怎么分活与交接"——可组合（角色可被指派为子代理） |
| PRD-255 收录安检 | 若模板包进市场收录，照走 255 安检；模板无代码，风险面天然小 |

## 3. 方案设计

### 3.1 三角色定义（模板包核心）

| 角色 | 职责 | 明确不做 |
|---|---|---|
| `explore`（探索） | 只读侦察：定位相关文件/约定/约束，产出结构化侦察报告 | 不改文件、不装依赖 |
| `implement`（实现） | 按 spec 写最小实现 + 测试 | 不扩 spec 范围、不部署 |
| `verify`（验证） | 按 acceptance 独立验收：跑测试、对照验收标准逐条给证据 | 不修代码（发现问题打回，不自己顺手改） |

角色模板各一页 Markdown：职责、输入要求、产出格式、禁止事项、打回路径。角色间**无横向通信**——一切经主会话中转。

### 3.2 交接合同（`handoff-v1`，T1 核心交付）

每次派发与回传都带同构合同（JSON frontmatter 或独立 JSON）：

```json
{
  "schema": "handoff-v1",
  "task_id": "hb_<uuid>",
  "from": "main|explore|implement|verify",
  "to": "explore|implement|verify|main",
  "input":  { "spec_ref": "<输入说明的引用或内联短文>", "files": ["<相对路径>"], "constraints": ["<红线/边界一句话>"] },
  "expect": { "artifacts": ["<预期产物名>"], "acceptance": ["<可判定的验收句，逐条>"] },
  "result": { "status": "done|blocked|rejected", "artifacts": ["<实际产物>"], "evidence": ["<验收证据：测试名/命令/输出摘要>"], "notes": "" }
}
```

硬规则：
1. `acceptance` 逐条**可判定**（能跑命令/能看文件），"做好一点"类措辞不算；
2. `verify` 打回时 `result.status: rejected` + `evidence` 指向失败验收条目——`implement` 修复后重新出合同（新 task_id，引用原 task_id），**不允许 verify 自己修**；
3. 主会话汇总 = 收集三份合同的 `result`，按验收条目对照呈现；合同本身即汇总材料，不需要额外写报告。

### 3.3 模板包结构（T2）

```
templates/pi-subagents/
  README.md               # 何时用/何时不用（指向 112）
  roles/explore.md
  roles/implement.md
  roles/verify.md
  handoff.schema.json     # handoff-v1 JSON Schema
  example-walkthrough.md  # 一个虚构任务的三角色完整走查（T3 示范蓝本）
```

纯模板零代码；`handoff.schema.json` 供机器校验合同完整性（T2/T3 的测试即"示范走查的合同全部过 schema 校验"）。

### 3.4 会话内编排示范（T3）

`example-walkthrough.md`：虚构任务（给既有 CLI 加一个小子命令）走三角色全程——主会话派 explore（回侦察报告）→ 派 implement（回产物+自测证据）→ 派 verify（打回一次演示 rejected 流转 → 修复 → 通过）→ 主会话汇总。示范同时是 T5 验收脚本。

## 4. 安全红线

1. 只借形态零拷贝：上游 pi-subagents 许可证实测 **MIT**（License API），仅借鉴"三角色+交接合同"形态，角色定义/合同 schema/示范全部本仓原创，不复制其文案与文件；
2. 模板不含密钥/内网主机名；示范用虚构任务与占位路径；
3. verify 不修代码的独立性纪律写进模板（防"自己验收自己"）；
4. 合同含 `constraints` 字段——派发时必须携带该任务相关的红线（如"不得动 CI 配置"）。

## 5. T2–T5 任务拆分（按 PRD）

| 任务 | 内容 | 验收标准（PRD 原文口径） |
|---|---|---|
| T2 | 模板包最小实现（Markdown/JSON） | 模板可安装/加载 |
| T3 | 会话内编排示范（探索→实现→验证） | 示范可跑通并回主会话汇总 |
| T4 | 与 PRD-112 边界说明与选用指引 | 文档划清会话内分工 vs 专家编排 |
| T5 | 验收试运行：样例任务走三角色 | 交接合同齐全；无密钥；只借形态无违规拷贝 |

## 6. T5 验收标准

1. 示范任务三角色走通，全部交接合同过 `handoff.schema.json` 校验；
2. 合同三要素（input/expect/result）齐全；acceptance 逐条有 evidence；
3. 演示含一次 verify 打回→implement 修复→重新派发的完整流转（rejected 状态留痕）；
4. 主会话汇总由合同 result 对照呈现（无需额外报告文件）；
5. 模板包与示范零密钥；与上游 pi-subagents 逐段比对确认零文案拷贝。

## 7. 借鉴划界

- [nicobailon/pi-subagents](https://github.com/nicobailon/pi-subagents)：License API 实测 **MIT**（日报标注"未核实协议"，本次实测确认）。仅借鉴"探索/实现/验证三角色 + 交接合同"的分工形态，不复制其角色文案、模板文件与代码；角色边界、`handoff-v1` 字段、示范走查为本仓原创。
- 与日报原文的差异修正：日报称"未核实协议"，实测 MIT，借鉴口径维持"仅思路、零复用"。
