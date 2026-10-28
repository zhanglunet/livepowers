# PRD-256/T3：三角色会话内编排示范走查（example-walkthrough）

- 日期：2026-10-28
- trend issue：[zhanglunet/trend#1282](https://github.com/zhanglunet/trend/issues/1282)
- 设计：`docs/plans/2026-10-28-prd-256-pi-subagents-template.md`（T1 §3.4 为本示范蓝本，分支 `trend/prd-256-t1-subagents-template`）
- 前置：T2 模板包 PR（`templates/pi-subagents/`：三角色页 + `handoff.schema.json` + `scripts/validate_handoff.py`）
- 状态：T3 示范稿，实现类 PR 只开不合并

## 0. 任务与走查总览

**虚构任务**：给示例 CLI `examples/echo-cli`（本示范虚构的演示项目，现实中不存在）新增一个 `status` 子命令——输出 `status: ok` 与检查项计数，支持 `--format json`。**本文件一切路径、命令、输出均为虚构演示**，不含真实主机名、账号、密钥。

派发序列（角色间无横向通信，一切经主会话中转）：

```text
main ──派 explore（hb_explore_101）──▶ explore 回传：侦察报告 done
main ──派 implement（hb_impl_101）──▶ implement 回传：产物+自测证据 done
main ──派 verify（hb_verify_101）──▶ verify 独立复验：rejected（第 2 条验收失败，打回）
main ──重派 implement（hb_impl_102，新 task_id 引用 hb_impl_101）──▶ implement 修复 done
main ──重派 verify（hb_verify_102）──▶ verify 复验：done（通过）
main ──汇总：三份合同 result 对照（第 6 节，无额外报告文件）
```

约定：每次派发与回传使用同构 `handoff-v1` 合同——下文各节的 JSON 围栏块即合同本体，逐个可过 `scripts/validate_handoff.py` 机器校验。

## 1. 派发 explore（只读侦察）

```json
{
  "schema": "handoff-v1",
  "task_id": "hb_explore_101",
  "from": "main",
  "to": "explore",
  "input": {
    "spec": "只读侦察示例 CLI（examples/echo-cli，虚构演示项目）的命令注册方式与输出约定，为新增 status 子命令做准备",
    "files": ["examples/echo-cli/main.py", "examples/echo-cli/README.md"],
    "constraints": ["只读侦察不改文件", "不动 CI 配置", "不安装依赖"]
  },
  "expect": {
    "artifacts": ["侦察报告（结构化，回写本合同 result）"],
    "acceptance": [
      "列出全部子命令及其注册位置（文件:行）",
      "给出新增子命令应遵循的输出约定一句话结论"
    ]
  },
  "result": {
    "status": "done",
    "artifacts": ["侦察报告"],
    "evidence": [
      "examples/echo-cli/main.py:L12 命令注册入口（COMMANDS 字典：name → handler）",
      "现有子命令 2 个：echo、ping（均经 COMMANDS 字典分发）",
      "输出约定结论：人类可读文本走 print；机器可读走 --format json 单行合法 JSON，二者不混排"
    ],
    "notes": ""
  }
}
```

主会话核对：acceptance 两条均有可判定证据（文件:行、一句话结论），侦察通过，进入实现派发。

## 2. 派发 implement（第一轮）

```json
{
  "schema": "handoff-v1",
  "task_id": "hb_impl_101",
  "from": "main",
  "to": "implement",
  "input": {
    "spec": "按 hb_explore_101 侦察结论新增 status 子命令：注册进 COMMANDS，输出 status: ok 与检查项计数；--format json 时输出单行合法 JSON",
    "files": ["examples/echo-cli/main.py"],
    "constraints": ["不引入新依赖", "遵循既有 COMMANDS 注册风格", "不动既有 echo/ping 行为"]
  },
  "expect": {
    "artifacts": ["examples/echo-cli/main.py（含 status 子命令）"],
    "acceptance": [
      "python examples/echo-cli/main.py status 退出码 0 且输出含 status: ok",
      "python examples/echo-cli/main.py status --format json 输出可被 json.loads 解析且含 version 字段",
      "既有子命令 echo/ping 行为不变（回归通过）"
    ]
  },
  "result": {
    "status": "done",
    "artifacts": ["examples/echo-cli/main.py"],
    "evidence": [
      "python examples/echo-cli/main.py status → status: ok / checks: 2（退出码 0）",
      "--format json 已实现（自测仅留第 1/3 条输出摘要，第 2 条未附可判定证据）",
      "回归：echo/ping 各跑 1 次，行为不变"
    ],
    "notes": ""
  }
}
```

主会话核对：implement 自称 done，但第 2 条验收缺可判定证据——照常派 verify 独立复验（不凭自述放行）。

## 3. 派发 verify（第一轮）→ rejected 打回

```json
{
  "schema": "handoff-v1",
  "task_id": "hb_verify_101",
  "from": "main",
  "to": "verify",
  "input": {
    "spec": "按 hb_impl_101 合同 acceptance 逐条独立验收 status 子命令",
    "files": ["examples/echo-cli/main.py"],
    "constraints": ["独立验收不修代码", "逐条给可判定证据，失败打回"]
  },
  "expect": {
    "artifacts": ["验收结论（回写本合同 result）"],
    "acceptance": [
      "python examples/echo-cli/main.py status 退出码 0 且输出含 status: ok",
      "python examples/echo-cli/main.py status --format json 输出可被 json.loads 解析且含 version 字段",
      "既有子命令 echo/ping 行为不变（回归通过）"
    ]
  },
  "result": {
    "status": "rejected",
    "artifacts": ["验收结论"],
    "evidence": [
      "acceptance 第 2 条失败：--format json 输出末尾混入提示行（更多子命令见 README），json.loads 抛 Extra data",
      "acceptance 第 1 条通过：status 退出码 0，输出含 status: ok",
      "acceptance 第 3 条通过：echo/ping 回归无差异"
    ],
    "notes": "打回 implement 修复第 2 条；verify 不修自己验收的代码（角色纪律）"
  }
}
```

打回处理：verify 只给失败证据不改代码；主会话收到 `rejected` 后**重新出合同派 implement**（新 task_id，引用原 task_id），不允许 verify 顺手修。

## 4. 打回流转：主会话重派 implement（新 task_id 引用原 task_id）

```json
{
  "schema": "handoff-v1",
  "task_id": "hb_impl_102",
  "retries": ["hb_impl_101"],
  "from": "main",
  "to": "implement",
  "input": {
    "spec": "修复 hb_verify_101 rejected 指出的 acceptance 第 2 条失败：--format json 时仅输出单行合法 JSON，提示行只保留在人类可读输出",
    "files": ["examples/echo-cli/main.py"],
    "constraints": ["不引入新依赖", "遵循既有 COMMANDS 注册风格", "不动既有 echo/ping 行为"]
  },
  "expect": {
    "artifacts": ["examples/echo-cli/main.py（status --format json 修复）"],
    "acceptance": [
      "python examples/echo-cli/main.py status 退出码 0 且输出含 status: ok",
      "python examples/echo-cli/main.py status --format json 输出可被 json.loads 解析且含 version 字段",
      "既有子命令 echo/ping 行为不变（回归通过）"
    ]
  },
  "result": {
    "status": "done",
    "artifacts": ["examples/echo-cli/main.py"],
    "evidence": [
      "python examples/echo-cli/main.py status --format json → 单行合法 JSON，json.loads 通过且含 version 字段",
      "python examples/echo-cli/main.py status → status: ok / checks: 2（退出码 0）",
      "回归：echo/ping 各跑 1 次，行为不变"
    ],
    "notes": "重派合同：新 task_id hb_impl_102 引用原 task_id hb_impl_101（retries 字段留痕），修复 hb_verify_101 打回的第 2 条"
  }
}
```

## 5. 重派 verify → 通过

```json
{
  "schema": "handoff-v1",
  "task_id": "hb_verify_102",
  "retries": ["hb_verify_101"],
  "from": "main",
  "to": "verify",
  "input": {
    "spec": "按 hb_impl_102 合同 acceptance 逐条复验 status 子命令修复",
    "files": ["examples/echo-cli/main.py"],
    "constraints": ["独立验收不修代码", "逐条给可判定证据，失败打回"]
  },
  "expect": {
    "artifacts": ["验收结论（回写本合同 result）"],
    "acceptance": [
      "python examples/echo-cli/main.py status 退出码 0 且输出含 status: ok",
      "python examples/echo-cli/main.py status --format json 输出可被 json.loads 解析且含 version 字段",
      "既有子命令 echo/ping 行为不变（回归通过）"
    ]
  },
  "result": {
    "status": "done",
    "artifacts": ["验收结论"],
    "evidence": [
      "acceptance 第 1 条通过：status 退出码 0，输出含 status: ok",
      "acceptance 第 2 条通过：--format json 输出被 json.loads 成功解析且含 version 字段",
      "acceptance 第 3 条通过：echo/ping 回归无差异"
    ],
    "notes": "复验通过；原验收 hb_verify_101 rejected 已闭环"
  }
}
```

## 6. 主会话汇总（三份合同 result 对照）

主会话不写额外报告——直接收集三份合同 `result` 对照呈现（合同本身即汇总材料）：

| 角色 | 合同（task_id） | result.status | 验收对照 | 关键证据（result.evidence 摘要） |
|---|---|---|---|---|
| explore | hb_explore_101 | done | 侦察 2 条全过 | 注册入口 main.py:L12；输出约定结论一条 |
| implement | hb_impl_102（重派，retries 引用 hb_impl_101） | done | 3 条全过 | status / --format json / 回归逐条输出摘要 |
| verify | hb_verify_102 | done | 3 条全过（独立复验） | 逐条通过；hb_verify_101 rejected 已闭环 |

流转留痕：hb_verify_101（rejected，打回第 2 条）→ hb_impl_102（新 task_id 引用 hb_impl_101，修复）→ hb_verify_102（复验通过）。

**走查结论**：示范可跑通——三角色全部走通、rejected 打回一次并闭环修复、结果回主会话汇总对照呈现。何时不用本模板（跨会话持久协作走 PRD-112）见 README 与 T4 边界说明。借鉴划界：上游 pi-subagents 实测 MIT，仅借"三角色 + 交接合同"形态，本示范全虚构、零文案拷贝。
