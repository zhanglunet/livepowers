# 工程标准 checklist（PRD-147）机检工具与台账

> 条目与口径以 **PRD-147/T1 checklist v0.1** 为准（trend issue #735；草案见 PR #86 的
> `docs/plans/2026-10-23-compound-eng-checklist.md`）。本目录只放 T2 落地物：机检脚本、
> 豁免台账、金样例报告。checklist 本体入库与发布文档引用门禁是 T5 的事。

## 组成

| 文件 | 作用 |
|---|---|
| `../../scripts/eng_checklist.py` | 机检脚本（零依赖，Python 3.9+ 标准库，只报告不代改） |
| `exemptions.md` | 过渡期豁免台账（字段与规则见文内；阻断级条目不可豁免） |
| `samples/` | 金样例报告（T1 §6 走查计划；livepowers-night 为 T4 修复 E-X01 后的全绿版，trend #738；全绿由 `tests/test_eng_checklist.py::TestCLIOnRealRepo::test_night_plugin_all_green` 断言） |
| `prd-094-mapping.md` | E 条目 ↔ PRD-094 C 条目字段映射（T3，双向全量表；一致性由 `tests/test_checklist_mapping.py` 机检） |

## 用法

```bash
python3 scripts/eng_checklist.py --plugin livepowers-night   # 插件走查（含其 skills + 仓库级条目）
python3 scripts/eng_checklist.py --skill night-loop-planning # 单 skill
python3 scripts/eng_checklist.py --repo                      # 只打仓库级条目
python3 scripts/eng_checklist.py                             # 全仓（21 skills + 5 插件 + 仓库）
python3 scripts/eng_checklist.py --plugin livepowers-night --format markdown --out report.md
```

- 打分：0 / 1 / 2（2=满足、1=部分、0=缺失或违反）；机检不可判的条目输出 `人工`。
- 过门判定（T1 §2）：**阻断级全部 2 分，且常规级达标率 ≥90%**；豁免条目输出 `EXEMPT`
  并从分母剔除；`N/A` 不计入分母。
- 退出码：默认 FAIL=1、其余 0；`--report-only` 恒 0。CI 目前以 report-only 接入
  （`.github/workflows/test.yml`），把失败变成硬门禁是 T4/T5 收口后的决定。

## 机检与人工的边界

- 机检覆盖：文件存在性（tests/ 三件套、触发用例数、示例在位）、三处登记比对、
  插件拷贝逐字节比对、README 四节、SKILL.md 行数与引用、双语 description、
  allowed-tools 覆盖、凭据/私有网段 IP 模式扫描、manifest 路径相对性与目标存在。
- 交人工：E-T03（最近一次全量测试输出）、E-T05（CI run 链接）、E-D02（简洁判读）、
  E-X02（发版前实跑）、E-X03（示例数据抽查）、E-S03（无关高危工具）、
  E-S04（写操作类分类与仿真步骤核对）、E-S05（占位符规约核对）。
  报告末尾的"待人工复核清单"逐条列出。

## 与 PRD-094 的关系

C 条目是收录视角（外部考官，`docs/PRD-094-store-checklist.md`），E 条目是工程视角
（自家门槛）；映射关系落 **`prd-094-mapping.md`**（T3/#737 验收物：19 条 E 条目的
正向表 + C-01–C-31 逐条反向覆盖表，被引用 10 条 / 收录侧自管 21 条）。

## 相关门禁（选题 → 瘦身 → 工程门禁 → 收录）

本 checklist 是第三道闸（工程门），谁在哪个阶段拦什么：

| 阶段 | 门禁 | 拦什么 | 位置 |
|---|---|---|---|
| 选题 | PRD-078 选题审计（已收官，事后抽查） | 翻车点不成立、证据纯构造的选题（审计卡 + 待办清单，成果在 trend 仓库） | [PRD-078 总报告](https://github.com/zhanglunet/trend/blob/main/adopted/PRD-078-final-report.md) |
| 瘦身 | PRD-148 瘦身门 | 新提案 / 大改"这需要存在吗、能否并入已有 skill"——无决策记录不可标 published | [`docs/slim-gate/README.md`](../slim-gate/README.md) |
| 工程门禁 | **PRD-147 工程标准 checklist（本门）** | 测试 / 文档 / 示例 / 安全四类 19 条——阻断级不过不出发布 PR | 本目录（`docs/engineering-checklist/`） |
| 收录 | PRD-094 收录 checklist（C-01–C-31） | 官方目录视角"收不收"：结构 / 元数据 / 质量分 | [`docs/PRD-094-store-checklist.md`](../PRD-094-store-checklist.md) |

串联顺序：提案 → 瘦身门（选题）→ 工程门（本文，质量）→ 三处登记 → published；
收录打分以 published 为前提。瘦身门决策记录的 `cross_ref.engineering` 字段回填本门
打分位置（金样例在 [`samples/`](samples/)），两门以 ID 互查。
