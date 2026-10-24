# PRD-148/T1：skill 瘦身门问题清单与决策记录模板

> trend issue #740。对应 PRD-148（中央仓库 zhanglunet/trend）。
> 状态：草案，供评审。模板定稿后 T2（#741）才开工；本文只定问题、判据与模板，不写钩子和脚本。

## 1. 定位：瘦身门管什么、何时触发

瘦身门是**发布前的选题门**：一个 skill 在"标为 published"之前必须留一条决策记录。published 的判定锚点取本仓事实——进入 `using-livepowers` 路由表、根 README 技能表、`plugins/<name>/skills/` 插件拷贝三处登记（即 PRD-147 条目 E-D04 的三处）即视为 published。反向借用 ponytail 的用法：ponytail 在写代码前问"这需要存在吗"，本门在发 skill 前问同一组问题——**梯子停在第一个命中的动作，全部未命中才放行**。

**触发时机**：① 新 skill 提案（复制 `templates/skill.md` 之前）；② 既有 skill 大改（改名、触发条件变更、正文结构重写——判据：路由表条目措辞要动，或正文 ≥1/3 重写）。存量全量巡检不在本期（PRD-078 已做过一轮事后全量审计）。

**红线（借 ponytail 的"永不砍"清单）**：涉及安全、写操作审计、独立验收的 skill（`oltp-action-safety`、`acceptance-gates`、`auditable-agent-comms`、`takeover-handling`）不因瘦身门被合并或拒绝——它们即使与其他 skill 场景重叠，也直接跳到 Q3 并在记录中标 `safety_exempt: true`。瘦身门只挡"多余"，不砍"护栏"。

**合规说明**：[DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail)（MIT，173k★）。借鉴三点：决策梯"停在第一级满足"的结构、"信任边界/安全类永不砍"的红线思想、每轮末尾"跳过了什么、有什么风险"的披露习惯。问题清单与模板全部为按本仓现状另写的自研表述，未复制其 SKILL.md 文本；如后续引用其原文，须保留其 MIT 版权声明。

## 2. 瘦身门问题清单（决策梯，五问）

按序提问，命中即执行动作并停止；全部 pass → Q5 通过。每问的判据写死，压缩自由裁量。

| 问 | 判据（写死） | 动作 | 记录要求 |
|---|---|---|---|
| Q1 这需要存在吗（YAGNI） | 说不出翻车点（PRD-078 审计卡口径：模型原来错在哪，一句话 ≤50 字）；或翻车点用一段文档/一个模板即可解决，无需 Agent 触发式技能 | 命中 → **rejected**（不建），理由回提案人；可降级为文档段落 → **downgraded**（写进相关 skill 正文或 docs/） | 翻车点原句 + 证据链接（无证据即视为命中本问） |
| Q2 能否并入已有 skill | 与某既有 skill 翻车点相同或触发场景重叠（description 触发条件同一症状），且并入后目标 skill 正文 ≤500 行、路由表仍一句话说得清。**引用 ≠ 重叠**（见第 4 节先例） | 命中 → **merged**：进目标 skill 一节/一步骤，原提案关闭 | 目标 skill 名 + 并入位置（节名）+ 并入变更清单 |
| Q3 触发边界是否冲突 | 新 description 触发条件与某既有 skill 重叠，但翻车点不同（两个都该留） | 命中 → **reworded 后放行**：改写触发条件把边界写开；改不开回 Q2 | 修改前后的触发条件对照原文 |
| Q4 值得固化吗 | 沿用 `crystallize-to-system1` 的 F-V-S-R 预估：合成分 <5，或预计调用次数 ≤ n*；V=0（结果不可验证）一票否决 | 命中 → **rejected** 或 **deferred**（挂起进观察清单，等真实调用频次证据） | F/V/S/R 四值 + 预估依据一句话 |
| Q5 通过 | Q1–Q4 全部 pass | **approved**：进工程门（PRD-147 checklist），过门后才可发布 | 无附加 |

**Q1 证据口径（吸取 PRD-078 教训）**：翻车点证据分三档——`real-record`（真实翻车记录）、`reproducible-case`（可复现 bad case）、`constructed`（构造）。**仅 constructed 证据不得 approved**：记录照写，但状态为 `provisional`（观察清单），真实记录补齐后才转 `final`。这条直接落 PRD-078 总报告 P1 的口径修订结论（构造证据最高待改进），不在瘦身门里重蹈"19/19 全凭构造达标"的覆辙。

## 3. 决策记录模板（字段级）

一条记录一个文件，建议路径 `docs/slim-gate/records/<YYYYMMDD>-<skill-slug>.md`（最终存放形态 T2 定，须满足脚本可枚举）。YAML frontmatter + 正文，字段如下：

```yaml
record: SG-20261023-01              # 记录 ID：SG-<日期>-<两位序号>
skill: <提案名，kebab-case>          # merged 时此栏填被并入的提案名
proposer: <提案人>                   # 不得与 reviewer 相同（生成者 ≠ 采纳人）
reviewer: <人工终审人>               # PRD 风险节"保留人工终审"的落点
date: 2026-10-23
trigger: new-proposal | major-revision
ladder:                             # 五问逐问必填，不许跳格
  q1_exist: pass | rejected | downgraded
  q2_merge: pass | merged           # merged 时括注目标：<目标skill>#<节名>
  q3_boundary: pass | reworded
  q4_worth: pass | rejected | deferred
evidence:
  type: real-record | reproducible-case | constructed
  link: <证据位置；本仓内相对路径或 issue 链接>
decision: approved | merged | rejected | downgraded | deferred
target: <仅 merged：目标 skill 与节名>
changes: []                         # 并入/改名后的变更清单，逐条一行
safety_exempt: false                # 红线类 skill 标 true，跳过 Q2
cross_ref:
  audit: <PRD-078 审计卡链接；无则留空>
  engineering: <PRD-147 checklist 打分记录；发布前补填>
metrics_snapshot:
  skill_count_before: 21
  skill_count_after: 21             # approved 且确为新 skill 时 +1
status: provisional | final         # constructed 证据 → provisional
```

正文固定三段（借 ponytail 的披露习惯）：① 一句话结论；② 五问各自的判定理由（每问 ≤3 句）；③ **跳过了什么、有什么风险**——明确写出"没问的问题/没核的证据/带病点"，不许留白。

状态机：`provisional`（仅构造证据，进观察清单）→ `final`（真实证据补齐，或观察期内实际调用数据支持）；`rejected`/`merged`/`downgraded` 终态不可逆，翻案须新开记录并引用旧记录 ID。

## 4. 与 PRD-078 选题审计及 PRD-147 工程门的衔接

三道闸各管一段，判定词汇互相对齐：

| 维度 | PRD-078 选题审计（已收官） | PRD-148 瘦身门（本门） | PRD-147 工程门 |
|---|---|---|---|
| 时机 | 事后抽查（存量全量一轮） | 发布前（增量，每次提案/大改） | 发布前（过瘦身门之后） |
| 对象 | 审计时 19 个存量 skill | 新提案 + 大改的 skill | 过了瘦身门的 skill |
| 判定 | 达标 / 待改进 / 建议合并 / 建议删除 | approved / deferred / merged / rejected / downgraded | 过门 / 不过门（0/1/2 分） |
| 产出 | 审计卡 + 待办清单（trend 仓库） | 决策记录（livepowers 仓库） | checklist 打分表 |

衔接点逐条：

1. **判定词汇映射**：PRD-078 的"建议合并→merged、建议删除→rejected、待改进→deferred/observe、达标→approved"。审计待办清单里若有存量处置项，走瘦身门流程补正式记录，而不是直接动手。
2. **先例引用**：PRD-078 总报告的三处重叠定夺（crystallize-to-system1 vs nightly-crystallization-review、fde-delivery 资产回流 vs crystallize-to-system1、digital-role-spec 引用 outcome-ledger）是 Q2"引用 ≠ 重叠"判据的三个已裁先例——Q2 判定时逐案对照，不重新辩论。
3. **口径继承**：PRD-078 P1 的模板口径修订（构造证据最高待改进）已直接写进本门 Q1 证据口径（第 2 节）。
4. **交叉引用锚点（T4 执行，本文只定锚）**：① PRD-147 checklist 文档与其打分表的"定位"节互引本文；② `writing-livepowers-skills` 技能正文补一步"先过瘦身门"（它是新建技能的必读入口）；③ 决策记录 `cross_ref.engineering` 字段回填工程门打分位置。
5. **串联顺序**：提案 → 瘦身门（本文，选题）→ 工程门（PRD-147，质量）→ 三处登记 → published。两门记录以 ID 互查。

## 5. 相似 skill 检测的最小方案（T3 预告）

给 Q2/Q3 提供输入，**只提示、不判定、不自动删**（PRD 风险节红线）。

- 形态：`scripts/skill_similarity.py`，纯 Python 3.9+ 标准库（守仓库零依赖惯例），只读。
- 输入：`skills/*/SKILL.md` 的 frontmatter description（英文触发段与中文一句话分开比对，取较高值）+ 正文步骤标题。
- 算法：两两 `difflib.SequenceMatcher` 相似度；阈值 ≥0.6 提示、≥0.8 强提示。首跑基线即第 6 节"重复度"指标的来源。
- 输出：`相似对：A × B（0.72）| 重叠触发词：…`，Top-K 列表；可后续包成 `lp` 只读子命令（T3 定）。
- 明确不做：模型调用/语义嵌入；自动合并或自动改路由表；对已发布 skill 的任何自动处置。

## 6. 度量指标（技能数 / 重复度）

| 指标 | 定义 | 基线（2026-10-23） | 口径 |
|---|---|---|---|
| 技能总数 | `skills/` 目录数（契约 `EXPECTED_SKILL_COUNT = 21` 同源） | 21 | 每 minor 版本净增 ≤2，且每个新增必附 `approved` 决策记录；增减时同步契约常量 |
| 门通过率 | approved ÷（approved+rejected+merged+downgraded） | 无数据，门启用起记 | 只报告不设目标——拒绝率高不是坏事，防止"为过门而放水" |
| 重复度 | 相似度 ≥0.6 的 skill 对数（T3 脚本输出） | 待 T3 首跑 | 连续两个版本不降的高分组 → 进人工复核清单 |
| provisional 存量 | `status: provisional` 的记录数 | 0 | 季度清点，超一个 minor 版本未转 final 的逐条表态 |
| 案例留档 | merged 或 rejected 的记录数 | 0 | T5 验收要求 ≥1 例 |

度量来源只有两处：决策记录文件 + 相似度脚本输出；季度汇总回 trend 仓库统计口径，不引入新系统。

## 7. 下一步

确认后进 T2（#741）：发布前钩子 / checklist 强制项——把"无决策记录不可标为 published"落成可检查项（校验 `docs/slim-gate/records/` 与路由表/插件拷贝的差集，缺记录即 CI 失败），并在 `templates/skill.md` 自查清单追加"已过瘦身门并留记录"一条。

---

变更记录：v0.1（2026-10-23）草案。
