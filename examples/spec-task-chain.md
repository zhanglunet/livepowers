# 规格任务 ID 贯通示例

这个示例演示如何把同一个稳定任务 ID 串在规格、夜间作业契约和任务看板中。命令要求从仓库根目录运行，并使用 Python 3。

## 1. 定义规格任务

保存为 `examples/spec-task-chain.spec.md`：

```markdown
# 合同字段抽取

## 目标对象
合同文件与抽取结果。

## 验收样例
| # | 输入 | 预期结果 |
|---|---|---|
| 1 | 含合同编号、金额和日期的文件 | 三个字段均有来源引用 |

## 任务清单
- T001 [P] 定义抽取字段与来源引用契约
- T002 编写抽取和边界测试
```

`T001` 是规格中的稳定任务 ID；`[P]` 表示它可以与其他独立任务并行。

## 2. 在作业契约中引用 T001

保存为 `examples/spec-task-chain.job.json`：

```json
{
  "model_horizon_minutes": {"medium": 60},
  "jobs": [
    {
      "job_id": "contract-fields-001",
      "spec": "examples/spec-task-chain.spec.md",
      "spec_task": "T001",
      "tenant": "demo",
      "stage_id": "define-fields",
      "dependency": [],
      "priority": 2,
      "earliest_start": "20:00",
      "deadline": "08:00",
      "model_capability": "medium",
      "quality_floor": "all_fields_have_source=true",
      "expected_minutes": 30,
      "resources": {"cpu": 2, "expected_tokens": 20000},
      "max_cost": 5,
      "retry_limit": 1,
      "stop_condition": "one failed validation",
      "checkpoint": "artifacts/contract-fields-001/",
      "preemptible": true,
      "resume_policy": "from_checkpoint",
      "data_classification": "internal",
      "allowed_location": "on-prem",
      "handoff": {"actual_end_state": "artifacts/contract-fields-001/fields.json", "checker": "schema-checker"},
      "acceptance": "field schema validates and each field has a source citation"
    }
  ]
}
```

验证作业引用确实存在于规格中：

```bash
python3 scripts/lp.py job validate examples/spec-task-chain.job.json
```

## 3. 把同一任务放入本地看板

初始化本地 Livepowers 状态（已有 `.livepowers/` 时可跳过），再创建看板任务：

```bash
python3 scripts/lp.py init
TASK_ID=$(python3 scripts/lp.py task new \
  --title "定义合同抽取字段契约" \
  --intent "define contract extraction fields" \
  --spec examples/spec-task-chain.spec.md \
  --spec-task T001)
python3 scripts/lp.py task show "$TASK_ID"
```

`task show` 应显示规格路径和 `spec_task: T001`。这样，规格任务、作业 `contract-fields-001` 和看板条目共同指向 `T001`。
