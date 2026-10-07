# AGENTS.md —— Livepowers

供读取 AGENTS.md 的智能体（Codex 等）使用。可把本文件内容合并进你项目根目录的 AGENTS.md。

本项目按「活产品」范式工作：**Agentic AI = Agent + Ontology + Harness**。开始任何任务前：

1. 阅读 `skills/using-livepowers/SKILL.md`，按其路由表找到适用技能并遵循。
2. 业务请求先运行 `python scripts/lp.py registry find "<意图>"`：HIT 走已固化能力（System 1），MISS 才探索（System 2）。
3. 每次探索结束运行 `python scripts/lp.py evidence add ...` 记录证据。
4. 缺对象或口径时不要用脚本掩盖，按 `skills/ontology-evolution/SKILL.md` 提出本体变更。
5. 任何写生产状态的动作先遵循 `skills/oltp-action-safety/SKILL.md`。
6. 任何"已完成"都要过 `skills/acceptance-gates/SKILL.md`：生成者不评审自己，以真实回执为准。
7. 多 Agent 通信经 `scripts/agent_switch.py`（中转或 sidecar-log），不私下直连。
8. 长程 / 夜间任务按 `skills/night-loop-planning/SKILL.md` 拆 DAG、按模型可稳定时长切段、填作业契约、设止损。

规划用强模型，执行可切换便宜模型；上下文写入仓库文件（规格、计划、进度、交接），不要依赖对话记忆。

## 开发本仓库

- 技能在 `skills/<name>/SKILL.md`，脚本在 `scripts/`（只用 Python 标准库），模板在 `templates/`。
- 修改后运行 `python -m unittest discover -s tests -v`。
- 新技能遵循 `skills/writing-livepowers-skills/SKILL.md`，并加入 `using-livepowers` 路由表与 README 技能表。
- 不在任何文件中写入具体组织、人员、客户或项目名称。
