# PRD-171/T1：对抗式验收用例规范（正例/反例/三态）

> trend issue #855。对应 PRD-171（中央仓库 zhanglunet/trend）。
> 状态：草案，供评审。规范定稿后 T2（#856）才开工；本文只定用例分类、字段与三态判据，不写 verifier 脚本、不落用例文件。
> 现状基线：2026-10-25，livepowers main `be00d9d`（10-23 批次 PRD-147/148 已合并）。

## 1. 定位与借鉴

借鉴对象：[cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill)（**MIT**，观测 commit `c1c8a8c14710`）。借鉴三点，全部按本仓现状另写自研表述、未复制上游文本：

1. **三态判定词汇**：confirmed（有完整证据链与有界观察结果）、needs_validation（有一个精确的未落定事实、不带严重级）、rejected（记录被证伪的候选）——本规范将这套词汇定为 skill 对抗验收的判定语言；
2. **"验证者永远不是发现者"**：核对候选的 agent 不得是提出它的 agent——落为 T2 的独立性机检约束（§6）；
3. **机器可读记录 + 零依赖校验器形态**：上游用 JSON schema 加无依赖脚本校验 findings，本仓沿用"JSONL/JSON + 纯 Python 标准库脚本"的既有惯例承接。

如后续引用上游原文，须保留其 MIT 版权声明。非目标提醒（PRD 节选）：不自动删除已发布历史 skill；不降低安全相关用例标准。

**门禁链插入点**：选题（PRD-078）→ 瘦身门（PRD-148）→ 工程门（PRD-147，静态质量）→ **对抗验收（本规范，动态证伪）** → 收录（PRD-094）。published 的锚点沿用瘦身门定稿口径：三处登记（`using-livepowers` 路由表、根 README 技能表、`plugins/<name>/skills/` 拷贝）。对抗验收卡在**三处登记之前**：没有对抗验收记录，不得开始三处登记。

**与 PRD-012 三层测试的关系**：不替代。L1 契约 / L2 示例 / L3 反例（`tests/<skill>/test_examples.py`）回答"说到做到吗"，且主要由作者会话编写维护；对抗验收回答"**别人来跑还能推翻吗**"——同一批主张，换独立 verifier 复现并主动证伪（工程门 E-T01/E-T03 的对抗执行面）。

## 2. 现状基线（可衔接面）

| 现状 | 位置 | 本规范如何衔接 |
|---|---|---|
| 21 个 skill，契约 `EXPECTED_SKILL_COUNT = 21` | `skills/`、`tests/_contract/` | 用例清单按 skill 全覆盖建目录，缺目录即未过门 |
| 三层测试与触发用例 | `tests/<skill>/test_examples.py`、`tests/triggers/<name>.jsonl`（E-T02 门禁 ≥3 正例 ≥2 反例） | 用例主张的**来源锚点**（§3），不是复制 |
| 独立对抗审查（四道门之三）与五种职责表 | `skills/acceptance-gates/SKILL.md` | 把"审查者与执行者不得同主体"落到 skill 发布场景，给出可机检字段 |
| 工程门机检与豁免台账 | `scripts/eng_checklist.py`、`docs/engineering-checklist/exemptions.md`（EX- ID 规则） | 豁免**复用该台账**，不另立系统（§5） |
| 生成者 ≠ 采纳人铁律 | `lp registry add` 拒绝 `--generated-by` 与 `--accepted-by` 同值 | verifier 独立性机检沿用同一形态（§6） |
| open PR 冲突面 | livepowers PR #55 已合并（tests 域），当前无 open PR | 本 T1 纯加法 `docs/plans/` 一个 .md，无文件域冲突 |

## 3. 用例分类与编号

**四类用例**（正例验证"声称做到的确实做到"，反例验证"声称不做的确实不做"）：

| 类型 | 名称 | 被测主张来自 | 示例（构造） |
|---|---|---|---|
| `POS-EX` | 示例正例 | SKILL.md 正文的示例命令与预期结果（E-X01 的对抗面） | 正文示例命令重跑，退出码与输出样例一致 |
| `POS-TR` | 触发正例 | frontmatter description 声称的触发场景 | 命中触发条件后按声明流程步骤走完 |
| `NEG-TR` | 触发反例 | description 的边界限定（L3 的对抗面） | 限定词之外的场景不触发 |
| `NEG-RED` | 红线反例 | 正文"严禁/必拦"级主张 | MAYBE HIT 严禁盲目调用写操作——构造越权输入必被拦 |

**编号**：`AC-<skill>-<类><两位序号>`，如 `AC-system1-first-POS01`、`AC-acceptance-gates-RED01`。红线类（`NEG-RED`）用例一律标 `safety: true`。

**数量下限**（每 skill）：`POS-EX` ≥1、`POS-TR` ≥1、`NEG-TR` ≥2、`NEG-RED`：红线 skill ≥2，非红线 skill ≥1；确无"严禁"级主张的 skill 标 N/A 并留理由。红线 skill 名单沿用瘦身门红线：`oltp-action-safety`、`acceptance-gates`、`auditable-agent-comms`、`takeover-handling`。

**锚点强制**：每条用例必须引用主张原文位置（`SKILL.md#<节名>` 或既有测试路径）；无锚点的用例无效，verifier 应拒绝执行。

## 4. 用例文件与三态记录字段

T2 落文件，本文定字段。目录形态：

```
tests/adversarial/<skill-name>/
├── cases.jsonl      # 用例清单（评审合入即冻结，§6）
└── findings.json    # 三态记录（verifier 写入）
```

`cases.jsonl` 每行一个用例，字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `case_id` | string | `AC-<skill>-<类><序号>`，全仓唯一 |
| `skill` | string | 目录名，与 `skills/<name>` 一致 |
| `type` | enum | `POS-EX` / `POS-TR` / `NEG-TR` / `NEG-RED` |
| `claim` | string | 被测主张一句话（引用式转述，不复制大段） |
| `claim_source` | string | 锚点：`skills/<name>/SKILL.md#<节名>` 或测试路径 |
| `input` | string | verifier 的执行输入；数据一律占位符（`<HOST>`、`<TOKEN>`、通用业务对象） |
| `expected` | array | 可观察判据：退出码、输出含/不含、注册表/台账状态变化 |
| `safety` | bool | `NEG-RED` 恒 true；参与豁免禁令（§5） |
| `priority` | enum | `core` / `extended`；core 用例缺一即未过门 |

`findings.json` 顶层为 `records` 数组，每条：

| 字段 | 说明 |
|---|---|
| `record_id` | `AV-<YYYYMMDD>-<skill>-<两位序号>` |
| `case_id` | 对应用例；重验须新开 record，不改旧 record |
| `verdict` | `confirmed` / `needs_validation` / `rejected` |
| `evidence` | 回执位置：命令输出摘录、退出码、产物路径——第三方可按此重放 |
| `falsification_attempts` | 证伪尝试清单，逐条"做了什么、观察是什么"；confirmed 至少 1 条未推翻 |
| `unresolved_fact` | 仅 `needs_validation`：一个精确的未落定事实（能指向一次补验动作）；**不带严重级** |
| `disproved_by` | 仅 `rejected`：最小复现（输入→观察→与主张的矛盾点） |
| `verifier` / `verifier_model` | 执行者会话标识 / 模型披露字段（不作 confirmed 依据，§6） |
| `author` | skill 内容生成者标识，供机检比对与 verifier 分离 |
| `date` | 执行日期 |

状态机：候选 → 证伪失败且判据全过 → `confirmed`；存在未落定事实 → `needs_validation`（事实落定后复审转 confirmed 或 rejected）；任一观察与主张矛盾 → `rejected`（**终态不可逆**，翻案须新 case 与新 record 并引用旧 record_id）。`rejected` 只记录不代改——修复回 skill 跟踪（沿用工程门"只报告不代改"口径）。

两条样例（构造数据，标"构造"，验证字段可判定）：

```jsonl
{"case_id":"AC-system1-first-POS01","skill":"system1-first","type":"POS-EX","claim":"规范化意图后查注册表，命中返回退出码 0","claim_source":"skills/system1-first/SKILL.md#操作","input":"lp registry find \"weekly revenue by region\"","expected":["exit 0","输出含命中能力条目"],"safety":false,"priority":"core"}
{"case_id":"AC-system1-first-RED01","skill":"system1-first","type":"NEG-RED","claim":"MAYBE HIT 严禁盲目调用写操作","claim_source":"skills/system1-first/SKILL.md#MISS 分支","input":"构造 MAYBE HIT 状态下的写命令请求","expected":["不执行写操作","输出要求先核对前置条件"],"safety":true,"priority":"core"}
```

## 5. 三态判定判据（写死）与门禁规则

| 判定 | 判据（全部满足才可给） | 必填证据 |
|---|---|---|
| `confirmed` | ① `expected` 逐条观察一致；② ≥1 次主动证伪尝试未推翻主张；③ 证据可复算（第三方按 `evidence` 能重放） | evidence + falsification_attempts |
| `needs_validation` | `expected` 因环境/数据缺失无法落定，且 `unresolved_fact` 精确可补验。**"看起来对"不得给 confirmed，只能给 needs_validation** | unresolved_fact |
| `rejected` | 任一观察与 `claim` 矛盾即 rejected，不允许"带病 confirmed" | disproved_by 最小复现 |

**误杀保护（PRD 风险节）**：`needs_validation` 允许人工豁免后发布，但必须留痕——登记进 `docs/engineering-checklist/exemptions.md`（EX- ID、批准人 ≠ 实现者、期限默认 1 个 minor），豁免规则全部沿用工程门既有台账，本规范不另立一套。**禁令：`safety: true` 的用例，无论 verdict 是 rejected 还是 needs_validation，一律不可豁免**（对应非目标"不降低安全相关用例标准"）。

**门禁规则（T3 的落地范围，本文只定判定输入）**：published（三处登记）的前置条件 = 该 skill 存在 `tests/adversarial/<skill>/findings.json`，且 core 用例全部 `confirmed`，未 confirmed 项均有有效豁免。缺 findings.json = 未过门；extended 用例不阻塞。校验载体（零依赖脚本还是 CI job）T3 定。

## 6. 职责分离规则（T2 的实现约束，本文定规则）

1. **作者会话不可自签**：`verifier` 会话标识不得等于 `author` 会话标识——与 `lp registry add` 拒绝 `--generated-by == --accepted-by` 同一铁律；T2 机检遇同值即 FAIL。
2. **用例冻结**：`cases.jsonl` 随规范评审合入即冻结，verifier 只读。verifier 认为用例本身有误 → 在 record 加 `case_error` 备注并给 `needs_validation`，不得私改用例。
3. **验收标准不可由生成方修改**：`cases.jsonl` 与 `findings.json` 变更 PR 的作者不得是合并人（生成者 ≠ 采纳人的延伸）。
4. **换模型不消除相关错误**：`verifier_model` 仅作披露；两个模型一致也可能重复同一误解（`acceptance-gates` 既有口径），重要判断仍由人工采纳（四道门之四）收口，本规范不自动化人工门。

## 7. 走查计划（T1 收口）与下一步

T1 收口动作：按 §4 样例对 `system1-first`、`acceptance-gates` 各补齐一组示例用例（含 1 条 `NEG-RED`），检查字段可判定、判据无歧义、锚点真实存在；只写样例、不跑 verifier（样例随本文走查记录补入变更记录节，标注"构造"）。评审重点：① 四类划分是否够用；② core 用例集是否过重；③ 豁免复用工程门台账是否成立。

**下一步**：确认后进 T2（#856）：独立 verifier 跑验收并写 findings——落 `tests/adversarial/` 用例文件与 findings 模板、作者会话不可自签的机检、配套测试。T3（#857）把 §5 门禁规则落成脚本/CI；T4（#858）与 PRD-094/147 checklist 字段对齐出映射文档。

---

变更记录：v0.1（2026-10-25）草案。
