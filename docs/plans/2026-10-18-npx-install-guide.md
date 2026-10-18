# `npx skills add` 安装链路说明（给后续 skill 包复用）

> 来源：PRD-058/T1 实测（报告见 `2026-10-18-npx-install-t1-report.md`）
> 工具版本：skills CLI 1.7.2 / Node v24.20.0 / npx 10.9.4

## 1. 链路拆解（5 步）

1. **npx 拉包**：`npx skills` 现场下载 skills CLI（需 npm 源可达）。
2. **克隆仓库**：CLI 按 `<owner>/<repo>` 拼出 GitHub 地址并 clone（公开仓库免认证）。
3. **发现 skill**：扫描仓库中的 `SKILL.md`（livepowers 是 19 个）。
4. **选择并写入**：选 skill → 选目标 agent → 选范围（项目级 `./.agents/skills` 或全局 `~/.agents/skills`），写入/链接 skill 目录。
5. **发 telemetry**：安装事件上报（skills.sh 靠它自动索引，无人工审核）。

## 2. 哪几步最容易断（按踩坑概率排）

| # | 断点 | 现象 | 对策 |
|---|---|---|---|
| 1 | 第 4 步的**交互式选择** | 裸命令 `npx skills add <repo>` 停在 "Select skills to install"；CI/脚本无 TTY 时直接取消，装不上 | 文档永远给 `-y` 形态：`npx skills add <o>/<r> -y` |
| 2 | **项目级 vs 全局混淆** | `-y` 默认装到 `./.agents/skills`（相对 cwd）；用户以为装全局了，换目录找不到 | 两种场景各给一行命令，注明路径 |
| 3 | **目标 agent 不支持** | 如 Eve / PromptScript 不支持全局安装（上游限制） | 文档注明支持的 agent 范围；这是上游问题，不用修 |
| 4 | **仓库不可达** | 私有仓库没配 credential、网络不通，clone 失败 | 保持仓库公开；CI 里先做连通性检查 |

## 3. 自查清单（装完跑这 4 条）

```bash
npx skills list                       # 1. 全部 skill 在列表中（livepowers 应 19 个）
ls <skills-dir> | wc -l               # 2. 数量对得上（项目级 ./.agents/skills，全局 ~/.agents/skills）
grep -m1 "^name:" <skill>/SKILL.md    # 3. 抽 3–5 个，frontmatter name/description 完整
curl -sL -o /dev/null -w "%{http_code}" https://www.skills.sh/<owner>/<repo>
                                      # 4. skills.sh 索引：200=已收录，404=未收录（异步，需等）
```

## 4. 给仓库维护者的 checklist（发版前）

- [ ] 仓库公开，根目录有 `skills.sh.json`（自定义目录展示页，可选但建议）
- [ ] 每个 skill 有 `SKILL.md` 且 frontmatter 含 `name` / `description`
- [ ] README 安装章节给 `-y` 一键形态 + 验证步骤（不要只写裸命令）
- [ ] 跑一遍干净环境安装（全新 HOME + `-y`），确认数量

## 5. PRD-058 验收标准逐项确认

| # | 标准 | 状态 |
|---|---|---|
| 1 | `npx skills add zhanglunet/livepowers` 干净环境一键跑通，无人工干预 | ✅（T1/T3：`-y` 形态 3 环境全绿；裸命令需交互，已在文档注明） |
| 2 | 19 个 skill 清单完整，抽样 3–5 个可被 agent 拉起 | ✅（T3：19/19；抽样 5 个 frontmatter 完整） |
| 3 | skills.sh 可检索到 `zhanglunet/livepowers` | ⏳ 未点亮（监控 cron 每 6h 在查，点亮后自动提醒） |
| 4 | README 有一键安装章节，与实际链路一致 | ✅（本 PR：skills.sh 一节升级为 `-y` 一键形态 + 验证步骤） |

> 第 3 项是 skills.sh 侧异步 pipeline，不阻塞本文档项合并；点亮后由监控 cron 通知。
