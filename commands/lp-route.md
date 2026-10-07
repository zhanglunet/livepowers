---
description: 对一个业务请求执行 System 1 优先路由（查注册表 → HIT 执行 / MISS 探索并留证据）
argument-hint: <业务请求>
---
使用 `system1-first` 技能处理下面的业务请求：先规范化意图并运行 `lp registry find`；命中就走已固化能力，未命中按 `explore-with-evidence` 探索，结束时记录证据。

请求：$ARGUMENTS
