# 派发信封

编排者在 `dispatch` 阶段把下面这一块原样填好，交给每一个命中的只读专家。同一轮发出的多份信封互相独立：专家看不到彼此的中间过程，只看信封里点名的文件。

路径写绝对路径。不要把大段原文贴进对话，只给文件位置。

```
ENVELOPE
orchestra: {orchestra-name}
run_dir: {absolute-run-dir}
target: {target}
context_file: {absolute-run-dir}/context.json
modules: [{module-id}]
prior_findings: {absolute-run-dir}/findings.detect.json
return: 只返回 JSON 数组，元素符合 schema/finding.schema.json，不要散文
```

填空约定：

| 字段 | 填什么 |
|---|---|
| `orchestra` | 与 `orchestra.yaml` 的 `name` 相同 |
| `run_dir` | 本次运行目录，即 `output.root` 替换占位符后的绝对路径 |
| `target` | 本次判断对象，与 `orchestra.yaml` 的 `target.value` 相同 |
| `context_file` | `detect` 阶段写出的上下文，专家只读 |
| `modules` | 该专家在 `orchestra.yaml` 里声明的模块列表，不把别人的模块塞进来 |
| `prior_findings` | `detect` 已确定的发现；专家不得重复报这些 `id` |
| `return` | 固定句，不改 |

专家返回的每条发现必须带自己的 `expert` id。没有新发现时返回空数组 `[]`。
