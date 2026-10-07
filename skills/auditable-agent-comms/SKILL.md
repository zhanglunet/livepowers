---
name: auditable-agent-comms
description: Use whenever multiple agents (dispatcher / executor / reviewer, or agents across teams or organizations) communicate and the exchange must be logged, auditable, replayable and metered — picks direct, switch-relayed or sidecar logging by trust domain, separates coordination from content, uses a shared task id and contract version, and audits receipts. 多个 Agent 互相通信时使用。
---

# 可审计的智能体协作

**原则：智能体之间没有暗流通道。**看不见的协作无法被审计，也无法被评估和固化。可审计是可固化的前提。

## 1. 先判断信任域

| 信任域 | 方式 | 要求 |
|---|---|---|
| 可信沙箱内（同一任务、同一身份、受控资源） | 允许直连 | 沙箱边界记录输入输出，事后可复现 |
| 组织内跨团队 / 跨机器 | 交换机中转 或 旁路 Sidecar | 全量日志、可回放、按 Agent 计量 |
| 跨组织 / 广域 | 必须经网关 | 身份认证、策略检查、全栈审计 |

## 2. 两条线

- **协调线**：任务、结果、提问、审查、控制、回执 → 走交换机（小消息）。
- **内容线**：大块上下文（PRD、代码、文档、记忆）→ 共享工作空间 / 知识库，消息里只传引用（`--ref`）。交换机会拒绝超过 `SWITCH_MAX_BODY` 的消息体。

## 3. 消息信封

```json
{"trace_id":"t-01","task_id":"t_9f2c","contract_version":"spec-12@1.1",
 "from":"executor","to":"reviewer","type":"task|result|question|review|control|receipt",
 "body":"变更已提交，等待审查","ref":"git:feat/x@a1b2c3"}
```

交换机补全 `seq, ts, policy, prev_hash, hash`。**所有 Agent 挂在同一任务标识与契约版本上**：分工可以复杂，验收必须唯一。

## 4. 使用自带的交换机

```bash
python <plugin>/scripts/agent_switch.py serve --port 7070 --log .livepowers/comms.jsonl
python <plugin>/scripts/agent_switch.py send --from supervisor --to executor --type task \
  --body "实现 issue #12" --trace t1 --task t_9f2c --contract spec-12@1.1
# 收件：GET http://127.0.0.1:7070/inbox/<agent>
python <plugin>/scripts/agent_switch.py sidecar-log --from executor --to reviewer --type result \
  --body "完成" --ref "git:feat/x@a1b2c3" --trace t1        # 旁路模式
python <plugin>/scripts/agent_switch.py replay --trace t1 [--speed 1]   # 一键回放
python <plugin>/scripts/agent_switch.py verify                        # 哈希链防篡改
python <plugin>/scripts/agent_switch.py audit                         # 审计要点
```

策略：未知类型、超长消息体、`SWITCH_BLOCK_WORDS` 中的拦截词会被拒绝；被拒消息同样落盘。

## 5. 审计时看什么（`audit` 会列出前四项）

- 被拒绝的消息及原因；
- 没有审查或回执的 trace（链路未闭合）；
- 声称结果但没有产物引用的消息（"自我声明"）；
- 按 Agent 计的消息量（配合 Token 计量，供盈亏平衡的 c2 使用）；
- 是否有绕过交换机的通信（对比各 Agent 自身日志与交换机日志）；
- 哈希链是否完整。

## 6. 生产化建议

- 与 A2A / MCP 等开放协议对齐，由网关承担身份与策略；本脚本的信封与哈希链可作为日志格式参考。
- 日志字段对齐 OpenTelemetry GenAI 语义约定（`invoke_agent`、`execute_tool` span）。
- 规模上来后中心交换会成为瓶颈：沙箱内允许直连，只在信任域边界审计。
