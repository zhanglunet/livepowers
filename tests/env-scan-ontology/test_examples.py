"""env-scan-ontology 的独立验收测试。L1/L3 纯文本可跑；L2 需 lp 环境则跳过。"""
import re
import unittest
from pathlib import Path

from helpers import find_livepowers_lp, run_lp

SKILL = Path(__file__).resolve().parents[2] / "skills" / "env-scan-ontology" / "SKILL.md"
TEXT = SKILL.read_text(encoding="utf-8")
LP = find_livepowers_lp()


def _frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "缺 frontmatter"
    fm = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if line and ":" in line and not line.startswith("#"):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm


class Contract(unittest.TestCase):
    """L1：两种起点与只读扫描原则存在。"""

    def test_frontmatter_name_matches_dir(self):
        self.assertEqual(_frontmatter(TEXT).get("name"), "env-scan-ontology")

    def test_two_starting_points(self):
        self.assertIn("存量改造", TEXT)
        self.assertIn("新建再造", TEXT)

    def test_readonly_scan(self):
        self.assertIn("只读扫描", TEXT)
        self.assertIn("用只读账号", TEXT)

    def test_goal_statement(self):
        self.assertIn("知道自己在哪里", TEXT)


class Examples(unittest.TestCase):
    """L2：文档里的扫描命令例子可复现（纯文本）。"""

    def test_sqlite_scan_example(self):
        self.assertIn("scan_sqlite.py <db> --fingerprint", TEXT)

    def test_drift_detection_exit_code(self):
        self.assertIn("--diff .livepowers/env/fp-yesterday.json .livepowers/env/fp-today.json", TEXT)
        self.assertIn("有漂移 exit 5", TEXT)

    @unittest.skipIf(LP is None, "需 lp 真实环境")
    def test_lp_evidence_add_runs(self):
        r = run_lp(LP, "evidence", "add", "--intent", "ci-smoke-scan",
                   "--system", "S2", "--outcome", "success", "--verifiable")
        self.assertEqual(r.returncode, 0)


class Negative(unittest.TestCase):
    """L3：红线明确写出扫描阶段不能做的事。"""

    def test_never_write_during_scan(self):
        self.assertIn("绝不在扫描阶段写库", TEXT)

    def test_sensitive_fields_not_sampled(self):
        self.assertIn("只记字段名与类型，不抽样、不写日志", TEXT)


if __name__ == "__main__":
    unittest.main()
