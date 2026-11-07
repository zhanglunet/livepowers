# QUICKSTART：5 分钟跑通 livepowers

> 复制粘贴 → 出结果。不需要理解全部概念。

## 前置

- Python 3.11+
- `pip install pyyaml`（仅测试需要）

## 第 1 步：查看你能做什么（30 秒）

```bash
python3 scripts/skill_registry.py search "delivery"
```

你会看到 livepowers 里与 delivery 相关的技能列表。

## 第 2 步：跑一次审计流水线（2 分钟）

```bash
python3 scripts/audit_pipeline.py \
  --contract tests/fixtures/audit/demo-contract.md \
  --preset tests/fixtures/audit/preset-annotations.json
```

这条命令会用 demo 合同跑完六段审计（recon → hunting → 证伪 → findings → 复核 → 报告），
输出 findings.json 与 report_md。两次运行结果逐字节一致。

## 第 3 步：生成并行专家骨架（1 分钟）

```bash
python3 scripts/gen_harness.py --parallel-experts \
  examples/parallel-experts/page-review.yaml \
  --output /tmp/my-first-experts
```

你会在 `/tmp/my-first-experts/` 下看到：
```
agents/
  content.md    ← 专家 1：内容审查
  meta.md       ← 专家 2：元信息审查
  media.md      ← 专家 3：媒体审查（条件触发）
writer.md         ← 汇总写手
```

## 第 4 步：仲裁你的第一组产出（1 分钟）

```python
import sys; sys.path.insert(0, "scripts")
from parallel_arbitration import arbitrate

experts = [
    {"id": "content", "when": "always", "modules": ["headings"]},
    {"id": "meta", "when": "always", "modules": ["title"]},
]
outputs = {
    "content": [{"module": "headings", "verdict": "pass"}],
    "meta": [{"module": "title", "verdict": "pass"}],
}
result = arbitrate(experts, outputs)
print(result["adopted"])  # 你会看到两条产出被采纳
```

## 恭喜 🎉

你已经在 5 分钟内：
1. 检索了技能注册表
2. 跑通了六段审计流水线
3. 生成了并行专家骨架
4. 体验了仲裁规则

## 下一步

- 浏览 `skills/` 下的 21 个技能（用 `search` 找你关心的）
- 读 `README.md` 了解架构
- 改 `examples/parallel-experts/page-review.yaml` 里的 modules 看输出变化
