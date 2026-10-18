# PRD-058/T1：`npx skills add` 安装链路现状调研报告

> trend issue：[#263](https://github.com/zhanglunet/trend/issues/263)（安装链路现状调研）
> 调研日期：2026-10-17（真实安装）/ 2026-10-18（裸命令与 `-y` 行为探测）
> 结论一句话：**链路是通的，阻塞项为零**；唯一要写进文档的是"一键安装"的正确命令形态。

## 1. 环境（工具版本）

| 工具 | 版本 |
|---|---|
| skills CLI | 1.7.2（`npx -y skills --version`） |
| Node | v24.20.0 |
| npx（npm） | 10.9.4 |
| OS | Linux（VM，x64） |

> PRD-058 风险节要求 T1 记录工具版本，T3 请用同一版本验证。

## 2. 三次实测

### 2.1 真实安装（2026-10-17）：`npx -y skills add zhanglunet/livepowers --all -g`

- 仓库解析成功：`https://github.com/zhanglunet/livepowers.git`
- 发现 **19 个 skill**，全部安装到全局 `~/.agents/skills/`
- 每个 skill 链接到数十个 agent 目录（Claude Code、Codex、Cline、Amp 等）
- 唯一报错：`Eve` / `PromptScript` 两个小众平台不支持全局安装——上游工具限制，非阻塞

### 2.2 裸命令探测（2026-10-18）：`npx skills add zhanglunet/livepowers`（无 flag，干净 HOME，无 TTY）

- 克隆仓库 → 发现 19 skills → 进入 **"Select skills to install" 交互式选择**
- 无 TTY 时干净取消，提示：`Use --agent <name> (or --agent '*') and -y to run non-interactively.` 未安装任何东西
- 结论：**裸命令不是一键的**，会停在 skill 选择这一步等人点

### 2.3 `-y` 单独测试（2026-10-18）：`npx skills add zhanglunet/livepowers -y`（干净 HOME，无 TTY）

- 非交互跑通，19 个 skill **全选安装**（跳过了选择步骤）
- 默认装到**项目级** `./.agents/skills`（相对当前目录）；加 `-g` 才进全局
- 工具自身提示：`use the --yes (-y) and --global (-g) flags to install without prompts`

## 3. 断点清单

### 阻塞项（必须修，否则装不上）：无

### 非阻塞注意项（文档口径，不用改代码）

1. **一键安装命令形态**：裸命令会弹交互式选择；真正"无人工干预一键跑通"的是
   `npx skills add zhanglunet/livepowers -y`（项目级）或加 `-g`（全局）。
   → T5 的 README"一键安装"章节必须写带 `-y` 的形态，不能只写裸命令。
2. **Eve / PromptScript 不支持全局安装**：上游 skills CLI 的平台限制，与本仓库无关；
   用户若用这两个平台，改用项目级安装。
3. **`-y` 默认项目级**：在仓库目录里跑会装到 `./.agents/skills`；要全局才加 `-g`。
   README 里两种场景各给一行命令即可。

## 4. skills.sh 索引当前状态

- 索引机制（2026-10-17 浏览器实测）：无提交流程、无人工审核；
  靠 `npx skills add` 的匿名 telemetry 自动触发 ingestion pipeline；排名按去重安装量。
- 当前状态：**未收录**（`https://www.skills.sh/zhanglunet/livepowers` 返回 404；
  2026-10-17 22:21 / 2026-10-18 04:21 两轮自动检查 + 10-18 09:14 手动复查均未收录）。
- 跟进：监控 cron（`skillsh-listing-watch`，每 6 小时）已在跑；收录后会自动提醒用户。
- `skills.sh.json`（5 分组、19 skill 元数据）已合入 main（PR #43），索引点亮后展示页即定制形态。

## 5. 给 T2 的结论

**T2（断点修复）无修复项**：三个注意项都是上游工具行为与文档口径问题，
不涉及本仓库任何文件修改。建议 T2 直接关闭（或转为 T5 文档项），
T3 可直接用 `-y` / `--all -g` 形态进多环境验证。

## 6. 测试清理说明

2.3 的 `-y` 探测在 `/home/hatch/.agents/skills/` 留下 19 个项目级安装，
已按时间戳精确清理（28 个 2026-10-14 的 lark-* 预装项未动）。
2.2 的裸命令探测未安装任何东西。全局 `~/.agents/skills/` 的 19 个为 2.1 真实安装结果，保留。
