# 并行专家编排模板

复制整个 `templates/parallel-experts/` 目录，把花括号占位符换成自己的编排名、专家、模块和对象，再使用。未替换前不要对真实对象运行。

这套模板只规定文件与字段。它没有运行器，也不注册为技能。

## 文件

| 文件 | 作用 |
|---|---|
| `orchestra.yaml` | 阶段、只读专家、条件增派、唯一写入者、合并规则、产物路径 |
| `envelope.md` | 同一轮发给每位只读专家的信封 |
| `agents/specialist.md` | 只读专家骨架，工具限于 Read、Grep、Glob |
| `agents/writer.md` | 唯一写入者骨架，须先有人工门 `confirm-write` |
| `orchestrator.md` | 编排者的四个阶段 |
| `schema/finding.schema.json` | 单条发现 |
| `schema/report.schema.json` | 合并报告 |
| `NOTICE` | 许可证与「复用上游源码时必须保留版权声明」 |

## 阶段

1. `detect` 写上下文，不派发专家。
2. `dispatch` 在同一轮派发所有命中的只读专家。
3. `synthesize` 按发现 `id` 去重，保留更高严重度，写出报告。
4. `write` 等人确认后，才派发写入者。

## 占位符

只使用花括号占位符，例如 `{orchestra-name}`、`{target}`、`{run-id}`、`{write-root}`。不要写入真实主机名、IP、账号或密钥。
