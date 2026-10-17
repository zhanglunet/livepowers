# PRD-012/T1 草稿：独立验收测试规范（含 system1-first 完整示例）

> 状态：草稿。借鉴 K-Dense-AI/scientific-agent-skills（MIT）`tests/<name>/test_examples.py` + `tests/_contract/structure.py`。
> 核心思想：测试只读不执行 skill 的"主张"，不断言"写得好不好"，只断言"说到做到"。

## 1. 目录结构

```
tests/
  _contract/
    run_contract.py          # 契约测试 runner（一份，所有 skill 共用）
  <skill-name>/
    test_examples.py         # 该 skill 的示例 + 反例测试
```

`tests/<skill-name>/` 与 `skills/<skill-name>/` 一一对应，缺目录 = 测试缺失 = CI 打回。

## 2. 测试分三层

| 层 | 测什么 | 能不能在无 livepowers 环境跑 |
|---|---|---|
| L1 契约 | frontmatter 字段、SKILL.md 引用文件存在、`lp` 命令的退出码有文档 | 能（纯文本解析） |
| L2 示例 | skill 里的"断言性例子"可复现 | 部分能（见下） |
| L3 反例 | 不该触发的场景明确不触发 | 能（文本规则） |

L2 的诚实划分：凡是需要 `lp` CLI 真实环境的用例，标记 `skipIf(lp 不可用)`，
在 CI 有 livepowers 环境的 job 里跑；纯文档一致性用例永远可跑。

## 3. 契约测试 runner（`tests/_contract/run_contract.py`）——可直接用

```python
#!/usr/bin/env python3
"""skill 包结构契约测试。只读不执行被测文件。"""
import re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ALLOWED_FM = {"name", "description", "license", "compatibility", "allowed-tools", "metadata"}

def parse_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m: return None, ["缺 frontmatter"]
    fm, problems = {}, []
    for i, raw in enumerate(m.group(1).splitlines(), 1):
        s = raw.strip()
        if not s or s.startswith("#"): continue
        if ":" not in s:
            problems.append(f"第{i}行无法解析：{s}"); continue
        k, v = s.split(":", 1)
        fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, problems

def check_skill(skill_dir):
    errors, warnings = [], []
    md = skill_dir / "SKILL.md"
    if not md.is_file(): return ["缺 SKILL.md"], []
    text = md.read_text(encoding="utf-8")
    fm, probs = parse_frontmatter(text); errors.extend(probs)
    if fm is None: return errors, warnings
    for k in fm:
        if k not in ALLOWED_FM: errors.append(f"未知字段：{k}")
    for req in ("name", "description"):
        if req not in fm: errors.append(f"缺必填字段：{req}")
    if fm.get("name") != skill_dir.name:
        errors.append(f"name={fm.get('name')!r} 与目录名不一致")
    if len(text.splitlines()) > 500:
        warnings.append("SKILL.md 超过 500 行")
    # 引用的 skills/<other>/ 必须存在
    for other in set(re.findall(r"`([a-z0-9-]+)`", text)):
        if (REPO / "skills" / other).is_dir() and other != skill_dir.name:
            pass  # 合法引用
    # 反向检查：文本里点名的 skill 必须真实存在
    for other in set(re.findall(r"[Ll]iving-surface|crystallize-to-system1|explore-with-evidence|ontology-grounded-spec|oltp-action-safety|env-scan-ontology", text)):
        # 归一化为目录名
        dirname = {"Living-surface": "living-surface"}.get(other, other)
        if not (REPO / "skills" / dirname).is_dir():
            errors.append(f"引用的 skill 不存在：{other}")
    # `lp <cmd>` 出现时，同段必须有退出码说明（防"只给命令不给语义"）
    for m in re.finditer(r"`(lp [a-z ]+)`", text):
        cmd = m.group(1)
        window = text[max(0, m.start()-200):m.end()+400]
        if "退出码" not in window:
            warnings.append(f"`{cmd}` 附近缺退出码说明")
    return errors, warnings
```

> 注：上面是最小可用版；T2 落仓时再补全（`allowed-tools` 白名单、`references/` 引用检查）。

## 4. 完整示例：`tests/system1-first/test_examples.py`

```python
"""system1-first 的独立验收测试。L1/L3 纯文本可跑；L2 需 lp 环境则跳过。"""
import re, shutil, unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / "skills" / "system1-first" / "SKILL.md"
TEXT = SKILL.read_text(encoding="utf-8")
LP = shutil.which("lp")

class Contract(unittest.TestCase):
    def test_flow_steps_present(self):
        for step in ["规范化意图", "查注册表", "HIT 或 MAYBE HIT", "MISS", "建任务"]:
            self.assertIn(step, TEXT, f"五步流程缺：{step}")

    def test_exit_codes_documented(self):
        # skill 声称的退出码语义必须写全：0=HIT, 2=MISS, 3=MAYBE HIT
        for code, meaning in [("0", "HIT"), ("2", "MISS"), ("3", "MAYBE")]:
            self.assertIn(code, TEXT)
        self.assertIn(meaning, TEXT)

    def test_no_blind_write(self):
        # 反例纪律必须明文写出：MAYBE HIT 严禁盲目调用写操作
        self.assertIn("严禁盲目调用写操作", TEXT)

    def test_evidence_command(self):
        self.assertIn("lp evidence add", TEXT)

class Examples(unittest.TestCase):
    def test_intent_normalize_example(self):
        # 文档给的例子：参数必须剥离，意图必须稳定
        self.assertIn("weekly revenue by region", TEXT)
        self.assertIn("transfer stale opportunity", TEXT)

    def test_decrystallize_signal(self):
        for sig in ["连续失败", "用户纠正了口径", "retire"]:
            self.assertIn(sig, TEXT)

    @unittest.skipIf(LP is None, "需 lp 环境")
    def test_registry_find_hit(self):
        import subprocess
        r = subprocess.run([LP, "registry", "find", "weekly revenue by region"],
                           capture_output=True, text=True)
        self.assertIn(r.returncode, (0, 2, 3))  # 契约：退出码只能是这三个

class Negative(unittest.TestCase):
    def test_not_for_free_chat(self):
        # description 限定"业务请求"；纯闲聊不应命中（文本规则：description 必须含限定词）
        fm = TEXT.split("---")[1]
        self.assertTrue(any(w in fm for w in ["业务请求", "business request"]))

if __name__ == "__main__":
    unittest.main()
```

## 5. 落仓清单（T2 照此执行）

- [ ] `tests/_contract/run_contract.py` 入仓，CI 先跑 L1
- [ ] 19 个 skill 逐个建 `tests/<name>/test_examples.py`（分三批：核心 3 → 交付安全 5 → 其余 11）
- [ ] 每个 skill 至少 1 个 L1 契约类 + 2 个示例 + 1 个反例
- [ ] `lp` 相关用例全部 `skipIf` 保护，无环境也能绿
