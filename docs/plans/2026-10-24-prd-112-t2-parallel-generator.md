# PRD-112/T2：并行专家模板接入 harness 生成器

> 状态：生成器已能一键铺骨架，供评审。对应 trend 跟踪 #560。
> 范围：给 `scripts/gen_harness.py` 增加一条并行专家路径。不新增技能，不实现运行器。

## 1. 决定

编排规格不塞进 `capability.yaml`。那份 schema 会拒绝未知字段，而且命令、存储与专家槽位不是同一份契约。同一脚本用 `--parallel-experts` 切换路径：读一份短规格，按 `templates/parallel-experts/` 铺目录。

阶段文案、合并规则、工具列表、门禁、提示路径和两份 JSON Schema 都从模板读取或原样复制。生成器不另写一套契约。

专家槽位与 T1 骨架一致：恰好 3 个只读专家（前两个 `when: always`，第三个是条件占位符）和 1 个写入者。模块名在规格里不重复。`target.value` 必须是花括号占位符，生成期不写入具体对象。

## 2. 一键生成

```bash
python3 scripts/gen_harness.py --parallel-experts -o . examples/parallel-experts/page-review.yaml
```

输出：

```
harness/page-review/
  README.md
  NOTICE
  orchestra.yaml
  envelope.md
  orchestrator.md
  agents/specialist.md
  agents/writer.md
  schema/finding.schema.json
  schema/report.schema.json
  spec.yaml
```

`spec.yaml` 是输入原样存档。其余 9 个文件与模板对应。`NOTICE`、两份 schema、`agents/specialist.md` 逐字节复制。编排名写入 `orchestra.yaml`、`orchestrator.md`、`envelope.md`；写入者 id 写入 `agents/writer.md`。`{target}`、`{run-id}`、`{expert-id}`、`{write-root}` 留给每次运行前替换。

退出码沿生成器旧例：`0` 成功，`1` 校验或读写失败，`2` 用法错误。`--json` 多一个 `kind: parallel-experts`。不带该旗标时，输出形状与原来的 capability 路径相同。

规格里出现地址、邮箱或密钥样式时拒绝，错误信息不回显原文。

## 3. 验收

`python3 -m unittest tests.test_gen_parallel_experts tests.test_parallel_expert_template -v`

生成物要能被标准库解析，阶段、角色、工具、门禁、合并规则、发现/报告必填字段与 T1 一致，且目录内无地址或密钥样式。
