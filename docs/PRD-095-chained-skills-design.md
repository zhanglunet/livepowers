# PRD-095/T1：链式 skill 形态设计定稿

> 状态：定稿（final），2026-10-20 用户确认（6 条待确认事项全部按推荐拍板，见第 5 节「决策记录」）。\
> 对应：trend `adopted/PRD-095-livepowers-chained-skills.md`；livepowers issue #61（T1）、trend 跟踪 #477。\
> 红线：仅借鉴 academic-research-skills 的「多阶段链」形态思路，未复用其任何文本与代码（见末尾合规声明）。

## 1. 背景与目标

livepowers 现有 20 个 skills 是「单点能力」：每个 skill 解决一类任务（探索留证据、验收门、结果台账……），由 `using-livepowers` 路由表按场景调度。但真实的业务工作流是多阶段流水线：比如「交付一条报表」要走 环境扫描 → 规格 → 探索 → 验收 → 台账，多个 skill 按固定顺序串起来。今天这种串联靠 Agent 现场拼装，没有契约：上游产物落在哪、下游去哪取、中断后从哪续跑，都没有约定。

链式 skill 把「多阶段工作流」本身打包成一个可调用、可测试、可上架的形态：

- **链不断，段也能单独用。** 每段仍然是一个普通 skill（走现有触发、路由、测试机制），链只是一层「包装层 + 段间契约」——对应 PRD 非目标「不改现有 skills 实现，只新增链式包装层」。
- **和单个 skill 的区别：** 单个 skill 教 Agent「怎么做一件事」（方法、判据、反模式）；链教「按什么顺序做哪几件事、段与段之间怎么交接」。链的 SKILL.md 里不重复段的方法论，只写工序、契约与运行语义（引用段时只写名字，不复制内容——沿 `writing-livepowers-skills` 的规矩）。

## 2. 形态规范

### 2.1 链的定义

- 一条链 = **一个链描述文件 `chain.yaml`** + 若干段（每段引用一个已存在的 skill）。
- 链的身份规则沿 `capability.yaml` 的约束（`docs/HARNESS-DESIGN.md` §1）：`name` 必须匹配 `^[a-z0-9-]+$`，同时是目录名与调用名，防止三处写劈叉。
- 每段的**执行内容**以其 skill 的 SKILL.md 为准；链描述只声明：段的顺序、输入/输出契约、段间产物落盘位置、检查门、是否可跳过、失败/续跑语义。

### 2.2 段的输入/输出契约

每个段在 `chain.yaml` 中声明：

| 字段 | 含义 | 依据/推导 |
|---|---|---|
| `id` | 段标识（kebab-case），在链内唯一 | 沿 `templates/job-contract.json` 的 `stage_id` 概念 |
| `skill` | 引用的 skill 名，必须是 `skills/` 下真实存在的目录；每段必须引用一个已存在的 skill，不允许在 chain.yaml 内嵌匿名段（决策 3A） | 沿 SKILL-TEST-SPEC 的「引用 skill 必须存在」反向检查 |
| `inputs` | 本段需要的上游产物：`from`（上游段 id 或 `chain` 表示链级输入）+ `needs`（产物名列表，按名引用，不写裸路径） | 按名引用保证契约稳定：换段实现时只改映射，不改下游 |
| `outputs` | 本段承诺产出的产物名列表（每产物的格式/位置在段运行清单中声明，见 2.3） | 宽契约先行：第一期只声明产物名，T3 验证时再收敛格式（对应 PRD 风险「契约先宽后严」） |
| `params` | 段参数，`key: value`；在段调用命令中以 `{param}` 占位传入 | 沿 `capability-package.yaml` 的 `implementation.entry` 占位符风格 |
| `optional` | `true/false`，是否可跳过（默认 `false`） | 为 T3 跳段验证留口 |
| `gate` | 段后检查门：`none`（默认，自动继续）/ `human`（人工确认）/ `checker:<名>`（自动校验器，沿 job-contract 的 `handoff.checker` 概念） | 验收门类段（`acceptance-gates`）天然是 `human` |
| `retry_limit` | 段失败重试次数（默认 0，决策 5B；段显式声明才重试，重试与否由 Agent 按 skill 的停止/恢复规则判断，失败后靠断点续跑恢复） | 沿 job-contract 的 `retry_limit` 语义 |

依赖关系由 `stages` 数组顺序 + `inputs.from` 共同表达：默认线性执行；`from` 可指向任意**排在本段之前**的段（允许菱形依赖，禁止前向引用与环——校验规则沿 `lp job validate` 的「悬空依赖、环」检查）。

### 2.3 段间产物格式（文件约定）

每次链运行分配一个 `run-id`，产物落盘在项目工作区内：

```
.livepowers/chains/<chain-name>/runs/<run-id>/
  chain-manifest.json        # 本次运行的总清单（链、段顺序、状态、起止时间）
  <stage-id>/
    manifest.json            # 本段运行清单：inputs（实际取到的产物）/ outputs（实际产出）/ status / generated_by / model / note
    <产物文件…>              # 本段产出的文件，原生格式（md/json/csv…）；≤100KB 全量落盘，大/二进制产物只登记不落盘（见说明 4）
```

依据与说明：

1. `.livepowers/` 是项目运行产物的既定位置（`using-livepowers` 项目目录约定表：证据、注册表、看板、台账、pending、explorations 均在此，入 git）；链运行产物与其同仓位。`lp init` 已创建该目录，无需新约定。
2. `manifest.json` 字段风格沿 `lp pending add` 写入的 `.livepowers/pending/<意图>/manifest.json`（`intent/score/tests/result/location/generated_by/writes_state/model/note/status/created`，验收后追加 `decided_by/decided/decision_reason`）——链清单复用同一套字段词，Agent 与脚本已有读写惯例。
3. 下游段**只读上游 `manifest.json` 中声明的 `outputs`**（按名取路径），不直接猜上游目录结构。这是契约稳定的关键。
4. 大文件口径（决策 4B）：小文件（≤100KB）全量落盘到段运行目录，随 `.livepowers/` 的既定口径管理；大文件/二进制产物（如导出的报表 PDF）只在 manifest 中登记路径+哈希，文件本体不落盘、按项目 `.gitignore` 处理（沿 `.livepowers/` 在本仓库被 ignore、项目自定的先例——`using-livepowers` 明确写了「本仓库自己的 `.gitignore` 忽略它，你的项目不要照抄」）。下游按 manifest 登记的路径取大文件，并以哈希校验完整性。

### 2.4 链描述文件 `chain.yaml`（完整示例，原创）

> 示例链「业务交付链」串起 5 个真实存在的 skill，既用于说明格式，也是 T2 的示范链（决策 6A：用现有 skills 串真实交付链，零新 skill；学术生产链留作第二条链，形态验证通过后再做）；字段名全部原创，风格对齐 `capability.yaml`。\
> 格式约束：手写风格与 `capability.yaml` 一致（2 空格缩进、字符串加引号）；**不使用** YAML 锚点/别名、流式集合、块标量——以便未来可被 `gen_harness.py` 自带的最小 YAML 解析器读取（该解析器的限制见其文件头注释）。T2 原型已按此约束自研子集解析器并跑通；下方示例与 T2 实际文件逐字一致（草稿示例曾误用流式集合，定稿后修正）。

```yaml
# 链描述文件：skills/delivery-chain/chain.yaml（决策 1A：放在 skills/<chain>/ 内，链作为普通 skill 上架）
# 格式：2 空格缩进、字符串加引号；不使用锚点/别名、流式集合、块标量（needs/outputs 一律块式列表）。
# 本示例与 T2 原型实际跑通的 chain.yaml 逐字一致（见 T2 验证日志）。
name: delivery-chain
description: "一条业务请求的端到端交付流水线：环境扫描 → 规格 → 探索 → 验收门 → 结果台账"
version: "0.1.0"
inputs:
  - name: request
    help: "业务请求原文，如 '按区域统计上周营收'"

stages:
  - id: scan
    skill: env-scan-ontology
    inputs:
      from: chain
      needs:
        - request
    outputs:
      - ontology-draft
    params:
      start: "brownfield"
    optional: false
    gate: none
    retry_limit: 0

  - id: specify
    skill: ontology-grounded-spec
    inputs:
      from: scan
      needs:
        - ontology-draft
    outputs:
      - spec-doc
    params:
      spec_template: "templates/spec.md"
    optional: false
    gate: none
    retry_limit: 0

  - id: explore
    skill: explore-with-evidence
    inputs:
      from: specify
      needs:
        - spec-doc
    outputs:
      - analysis-result
    params:
      max_rounds: 3
    optional: false
    gate: none
    retry_limit: 0

  - id: accept
    skill: acceptance-gates
    inputs:
      from: explore
      needs:
        - analysis-result
    outputs:
      - acceptance-record
    params:
      require_independent_review: true
    optional: false
    gate: human
    retry_limit: 0

  - id: ledger
    skill: outcome-ledger
    inputs:
      from: accept
      needs:
        - acceptance-record
    outputs:
      - ledger-entry
    params:
      scenario: "delivery-chain-run"
    optional: true
    gate: none
    retry_limit: 0
```

### 2.5 错误、中断与续跑语义

| 情形 | 语义 | 依据 |
|---|---|---|
| 某段失败（`retry_limit` 耗尽后仍失败） | 链停在该段；`chain-manifest.json` 记 `status: failed`、失败段 id 与原因；每段结束记一条 `lp evidence add`（探索类记 S2），失败本身也是一条证据 | 「探索必留证据」铁律；失败即证据 |
| 段后 `gate: human` | 链停在该段，状态 `awaiting`，退出码 3（见 3.3）；人工确认后从下一段继续 | 沿 registry find 的「3 = MAYBE/待定」语义占用 |
| 续跑 | `run --from <stage-id>`：复用该段之前各段 `manifest.json` 中的产物（先校验产物文件存在），从指定段开始重跑 | 沿 job-contract 的 `checkpoint` 目录 + `resume_policy: from_checkpoint` 语义 |
| 跳过 `optional` 段 | 允许；下游段 `inputs.from` 自动回退到最近的可用上游产物 | —— |
| 跳过非 `optional` 段 | 明确报错退出（退出码 1，`--json` 给结构化错误），**不静默降级** | 沿「严禁盲目」类红线的精神：含糊继续比停下来更贵 |
| 超预算/异常 | 链状态转 `takeover`，按 `takeover-handling` 流程处理 | 沿任务看板「任何状态可 → 异常接管」语义 |

### 2.6 跳段与重排的支持口径（为 T3 留验证点）

- **第一期口径（静态声明 + 有限运行时参数）：** 跳段只能跳 `optional: true` 的段；重排 = 修改 `chain.yaml` 的段顺序与 `from` 引用后重新运行。运行时参数 `--skip <stage-id>` 仅对已声明 `optional` 的段有效。
- **校验：** 运行前校验 `from` 只能指向排在前面的段、无环、无悬空引用（规则沿 `lp job validate`）；任意 DAG 编排不在第一期范围（明确非目标）。
- **T3 验证点清单（T3 照此出用例）：**
  1. 跳过 `optional` 段：下游回退取上游产物，全链成功。
  2. 跳过非 `optional` 段：明确报错退出，退出码 1，无部分产物被下游误用。
  3. 重排段顺序并修正 `from`：校验通过，全链成功。
  4. `from` 指向后序段/不存在的段：校验失败，运行前即报错（不执行任何段）。
  5. 段独立调用的产物可被链的后续段复用（同一 `runs/<run-id>/` 约定，见 3.2）。
  6. 段失败耗尽重试：链停在该段，manifest 状态正确，证据已记。

## 3. 调用接口

### 3.1 两种入口

| 入口 | 面向 | 形态 | 依据 |
|---|---|---|---|
| Agent 入口（skill 触发） | Agent 在对话中被路由命中 | 链自带 `SKILL.md`（按 `templates/skill.md` 骨架：为什么→步骤→命令→反模式/红线+简洁输出规范节），`description` 只写触发条件；正文引用各段 skill 只写名字 | `writing-livepowers-skills` 格式要求 |
| CLI 入口（确定性驱动） | 脚本、CI、人工精确控制 | 最终形态为 `lp chain` 子命令组（见 3.2）；实现路径按决策 2A：T2 先做独立运行器脚本原型，稳定后再并入 `lp` | 沿 `gen_harness`「原型先行」的先例；`lp` 现有子命令组风格（名词+动词） |

### 3.2 CLI 子命令设计（定稿接口；T2 先以独立运行器脚本实现同一接口，见决策 2A）

```
lp chain validate <chain>            # 校验 chain.yaml：字段、段引用存在、from 无环（沿 lp job validate）
lp chain run <chain> [--param k=v…] [--json]
lp chain run <chain> --from <stage-id> [--param k=v…]   # 断点续跑
lp chain run <chain> --skip <stage-id>                  # 仅 optional 段
lp chain stage <chain> <stage-id> [--param k=v…] [--run <run-id>]  # 段独立调用
lp chain status <run-id> [--json]    # 查看某次运行的段状态与产物清单
```

- 段独立调用（`chain stage`）：不带 `--run` 时开新 `run-id`（产物自成一次运行）；带 `--run` 时把产物写入指定运行目录，供链后续段复用（对应 T3 验证点 5）。
- 参数传递 `--param k=v`，映射到 `chain.yaml` 的 `{param}` 占位（沿 capability entry 风格）。

### 3.3 退出码（拟分配，已核对现有占用）

| 码 | 含义 | 备注 |
|---|---|---|
| 0 | 全链/段成功 | 沿用 |
| 1 | 段失败 / 校验失败 / 非法跳段 | 沿用（失败） |
| 2 | 用法错误 / 描述文件结构错误 | 沿用（argparse 默认 + job validate 惯例） |
| 3 | 停在人工验收门（`awaiting`），待确认后可继续 | 借用现有「3 = MAYBE/待定」语义 |
| 4 | 上游产物缺失或契约不满足，无法继续 | **新增**：经核对，`lp` 现有退出码占用为 0/1/2/3（通用+registry/score）与 5（canary 回归），4 未见占用；T5 前与现有码表正式核对一次 |

所有命令支持 `--json`（`{"ok": true/false, …}` 信封，沿 harness 生成器的 agent 友好约定）与人类可读三段式输出（结论/关键信息/详情折叠，沿简洁输出规范）。

## 4. 与现有体系的关系（为 T4 留口）

1. **PRD-003 市场格式：** 链的 SKILL.md 走现有插件上架路径（`.claude-plugin/plugin.json` + `marketplace.json`，插件内 skills 为根 `skills/` 逐字节拷贝）。链描述文件按决策 1A 放在 `skills/<chain>/` 内，故**零新增打包约定**：链就是一个带 `chain.yaml` 附件的普通 skill，5 个主题插件的拷贝机制直接适用；T4 只需在文档模板里加「链附件」一节。
2. **PRD-094 上架 checklist：** 链 SKILL.md 必须通过同一套 checklist：每条打分有证据链接；`lp` 命令出现处同段必须有退出码说明（SKILL-TEST-SPEC L1 契约的既有要求，链文档同理）；description ≤1024 字符且只写触发条件。
3. **能力注册表：** 链跑稳后可注册为 System 1 能力：`implementation.kind: workflow`（`capability-package.yaml` 的 kind 枚举已含 `workflow`），`entry` 指向链运行命令；走 `lp registry add`（须带 `--tests`，生成者 ≠ 采纳人，由代码强制）。
4. **测试：** `tests/<chain-name>/test_examples.py`（L1：chain.yaml 结构合法、引用的 skill 真实存在——沿 `run_contract.py` 的反向检查思路；L2/L3 按链的断言性例子与反例）；`tests/triggers/<chain-name>.jsonl`（≥3 正例 ≥2 反例，沿 `writing-livepowers-skills` 要求）。
5. **路由：** 新链加入 `using-livepowers` 路由表与 README 技能表（`writing-livepowers-skills` 检查清单既有要求）。

## 5. 决策记录（2026-10-20 用户确认）

原草稿的 6 条待确认事项，用户已于 2026-10-20 全部按推荐拍板，结论如下（正文已按此统一）：

1. **1A 链描述文件的存放位置**：问题——`chain.yaml` 放 `skills/<chain-name>/` 内，还是顶层新目录 `chains/<chain-name>/`？结论——**A**：放 `skills/<chain-name>/` 内（`SKILL.md` + `chain.yaml`），链即一种带附件的 skill；上架、触发、测试全沿现成机制，零新增打包约定，链与普通 skill 靠 `chain.yaml` 存在与否区分。2026-10-20 用户确认。
2. **2A 链运行入口的实现路径**：问题——T2 直接改 `scripts/lp.py` 加 `chain` 子命令组，还是先做独立运行器脚本原型？结论——**A**：T2 先做独立运行器脚本（沿 `gen_harness` 原型先行先例），语义跑通、稳定后再并入 `lp chain`。2026-10-20 用户确认。
3. **3A 段的粒度**：问题——一段必须引用一个已存在的 skill，还是允许链内嵌「匿名段」？结论——**A**：每段必须引用一个已存在的 skill；缺 skill 的工序先走 `writing-livepowers-skills` 流程立新 skill 再入链。不允许匿名段，以保住核心卖点「段可独立调用」——段离开链仍可单独触发、测试与上架。2026-10-20 用户确认。
4. **4B 运行产物的大文件口径**：问题——全部产物进 `.livepowers/chains/`，还是大/二进制产物只登记？结论——**B**：小文件（≤100KB）全量落盘 `.livepowers/chains/`；大文件/二进制产物只在 manifest 登记「路径 + 哈希」，文件本体按项目 `.gitignore` 处理（见 2.3 说明 4）。2026-10-20 用户确认。
5. **5B 段失败重试默认值**：问题——`retry_limit` 全链默认 1，还是默认 0？结论——**B**：默认 0，段显式声明才重试；失败即停、留证据，重试与否由 Agent 按 SKILL.md 的停止/恢复规则判断，靠断点续跑恢复。2.4 示例原暂填的 1 已按本条统一改为 0。2026-10-20 用户确认。
6. **6A 示范链选材**：问题——T2 示范链用现有 skills 串真实交付链，还是按 PRD 建议做学术生产链（需要新建多个段 skill）？结论——**A 先行**：用现有 skills 串一条真实交付链（即 2.4 示例链 `env-scan-ontology → ontology-grounded-spec → explore-with-evidence → acceptance-gates → outcome-ledger`），零新 skill，第一期先验证形态；学术生产链留作第二条链，形态验证通过后再做（还能反过来检验形态的通用性）。2026-10-20 用户确认。

## 6. 合规声明

- 本设计**仅**借鉴 academic-research-skills 的「多阶段链」形态思路。形态层面的观察仅限于其公开仓库的**目录结构**：若干个阶段各是一个自带 SKILL.md 的独立 skill 目录，另有一个编排型 skill 把各段串成全流程，段既可单独调用也可组合运行。本次调研**未读取**该仓库任何 SKILL.md 正文、命令文本或代码，未复用、改写、翻译其任何文本与代码。
- 本稿的全部字段名、文件名、退出码、目录约定，均从 livepowers 自身文件推导，依据可查：`skills/using-livepowers/SKILL.md`（`.livepowers/` 约定、lp 用法）、`skills/writing-livepowers-skills/SKILL.md` 与 `templates/skill.md`（skill 格式骨架）、`docs/HARNESS-DESIGN.md` 与 `scripts/gen_harness.py`（capability.yaml schema、退出码、YAML 子集限制）、`templates/capability-package.yaml`、`templates/job-contract.json` 与 `examples/spec-task-chain.job.json`（段/依赖/检查点/交接词汇）、`scripts/lp.py` 子命令面与 pending manifest 字段、`docs/SKILL-TEST-SPEC.md`（契约测试）、`.claude-plugin/plugin.json` 与 `marketplace.json`（PRD-003 市场格式）。
- 推导边界：2.4 示例中的产物名（如 `ontology-draft`、`spec-doc`）与 3.3 中退出码 `4` 的拟分配为本稿原创提议，前者 T2 定稿、后者 T5 前须与现有 lp 退出码表正式核对（已在正文标注）。推导不出的部分已全部列入第 5 节并经用户确认（见决策记录），未臆造约定。

## 附：与任务拆分的衔接

- 本稿 = T1 产出，已定稿（第 5 节决策记录为据；验收：形态规范定稿、段契约与调用接口无歧义）。
- T2 输入：第 2、3 节 + 决策 6A 的示范链（2.4 示例链）；运行入口按决策 2A 先做独立运行器脚本原型。
- T3 输入：2.6 节的 6 个验证点。
- T4 输入：第 4 节的衔接点清单。
