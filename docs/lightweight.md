# 轻量接入：借概念，不搭全套

Livepowers 的完整形态包括夜间固化、Agent 交换机、结果台账和金丝雀评测，适合要把一个领域产品长期运营下去的团队。很多团队只想要其中几个**概念**：本体独立、先查再建、值不值得固化要算账、验收不能自己查自己。本页说明最小要用到哪些部分，以及哪些可以先不碰。

## 先选目标

| 你想解决的问题 | 最小组合 |
|---|---|
| 同一种 skill 每个项目重写一份，想跨项目复用 | `generalizing-skills` + `acceptance-gates` |
| Agent 反复从零推理同一件事，想让做过的事直接复用 | `system1-first` + `explore-with-evidence` + `crystallize-to-system1` |
| 业务口径散落在各处，想有一份真值 | `env-scan-ontology` + `ontology-evolution` |
| Agent 说"做完了"，但没人敢信 | `acceptance-gates` |

四个概念对应的落点：

| 概念 | 在 Livepowers 里是什么 | 最小用法 |
|---|---|---|
| 本体独立成资产 | `ontology/ontology.yaml`，按 候选 → 已校验 → 已确认 → 已发布 演进 | 先用扫描出的草稿本体（`0.1.0-draft`）起步；skill 只写"依赖哪些对象和规则"，不复制规则正文 |
| 先查再建 | 能力注册表 + `lp registry find` | 泛化好的 skill 和脚本登记进注册表；收到请求先查，命中就用 |
| 值不值得固化 | F-V-S-R 评分 + 盈亏平衡 n* | 结果没法自动核对的（V=0）不固化；只做一次的不固化 |
| 验收分权 | 四道门：形式检查 → 契约测试 → 独立对抗审查 → 人工采纳 | 至少做到"生成者不验收自己"，并且有另一个人在另一份数据上跑通 |

## 只装需要的部分

**Claude Code**：按主题插件装，不必装全套。

```text
/plugin marketplace add zhanglunet/livepowers
/plugin install livepowers-tooling@livepowers-marketplace     # generalizing-skills、writing-livepowers-skills
/plugin install livepowers-core@livepowers-marketplace        # system1-first、explore-with-evidence、crystallize-to-system1
/plugin install livepowers-delivery@livepowers-marketplace    # acceptance-gates 等
```

**其他客户端**：`npx livepowers install` 会装全部技能；用不到的技能不会被触发，不影响使用。也可以只复制需要的 `skills/<name>/` 目录。

用到 `lp` 命令时需要 Python 3.9+：`npm i -g livepowers` 后直接可用。

## 只用到这几条命令

```bash
lp init                                         # 在项目里建 .livepowers/
lp registry find "<意图>"                        # 先查：HIT 直接用，MISS 再做
lp evidence add --intent "<意图>" --system S2 --outcome success|fail|partial   # 做完记一笔
lp score --freq <每月次数> --verifiable 0|1|2 --stability 0|1|2 --c2 <成本> --K <固化成本>   # 值不值得固化
lp registry add --name <名> --kind skill|script --intents "<意图>,<别名>" --entry <入口> \
  --generated-by <做的人> --accepted-by <验收的人>   # 验收通过后登记，生成者 ≠ 采纳人
lp intents alias "<规范意图>" "<另一种说法>"       # 同一件事换个说法不重复做
```

环境扫描与漂移比对（泛化 skill 的初始化和复用前检查会用到）：

```bash
python3 $(livepowers path)/scripts/scan_sqlite.py <db> --fingerprint fp.json > ontology.draft.yaml
python3 $(livepowers path)/scripts/scan_sql.py --dsn <dsn> --fingerprint fp.json > ontology.draft.yaml
python3 $(livepowers path)/scripts/scan_sqlite.py --diff fp-old.json fp-new.json   # 有漂移 exit 5
```

## 可以先不碰的

| 部分 | 什么时候再加 |
|---|---|
| 夜间固化评审、晨报（`nightly-crystallization-review`） | 固化候选多到需要每天集中处理时 |
| 长程任务切段（`night-loop-planning`） | 有跨小时、跨夜的任务时 |
| Agent 交换机（`auditable-agent-comms`） | 多个 Agent 之间要传消息、要能审计回放时 |
| 结果台账（`outcome-ledger`） | 要向业务证明价值、按结果计价时 |
| 金丝雀评测、能力复核 | 能力多了、模型要换了时 |
| 活软件生长面（`living-surface`） | 业务应用里要让 Agent 生成展示页时 |

## 什么时候该从轻量升级

- 注册表里的能力超过二三十个，靠人记不住哪些该复核了 → 加夜间评审和能力复核。
- 同一类泛化 skill 已经在三个以上 workspace 跑，口径开始有人改 → 把本体从草稿推进到"已发布"，走 `ontology-evolution`。
- 要对外承诺业务结果 → 加结果台账，先登记基线。
