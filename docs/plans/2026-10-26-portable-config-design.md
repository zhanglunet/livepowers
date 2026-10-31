# PRD-228/T1：通用配置格式设计（一次配置多 agent 通用）

> trend issue：[#1140](https://github.com/zhanglunet/trend/issues/1140)（通用配置格式设计）
> 对应 PRD-228（中央仓库 zhanglunet/trend，`adopted/PRD-228-livepowers-portable-config.md`）
> 状态：草案，供评审。评审通过后 T2（#1141）才开工；本文只定格式，不写生成器代码。
> 关联：PRD-200（跨工具同步清单，#1000）、PRD-130（多 harness 发布矩阵）、PRD-236（feishu-reminder 同形态）
> 现状基线：2026-10-26，livepowers main `7fc9e8e`

## 0. 借鉴声明与红线

借鉴对象 gentle-ai（Gentleman-Programming/gentle-ai）的**协议未核实**，本设计只借鉴
"一份源配置、多工具通用"的**形态**：源配置是唯一事实来源，各工具配置由它派生。
未复用其任何代码、字段名或文件结构；下文字段集、映射与规则全部按本仓现状另行设计。

红线：

- 源配置与生成产物中**绝不出现密钥/token 本体**，只放引用名（§7）；
- 文档与示例中的主机名、IP、账号、密钥一律占位符；
- 本 PR 只开不合并，等用户 review。

## 1. 与现状的衔接（设计前提）

本设计接着仓库已有惯例长，不另起平行体系：

| 现状 | 出处 | 本设计如何接 |
|---|---|---|
| 全部本地状态放 `<LIVEPOWERS_HOME>/`（默认 `.livepowers/`），`config.yaml` 与 `registry.json` 同级；`LIVEPOWERS_HOME` 可整体搬移工作区，配置跟人走 | `scripts/lp_output.py` | 源配置放同一目录（§2），跟随 `LIVEPOWERS_HOME` 搬移 |
| `config.yaml` 只承载 livepowers 自身运行时开关（现仅 `verbose:`），解析为"只认顶层键"的极简子集、纯标准库 | 同上 | `config.yaml` 职责不动；跨工具源配置另开文件，避免职责混杂（决策点 D1） |
| 环境变量覆盖配置的惯例（如 `LIVEPOWERS_VERBOSE=1`） | 同上 | 预留 `LIVEPOWERS_PORTABLE_CONFIG` 环境变量覆盖源配置路径 |
| skills 分发链路已实测跑通：`npx skills add` → 全局 `~/.agents/skills/` 或项目级 `./.agents/skills/`，再链接进各 agent 目录（Claude Code、Codex、Cursor、Pi 等） | PRD-058/T1、T3 报告 | skills 类字段的映射以这条已验证链路为地基，不另造分发（§4） |
| 角色已有定义源：`role-packs/manifest.json`（`schema_version` + `pack_id` + 每包 skills 清单） | `role-packs/manifest.json` | roles 类只引用 `pack_id` + 本地覆盖，不重复定义角色（§3.5） |
| 插件清单按工具分开：`.claude-plugin/`、`.codex-plugin/`、`.cursor-plugin/` 各有 `plugin.json` | 仓库根目录 | "各工具配置载体不同"是既成事实，映射按工具分别给出（§4） |

## 2. 源配置格式总览

- **文件形态**：单个 YAML 文件，名为 `portable.yaml`，位于 `<LIVEPOWERS_HOME>/portable.yaml`
  （默认 `.livepowers/portable.yaml`）；路径可用环境变量 `LIVEPOWERS_PORTABLE_CONFIG` 覆盖。
- **为什么是 YAML**：与同目录的 `config.yaml` 一致；人可读、可手改、可 diff，
  与"配一次、处处用"的用户侧定位匹配（非目标：不替代各工具自身的配置系统）。
- **结构约束**：顶层固定六个键——`schema_version` 等元信息平铺在顶层，
  其余按四类组织：`memory` / `skills` / `mcp` / `roles`，外加 `overrides`（工具原生覆盖区，§3.6）。
  嵌套深度 ≤3 层，保证后续解析实现（T2）可选极简子集或正式 YAML 库（决策点 D2）。
- **版本**：`schema_version` 必填；格式演进只增可选字段，删改字段必须升版本，
  漂移检查按版本比对（§6）。

## 3. 字段集

### 3.1 元信息（顶层）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `schema_version` | int | 是 | 格式版本，本设计为 1；与 `role-packs/manifest.json` 的 `schema_version` 惯例一致 |
| `profile_name` | string | 否 | 这份配置的名字（仅展示与报告引用，不参与生成逻辑） |
| `updated` | string（日期） | 否 | 最后修改日期，漂移检查与报告展示用 |

### 3.2 `memory`：记忆偏好

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `memory.language` | string | 否 | 默认回复语言（如语言代码）；生成时写入各工具指令载体的托管段 |
| `memory.timezone` | string | 否 | IANA 时区名；同上 |
| `memory.verbosity` | enum：`concise` / `full` | 否 | 输出详尽程度的**偏好声明**。与 `config.yaml` 的 `verbose` 划界：`verbose` 是 livepowers 脚本的运行时开关、以 `config.yaml` 为准；本字段只声明给各 agent 工具看，生成时写入指令文件，**不反向改 `config.yaml`**（决策点 D4） |
| `memory.shared_context_files` | string[] | 否 | 共享指令文件路径（相对 `LIVEPOWERS_HOME` 或绝对路径）；内容拼入各工具的记忆/指令载体托管段 |
| `memory.preference_notes` | string[] | 否 | 短偏好条目，一句一条；生成时以列表形式拼入指令载体托管段 |

### 3.3 `skills`：精选技能

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `skills.source` | string | 否 | 技能来源仓库引用，形态 `<owner>/<repo>`；缺省为本仓 |
| `skills.scope` | enum：`global` / `project` | 否 | 安装范围，缺省 `global`；对应 PRD-058 实测的全局 `~/.agents/skills/` 与项目级 `./.agents/skills/` 两种形态 |
| `skills.include` | string[] | 否 | 精选清单（skill 名）；为空 = 全部 |
| `skills.exclude` | string[] | 否 | 排除清单；与 `include` 同时命中时 **exclude 优先** |
| `skills.pin_version` | string | 否 | 钉住的版本/引用；漂移检查的版本比对基准（与 PRD-200 的"版本对不对"衔接） |

### 3.4 `mcp`：MCP 服务器

`mcp.servers` 为列表，每项：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | 是 | 服务器名，在源配置内唯一，映射到各工具时保持同名 |
| `transport` | enum：`stdio` / `http` | 是 | 传输方式 |
| `command` | string | `stdio` 时必填 | 启动命令 |
| `args` | string[] | 否 | 命令参数 |
| `url` | string | `http` 时必填 | 服务地址；**不得内嵌凭据**（禁止 `user:password@` 形态，§7 S2） |
| `env_refs` | string[] | 否 | 需要的环境变量**名**列表——只放名字，本体由各工具运行时从环境读取（§7 S1） |
| `enabled` | bool | 否 | 缺省 `true`；`false` = 保留声明、生成时跳过 |

### 3.5 `roles`：角色

角色的定义源是 `role-packs/manifest.json`，本类只声明"启用哪个 + 本地覆盖"，不重复定义角色，避免双源漂移。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `roles.active` | string | 否 | 当前激活角色包的 `pack_id`（与 `role-packs/manifest.json` 的 `pack_id` 对齐） |
| `roles.enabled_packs` | string[] | 否 | 本机启用的角色包集合；为空 = 仅 `active` |
| `roles.overrides` | list | 否 | 本地覆盖项列表，每项含：`pack_id`（必填）、`persona_file`（可选，人设补充文件路径）、`extra_notes`（可选，string[]，拼入该角色的指令段） |

角色字段的生成细节（角色切换如何在各工具一致生效）是 T4（#1143）的范围，本节只定字段口径。

### 3.6 `overrides`：工具原生覆盖区

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `overrides.claude` | map | 否 | Claude 原生配置片段 |
| `overrides.cursor` | map | 否 | Cursor 原生配置片段 |
| `overrides.codex` | map | 否 | Codex 原生配置片段 |
| `overrides.pi` | map | 否 | Pi 原生配置片段 |

口径：`overrides` 是 PRD 风险项"每工具保留原生覆盖项"的落点——生成器**不解释、不校验**
其内部结构，只负责合并到对应工具的配置里；同一字段与通用层冲突时以 `overrides` 为准（§5 R2）。
值形态随各工具原生格式（JSON 对象 / TOML 表），在 YAML 里以嵌套 map 表达，转码由 T2 负责。

## 4. 四工具映射表

标注图例：

- **● 直接映射**：字段可无损落到该工具配置；
- **◐ 降级映射**：可落，但形态降级（如结构化字段降为指令文本），降级方式在表中注明；
- **○ 不支持**：该工具无对应载体，生成时跳过并写入生成报告的"未映射清单"
  （字段路径 + 工具 + 原因），不中断生成（§5 R5）。

各工具的"配置载体"只写形态；具体键名随工具版本演进，T2 实现时以当时版本实测钉死。

### 4.1 Claude（Claude Code）

配置载体：用户级 `~/.claude/settings.json`、项目级 `.claude/settings.json`；
MCP 在 `.mcp.json` 或 settings 的 MCP 区；记忆/指令为 `CLAUDE.md`（用户级/项目级）。

| 通用字段 | 落点 | 标注 |
|---|---|---|
| `memory.language` / `timezone` / `preference_notes` | `CLAUDE.md` 托管段（文本行） | ● |
| `memory.shared_context_files` | `CLAUDE.md` 托管段拼入 | ● |
| `memory.verbosity` | `CLAUDE.md` 托管段的偏好声明行 | ◐（声明性文本，无原生开关对应） |
| `skills.*` | `~/.agents/skills` 分发（PRD-058 实测链路）；启用状态在 settings 侧登记 | ◐（启用登记的键名随版本，T2 核实） |
| `mcp.servers[]` | `.mcp.json` / settings 的 MCP 区，`env_refs` 转 `${NAME}` 引用 | ● |
| `roles.active` / `overrides` | 角色包插件启用 + `CLAUDE.md` 托管段写入角色指令 | ◐ |

### 4.2 Cursor

配置载体：MCP 为用户级 `~/.cursor/mcp.json`；指令为项目 `.cursor/rules/` 下的规则文件
或用户规则；skills 经 `~/.agents/skills` 链接发现（PRD-058 实测）。

| 通用字段 | 落点 | 标注 |
|---|---|---|
| `memory.*` 偏好类 | 规则文件托管段 | ◐（用户级规则无稳定文件载体时，降级为项目级规则文件） |
| `skills.*` | `~/.agents/skills` 链接发现 | ● |
| `mcp.servers[]` | `~/.cursor/mcp.json` 的 `mcpServers`，`env_refs` 转 `${NAME}` 引用 | ● |
| `roles.active` / `overrides` | 规则文件中的角色段 | ◐ |

### 4.3 Codex

配置载体：`~/.codex/config.toml`（含 MCP 服务器表）；指令为 `AGENTS.md`（用户级/项目级）；
插件清单 `.codex-plugin/plugin.json`。

| 通用字段 | 落点 | 标注 |
|---|---|---|
| `memory.*` 偏好类 | `AGENTS.md` 托管段 | ● |
| `skills.*` | `~/.agents/skills` 链接发现 | ● |
| `mcp.servers[]` | `config.toml` 的 MCP 服务器表：`command` / `args` 直接对应，`env_refs` 转环境变量名声明 | ● |
| `roles.active` / `overrides` | `AGENTS.md` 托管段的角色段 | ◐ |

### 4.4 Pi

配置载体：`~/.pi/agent/settings.json`；上下文文件 `AGENTS.md` / `SYSTEM.md`；
skills 目录为 `~/.pi/agent/skills` 或经 `~/.agents/skills` 发现。

| 通用字段 | 落点 | 标注 |
|---|---|---|
| `memory.*` 偏好类 | 上下文文件托管段；偏好类原生键（若该版本 settings 有对应键）优先 | ◐（原生键名随版本，T2 核实） |
| `skills.*` | skills 目录 / `~/.agents/skills` 发现 | ● |
| `mcp.servers[]` | MCP 扩展配置 | ◐（载体形态随版本差异大，先生成独立片段文件供扩展加载，T2 实测后钉死；决策点 D3） |
| `roles.active` / `overrides` | 上下文文件托管段的角色段 | ◐ |

### 4.5 映射汇总矩阵

| 字段类 | Claude | Cursor | Codex | Pi |
|---|---|---|---|---|
| `memory` 偏好（语言/时区/备注） | ● | ◐ | ● | ◐ |
| `memory` 共享指令文件 | ● | ◐ | ● | ● |
| `memory.verbosity` | ◐ | ◐ | ◐ | ◐ |
| `skills` 精选与范围 | ◐ | ● | ● | ● |
| `mcp.servers` | ● | ● | ● | ◐ |
| `roles` 启用与人设 | ◐ | ◐ | ◐ | ◐ |

四工具 × 六类字段映射齐全，无整类缺失；◐ 项的降级方式均已在各工具表中注明，○ 项本期为零——
若 T2 实测发现某格实为 ○，按 §5 R5 进未映射清单并回写本表。

## 5. 冲突处理规则

- **R1 通用层边界**：通用层只定义 §3 的公共字段；工具专属配置一律进 `overrides.<tool>`，
  生成器不解释其内部结构。通用层不管公共字段之外的任何东西。
- **R2 三层优先级**（同一字段冲突时）：工具原生配置中的**非托管键**（用户手写的、
  与 livepowers 无关的键）永远不动 > `overrides.<tool>` 的同字段声明 > 通用层字段的生成值。
  即：原生覆盖赢通用层（PRD 风险项口径），但任何一层都不许动非托管键。
- **R3 托管边界**：生成器只写两类位置——结构化配置里的**托管键**（仅 §3 字段映射出的键），
  与文本文件里的**托管段**（以 `<!-- livepowers:portable begin -->` …
  `<!-- livepowers:portable end -->` 标记包裹）。托管范围之外一律只读。
- **R4 冲突可见**：任何字段发生覆盖、降级或跳过，生成报告必须逐条列出
  （字段路径、工具、来源层、处理结果），禁止静默覆盖。
- **R5 未映射不阻塞**：○ 字段跳过 + 进未映射清单，生成继续完成其余字段。
- **R6 幂等与可回退**：同一源配置 + 同一 `overrides` 重复生成，产物逐字节一致；
  生成前把将被修改的文件备份为同目录 `<name>.bak-portable`（只留最近一份）。
  本节定口径，备份与生成的实现属 T2。

## 6. 与 PRD-200 同步清单的衔接（供 T3）

分工：PRD-200 管**技能安装状态**漂移（装了没 / 版本对不对 / 旧版残留），
本条 T3（#1142）管**配置内容**漂移；两者共用一张状态表呈现（工具 × 检查域 × 状态），
检查项清单的总体设计在 PRD-200/T1（#1000），本节只定配置域的比对口径与数据接口，
检查实现不在本任务。

**生成清单 `portable-manifest.json`**：每次生成时落在 `<LIVEPOWERS_HOME>/portable-manifest.json`，
作为漂移检查的基线，字段如下：

| 字段 | 类型 | 说明 |
|---|---|---|
| `tool` | string | `claude` / `cursor` / `codex` / `pi` |
| `target_file` | string | 被写的目标文件路径 |
| `field_path` | string | 托管字段路径（如 `mcp.servers.<name>`、`memory.language`） |
| `value_hash` | string | 生成值的哈希指纹——**只存指纹不存值本体**（§7 S4） |
| `generated_at` | string（时间） | 生成时间 |
| `source_schema_version` | int | 生成时源配置的 `schema_version` |
| `source_hash` | string | 源配置整体哈希，判断"源改了没同步" |

**检查读什么**：源配置 `portable.yaml`（期望）、`portable-manifest.json`（上次生成基线）、
四工具目标文件中的托管键/托管段（实际）。检查**只读不写**；修复动作（重新生成）由用户触发——
与 PRD-200"只检查与建议、不做自动静默更新"的口径一致。

**漂移三态判定**：

| 状态 | 判定 |
|---|---|
| 一致 | 工具侧托管值哈希 == `manifest.value_hash`，且 `manifest.source_hash` == 当前源配置哈希 |
| 源已更新未同步 | `manifest.source_hash` != 当前源配置哈希（源改了、还没重新生成） |
| 工具侧被手改 | 工具侧托管值哈希 != `manifest.value_hash`（生成后被手改）；托管范围之外的手改不算漂移（R3） |

## 7. 安全口径

- **S1 只放引用名**：密钥/token 本体绝不写入 `portable.yaml`，也不写入生成的工具配置；
  MCP 凭据一律用 `env_refs` 声明环境变量名，生成时写成 `${NAME}` 形式的引用，
  由各工具运行时从环境展开。
- **S2 地址不内嵌凭据**：`mcp.servers[].url` 禁止 `user:password@` 形态，T2 生成时须校验拒绝。
- **S3 本地状态不分发**：`portable.yaml` 含个人偏好，属用户本地状态
  （`LIVEPOWERS_HOME`，默认 `.livepowers/`），不随仓库分发、不进任何示例仓库。
- **S4 清单只存指纹**：`portable-manifest.json` 只存哈希，不存配置值本体，
  避免把偏好与服务器清单再复制一份明文。

## 8. 完整示例（占位符）

```yaml
schema_version: 1
profile_name: "<PROFILE_NAME>"
updated: "2026-10-26"

memory:
  language: "<REPLY_LANGUAGE>"
  timezone: "<IANA_TIMEZONE>"
  verbosity: concise
  shared_context_files:
    - "context/shared.md"            # 相对 LIVEPOWERS_HOME
  preference_notes:
    - "<PREFERENCE_NOTE_1>"

skills:
  source: "<owner>/<repo>"
  scope: global
  include:
    - "<skill-name-1>"
    - "<skill-name-2>"
  exclude: []
  pin_version: "<VERSION_OR_REF>"

mcp:
  servers:
    - name: "<server-name>"
      transport: stdio
      command: "<command>"
      args: ["<arg1>"]
      env_refs: ["<YOUR_TOKEN_NAME>"]
      enabled: true
    - name: "<http-server-name>"
      transport: http
      url: "https://<mcp-host>/<path>"
      env_refs: ["<YOUR_API_KEY_NAME>"]

roles:
  active: "<role-pack-id>"
  enabled_packs: ["<role-pack-id>"]
  overrides:
    - pack_id: "<role-pack-id>"
      persona_file: "roles/<role-pack-id>-persona.md"

overrides:
  claude:
    "<native-key>": "<native-value>"
  codex:
    "<native-key>": "<native-value>"
```

## 9. 非目标与后续任务接口

- 非目标（PRD 口径）：不做配置云同步服务；不替代各工具自身的配置系统。
- T2（#1141）配置生成与分发：按 §3 字段集、§4 映射、§5 规则实现生成器，产出生成报告与 §6 的 manifest。
- T3（#1142）配置同步检查：按 §6 口径实现漂移检查，与 PRD-200 清单合表呈现。
- T4（#1143）角色落地：`roles` 类字段的生成细节与四工具一致生效验证。
- T5（#1144）验收试运行：新机器按一份 `portable.yaml` 完成四工具初始化。

## 10. 待评审决策点

| 编号 | 决策点 | 本设计建议 |
|---|---|---|
| D1 | 源配置独立文件 `portable.yaml` vs 并入 `config.yaml` | 独立文件：`config.yaml` 是极简解析的运行时开关文件，职责不同；并入会逼着重写解析且混淆"livepowers 自身开关"与"跨工具源配置" |
| D2 | YAML 解析走极简子集（零依赖、续现有惯例）vs 正式 YAML 库 | T2 定：字段结构已约束在 ≤3 层嵌套，极简子集可覆盖；若 T2 发现 `overrides` 透传表达力不够，再引正式库 |
| D3 | Pi 的 MCP 载体形态随版本差异大 | 本设计先标 ◐（独立片段文件），T2 以当时版本实测钉死后回写 §4.4 |
| D4 | `memory.verbosity` 与 `config.yaml` 的 `verbose` 关系 | 本设计划界为"偏好声明 vs 运行时开关"、互不反向改写，请评审确认 |
