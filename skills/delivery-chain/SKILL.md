---
name: delivery-chain
description: Use when a business request must be delivered end-to-end as one pipeline (scan the environment and ontology, ground a spec, explore with evidence, pass the acceptance gates, then record the outcome in the ledger), or when such a delivery stopped at the human acceptance gate and must be resumed. 一条业务请求需要端到端交付（扫描→规格→探索→验收→台账）、或交付停在人工验收门需要续跑时使用。
allowed-tools: Bash, Read
license: MIT
metadata:
  when_not_to_use: 非交付链路的分析任务不适用
  output: 交付链路核对记录
  compatibility: 需 Bash 与 Read 工具
---

# 业务交付链

**一句话：把五个段 skill 按固定契约串成一条可续跑、可验收的交付流水线，段间交接不再靠 Agent 现场拼装。**（为什么：没有链时，上游产物落在哪、下游去哪取、停在验收门之后从哪继续，全靠临场记忆，换个 Agent 就接不上；链把工序、契约与续跑语义写死在同目录的 `chain.yaml` 里。）

本文件只写工序、契约与运行语义。各段怎么做以各自 skill 的 SKILL.md 为准，这里只引用名字：`env-scan-ontology`、`ontology-grounded-spec`、`explore-with-evidence`、`acceptance-gates`、`outcome-ledger`。

## 工序与契约（摘要，全文以 chain.yaml 为准）

| 段 id | skill | 输入（按名引用） | 产出 | 门 / 备注 |
|---|---|---|---|---|
| scan | env-scan-ontology | 链输入 `request` | ontology-draft | 无 |
| specify | ontology-grounded-spec | ontology-draft | spec-doc | 无 |
| explore | explore-with-evidence | spec-doc | analysis-result | 无 |
| accept | acceptance-gates | analysis-result | acceptance-record | **gate: human**，人工采纳后才继续 |
| ledger | outcome-ledger | acceptance-record | ledger-entry | optional，可跳过 |

运行产物落在工作区 `.livepowers/chains/delivery-chain/runs/<run-id>/`：每段一个子目录，含产物文件与 `manifest.json`；下游只读上游 manifest 中按名声明的产物，不猜目录结构。产物 ≤100KB 全量落盘；大文件只在 manifest 登记路径与 sha256（定稿口径 4B）。

## 步骤

1. **先校验。**改过 chain.yaml、换过段引用、或第一次跑这条链时，先跑 `validate`，校验不过不许开跑。
2. **启动运行。**用 `run` 并以 `--param request="..."` 传入业务请求原文；记下输出的 run-id，后续 status、续跑都靠它定位。
3. **逐段执行。**轮到哪段，就按那段 skill 的 SKILL.md 干活，把产物按契约写进该段目录；编排、落盘与 manifest 由运行器负责，不要手写 manifest。
4. **停在验收门是正常状态。**accept 段产出验收记录后运行器以退出码 3 停下（status 为 `awaiting`）。把验收记录交有权采纳人确认；**确认前不要替他点通过**，也不要绕过验收门直接跑 ledger 段。
5. **采纳后用续跑继续。**带 `--from accept --approve --by <采纳人>` 续跑：采纳决定会记进 accept 段的 manifest（decided_by / decided），随后 ledger 段执行，全链完成（status 为 `completed`）。
6. **段失败就停在该段。**全链 retry_limit 为 0，不自动重试；按失败段的证据诊断原因，修好后用 `--from <段 id>` 从该段重跑，前面的段产物复用不重做。

## 命令

当前运行器是独立脚本原型（定稿口径 2A：先脚本、稳定后并入 `lp chain` 子命令组，届时命令一一对应：`lp chain validate / run / status / stage`）。

```bash
# 校验链描述（段引用存在、from 无悬空/无环、契约自洽）
python scripts/chain_runner.py validate skills/delivery-chain

# 启动一次运行（停在验收门时退出码 3）
python scripts/chain_runner.py run skills/delivery-chain --workspace . \
  --param request="按区域统计上周营收"

# 查看某次运行的段状态与产物
python scripts/chain_runner.py status <run-id> --workspace .

# 段独立调用（只跑一段；不带 --run 时自成一次运行，带 --run 时产物写进指定运行目录，供后续整链 run --from 复用）
python scripts/chain_runner.py stage skills/delivery-chain scan --workspace . \
  --param request="按区域统计上周营收"

# 人工采纳后从验收段续跑到全链完成
python scripts/chain_runner.py run skills/delivery-chain --workspace . \
  --run-id <run-id> --from accept --approve --by <采纳人>

# 跳过 optional 段（仅 ledger 可跳；跳非 optional 段会明确报错）
python scripts/chain_runner.py run skills/delivery-chain --workspace . \
  --param request="..." --skip ledger
```

退出码（上面每条命令同此表）：

| 码 | 含义 |
|---|---|
| 0 | 全链完成 / 校验通过 / status 查询成功 |
| 1 | 段失败 / 校验失败 / 非法跳段 / 验收门未确认却试图越过 |
| 2 | 用法错误（参数缺失、未声明的 --param 等） |
| 3 | 停在人工验收门（awaiting），待采纳后用续跑继续 |
| 4 | 上游产物缺失或契约不满足，无法继续 |

## 反模式

| 反模式 | 为什么错 |
|---|---|
| 验收门停下后，Agent 自己“代表用户”确认通过 | gate: human 的决定权在有权采纳人；自批等于没有验收门，采纳记录里必须留 decided_by |
| 段失败了整条链从头重跑 | 前面段的产物与证据都还在；从失败段 `--from` 续跑即可，从头跑会重复烧成本还可能产生重复台账 |
| 直接改某段目录里的产物文件，再让下游“将就用” | 下游按 manifest 的 sha256 认产物；手改文件后哈希对不上，续跑会以退出码 4 拦下——应回该段重跑 |
| 为了赶进度跳过 accept 段 | accept 不是 optional，运行器会明确报错；真要免验收，先改 chain.yaml 的契约并重新校验留痕 |
| 在本文件里复述各段 skill 的方法论 | 段的方法以各自 SKILL.md 为唯一真源；链只写工序与契约，复述必然漂移 |

## 红线

- 验收段 `gate: human` 未获有权采纳人确认，不得以任何方式越过或代批。
- 不跳过非 optional 段；不静默降级（缺产物、契约不符一律停下报错，先诊断再续跑）。
- 每段结束必留 manifest 与产物回执；声称完成而无 manifest 者，视为未完成。

## 简洁输出规范

人类可读输出遵循三段式：**结论**（一句话，≤50 字）/ **关键信息**（≤5 条，每条 ≤30 字）/ **详情**（折叠，需要时展开）。`--json`、退出码、机器协议逐字节不动。
全量输出：`LIVEPOWERS_VERBOSE=1 <命令>`（临时）；`<LIVEPOWERS_HOME>/config.yaml` 写 `verbose: true`（持久）。

本链各命令的结论行原文：validate 为「校验通过：delivery-chain（5 段）」；run 完成为「全链完成：<run-id>」，停门为「停在验收门：accept（退出码 3，待采纳后续跑）」；status 为「<run-id>：<状态>（完成 x/5 段）」。
