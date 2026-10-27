# 对抗验收发布门禁（PRD-171/T3）

> 规范：docs/plans/2026-10-25-adversarial-acceptance.md（PRD-171/T1，trend issue
> #855）；本门：trend issue #857。判定输入：scripts/adversarial_verify.py 的
> `gate` 命令（PRD-171/T2 落）；发布面接线：scripts/adversarial_gate.py（本门）。

## 规则（T1 §5，写死）

published 的前置条件 = 过对抗验收门，全部满足才可三处登记：

1. 存在 `tests/adversarial/<skill>/cases.jsonl`（用例清单随评审冻结，缺目录即未过门）；
2. `findings.json` 判定 PASS：core 用例全部 `confirmed`；未 confirmed 项均有有效
   豁免（`exempt_ref` 指向工程门豁免台账 docs/engineering-checklist/exemptions.md
   里登记的 EX- ID，且对象为该 skill）；
3. `safety: true` 用例一律不可豁免；`rejected` 无豁免通道；extended 用例不阻塞；
4. **缺 findings.json = 未过门（缺 findings 即拒）**。

## published 锚点

沿用瘦身门定稿口径（三处登记，scripts/slim_gate.py `published_map`）：
① `using-livepowers` 路由表 ② 根 README 技能表 ③ `plugins/<name>/skills/` 拷贝。
对抗验收卡在三处登记**之前**：没有对抗验收记录，不得开始三处登记。

## 基线与豁免

- **基线存量**：docs/adversarial-gate/baseline-2026-10-25.md（启用日 2026-10-25，
  21 个存量 skill，口径对齐瘦身门）。基线内不要求补记录；入组验收通过后移出
  基线，移出即按基线外规则强制。
- **needs_validation 人工豁免**：允许豁免后发布，但必须留痕进工程门豁免台账
  （EX- ID、批准人 ≠ 实现者、期限默认 1 个 minor，规则全部沿用既有台账）；
  **safety 用例不可豁免**（对应 PRD-171 非目标"不降低安全相关用例标准"）。

## 门禁链位置

选题（PRD-078）→ 瘦身门（PRD-148）→ 工程门（PRD-147，静态质量）→
**对抗验收（本门，动态证伪）** → 收录（PRD-094）。
与 PRD-012 三层测试不替代：三层测试回答"说到做到吗"，对抗验收回答
"别人来跑还能推翻吗"。

## 用法

    python3 scripts/adversarial_gate.py                # 全量检查（违规退出 1）
    python3 scripts/adversarial_gate.py --report-only  # 恒退出 0

CI：.github/workflows/test.yml 在 slim gate 之后硬失败运行本门（`python
scripts/adversarial_gate.py`），基线外 published skill 未过门即打回。

## 全流程走查留档

- [demo-2026-10-27.md](demo-2026-10-27.md)（PRD-171/T5，trend issue #859）：虚构
  skill 夹具完整走 cases → check → gate 三阶段，含误报驳回（rejected 留痕 → 修复
  重验过门 core 3/3）与五类故意失败反向对照；机检复现 `python3 -m unittest
  tests.test_adversarial_t5 -v`。
