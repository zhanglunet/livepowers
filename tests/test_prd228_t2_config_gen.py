# -*- coding: utf-8 -*-
"""PRD-228/T2 自测（trend #1141）：一份源配置生成四工具配置。

运行：uv run --with pytest python -m pytest tests/test_prd228_t2_config_gen.py -q

覆盖（验收「四工具配置均可由一份源配置生成」）：
  源配置 → 四工具配置文件全部生成且路径正确；
  内容映射：Claude JSON 可解析含 model/allow；Cursor md 含模型与命令；
    Codex TOML model = 值；Pi telemetry 布尔；
  缺必填字段拒绝；
  幂等（二次生成零 diff）；
  只写 out_dir（调用方给临时目录）。
零网络。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from tool_config_gen import ConfigGenError, generate_tool_configs, source_config  # noqa: E402

SRC = source_config("/path/to/skills", "test-model",
                    allowed_commands=["git status", "pytest"],
                    telemetry_enabled=False)


class ConfigGenTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / "out"

    def test_all_four_tools_generated(self):
        written = generate_tool_configs(SRC, self.out)
        self.assertEqual(set(written.keys()), {"claude", "cursor", "codex", "pi"})
        for path in written.values():
            self.assertTrue(Path(path).exists())

    def test_claude_json_parseable_with_model_and_allow(self):
        written = generate_tool_configs(SRC, self.out)
        data = json.loads(Path(written["claude"]).read_text(encoding="utf-8"))
        self.assertEqual(data["model"], "test-model")
        self.assertIn("pytest", data["permissions"]["allow"])

    def test_cursor_md_contains_model_and_commands(self):
        written = generate_tool_configs(SRC, self.out)
        text = Path(written["cursor"]).read_text(encoding="utf-8")
        self.assertIn("test-model", text)
        self.assertIn("git status", text)

    def test_codex_toml_model_line(self):
        written = generate_tool_configs(SRC, self.out)
        text = Path(written["codex"]).read_text(encoding="utf-8")
        self.assertIn('model = "test-model"', text)

    def test_pi_telemetry_bool(self):
        written = generate_tool_configs(SRC, self.out)
        text = Path(written["pi"]).read_text(encoding="utf-8")
        self.assertIn("enabled = false", text)

    def test_missing_required_field_rejected(self):
        with self.assertRaises(ConfigGenError):
            generate_tool_configs({"model": "m"}, self.out)

    def test_idempotent_second_run_zero_diff(self):
        generate_tool_configs(SRC, self.out)
        before = {p: Path(p).read_text(encoding="utf-8") for p in
                  [str(self.out / t / f) for t, f in
                   [("claude", "settings.json"), ("cursor", "rules.md"),
                    ("codex", "config.toml"), ("pi", "agent.toml")]]}
        generate_tool_configs(SRC, self.out)
        for p, content in before.items():
            self.assertEqual(Path(p).read_text(encoding="utf-8"), content)


if __name__ == "__main__":
    unittest.main()
