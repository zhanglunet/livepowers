# -*- coding: utf-8 -*-
"""PRD-256/T2 自测（trend #1281）：模板包可安装/加载 + 合同 schema 机器校验。

运行：python3 -m unittest test_prd256_handoff_template -v（在 tests/ 目录执行）

覆盖：
  模板包结构：README/三角色/handoff.schema.json 在位
  示例合同（三角色各一，虚构任务）全部过 schema 校验
  非法合同：缺 constraints / 缺 acceptance / 非法 status / 非法枚举 → 校验拒绝
  内置退化校验与 jsonschema 一致判 0/1

虚构纪律：合同内容全虚构；不含真实主机名、账号、密钥。
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_handoff as vh  # noqa: E402

TEMPLATE = ROOT / "templates" / "pi-subagents"
SCHEMA = TEMPLATE / "handoff.schema.json"

SAMPLES = {
    "explore": {
        "schema": "handoff-v1", "task_id": "hb_explore_001", "from": "main", "to": "explore",
        "input": {"spec": "侦察示例 CLI 的命令注册方式", "files": ["cli/main.py"],
                   "constraints": ["只读侦察不改文件", "不动 CI 配置"]},
        "expect": {"artifacts": ["侦察报告"], "acceptance": ["列出全部命令注册点"]},
        "result": {"status": "done", "artifacts": ["侦察报告"],
                    "evidence": ["cli/main.py:L20 注册入口", "共 3 个子命令"]},
    },
    "implement": {
        "schema": "handoff-v1", "task_id": "hb_impl_001", "from": "main", "to": "implement",
        "input": {"spec": "新增 status 子命令", "files": ["cli/main.py"],
                   "constraints": ["不引入新依赖", "遵循既有 argparse 风格"]},
        "expect": {"artifacts": ["cli/main.py 修改"], "acceptance": ["status 命令可执行且输出版本"]},
        "result": {"status": "done", "artifacts": ["cli/main.py"],
                    "evidence": ["python cli/main.py status 输出 v0.1.0"]},
    },
    "verify": {
        "schema": "handoff-v1", "task_id": "hb_verify_001", "from": "main", "to": "verify",
        "input": {"spec": "按 acceptance 验证 status 子命令", "files": ["cli/main.py"],
                   "constraints": ["独立验收不修代码"]},
        "expect": {"artifacts": ["验收结论"], "acceptance": ["status 命令可执行且输出版本"]},
        "result": {"status": "done", "evidence": ["验收通过：status 输出 v0.1.0（运行记录）"]},
    },
}


class TestTemplateStructure(unittest.TestCase):
    def test_files_in_place(self):
        for rel in ("README.md", "handoff.schema.json",
                    "roles/explore.md", "roles/implement.md", "roles/verify.md"):
            self.assertTrue((TEMPLATE / rel).exists(), rel)

    def test_roles_carry_forbidden_section(self):
        for role in ("explore", "implement", "verify"):
            text = (TEMPLATE / "roles" / f"{role}.md").read_text(encoding="utf-8")
            self.assertIn("不做", text, f"{role} 角色页缺禁止事项节")


class TestSchemaValidation(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def test_sample_contracts_valid(self):
        for role, contract in SAMPLES.items():
            self.assertEqual(vh.builtin_validate(contract, self.schema), [], role)

    def test_missing_constraints_rejected(self):
        bad = json.loads(json.dumps(SAMPLES["explore"]))
        del bad["input"]["constraints"]
        self.assertNotEqual(vh.builtin_validate(bad, self.schema), [])

    def test_missing_acceptance_rejected(self):
        bad = json.loads(json.dumps(SAMPLES["implement"]))
        del bad["expect"]["acceptance"]
        self.assertNotEqual(vh.builtin_validate(bad, self.schema), [])

    def test_illegal_status_rejected(self):
        bad = json.loads(json.dumps(SAMPLES["verify"]))
        bad["result"]["status"] = "passed"  # 不在枚举 done|blocked|rejected
        self.assertNotEqual(vh.builtin_validate(bad, self.schema), [])

    def test_bad_task_id_pattern_rejected(self):
        bad = json.loads(json.dumps(SAMPLES["explore"]))
        bad["task_id"] = "INVALID"
        self.assertNotEqual(vh.builtin_validate(bad, self.schema), [])

    def test_jsonschema_backend_agrees(self):
        """jsonschema 可用时与内置退化校验判定一致（都判合法）。"""
        try:
            import jsonschema  # noqa: F401
        except ImportError:
            self.skipTest("jsonschema 未安装")
        import jsonschema.validators
        validator = jsonschema.validators.Draft7Validator(self.schema)
        for contract in SAMPLES.values():
            errs = list(validator.iter_errors(contract))
            self.assertEqual(errs, [])
            self.assertEqual(vh.builtin_validate(contract, self.schema), [])


if __name__ == "__main__":
    unittest.main()
