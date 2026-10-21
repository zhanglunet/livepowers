# SKILL.md `allowed-tools` 声明规范（PRD-094/T4 C-29）

## 语义

`allowed-tools` 列出该 skill **激活时无需询问即可使用**的工具（Claude Agent Skills 规范）。
技能被调用时，Agent 按此清单直接调用工具；不在清单里的工具需先征得用户确认。

## 写法

- 写在 SKILL.md frontmatter 里，放在 `name`、`description` 之后，单行逗号分隔：
  ```yaml
  allowed-tools: Bash, Read
  ```
- 工具名用 Claude Code 标准工具名（`Bash`、`Read`、`Write`、`Edit`、`Grep`、
  `Glob`、`TodoWrite`、`WebFetch`、`WebSearch`、`Task`、`Skill`、`SlashCommand`）。
- 单行写法：与仓库契约测试的 frontmatter 简单解析器兼容（`docs/SKILL-TEST-SPEC.md`
  的 `ALLOWED_FM` 已收录该字段）。

## 诚实声明四原则

1. **只声明正文真实用到的工具**，不做预防性填充。
2. 经 Bash 跑的 `lp` CLI、`python3 scripts/*`、`git` 归为 `Bash`；shell 重定向、管道同理。
3. 正文说"产出为文件/写 YAML 规格/写入文件"才给 `Write`；说"修改现有文件"才给 `Edit`；
   读模板、读规格、读证据、读回执给 `Read`。
4. 输出格式里的"可 grep"、正文里的 `TODO(...)` 标记、"任务清单"散文，不对应
   `Grep`/`TodoWrite` 工具；技能之间互相引用不对应 `Skill` 工具；
   明确编排子 Agent 才给 `Task`。

## 本轮 20 个 skill 的声明结论

- 全部：`Bash, Read`（跑 `lp` CLI / 脚本靠 Bash；读规格、证据、回执靠 Read）。
- 加 `Write`：`digital-role-spec`（产出岗位规格 YAML，无终端输出，故无 Bash）、
  `ontology-evolution`、`ontology-grounded-spec`、`night-loop-planning`、
  `writing-livepowers-skills`。
- 加 `Edit`：`writing-livepowers-skills`（新建或**修改**技能）。
- 加 `Task`：`night-loop-planning`（正文明确编排子 Agent 并要求其从文件读上下文）。
- 无 `WebFetch`/`WebSearch`：20 份正文均无联网查阅行为。
