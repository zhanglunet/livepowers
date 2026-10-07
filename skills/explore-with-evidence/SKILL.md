---
name: explore-with-evidence
description: Use when the capability registry misses, when a request is new, rare or the environment has changed, and the agent must reason it out with the LLM (write SQL, analyze, trial-and-error, orchestrate tools). 注册表未命中、需要 Agent 自主探索时使用。
---

# 探索并留证据

System 2 昂贵，所以每次探索都要"值回票价"：要么解决了问题，要么留下了下次能少花钱的证据。

## 开始前：定边界、定预算、定刹车

- **本体范围内探索。**只用本体定义的对象、规范表、视图与原子行动。需要越界时停下，走 `ontology-evolution` 提出 Delta。
- **预算与止损。**在任务上写明最大轮次与预算（`lp task new --max-loops N --budget B`）。每进入一轮探索 `lp task move <id> explore --by <你> --reason "<本轮假设>" --cost <本轮花费>`；超限时工具会自动转入"异常接管"，此时停止并交付可诊断记录，不要无限重试。
- **OLAP（只读）**：允许多次尝试；先小样本、带 `LIMIT`，确认口径后再全量。
- **OLTP（写入）**：探索阶段只做**预演**——隔离环境、本体孪生或"事务 + 最终 ROLLBACK"。正式执行前必须过 `oltp-action-safety`。

## 步骤

1. **写下假设。**两三句话：用哪些对象、哪条关联路径、什么口径。用户给出的不确定说法记为"假设"，不要当成已确认的指令。
2. **小步试。**每一步看中间结果，不要一口气写完再跑。
3. **核对样例。**用规格里的验收样例、已确认的报表或业务已知数字核对。核对通过才算 `success`；无法核对的结果明确标注"未经核验"交给用户判断。两次生成给出相同答案不等于正确——它们可能共享同一个错误前提。
4. **留下可接手的产物。**把有效步骤整理成干净、参数化的代码或查询（丢掉试错过程），存到 `.livepowers/explorations/<日期>-<意图>.md`，包含：
   - 意图、参数、最终代码；
   - 采用的事实与来源；
   - 候选本体（新对象 / 口径，如有）与未决问题；
   - 样例核对结果；踩过的坑。
5. **记录证据**（必做）：
   ```bash
   lp evidence add --intent "<规范化意图>" --system S2 --outcome success|fail|partial \
     --tokens <估计> --seconds <耗时> --cost <估计成本> --model <模型> --task <任务id> \
     --domain OLAP|OLTP|HTAP [--writes-state] [--verifiable] --note "exploration: <路径>; scenario=<场景名>"
   ```
   `--verifiable` 仅在结果被样例或断言自动核对过时才加。在 Claude Code 插件里，若本轮忘了记，钩子会在回合结束时补记一条 `outcome partial` 的自动证据——它没有结论和可验证标记，不能替代这一步。
6. **提示固化。**同一意图已是第 3 次探索，或用户说"以后每周都要"，在回复末尾提示："该路径已满足固化候选条件，建议今晚纳入固化评审。"

## 意图命名

- 英文小写 + 空格，或简短中文；动宾结构；不含参数值：`weekly revenue by region`、`转交逾期商机`。
- 同一件事始终用同一个名字（先 `lp evidence stats` 看已有名字），否则频率统计会被稀释。

## 反模式

- 不记证据就结束。
- 把探索中的中间查询当成最终答案交付。
- 预算用完还在"再试一次"。
- 为了"更通用"在探索中顺手重构本体。
