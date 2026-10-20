# 链式 skill 使用指南

单个 skill 教 Agent「怎么做一件事」；一条**链**把多个 skill 按固定顺序串成多阶段工作流，并把段与段之间的交接写成契约：上游产物落在哪、下游按什么名字去取、停在人工门之后从哪续跑、哪段失败了留什么痕。本页面向使用者：怎么跑一条现成的链、怎么编排一条新链、链上架前要过哪些检查。形态规范与设计依据见 [PRD-095 设计定稿](PRD-095-chained-skills-design.md)。

## 一条链长什么样

链的家就是一个普通 skill 目录，只比普通 skill 多一个 `chain.yaml`：

```text
skills/<chain-name>/
  SKILL.md      # 工序、契约与运行语义（触发与路由仍走普通 skill 机制）
  chain.yaml    # 链描述：段顺序、输入/输出契约、门、跳段与重试口径
```

第一条示范链是 `skills/delivery-chain/`（五段：环境扫描 → 规格 → 探索 → 验收门 → 结果台账）；最小示例是 `skills/delivery-chain/examples/minimal-chain/`（两段，无人工门，下文有走读）。

每次运行的产物落到**项目工作区**（不是仓库里）：

```text
<workspace>/.livepowers/chains/<chain-name>/runs/<run-id>/
  chain-manifest.json     # 本次运行总清单：链名、状态、段序、各段状态、链输入、跳段记录
  inputs/<name>.txt       # 链输入的落盘副本（每项输入一个文件）
  <stage-id>/
    manifest.json         # 本段清单：inputs（按名取到的上游产物+路径+sha256）
                          #          outputs（产物名/路径/sha256/大小/存放方式）、参数、状态
    <产物文件>             # 本段产物本体（≤100KB）；下游只读 manifest 按名取，不猜路径
```

产物大于 100KB（102400 字节）时不进段目录，而是移到 `.livepowers/chains/<chain-name>/large/<run-id>/<stage-id>/`，manifest 里 `stored` 记为 `external` 并登记该路径与 sha256；下游按登记路径取、按哈希验。

## 运行一条现成的链

运行器是仓库根 `scripts/chain_runner.py`（独立脚本原型；设计定稿的 `lp chain` 子命令组是后续并入形态，子命令与参数一一对应）。前提：Python 3.9+，只用标准库，零第三方依赖。下文命令都在**仓库根目录**执行，`<chain>` 写链目录路径（如 `skills/delivery-chain`，也可以直接写它的 `chain.yaml` 文件路径）。

### 1. 校验

```bash
python scripts/chain_runner.py validate skills/delivery-chain
# 结论：校验通过：delivery-chain（5 段）
# 关键信息：段顺序 scan → specify → explore → accept → ledger
```

改过 chain.yaml、换过段引用、或第一次跑一条链时，先校验再运行。校验收集**全部**问题一次报出（不首错即停），查的项见下文「编排新链」的校验清单。退出码：通过 0；有校验错误 1；chain.yaml 结构本身解析不了 2。

链目录不在 `skills/` 顶层时（如 examples 里的最小链），运行器靠当前目录推断仓库根：在仓库根执行即可，或显式给 `--repo-root <仓库根>`。

### 2. 运行

```bash
python scripts/chain_runner.py run skills/delivery-chain --workspace . \
  --param request="按区域统计上周营收"
```

- `--param k=v` 传链输入，可重复；键必须是 chain.yaml `inputs` 里声明过的，未声明的键、缺必填输入都会以退出码 2 拒绝。链输入的值会落盘到运行目录 `inputs/<name>.txt`。
- `--workspace` 是产物落点根目录，默认 `.`（当前目录）。
- run-id 由运行器生成：`YYYYMMDD-HHMMSS`（本地时间），同秒冲突自动加 `-2`、`-3` 后缀。记下它，查状态、续跑全靠它定位。
- 本链第 4 段是人工验收门，运行到那里会停下（见下节），所以这条命令的实际结果是：

```text
结论：停在验收门：accept（待采纳后续跑）
关键信息：run-id 20261020-081420；验收记录 accept/acceptance-record.md
详情：采纳后续跑：run skills/delivery-chain --workspace . --run-id 20261020-081420 --from accept --approve --by <采纳人>
（退出码 3）
```

没有人工门的链（如最小链）一次运行即全链完成，退出码 0，结论行是「全链完成：<run-id>」。

### 3. 人工门与采纳续跑

`gate: human` 的段执行完后，链状态变 `awaiting`、退出码 3——**这是正常状态，不是失败**。把该段产出（如验收记录）交有权采纳人确认；确认前不要替他点通过，也不要绕过门直接跑后面的段（运行器会以退出码 1 拦下越门续跑）。

采纳后用一条命令续跑到全链完成（退出码 0）：

```bash
python scripts/chain_runner.py run skills/delivery-chain --workspace . \
  --run-id <run-id> --from accept --approve --by <采纳人>
```

续跑规则（运行器强制）：

- `--from` / `--approve` 必须同时给 `--run-id`，缺了是用法错误（退出码 2）。
- 续跑**不接受 `--param`**：链输入已在首次运行时落盘，改口径要开新运行。
- `--approve` 时的 `--by` 是采纳人；省略时记为「（未具名）」。采纳决定写入验收段 manifest 的 `decided_by` / `decided` / `decision_reason`；验收记录是 .md 时还会追加一段「人工采纳」留痕，并回写 manifest 里的 sha256 与大小（保证 manifest 继续是产物的防篡改真源）。
- 段失败后同样用 `--run-id <run-id> --from <失败段>` 从该段重跑：前段产物按 manifest 的 sha256 复验后复用，不重做；产物被手改或缺失会以退出码 4 拦下，先回出问题那段重跑，不要手改产物文件绕过。

### 4. 查状态

```bash
python scripts/chain_runner.py status <run-id> --workspace .
# 结论：20261020-081420：completed（完成 5/5 段）
# 关键信息：scan=done；specify=done；explore=done；accept=done；ledger=done
```

只需 run-id 和工作区：运行器会在该工作区所有链的 runs 下定位。找不到、或同一 run-id 在多条链下重复，退出码 1。链的整体状态取值：`running` / `awaiting` / `completed` / `failed`；段状态：`pending` / `done` / `failed` / `skipped`。

### 5. 段独立调用

每段本就是普通 skill，可以离开链单独触发；要用运行器单独跑一段（产物照样进运行目录、写 manifest，供整链复用）：

```bash
# 自成一次新运行（chain-manifest 只落骨架，其余段为 pending）
python scripts/chain_runner.py stage skills/delivery-chain scan --workspace . \
  --param request="按区域统计上周营收"

# 写进一次已有运行（之后可被 run --from 复用，复用时按名+哈希校验）
python scripts/chain_runner.py stage skills/delivery-chain scan --workspace . \
  --run <run-id> --param request="..."
```

段独立调用的输入解析与整链相同：缺上游产物（如脱离运行单独调一段需要上游产物的段）以退出码 4 拒绝。目标段是人工门时，段执行后链置 `awaiting`，后续同样走 `--approve` 续跑。

### 6. 跳段

只有 chain.yaml 里声明 `optional: true` 的段能跳：

```bash
python scripts/chain_runner.py run skills/delivery-chain --workspace . \
  --param request="..." --skip ledger
```

被跳段在 chain-manifest 里记 `skipped` 并留一段 manifest 说明；它的下游取产物时自动回退到更早的可用上游。跳非 optional 的段或不存在的段，运行器明确报错（退出码 1）并提示先改 chain.yaml 契约再重新校验——**不静默降级**。

### 退出码（全部命令同此表）

| 码 | 含义 | 典型场景 |
|---|---|---|
| 0 | 成功 | 校验通过 / 全链完成 / 段独立调用完成 / 状态查询成功 |
| 1 | 失败 | 校验有错误；段失败（含重试耗尽）；非法跳段；越过未确认的人工门；status 找不到 run-id |
| 2 | 用法或结构错误 | chain.yaml 解析失败；`--param` 不是 k=v、键未声明、必填输入缺失；续跑没给 --run-id、续跑带了 --param |
| 3 | 停在人工验收门 | 链状态 `awaiting`，按输出给出的续跑命令采纳后继续 |
| 4 | 上游产物缺失或契约不满足 | 上游 manifest 缺失、产物文件被删或被改（sha256 对不上）、段独立调用缺上游产物 |

全部命令支持 `--json`，输出统一信封（含 `ok` 字段与结构化结果/错误），机器消费用它，人读默认三段式。注意退出码 3 时 `--json` 的 `ok` 为 false，但语义是「待人工」，不是失败。

## 编排一条新链

1. **选段**：每段必须引用一个 `skills/` 下已存在的 skill（链不内嵌匿名段）。缺工序时先按 `writing-livepowers-skills` 的流程立新 skill，再入链。
2. **建目录**：`skills/<chain-name>/`，放 `SKILL.md`（只写工序、契约与运行语义，不复述各段方法论）+ `chain.yaml`。
3. **写 chain.yaml**（字段见下节），然后 `validate` 到退出码 0。
4. **登记上架**：按文末「链上架 checklist」逐项补齐（路由表、README、插件拷贝、触发评测、计数、变更记录）——这是仓库的硬契约，缺一项 CI 就红。
5. **跑通留痕**：至少完整跑一次（有人工门的要走到采纳完成），运行产物与 manifest 就是验收证据。

### chain.yaml 字段逐项

顶层：

| 字段 | 必填 | 说明与校验 |
|---|---|---|
| `name` | 是 | kebab-case（`^[a-z0-9-]+$`），且必须与所在目录名一致 |
| `description` | 是 | 一句话说清这条链交付什么；缺失即校验错误 |
| `version` | 否 | 链自身的版本号（当前示范链 `0.1.0`），与仓库/插件包版本（1.6.0）相互独立；段契约有不兼容变更时递增。运行器不校验此字段，写不写不影响运行，但上架的链应写 |
| `inputs` | 否 | 链级输入清单，每项含 `name`（必填）与 `help`；运行时以 `--param name=值` 传入，段以 `from: chain` 按名取 |
| `stages` | 是 | 段数组，非空；数组顺序即默认执行顺序 |

每段：

| 字段 | 必填 | 说明与校验 |
|---|---|---|
| `id` | 是 | kebab-case，链内唯一 |
| `skill` | 是 | 引用的 skill 名；`skills/<skill>/SKILL.md` 必须真实存在（按仓库根核对） |
| `inputs.from` | 否 | 上游段 id，或 `chain`（取链输入）；缺省按 `chain` 处理。只能指向排在**前面**的段：指向不存在的段、自身或后面的段都是校验错误（悬空/前向引用/环一次查出） |
| `inputs.needs` | 否 | 按名取的产物清单：`from` 是某段时，每个名字必须在该段的 `outputs` 里；`from: chain` 时，每个名字必须是链 `inputs` 里声明过的 |
| `outputs` | 是 | 本段承诺产出的产物名清单，非空。下游按名引用，不写裸路径 |
| `params` | 否 | 段参数映射，写进本段 manifest 供执行时读取；其中 `simulate=fail`、`pad_bytes` 是运行器测试钩子（分别强制本段失败、把首个产物撑大到指定字节），编排时不要用这两个键 |
| `optional` | 否 | `true`/`false`（缺省 false），只有 `true` 的段可被 `--skip` 跳过 |
| `gate` | 否 | `none`（缺省）/ `human`（人工确认后才继续）/ `checker:<名>`（自动校验器）。注意：`checker:` 门能通过校验，但当前运行器原型**未实现**校验器执行，运行到该段会以退出码 1 拒绝放行——现阶段编排请用 `none` 或 `human` |
| `retry_limit` | 否 | 非负整数，缺省 0（不重试，段显式声明才重试）；重试耗尽仍失败则链停在该段、状态 `failed`、失败原因记进该段 manifest |

格式约束（与仓库 capability 描述文件同一套手写风格）：2 空格缩进、字符串加引号；**不使用** YAML 锚点/别名、流式集合（如 `[a, b]`）、块标量（`|`/`>`），`needs`/`outputs` 一律块式列表——运行器内置的是 YAML 子集解析器，超出子集的写法会以退出码 2 报结构错误。

### 最小链走读

`skills/delivery-chain/examples/minimal-chain/` 是示范链前两段组成的两段链（scan → specify，无人工门、无可跳段），chain.yaml 全文：

```yaml
name: minimal-chain
description: "最小链示例：环境扫描 → 规格，两段演示链的输入/输出契约与运行产物结构"
version: "0.1.0"
inputs:
  - name: request
    help: "业务请求原文，如 '统计本月退款率'"
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
```

实测（仓库根执行）:

```bash
python scripts/chain_runner.py validate skills/delivery-chain/examples/minimal-chain
# 结论：校验通过：minimal-chain（2 段）；段顺序 scan → specify（退出码 0）

python scripts/chain_runner.py run skills/delivery-chain/examples/minimal-chain \
  --workspace . --param request="统计本月退款率"
# 结论：全链完成：<run-id>；2/2 段完成（退出码 0）
```

跑完看 `<workspace>/.livepowers/chains/minimal-chain/runs/<run-id>/`：`chain-manifest.json` 里两段都是 `done`，`specify/manifest.json` 的 inputs 里 ontology-draft 带着 scan 段产物的路径与 sha256——这就是段间契约的全部交接面。

## 元数据与兼容性口径

- **包版本只有一个真源**：`.claude-plugin/plugin.json`、marketplace 各条目、`package.json` 与各主题插件的版本由仓库契约测试强制一致（当前 1.6.0）。链不另立包级版本字段；chain.yaml 的 `version` 只是链自身版本（见字段表），不要拿它对齐包版本，也不要给链的 SKILL.md frontmatter 加私有字段——全仓 SKILL.md frontmatter 只写 `name` + `description`，链的同样如此。
- **运行器兼容性**：Python 3.9+、仅标准库；chain.yaml 的 YAML 子集约束（见上）就是链描述的可移植边界，按子集写的链可被仓库的最小解析器与 `gen_harness.py` 一脉的工具读取。
- **上架路径与普通 skill 完全一致**：链目录随主题插件打包（示范链在 `livepowers-delivery` 插件内有逐字节拷贝），不需要新的分发约定。

## 链上架 checklist

新链入仓前逐项核对（与 PRD-094 上架清单的文档类要求对齐，仓库契约测试会自动查其中大部分）：

- [ ] `skills/<chain>/SKILL.md` + `chain.yaml` 就位，`validate` 退出码 0
- [ ] SKILL.md 正文只写工序/契约/运行语义；出现的每条运行器命令同段给出退出码说明；引用的文件、skill 全部真实存在
- [ ] `using-livepowers` 路由表新增一行，场景写清何时该用这条链
- [ ] 根 README 技能表新增一行，技能计数同步
- [ ] 归属主题插件的 `plugins/<plugin>/skills/` 下放逐字节拷贝（含 SKILL.md 的插件拷贝，如 `using-livepowers` 在 core 插件的那份）
- [ ] `tests/triggers/<chain>.jsonl` 备齐（≥3 正例、≥2 反例），`tests/<chain>/test_examples.py` 覆盖契约/正例/反例
- [ ] `tests/test_marketplace_install.py` 的 `EXPECTED_SKILL_COUNT` 同步 +1
- [ ] CHANGELOG 的 `[Unreleased]` 记一条（含链名、段构成、归属插件）
- [ ] 完整跑通一次并留 manifest 证据；有人工门的，采纳留痕（decided_by）齐全

## 当前边界（与设计稿的差异，以实现为准）

- **段执行是模拟的**：随仓运行器内置模拟执行器，`run`/`stage` 产出的是按契约生成的模拟产物（段 manifest 的 `generated_by` 写作「scripts/chain_runner.py（模拟执行器）」、`model` 为 `simulated`）。当前已验证的是编排、契约、人工门、续跑与跳段语义；段的真实业务执行（由 Agent 按各段 SKILL.md 干活、运行器只管编排与落盘）与 `lp chain` 子命令组并入，是后续增量，不在本页承诺内。
- **续跑必须带 run-id**：设计稿的接口示意里 `--from` 可独立出现；实现要求 `--from`/`--approve` 必须同时给 `--run-id`（缺失为退出码 2），本页按实现写。
- **失败证据的落点**：设计稿设想每段结束记一条 `lp evidence add`；原型未接证据命令，失败与状态全部记在 manifest 里，本页按实现写。
- **大文件落点**：设计稿口径是「只登记路径+哈希，文件本体按项目 .gitignore 处理」；实现把 >100KB 产物搬到 `.livepowers/chains/<chain>/large/<run-id>/<段>/` 再登记（仍在工作区内），本页按实现写。
- **checker 门未实现**：校验认 `checker:<名>`，运行到该段以退出码 1 拒绝放行（见字段表）。
