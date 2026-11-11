# livepowers-role-content-marketer —— 内容营销策划角色包

面向内容营销策划角色的 skill 包（骨架，PRD-114/T2）：素材生成、文案与反 AI 味把关。纯 Markdown + JSON，无构建依赖。

## 状态

- 骨架包：清单条目 + 人格卡 + plugin.json 已就位；`video_llm`、`video_copy`、`slop_gate` 三个技能待建，尚未落到根 `skills/`，包内暂无 `skills/` 拷贝目录；
- 本包状态为 `draft`，暂不上架市场清单；转 `published` 须等技能落地 + 对抗验收门禁全过（发行清单 `../manifest.json` 为单一真值源）。

## 包内技能表（规划映射）

| 技能 | 桶 | 必含/选含 | 对抗验收状态 |
|---|---|---|---|
| `video_llm` | core | 必含 | pending |
| `video_copy` | core | 必含 | pending |
| `slop_gate` | core | 必含 | pending |

## 验收状态与补偿规则

- **pending** = 对抗验收（PRD-171：作者≠验收者、三态记录）尚未跑完；技能待建期间本包不上架市场清单；
- **补偿规则**：`using-livepowers` 路由表中未随包安装的技能视为未启用，命中即按 MISS 走 `explore-with-evidence`，不改入口正文。

许可：MIT（见本包 `LICENSE`，与仓库根 LICENSE 一致）。
