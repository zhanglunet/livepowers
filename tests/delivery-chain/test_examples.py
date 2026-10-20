"""delivery-chain 的独立验收测试（PRD-095/T2 原型配套）。

L1：chain.yaml 结构与引用契约——在临时组装的仓库夹具里跑运行器 validate；
    夹具中的 5 个段 skill 是占位 SKILL.md（真实 skill 已在 livepowers 仓库
    核对存在，本测试只验链的编排与契约，不验段内方法论）。
L2：运行器全链路语义在临时工作区复现：五段顺序执行 → 验收段 gate: human
    以退出码 3 停下 → --approve 续跑 → 全链 completed。
L3：反例——悬空依赖、环依赖、跳非 optional 段、上游产物缺失（退出码 4）、
    大文件只登记路径+哈希（定稿口径 4B）。
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "chain_runner.py"
CHAIN_SRC = ROOT / "skills" / "delivery-chain"
STAGE_SKILLS = ["env-scan-ontology", "ontology-grounded-spec",
                "explore-with-evidence", "acceptance-gates", "outcome-ledger"]


def _cli(*argv):
    return subprocess.run([sys.executable, str(RUNNER), *argv],
                          capture_output=True, text=True)


class Fixture(unittest.TestCase):
    """组装一次性仓库夹具：真链 + 5 个段 skill 占位 + 空工作区。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="lp-chain-test-"))
        self.repo = self.tmp / "repo"
        (self.repo / "skills").mkdir(parents=True)
        shutil.copytree(CHAIN_SRC, self.repo / "skills" / "delivery-chain")
        for name in STAGE_SKILLS:
            d = self.repo / "skills" / name
            d.mkdir()
            (d / "SKILL.md").write_text(
                "---\nname: %s\ndescription: sandbox stub（链运行器原型测试夹具）\n---\n"
                % name, encoding="utf-8")
        self.ws = self.tmp / "ws"
        self.ws.mkdir()
        self.chain = self.repo / "skills" / "delivery-chain"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def chain_text(self):
        return (self.chain / "chain.yaml").read_text(encoding="utf-8")

    def write_chain(self, text):
        (self.chain / "chain.yaml").write_text(text, encoding="utf-8")

    def run_dir_of(self, run_id):
        return self.ws / ".livepowers" / "chains" / "delivery-chain" / "runs" / run_id

    def start_run(self):
        r = _cli("run", str(self.chain), "--workspace", str(self.ws),
                 "--param", "request=按区域统计上周营收", "--json")
        payload = json.loads(r.stdout)
        return r, payload["run_id"]


class Contract(Fixture):
    """L1：校验通过、悬空依赖、环依赖。"""

    def test_validate_ok(self):
        r = _cli("validate", str(self.chain))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("校验通过", r.stdout)

    def test_dangling_dependency_rejected(self):
        self.write_chain(self.chain_text().replace("from: scan", "from: ghost-stage"))
        r = _cli("validate", str(self.chain))
        self.assertEqual(r.returncode, 1)
        self.assertIn("悬空依赖", r.stderr)

    def test_cycle_dependency_rejected(self):
        # scan 改为 from: specify（后序段），与 specify 的 from: scan 构成环
        self.write_chain(self.chain_text().replace("from: chain", "from: specify"))
        r = _cli("validate", str(self.chain))
        self.assertEqual(r.returncode, 1)
        self.assertIn("环", r.stderr)


class Examples(Fixture):
    """L2：全链路语义可复现。"""

    def test_gate_then_approve_completes(self):
        r, run_id = self.start_run()
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)  # 停在验收门
        run_dir = self.run_dir_of(run_id)
        for stage, artifact in [("scan", "ontology-draft.md"),
                                ("specify", "spec-doc.md"),
                                ("explore", "analysis-result.md"),
                                ("accept", "acceptance-record.md")]:
            self.assertTrue((run_dir / stage / artifact).exists(),
                            "缺产物：%s/%s" % (stage, artifact))
            self.assertTrue((run_dir / stage / "manifest.json").exists())
        s = _cli("status", run_id, "--workspace", str(self.ws), "--json")
        self.assertEqual(json.loads(s.stdout)["status"], "awaiting")

        r2 = _cli("run", str(self.chain), "--workspace", str(self.ws),
                  "--run-id", run_id, "--from", "accept",
                  "--approve", "--by", "测试采纳人")
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
        self.assertTrue((run_dir / "ledger" / "ledger-entry.json").exists())
        accept_man = json.loads(
            (run_dir / "accept" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(accept_man["decided_by"], "测试采纳人")
        s2 = _cli("status", run_id, "--workspace", str(self.ws), "--json")
        self.assertEqual(json.loads(s2.stdout)["status"], "completed")

    def test_skip_optional_stage_ok(self):
        r = _cli("run", str(self.chain), "--workspace", str(self.ws),
                 "--param", "request=测试请求", "--skip", "ledger", "--json")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)  # 仍停验收门
        run_id = json.loads(r.stdout)["run_id"]
        r2 = _cli("run", str(self.chain), "--workspace", str(self.ws),
                  "--run-id", run_id, "--from", "accept", "--approve")
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
        ledger_man = json.loads((self.run_dir_of(run_id) / "ledger"
                                 / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(ledger_man["status"], "skipped")


class Negative(Fixture):
    """L3：反例边界。"""

    def test_skip_non_optional_stage_rejected(self):
        r = _cli("run", str(self.chain), "--workspace", str(self.ws),
                 "--param", "request=测试请求", "--skip", "scan")
        self.assertEqual(r.returncode, 1)
        self.assertIn("optional", r.stderr)

    def test_missing_upstream_artifact_exit4(self):
        _r, run_id = self.start_run()
        (self.run_dir_of(run_id) / "explore" / "analysis-result.md").unlink()
        r = _cli("run", str(self.chain), "--workspace", str(self.ws),
                 "--run-id", run_id, "--from", "accept")
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        self.assertIn("缺失", r.stderr)

    def test_large_artifact_registered_by_path_and_hash(self):
        big = self.repo / "skills" / "big-chain"
        big.mkdir()
        (big / "chain.yaml").write_text(
            "name: big-chain\n"
            "description: \"大文件登记口径测试链\"\n"
            "version: \"0.1.0\"\n"
            "inputs:\n"
            "  - name: request\n"
            "    help: \"测试请求\"\n"
            "stages:\n"
            "  - id: scan\n"
            "    skill: env-scan-ontology\n"
            "    inputs:\n"
            "      from: chain\n"
            "      needs:\n"
            "        - request\n"
            "    outputs:\n"
            "      - ontology-draft\n"
            "    params:\n"
            "      pad_bytes: 150000\n"
            "    optional: false\n"
            "    gate: none\n"
            "    retry_limit: 0\n", encoding="utf-8")
        r = _cli("run", str(big), "--workspace", str(self.ws),
                 "--param", "request=测试请求", "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        run_id = json.loads(r.stdout)["run_id"]
        man = json.loads((self.ws / ".livepowers" / "chains" / "big-chain"
                          / "runs" / run_id / "scan" / "manifest.json")
                         .read_text(encoding="utf-8"))
        out = man["outputs"][0]
        self.assertEqual(out["stored"], "external")
        self.assertGreater(out["size"], 100 * 1024)
        self.assertTrue(Path(out["path"]).exists())
        self.assertEqual(len(out["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
