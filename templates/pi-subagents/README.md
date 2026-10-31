# pi 会话内子代理分工模板（探索 / 实现 / 验证）

PRD-256/T2 交付（trend #1281）：给主会话 agent 的**结构化指令与格式约定**——不是编排引擎，没有调度器。

## 何时用 / 何时不用

| 场景 | 用什么 |
|---|---|
| 单会话内一次任务需要分工（探索→实现→验证） | 本模板 |
| 跨会话持久协作、多专家并行、需要基础设施 | PRD-112 并行专家编排 |

## 用法

1. 主会话按 `roles/explore.md` 的职责边界派发探索子代理，附 `handoff.schema.json` 合同（input 必带 constraints 红线）；
2. 收到 `result` 后按合同验收，再派 `implement`（引用探索结论）→ `verify`（独立验收）；
3. verify 打回（`status: rejected`）→ implement 修复后**重新派发新合同**（引用原 task_id）——verify 不修自己验收的代码；
4. 主会话汇总 = 收集三份合同 result 对照呈现，无需额外报告。

## 文件

- `roles/` 三角色页（职责/输入/产出/禁止事项）
- `handoff.schema.json` 交接合同 JSON Schema（T2 附机器校验入口 `scripts/validate_handoff.py`）
- `example-walkthrough.md` 虚构任务三角色完整走查（T3 示范蓝本）

## 红线

零网络零密钥；constraints 派发必带；只借形态零拷贝（上游 pi-subagents 实测 MIT，未复制其任何文案）。
