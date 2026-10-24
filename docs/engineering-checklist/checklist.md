# 官方级工程标准 checklist v0.1（PRD-147）

> 本体入库（PRD-147/T5，trend #739）。草案与评审记录见
> `docs/plans/2026-10-23-compound-eng-checklist.md`（T1，trend #735 / PR #86）；
> 机检口径以 `scripts/eng_checklist.py` 为准，条目编号 / 类别 / 级别与本表的一致性由
> `tests/test_eng_checklist_t5.py` 断言。发布文档（根 README「发布门禁」节）引用本门。
> 借鉴 [EveryInc/compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin)
> （MIT）的两点做法：条目给"可用命令复核"的验收方式、评审只报告不代改；条目文本为自研表述。

## 1. 公共约定

| 约定项 | 口径 |
|---|---|
| 条目编号 | `E-<类><两位序号>`：T=测试、D=文档、X=示例、S=安全。与 PRD-094 的 C-01–C-31 不共用编号空间，映射只走 `prd-094-mapping.md` |
| 打分 | 0 / 1 / 2：2=完全满足，1=部分满足，0=缺失或违反；机检不可判输出"人工"，不打自由分 |
| 门禁级别 | **阻断**：得 0 或 1 分即挡发布，不可豁免；**常规**：可修复，或走第 3 节豁免登记（限期） |
| 适用范围 | skill / 插件 / 仓库三层，分开算分、不折总分 |
| 证据强制 | 每条打分必须附证据（文件路径 + 字段/行号，或命令输出存档位置）；无证据视为未打分 |
| N/A | 不适用标 N/A 并写明理由，不计入分母 |
| 版本标 | v0.1（2026-10-23 入库）；每次修订升小版本并在文末变更节记录 |
| 过门判定 | 阻断级条目全部得 2 分，且（常规级得 2 分数 ÷ 常规级适用条目数）≥ 90%。任一不满足 → 修复或豁免，否则不出发布 PR |

## 2. 条目表（四类 19 条）

### 2.1 测试（E-T01–E-T05）

| 编号 | 类别 | 级别 | 适用 | 要求（判定写死） | 验收方式 |
|---|---|---|---|---|---|
| E-T01 | 测试 | 阻断 | skill | 每个 skill 有独立验收测试目录，L1 契约 / L2 示例 / L3 反例三层齐备；`tests/<skill-name>/test_examples.py` 与 `skills/<skill-name>/` 一一对应，缺目录即缺测试 | 目录清单比对 + `python -m unittest tests._contract.run_contract` 输出 |
| E-T02 | 测试 | 阻断 | skill | 触发用例齐备：`tests/triggers/<name>.jsonl` 存在且 ≥3 条正例、≥2 条反例 | 文件存在性 + jsonl 行数统计（脚本可判） |
| E-T03 | 测试 | 阻断 | skill | 示例可复现、反例不误触发；需真实环境的 L2 用例必须显式 `skipIf` 标注，不得假绿 | `python -m unittest discover -s tests -v` 最近一次输出，skip 项逐条有标注 |
| E-T04 | 测试 | 阻断 | plugin | 插件拷贝同步：`plugins/<name>/skills/` 内容与根 `skills/` 一致，无分叉、无漏带新 skill | `python -m unittest tests.test_plugin_sync tests.test_marketplace_install` 通过 |
| E-T05 | 测试 | 常规 | repo | CI 矩阵全绿：`test.yml` 在 Python 3.9 / 3.11 / 3.13 三个版本全部通过，含 denylist 扫描 job | 最近一次 CI run 记录（三个 job 全 success） |

### 2.2 文档（E-D01–E-D05）

| 编号 | 类别 | 级别 | 适用 | 要求（判定写死） | 验收方式 |
|---|---|---|---|---|---|
| E-D01 | 文档 | 阻断 | plugin | 插件 README 含四节：用途、安装、快速上手、配置项；缺一节即 1 分 | 逐插件 README 对照四节清单 |
| E-D02 | 文档 | 常规 | skill | SKILL.md 正文简洁可执行：以步骤/判据表/命令为主，无大段理念叙述；正文 ≤500 行 | 行数统计 + 人工判读（判读存疑标"待复核"） |
| E-D03 | 文档 | 阻断 | skill | 引用完整性：正文引用的文件、其他 skill 真实存在；出现的 `lp <cmd>` 命令同段有退出码/语义说明 | 契约测试输出 + 引用清单 × 仓库文件核对 |
| E-D04 | 文档 | 阻断 | skill | 三处登记齐全：新 skill 必须同时登记 ① `using-livepowers` 路由表 ② 根 README 技能表 ③ CHANGELOG（Unreleased 节）；缺任一处即 0 分 | 三处逐一 grep skill 名比对（脚本可判） |
| E-D05 | 文档 | 常规 | skill | 描述双语口径：frontmatter `description` 为英文触发条件 + 中文一句话；只有单一语言即 1 分 | frontmatter description 原文核对 |

### 2.3 示例（E-X01–E-X04）

| 编号 | 类别 | 级别 | 适用 | 要求（判定写死） | 验收方式 |
|---|---|---|---|---|---|
| E-X01 | 示例 | 阻断 | skill | 每个 skill 正文至少 1 个可直接抄的示例：命令代码块 + 预期结果（退出码或输出样例二者其一）；只有命令没有预期结果即 1 分 | SKILL.md 命令节逐个核对 |
| E-X02 | 示例 | 常规 | repo | 仓库级示例一键可走通：`examples/walkthrough.sh` 五分钟体验跑通；最小链示例的试跑命令有效 | 本地实跑记录存档（每次发版前重跑一次） |
| E-X03 | 示例 | 阻断 | skill | 示例数据全部脱敏：只用通用业务对象（订单/商机/合同/工单），不出现真实组织、人员、项目名、主机名、IP、账号、密钥 | `TestNoIdentifyingInfo`（LP_DENYLIST）+ 人工抽查示例数据文件 |
| E-X04 | 示例 | 常规 | repo | 新能力形态配最小示例或模板：新增编排/链式/模板类能力时，须带最小可运行示例（如 `templates/parallel-experts/` 的 README 文件表）；纯流程修订不适用（N/A 须写理由） | 示例目录存在 + README 文件表与目录一致 |

### 2.4 安全（E-S01–E-S05）

| 编号 | 类别 | 级别 | 适用 | 要求（判定写死） | 验收方式 |
|---|---|---|---|---|---|
| E-S01 | 安全 | 阻断 | plugin/repo | 凭据不入库：全仓无字面 token/密钥/密码；机密一律 `${VAR}` 占位并在 manifest variables 声明名 | 凭据模式扫描记录（对 hooks、scripts、`.mcp.json`、示例） |
| E-S02 | 安全 | 阻断 | plugin | manifest 路径全部相对且不逃逸：plugin.json / marketplace.json 无绝对路径、无 `..`、目标文件存在 | 两个 manifest 路径字段逐项核对（脚本可判） |
| E-S03 | 安全 | 常规 | skill | `allowed-tools` 与正文实际用到的工具一致：声明清单 ⊇ 正文工具引用，且无与任务无关的高危工具 | frontmatter allowed-tools × 正文命令/工具引用核对 |
| E-S04 | 安全 | 阻断 | skill | 写操作类 skill 正文必须含"先仿真后执行"步骤，并挂 `oltp-action-safety` 八项检查口径（引用 skill 名即可，不得复制其内容）；缺仿真步骤即 0 分 | 正文步骤节人工核对 + 契约测试引用检查 |
| E-S05 | 安全 | 阻断 | skill/plugin/repo | 文档与示例中不得出现真实内部主机名、IP、账号或密钥，一律占位符（如 `<HOST>`、`<TOKEN>`、`example.com` 类保留域）；命中即 0 分 | `TestNoIdentifyingInfo` + 占位符规约核对（金样例报告与文档另由 `tests/test_eng_checklist_t5.py` 扫描断言） |

与 PRD-094 收录 checklist（C-01–C-31）的字段映射见 [`prd-094-mapping.md`](prd-094-mapping.md)（T3，trend #737）；
两表关系：C 条目是收录视角（外部考官），E 条目是工程视角（自家门槛），重合条目 E 只收紧不放松。

## 3. 过渡期豁免

允许"过渡期豁免"但须标注（PRD-147 风险节）。登记位置：[`exemptions.md`](exemptions.md)
台账（一行一条豁免，`scripts/eng_checklist.py` 解析后输出 `EXEMPT` 并从达标率分母剔除）。
规则：阻断级不可豁免；同一对象同时有效的豁免 ≤3 条；同一条目不得连续豁免两次；
批准人不得与实现者同一人（生成者 ≠ 采纳人）；限期到期自动失效。字段定义见 T1 草案第 5 节。

## 4. 谁来跑、何时跑

- 机检：`python3 scripts/eng_checklist.py`（全仓）或 `--plugin <name>` / `--skill <name>` / `--repo`；
  CI 以 report-only 接入（`.github/workflows/test.yml`），报告与金样例在 [`samples/`](samples/)。
- 发布前：过门口径见第 1 节；发布文档（根 README「发布门禁」节）引用本门，未过门不出发布 PR。
- 与瘦身门（PRD-148）、收录（PRD-094）的串联顺序见 [`README.md`](README.md) 的「相关门禁」。

---

变更记录：v0.1（2026-10-23）草案定稿并入库（T5）；条目与 `scripts/eng_checklist.py` 的
ITEMS 登记表同口径（`tests/test_eng_checklist_t5.py` 断言编号 / 类别 / 级别一致）。
