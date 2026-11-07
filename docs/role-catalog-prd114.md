# PRD-114/T1：专家人格化打包——角色清单

> trend issue #569 · PRD 全文 adopted/PRD-114-livepowers-persona-packaging.md
> 借鉴：agency-agents（MIT）"专家人格化打包"形态——把技能集按角色组织成
> 可安装的 persona pack。只借形态，零代码复用。
> 红线：本层只盘点与设计目录结构，不新建角色包；示例全占位。

## 已有基础

- `skills/digital-role-spec/`：角色定义方法论（人 + 智能体团队 = 数字角色）
- `role-packs/`：3 个 draft 角色包（sales / hr / finance）+ manifest.json
- manifest 记录 pack_id/title/version/status/entry_skill/skills[]（含 bucket/inclusion/acceptance）

## 角色清单（v1 规划 6 角色；★ = role-packs/ 已有骨架）

| # | 角色卡 ID | 人格名称 | 核心场景 | 已有技能映射 | 状态 |
|---|---|---|---|---|---|
| 1 | ★ sales | 投放交付顾问 | 端到端交付链路 | delivery-chain + fde-delivery + acceptance-gates | draft（需补人格卡） |
| 2 | ★ hr | 招聘与人力运营 | 岗位管理 + 人才发现 | digital-role-spec + ontology-grounded-spec | draft |
| 3 | ★ finance | 财务与账单 | 预算/成本/账单口径 | token-meter + cost_recommendation | draft |
| 4 | content-marketer | 内容营销策划 | 素材生成 + 反 AI 味 | video_llm + video_copy + slop_gate | 待建 |
| 5 | ops-analyst | 运营数据分析师 | 日报 + 信号 + 推荐 | daily_report + signals + cost_learning | 待建 |
| 6 | compliance-auditor | 合规审计师 | 规则审计 + 安全门 | oltp-action-safety + acceptance-gates + audit_chain | 待建 |

## 角色卡 schema（T2 设计稿，本层定字段）

```yaml
role_id: sales            # 唯一标识
persona_name: 投放交付顾问
tagline: "从需求到上线的端到端交付"   # 一句话人格
entry_skill: using-livepowers
skills: [...]              # 复用 manifest.json 的 skills[] 结构
tone: 专业、直接、结果导向
constraints:               # 角色级红线
  - 不自动发布
  - 不跳过验收门
greeting: "你好，我是投放交付顾问。……"
```

## T2 补交付

- 3 个 draft 包补人格卡（tone/greeting/constraints）
- 3 个新角色包骨架（skills 映射 + manifest 条目）
- 角色卡 schema 进 `role-packs/schema.json`
