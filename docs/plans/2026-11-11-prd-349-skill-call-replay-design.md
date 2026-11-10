# PRD-349/T1：skill 调用重放包设计（同一输入下 skill 行为可重放）

> trend issue #1628。对应 PRD-349（2026-10-30 日报遗留第 5 条，用户「继续」按既定流水线立项）。
> 设计日：2026-11-11 · 目标仓库：zhanglunet/livepowers
> 状态：T1 设计草案，待评审。仅设计文档（纯加法 .md）；重放账本内核（T2）、重放闸门（T3）、划界断言（T4）、全链验收（T5）按本设计后续落地。
> 示例全部虚构占位（`写周报` 占位风格），不出现真实主机名、IP、账号、密钥。

## 0. 红线

| # | 红线 | 落地方式 |
|---|---|---|
| R1 | **重放包三件套齐备** | `{input_fingerprint（中文触发指令原文 digest）, decisions（skill 版本+参数+歧义候选处理）, output（结果摘要）}` 缺一拒绝入账（T3） |
| R2 | **重放零执行** | 重放只复算解析/选择层（skill_ref_resolver.resolve 注入式，PRD-227 登记册形态注入）——**零 skill 实际执行**零网络（T4 AST） |
| R3 | **对不上即报账本失败** | 重放解析结果与包内不一致 → REPLAY_MISMATCH 显形落失败证据（中文名解析不稳定即显形），零静默换新结果 |
| R4 | **账本 append-only** | ReplayLedger 只增不删 |
| R5 | 占位符纪律 | T5 检查覆盖本文件 |
| R6 | 实现类 PR 只开不合并 | 等用户 review |

## 1. 借鉴对象、许可证与不复用红线

beenuar/AiSOC（MIT，2026-11-11 实测）+ CopilotKit/OpenBot（MIT，实测）——只借鉴「可重放决策账本」形态；包 schema 按本仓中文 skill 域自研，零代码复用，不引入原仓依赖。

## 2. 与既有机制划界

| 维度 | PRD-349（本条） | PRD-279 安装快照 | PRD-171 对抗验收 | PRD-341 checklist |
|---|---|---|---|---|
| 管什么 | 调用行为**可重放** | 安装可逆 | 独立 verifier | 生产化成熟度 |
| 重放 | 解析层复算 | 版本回滚 | 独立再验 | 无 |
| 执行语义 | 零 skill 执行（R2） | 回滚写 | 验证写 | 只读机检 |

## 3. 重放包设计

### 3.1 schema（T2 预埋）

```json
{"schema": "skill-call-replay-pack/v1",
 "input_fingerprint": {"utterance": "写周报（占位）", "utterance_digest": "sha16:…",
   "registry_version": "vN", "registry_digest": "sha16:…"},
 "decisions": [{"resolved_skill": "weekly-report（占位）",
   "trigger_conditions": "…（占位）", "refusal_code": null}],
 "output": {"result_digest": "sha16:…", "summary": "结果摘要（占位）"}}
```

### 3.2 流程（确定性）

指纹复核（utterance/registry digest 不符 → REPLAY_INPUT_DRIFT 拒绝）→ 注入同一登记册快照重放 skill_ref_resolver.resolve → 解析结果逐字节比对 → REPLAY_OK / REPLAY_MISMATCH。

## 4. 失败闸门（T3 落地）

| 错误码 | 触发 | 行为 |
|---|---|---|
| REPLAY_INPUT_DRIFT | 指令/注册表指纹不符 | 拒绝重放 |
| REPLAY_MISMATCH | 解析结果不一致 | 显形+失败证据入账 |
| PACK_INCOMPLETE | 三件套缺一 | 拒绝入账 |

## 5. 衔接

T2 内核；T3 闸门（三码+R2 零执行 AST）；T4 划界（与 279/171/341 划界钉值+registry 快照注入）；T5 样例回放+MISMATCH 演练+文档无密钥。

## 6. 开放问题

1. registry 快照来源（重放需当时注册表版本——倾向包内存 registry_digest 并要求注入方提供同版本快照，缺档拒绝显形，待 T2）；
2. 歧义候选重放的比对口径（候选集合逐字节 vs 集合等价——倾向逐字节含序，解析序即决策，待 T2）。
