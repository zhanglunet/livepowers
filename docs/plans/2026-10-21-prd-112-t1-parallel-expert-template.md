# PRD-112/T1：并行专家编排模板结构

> 状态：模板结构已落地，供评审。对应 trend 跟踪 #559。\
> 范围：只有模板文件与契约测试。不新增技能，不改路由表，不实现运行器。

## 1. 目标

把「多名只读专家同一轮判断、合并之后才允许一位写入者落盘」做成可复制的模板。复制 `templates/parallel-experts/` 后替换占位符即可得到一套编排骨架。

非目标（留给后续任务）：

- 不实现调度脚本或 `lp` 子命令。
- 不把编排者注册进 `skills/`，因此不改 `using-livepowers` 路由表，也不增加技能计数。
- 不提供行业检查项、外部数据源或报告导出。

## 2. 目录

```
templates/parallel-experts/
  README.md
  NOTICE
  orchestra.yaml
  envelope.md
  orchestrator.md
  agents/specialist.md
  agents/writer.md
  schema/finding.schema.json
  schema/report.schema.json
```

唯一位置是仓库根 `templates/parallel-experts/`。插件拷贝留到真有技能引用这些文件时再做，避免两份模板分叉。

## 3. 角色

| 角色 | 人数 | 何时出现 | 工具 |
|---|---|---|---|
| 编排者 | 1 | 四个阶段都在 | Read, Grep, Glob |
| 只读专家 | 多名，由 `experts` 声明 | `dispatch` 同一轮 | Read, Grep, Glob |
| 写入者 | 恰好 1 | `confirm-write` 通过之后 | Read, Edit, Write |

`when: always` 的专家每轮都派发。`when` 为其他占位符时，仅当 `detect` 写入的上下文满足该条件才派发。写入者不参与这一轮。

## 4. 字段

`orchestra.yaml` 顶层字段：`name`、`description`、`version`、`target`、`phases`、`experts`、`writer`、`merge`、`output`。

- `target.kind` / `target.value`：判断对象。值用 `{target}`，不写真实地址。
- `phases`：固定四个 id：`detect`、`dispatch`、`synthesize`、`write`。
- `experts[]`：`id`、`role`（只许 `readonly`）、`when`、`modules`、`prompt`。
- `writer`：`id`、`role`（只许 `writer`）、`tools`、`gate`（固定 `confirm-write`）、`prompt`。
- `merge`：`dedupe_key` 为 `id`；`keep` 为 `highest-severity`；`rank` 从高到低为 critical、high、medium、low、info。
- `output.root`：`.livepowers/orchestras/{orchestra-name}/runs/{run-id}`。其下固定相对名 `context.json`、`findings.json`、`report.json`。`detect` 另写 `findings.detect.json`；人工确认写 `confirm-write.json`；写入者追加 `writes.json`。

信封字段见 `envelope.md`：`orchestra`、`run_dir`、`target`、`context_file`、`modules`、`prior_findings`、`return`。专家只返回符合 `schema/finding.schema.json` 的 JSON 数组。

发现必填：`id`、`expert`、`module`、`severity`、`summary`、`evidence`、`falsify`。报告必填：`orchestra`、`run_id`、`target`、`experts`、`findings`、`generated_by`。报告里的 `experts` 不含写入者。`generated_by` 不得与确认记录里的 `by` 相同。

## 5. 占位符

模板内只出现花括号占位符，不出现真实主机名、IP、账号或密钥。契约测试扫描 `templates/parallel-experts/` 下全部文件。

## 6. 验收

T1 通过的条件：

1. 第 2 节列出的文件都在，且 README 的文件表与之对应。
2. `orchestra.yaml` 含第 4 节的顶层字段、三个只读专家槽位、一个写入者，以及四段阶段 id。
3. 只读专家工具行为 `Read, Grep, Glob`；写入者工具行为 `Read, Edit, Write`；编排者自身不带 Write。
4. 两份 JSON Schema 可被标准库解析，必填字段与严重度枚举与第 4 节一致。
5. 目录内无 `http://`、`https://`、IPv4、`localhost`、邮箱样地址或常见密钥前缀。
6. `NOTICE` 写明：未复用上游源码；一旦复用，版权声明与许可全文不得删除。
7. `python -m unittest tests.test_parallel_expert_template -v` 通过。

## 7. 合规

形态借鉴公开的并行专家编排：识别上下文、同一轮派发只读专家、合并发现、写入与判断分开。本模板的文件名、字段名和正文是按 livepowers 现有约定另写的：产物放在 `.livepowers/` 下，技能骨架沿 `templates/skill.md`，YAML 用手写块式列表以便日后用标准库做浅检查。

没有复制上游命令、脚本、行业阈值或页脚。因此 `NOTICE` 不嵌入上游版权人姓名；它规定了复用源码时必须补上并保留该声明。
