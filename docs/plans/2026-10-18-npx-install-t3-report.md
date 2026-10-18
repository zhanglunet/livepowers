# PRD-058/T3：多环境安装验证报告

> trend issue：[#265](https://github.com/zhanglunet/trend/issues/265)（多环境验证）
> 验证日期：2026-10-18
> 结论一句话：**3 种干净环境全部 19/19 通过**；抽样 5 个核心 skill 可被 agent 识别。

## 1. 环境矩阵

| 环境 | Node | 用户目录 | 命令 | 安装位置 | 结果 |
|---|---|---|---|---|---|
| Env1 | v24.20.0（系统） | 全新（/tmp/t3e1home） | `npx skills add zhanglunet/livepowers -y` | 项目级 `./.agents/skills` | 19/19 ✅ |
| Env2 | v20.19.5（另装） | 全新（/tmp/t3e2home） | `npx skills add zhanglunet/livepowers -y` | 项目级 `./.agents/skills` | 19/19 ✅ |
| Env3 | v24.20.0（系统） | 全新（/tmp/t3e3home） | `npx skills add zhanglunet/livepowers --all -g` | 全局 `~/.agents/skills` | 19/19 ✅ |

- skills CLI 均为 1.7.2（npx 现场拉取）。
- 每个环境校验方式：19 个 skill 名逐一比对（acceptance-gates … writing-livepowers-skills），
  缺失数 0。
- 不同 OS：本机仅有 Linux x64；macOS / Windows 无条件验证（PRD 原文"如条件允许"，
  如实注明为未覆盖项）。

## 2. 抽样拉起（5 个核心 skill）

在 Env1 的安装结果中抽查（agent 识别 skill 靠 SKILL.md 的 frontmatter）：

| skill | SKILL.md | name | description |
|---|---|---|---|
| using-livepowers | ✅ | using-livepowers | ✅ 有 |
| system1-first | ✅ | system1-first | ✅ 有 |
| acceptance-gates | ✅ | acceptance-gates | ✅ 有 |
| explore-with-evidence | ✅ | explore-with-evidence | ✅ 有 |
| outcome-ledger | ✅ | outcome-ledger | ✅ 有 |

5/5 的 name/description 完整，可被 agent 正常识别与调用。
（功能级测试不在本 PRD 范围，见 PRD-058 非目标。）

## 3. 结论

- 安装链路在 Node 20 / 24、项目级 / 全局、干净用户目录下均一键跑通，无人工干预。
- 19 个 skill 清单完整，无缺失、无损坏。
- T3 通过。下一步：T4（索引确认，监控 cron 在跑）→ T5（README 一键安装章节，
  命令形态按 T1 结论写 `-y` 版）。

## 4. 测试清理

- /tmp/t3e1home、/tmp/t3e2home、/tmp/t3e3home 及对应 workdir 均为一次性目录，
  验证完即删（/tmp 本身也是临时盘）。
- 未动本机已有安装（~/.agents/skills 的 19 个为 2026-10-17 真实安装结果，保留）。
