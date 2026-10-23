# 对照抽查：writing-livepowers-skills（PRD-147/T2）

> 按 T1 §6 走查计划第 3 步：自指条目最容易暴露判定歧义的 skill 单独过一遍 skill 级条目。
> 结论：机检范围内全过（PASS，另有 2 项待人工）。

```
工程标准 checklist 机检报告（PRD-147/T2）
范围：skill:writing-livepowers-skills
HEAD：a5d4e65；日期：2026-10-23
条目来源：PRD-147/T1 checklist v0.1（trend #735 / PR #86）
----------------------------------------------------------------
E-T01 [阻断] PASS    skill:writing-livepowers-skills -> 2
      tests/writing-livepowers-skills/test_examples.py 存在
      三层标记：反例, Contract, Examples, Negative, L1, L2
E-T02 [阻断] PASS    skill:writing-livepowers-skills -> 2
      tests/triggers/writing-livepowers-skills.jsonl：正例 3、反例 2
E-T03 [阻断] MANUAL  skill:writing-livepowers-skills -> 人工
      skipIf 标注 1 处（tests/writing-livepowers-skills/test_examples.py）
      需最近一次 python -m unittest discover -s tests 输出核对
      说明：机检不可判：需最近一次全量输出与逐条 skip 理由
E-D02 [常规] PASS    skill:writing-livepowers-skills -> 2
      SKILL.md 58 行 ≤ 500
      说明：简洁判读为人工面（存疑标待复核，T1 口径）
E-D03 [阻断] PASS    skill:writing-livepowers-skills -> 2
      反引号引用、skills/ 路径、同目录文件引用全部在位
      lp 命令均带退出码或语义说明
E-D04 [阻断] PASS    skill:writing-livepowers-skills -> 2
      using-livepowers 路由表：在
      根 README 技能表：在
      CHANGELOG：在
      说明：新 skill 还须落在 CHANGELOG 的 Unreleased 节（机检不分节，人工注意）
E-D05 [常规] PASS    skill:writing-livepowers-skills -> 2
      description 含英文触发条件与中文一句话
E-X01 [阻断] PASS    skill:writing-livepowers-skills -> 2
      命令示例 1 个，均带预期结果或语义
E-X03 [阻断] PASS    skill:writing-livepowers-skills -> 2
      TestNoIdentifyingInfo 在 tests/test_repo.py 并接入 test.yml
      说明：示例数据只用通用业务对象需人工抽查（T1 口径）
E-S03 [常规] PASS    skill:writing-livepowers-skills -> 2
      声明：Bash, Read, Write, Edit
      正文引用工具：无
      说明：无关高危工具判断为人工面
E-S04 [阻断] MANUAL  skill:writing-livepowers-skills -> 人工
      未见强写操作标记（生产库/落库/DML 等）
      说明：写操作类判定需人工确认；确认在写操作类后按判据复核
----------------------------------------------------------------
汇总：PASS 9 | PARTIAL 0 | FAIL 0 | MANUAL 2 | EXEMPT 0 | NA 0
阻断级未过：0 条；常规级达标率：100%
判定：PASS(机检，另有待人工)（过门口径：阻断全 2 分且常规达标率 ≥90%）

待人工复核清单：
  - E-D02 skill:writing-livepowers-skills 行数达标（58 行），简洁可执行判读需人工
  - E-X03 skill:writing-livepowers-skills：denylist 扫描在位，示例业务数据抽查需人工
```
