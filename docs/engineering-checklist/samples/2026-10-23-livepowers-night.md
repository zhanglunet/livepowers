# 金样例：livepowers-night 插件走查（PRD-147/T2 生成，T4 修复后全绿版）

> 按 T1 §6 走查计划生成：主走查对象 livepowers-night（2 skills），仓库级条目随走查打一次。
> T2 首跑结论：机检范围内 1 条阻断级 PARTIAL（E-X01：nightly-crystallization-review
> 7 个命令示例中 5 个带预期结果），未过门（首跑版本见 PR #88）。
> T4（trend #738）修复：为 `lp pending add`、`lp registry review` 两个示例补预期结果
> （`skills/nightly-crystallization-review/SKILL.md` + 插件拷贝），机检转全绿。
> 下方为修复后脚本原样输出（重新生成命令：
> `python3 scripts/eng_checklist.py --plugin livepowers-night --format markdown`）。
> 结论：机检范围 PASS 28 / PARTIAL 0 / FAIL 0，阻断级全部 2 分，常规级达标率 100%，
> 判定 PASS(机检，另有待人工)；待人工复核清单见报告末尾。

```
工程标准 checklist 机检报告（PRD-147/T2）
范围：plugin:livepowers-night（skills: night-loop-planning, nightly-crystallization-review）；repo
HEAD：e5baf59；日期：2026-10-24
条目来源：PRD-147/T1 checklist v0.1（trend #735 / PR #86）
----------------------------------------------------------------
E-T01 [阻断] PASS    skill:night-loop-planning -> 2
      tests/night-loop-planning/test_examples.py 存在
      三层标记：契约, Contract, Examples, Negative, L1, L2
E-T02 [阻断] PASS    skill:night-loop-planning -> 2
      tests/triggers/night-loop-planning.jsonl：正例 3、反例 2
E-T03 [阻断] MANUAL  skill:night-loop-planning -> 人工
      skipIf 标注 1 处（tests/night-loop-planning/test_examples.py）
      需最近一次 python -m unittest discover -s tests 输出核对
      说明：机检不可判：需最近一次全量输出与逐条 skip 理由
E-D02 [常规] PASS    skill:night-loop-planning -> 2
      SKILL.md 94 行 ≤ 500
      说明：简洁判读为人工面（存疑标待复核，T1 口径）
E-D03 [阻断] PASS    skill:night-loop-planning -> 2
      反引号引用、skills/ 路径、同目录文件引用全部在位
      lp 命令均带退出码或语义说明
E-D04 [阻断] PASS    skill:night-loop-planning -> 2
      using-livepowers 路由表：在
      根 README 技能表：在
      CHANGELOG：在
      说明：新 skill 还须落在 CHANGELOG 的 Unreleased 节（机检不分节，人工注意）
E-D05 [常规] PASS    skill:night-loop-planning -> 2
      description 含英文触发条件与中文一句话
E-X01 [阻断] PASS    skill:night-loop-planning -> 2
      命令示例 1 个，均带预期结果或语义
E-X03 [阻断] PASS    skill:night-loop-planning -> 2
      TestNoIdentifyingInfo 在 tests/test_repo.py 并接入 test.yml
      说明：示例数据只用通用业务对象需人工抽查（T1 口径）
E-S03 [常规] PASS    skill:night-loop-planning -> 2
      声明：Bash, Read, Write, Task
      正文引用工具：无
      说明：无关高危工具判断为人工面
E-S04 [阻断] MANUAL  skill:night-loop-planning -> 人工
      未见强写操作标记（生产库/落库/DML 等）
      说明：写操作类判定需人工确认；确认在写操作类后按判据复核
E-T01 [阻断] PASS    skill:nightly-crystallization-review -> 2
      tests/nightly-crystallization-review/test_examples.py 存在
      三层标记：反例, Contract, Examples, Negative, L1, L2
E-T02 [阻断] PASS    skill:nightly-crystallization-review -> 2
      tests/triggers/nightly-crystallization-review.jsonl：正例 3、反例 2
E-T03 [阻断] MANUAL  skill:nightly-crystallization-review -> 人工
      skipIf 标注 1 处（tests/nightly-crystallization-review/test_examples.py）
      需最近一次 python -m unittest discover -s tests 输出核对
      说明：机检不可判：需最近一次全量输出与逐条 skip 理由
E-D02 [常规] PASS    skill:nightly-crystallization-review -> 2
      SKILL.md 78 行 ≤ 500
      说明：简洁判读为人工面（存疑标待复核，T1 口径）
E-D03 [阻断] PASS    skill:nightly-crystallization-review -> 2
      反引号引用、skills/ 路径、同目录文件引用全部在位
      lp 命令均带退出码或语义说明
E-D04 [阻断] PASS    skill:nightly-crystallization-review -> 2
      using-livepowers 路由表：在
      根 README 技能表：在
      CHANGELOG：在
      说明：新 skill 还须落在 CHANGELOG 的 Unreleased 节（机检不分节，人工注意）
E-D05 [常规] PASS    skill:nightly-crystallization-review -> 2
      description 含英文触发条件与中文一句话
E-X01 [阻断] PASS    skill:nightly-crystallization-review -> 2
      命令示例 7 个，均带预期结果或语义
E-X03 [阻断] PASS    skill:nightly-crystallization-review -> 2
      TestNoIdentifyingInfo 在 tests/test_repo.py 并接入 test.yml
      说明：示例数据只用通用业务对象需人工抽查（T1 口径）
E-S03 [常规] PASS    skill:nightly-crystallization-review -> 2
      声明：Bash, Read
      正文引用工具：无
      说明：无关高危工具判断为人工面
E-S04 [阻断] MANUAL  skill:nightly-crystallization-review -> 人工
      未见强写操作标记（生产库/落库/DML 等）
      说明：写操作类判定需人工确认；确认在写操作类后按判据复核
E-T04 [阻断] PASS    plugin:livepowers-night -> 2
      比对 plugins/livepowers-night/skills/ 与根 skills/ 共 2 个文件
E-D01 [阻断] PASS    plugin:livepowers-night -> 2
      plugins/livepowers-night/README.md 四节核对：用途（开篇简介）、安装、快速上手、配置项
E-S01 [阻断] PASS    plugin:livepowers-night -> 2
      凭据模式扫描 0 命中（plugins/livepowers-night）
      说明：机密应一律 ${VAR} 占位并在 manifest variables 声明名
E-S02 [阻断] PASS    plugin:livepowers-night -> 2
      plugins/livepowers-night/.claude-plugin/plugin.json icon=assets/icon.svg
E-S05 [阻断] PASS    plugin:livepowers-night -> 2
      识别信息模式扫描 0 命中（plugins/livepowers-night）
      TestNoIdentifyingInfo 在位：是
      说明：占位符规约核对为人工面（T1 口径）
E-T05 [常规] MANUAL  repo -> 人工
      test.yml 矩阵与 denylist job 配置在位
      说明：机检不可判：需最近一次 CI run 链接（三个 job 全 success）
E-X02 [常规] PASS    repo -> 2
      examples/walkthrough.sh：在
      最小链示例 skills/delivery-chain/examples/minimal-chain/：在
      说明：机检只验在位；一键走通需每次发版前实跑（T1 口径）
E-X04 [常规] PASS    repo -> 2
      templates/parallel-experts/ 在位（9 个文件）
      README 文件表核对：README 提到的 3 个文件全部存在
E-S01 [阻断] PASS    repo -> 2
      凭据模式扫描 0 命中（hooks+scripts+examples+templates）
      说明：机密应一律 ${VAR} 占位并在 manifest variables 声明名
E-S02 [阻断] PASS    repo -> 2
      .claude-plugin/plugin.json icon=.claude-plugin/assets/icon.svg
      .claude-plugin/marketplace.json source=./plugins/livepowers-core
      .claude-plugin/marketplace.json source=./plugins/livepowers-ontology
      .claude-plugin/marketplace.json source=./plugins/livepowers-delivery
      .claude-plugin/marketplace.json source=./plugins/livepowers-night
      .claude-plugin/marketplace.json source=./plugins/livepowers-tooling
      .cursor-plugin/marketplace.json source=plugins/livepowers-core
      .cursor-plugin/marketplace.json source=plugins/livepowers-ontology
      .cursor-plugin/marketplace.json source=plugins/livepowers-delivery
      .cursor-plugin/marketplace.json source=plugins/livepowers-night
      .cursor-plugin/marketplace.json source=plugins/livepowers-tooling
      .cursor-plugin/plugin.json skills=./skills/
      .cursor-plugin/plugin.json hooks=./hooks/hooks-cursor.json
E-S05 [阻断] PASS    repo -> 2
      识别信息模式扫描 0 命中（skills+plugins+docs+examples+hooks+scripts+templates+commands）
      TestNoIdentifyingInfo 在位：是
      说明：占位符规约核对为人工面（T1 口径）
----------------------------------------------------------------
汇总：PASS 28 | PARTIAL 0 | FAIL 0 | MANUAL 5 | EXEMPT 0 | NA 0
阻断级未过：0 条；常规级达标率：100%
判定：PASS(机检，另有待人工)（过门口径：阻断全 2 分且常规达标率 ≥90%）

待人工复核清单：
  - E-D02 skill:night-loop-planning 行数达标（94 行），简洁可执行判读需人工
  - E-X03 skill:night-loop-planning：denylist 扫描在位，示例业务数据抽查需人工
  - E-D02 skill:nightly-crystallization-review 行数达标（78 行），简洁可执行判读需人工
  - E-X03 skill:nightly-crystallization-review：denylist 扫描在位，示例业务数据抽查需人工
  - E-S05 plugin:livepowers-night：占位符规约（<HOST>/<TOKEN>/example.com）核对需人工
  - E-X02 repo：两处示例在位，发版前实跑记录需人工存档
  - E-S05 repo：占位符规约（<HOST>/<TOKEN>/example.com）核对需人工
```
