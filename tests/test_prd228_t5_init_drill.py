# -*- coding: utf-8 -*-
"""PRD-228/T5 测试：验收试运行——新机器按一份配置完成四工具初始化（trend #1144）。

运行：python3 -m unittest tests.test_prd228_t5_init_drill -v（仓库根执行）

验收标准（trend #1144）：**试运行通过，初始化步骤可复现**。

演练（tmp 沙盘 = 两台"新机器"，全合成占位）：
  1. 一份源配置（portable source：skills_root/model/allowed_commands/
     telemetry_enabled）→ validate_source 通过（源头校验前置）；
  2. 新机器 A：generate_tool_configs → 四工具配置物化（claude settings.json /
     cursor rules.md / codex config.toml / pi agent.toml）→ validate_generated
     四项全过；
  3. 新机器 B（同源配置独立初始化）：产物与机器 A 逐字节一致；
  4. 机器 A 重跑初始化：幂等（同字节）；
  5. 坏源（缺 model / 非 bool telemetry）：validate_source 逐项检出 +
     generate 拒绝——初始化在源头失败，不产出半套产物。
零网络；零真实主机名（全占位）。
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from config_validation import validate_generated, validate_source  # noqa: E402
from tool_config_gen import (  # noqa: E402
    TARGET_TOOLS,
    ConfigGenError,
    generate_tool_configs,
    source_config,
)

#: 唯一事实来源：一份源配置（占位值，零真实主机名/账号）
PORTABLE_SOURCE = source_config(
    skills_root="~/.agents/skills（占位）",
    model="示例模型占位名",
    allowed_commands=["python3 --version（占位）", "git status（占位）"],
    telemetry_enabled=False,
)


def _fresh_machine(tmp: Path, name: str) -> Path:
    home = tmp / name
    home.mkdir(parents=True)
    return home


def _snapshot(config_dir: Path) -> dict[str, str]:
    return {
        str(path.relative_to(config_dir)): path.read_text(encoding="utf-8")
        for path in sorted(config_dir.rglob("*")) if path.is_file()
    }


class 初始化试运行Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="lp228-t5-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_source_validates_before_anything(self):
        """① 一份配置先过源头校验（四字段齐备）。"""
        report = validate_source(PORTABLE_SOURCE)
        self.assertTrue(report["ok"], report["errors"])

    def test_new_machine_full_init(self):
        """② 新机器 A：一份配置 → 四工具配置物化 → 完整性校验全过。"""
        home = _fresh_machine(self.tmp, "machine-A")
        written = generate_tool_configs(PORTABLE_SOURCE, home / "livepowers-config")
        self.assertEqual(sorted(written), sorted(TARGET_TOOLS))
        report = validate_generated(home / "livepowers-config")
        self.assertTrue(report["ok"], report["checks"])
        self.assertEqual(len(report["checks"]), 4)
        # 产物内容体现源配置（claude JSON 可解析且含 model）
        claude = json.loads((home / "livepowers-config" / "claude"
                             / "settings.json").read_text(encoding="utf-8"))
        self.assertIn(PORTABLE_SOURCE["model"], json.dumps(claude, ensure_ascii=False))

    def test_reproducible_across_machines(self):
        """③④ 可复现：新机器 B 同源初始化与机器 A 逐字节一致；机器 A 重跑幂等。"""
        home_a = _fresh_machine(self.tmp, "machine-A")
        home_b = _fresh_machine(self.tmp, "machine-B")
        generate_tool_configs(PORTABLE_SOURCE, home_a / "livepowers-config")
        before_rerun = _snapshot(home_a / "livepowers-config")
        generate_tool_configs(PORTABLE_SOURCE, home_b / "livepowers-config")
        self.assertEqual(_snapshot(home_a / "livepowers-config"),
                         _snapshot(home_b / "livepowers-config"))
        # 机器 A 重跑（幂等）
        generate_tool_configs(PORTABLE_SOURCE, home_a / "livepowers-config")
        self.assertEqual(before_rerun, _snapshot(home_a / "livepowers-config"))

    def test_bad_source_rejected_before_materialization(self):
        """⑤ 坏源拒绝：缺 model / telemetry 非布尔 → 校验逐项检出 + 生成拒绝。"""
        bad = dict(PORTABLE_SOURCE)
        bad.pop("model")
        report = validate_source(bad)
        self.assertFalse(report["ok"])
        self.assertTrue(any("model" in e for e in report["errors"]))
        with self.assertRaises(ConfigGenError):
            generate_tool_configs(bad, self.tmp / "should-not-exist")
        bad2 = dict(PORTABLE_SOURCE, telemetry_enabled="yes")
        report2 = validate_source(bad2)
        self.assertFalse(report2["ok"])
        self.assertTrue(any("telemetry_enabled" in e for e in report2["errors"]))
        self.assertFalse((self.tmp / "should-not-exist").exists())


if __name__ == "__main__":
    unittest.main()
