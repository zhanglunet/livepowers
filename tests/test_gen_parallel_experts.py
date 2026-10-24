#!/usr/bin/env python3
"""PRD-112/T2：harness 生成器一键铺出并行专家骨架。

验收看生成物是否仍满足 T1 的目录、角色边界和专家/汇总契约。
不启动编排。Python 3.9 兼容。
"""
import contextlib
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import gen_harness  # noqa: E402

TPL = REPO / "templates" / "parallel-experts"
EXAMPLE = REPO / "examples" / "parallel-experts" / "page-review.yaml"
GEN = SCRIPTS / "gen_harness.py"

REQUIRED = (
    "README.md",
    "NOTICE",
    "orchestra.yaml",
    "envelope.md",
    "orchestrator.md",
    "agents/specialist.md",
    "agents/writer.md",
    "schema/finding.schema.json",
    "schema/report.schema.json",
)
PHASES = ("detect", "dispatch", "synthesize", "write")
SEVERITY = ["critical", "high", "medium", "low", "info"]
FINDING_REQUIRED = ["id", "expert", "module", "severity", "summary", "evidence", "falsify"]
REPORT_REQUIRED = ["orchestra", "run_id", "target", "experts", "findings", "generated_by"]
FORBIDDEN = re.compile(
    r"https?://|ftp://|\b(?:\d{1,3}\.){3}\d{1,3}\b|\blocalhost\b"
    r"|@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    r"|ghp_|github_pat_|sk-|AKIA|xox[baprs]-|-----BEGIN ",
    re.I,
)


def _run(argv):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return gen_harness.main(argv)


class TestParallelGenerate(unittest.TestCase):
    def test_documented_command_builds_skeleton(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [sys.executable, str(GEN), "--parallel-experts", "-o", tmp, str(EXAMPLE)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("harness/page-review/", proc.stdout)
            root = Path(tmp) / "harness" / "page-review"
            self.assertTrue((root / "orchestra.yaml").is_file())
            self.assertFalse((root / "cli.py").exists())

    def test_layout_contracts_and_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = _run(["--parallel-experts", "--json", "-o", tmp, str(EXAMPLE)])
            self.assertEqual(code, 0)
            root = Path(tmp) / "harness" / "page-review"
            for rel in REQUIRED:
                self.assertTrue((root / rel).is_file(), rel)
            self.assertEqual((root / "spec.yaml").read_bytes(), EXAMPLE.read_bytes())
            self.assertEqual((root / "NOTICE").read_bytes(), (TPL / "NOTICE").read_bytes())
            self.assertEqual(
                (root / "agents" / "specialist.md").read_bytes(),
                (TPL / "agents" / "specialist.md").read_bytes(),
            )
            for rel in ("schema/finding.schema.json", "schema/report.schema.json"):
                self.assertEqual((root / rel).read_bytes(), (TPL / rel).read_bytes())

            readme = (root / "README.md").read_text(encoding="utf-8")
            self.assertIn("page-review", readme)
            for rel in REQUIRED:
                if rel != "README.md":
                    self.assertIn(rel, readme)

            orchestra = (root / "orchestra.yaml").read_text(encoding="utf-8")
            self.assertNotIn("{orchestra-name}", orchestra)
            self.assertEqual(orchestra.count("role: readonly"), 3)
            self.assertEqual(orchestra.count("role: writer"), 1)
            self.assertIn("gate: confirm-write", orchestra)
            self.assertIn('keep: "highest-severity"', orchestra)
            self.assertIn('dedupe_key: "id"', orchestra)
            for phase in PHASES:
                self.assertIn("id: %s" % phase, orchestra)
            for level in SEVERITY:
                self.assertIn("- %s" % level, orchestra)
            self.assertIn(
                ".livepowers/orchestras/page-review/runs/{run-id}",
                orchestra,
            )

            parsed = gen_harness.parse_yaml(orchestra)
            tpl = gen_harness.parse_yaml((TPL / "orchestra.yaml").read_text(encoding="utf-8"))
            self.assertEqual(parsed["name"], "page-review")
            self.assertEqual([p["id"] for p in parsed["phases"]], list(PHASES))
            self.assertEqual([p["does"] for p in parsed["phases"]], [p["does"] for p in tpl["phases"]])
            self.assertEqual([ex["id"] for ex in parsed["experts"]], ["content", "meta", "media"])
            self.assertEqual([ex["role"] for ex in parsed["experts"]], ["readonly"] * 3)
            self.assertEqual([ex["when"] for ex in parsed["experts"]], ["always", "always", "{condition}"])
            self.assertEqual(parsed["experts"][0]["modules"], ["headings", "links"])
            self.assertEqual(parsed["experts"][0]["prompt"], "agents/specialist.md")
            self.assertEqual(parsed["writer"]["id"], "apply")
            self.assertEqual(parsed["writer"]["role"], "writer")
            self.assertEqual(parsed["writer"]["tools"], ["Read", "Edit", "Write"])
            self.assertEqual(parsed["writer"]["gate"], "confirm-write")
            self.assertEqual(parsed["writer"]["prompt"], "agents/writer.md")
            self.assertEqual(parsed["merge"], tpl["merge"])
            self.assertNotIn("apply", [ex["id"] for ex in parsed["experts"]])

            finding = json.loads((root / "schema" / "finding.schema.json").read_text(encoding="utf-8"))
            report = json.loads((root / "schema" / "report.schema.json").read_text(encoding="utf-8"))
            self.assertEqual(finding["required"], FINDING_REQUIRED)
            self.assertEqual(finding["properties"]["severity"]["enum"], SEVERITY)
            self.assertEqual(report["required"], REPORT_REQUIRED)
            self.assertEqual(report["properties"]["findings"]["items"]["required"], FINDING_REQUIRED)

            specialist = (root / "agents" / "specialist.md").read_text(encoding="utf-8")
            orchestrator = (root / "orchestrator.md").read_text(encoding="utf-8")
            writer = (root / "agents" / "writer.md").read_text(encoding="utf-8")
            envelope = (root / "envelope.md").read_text(encoding="utf-8")
            self.assertIn("tools: Read, Grep, Glob", specialist.split("---", 2)[1])
            self.assertNotIn("Write", specialist.split("---", 2)[1])
            self.assertIn("tools: Read, Grep, Glob", orchestrator.split("---", 2)[1])
            self.assertNotIn("Write", orchestrator.split("---", 2)[1])
            self.assertIn('name: "page-review-orchestrator"', orchestrator)
            self.assertNotIn("{orchestra-name}", orchestrator)
            self.assertNotIn("{orchestra-name}", envelope)
            self.assertIn("orchestra: page-review", envelope)
            for field in (
                "run_dir:",
                "target:",
                "context_file:",
                "modules:",
                "prior_findings:",
                "return:",
            ):
                self.assertIn(field, envelope)
            self.assertIn("{expert-id}", specialist)
            self.assertIn("tools: Read, Edit, Write", writer)
            self.assertIn("confirm-write", writer)
            self.assertIn('name: "apply"', writer)
            self.assertNotIn("{writer-id}", writer)
            self.assertIn("{write-root}", writer)

            hits = []
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    if FORBIDDEN.search(line):
                        hits.append("%s:%d" % (path.relative_to(root), i))
            self.assertEqual(hits, [])

    def test_second_run_is_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(_run(["--parallel-experts", "-o", tmp, str(EXAMPLE)]), 0)
            first = {
                p.relative_to(tmp).as_posix(): p.read_bytes()
                for p in Path(tmp).rglob("*")
                if p.is_file()
            }
            self.assertEqual(_run(["--parallel-experts", "-o", tmp, str(EXAMPLE)]), 0)
            second = {
                p.relative_to(tmp).as_posix(): p.read_bytes()
                for p in Path(tmp).rglob("*")
                if p.is_file()
            }
            self.assertEqual(first, second)

    def test_json_lists_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [sys.executable, str(GEN), "--parallel-experts", "--json", "-o", tmp, str(EXAMPLE)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["kind"], "parallel-experts")
            self.assertEqual(payload["name"], "page-review")
            self.assertEqual(len(payload["files"]), len(REQUIRED) + 1)
            self.assertIn("harness/page-review/spec.yaml", payload["files"])
            self.assertIn("harness/page-review/schema/finding.schema.json", payload["files"])


class TestParallelRejects(unittest.TestCase):
    def _spec(self, **overrides):
        data = gen_harness.parse_yaml(EXAMPLE.read_text(encoding="utf-8"))
        data.update(overrides)
        return data

    def test_rejects_endpoint_without_echoing_it(self):
        secret = "ghp_" + ("a" * 24)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.yaml"
            text = EXAMPLE.read_text(encoding="utf-8").replace(
                "判断一份页面草稿能否发布，不直接改文件",
                secret,
            )
            path.write_text(text, encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(GEN), "--parallel-experts", "--json", "-o", tmp, str(path)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 1)
            self.assertNotIn(secret, proc.stdout)
            self.assertNotIn(secret, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertFalse(payload["ok"])
            self.assertIn("占位符", payload["error"])
            self.assertFalse((Path(tmp) / "harness").exists())

    def test_rejects_comment_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.yaml"
            path.write_text(
                EXAMPLE.read_text(encoding="utf-8") + "\n# note " + "http://" + "placeholder\n",
                encoding="utf-8",
            )
            code = _run(["--parallel-experts", "-o", tmp, str(path)])
            self.assertEqual(code, 1)
            self.assertFalse((Path(tmp) / "harness").exists())

    def test_rejects_shape_errors(self):
        cases = []
        short = self._spec()
        short["experts"] = short["experts"][:2]
        cases.append(short)
        four = self._spec()
        four["experts"] = four["experts"] + [dict(four["experts"][1])]
        cases.append(four)
        bad_when = self._spec()
        bad_when["experts"][0]["when"] = "{condition}"
        cases.append(bad_when)
        always_third = self._spec()
        always_third["experts"][2]["when"] = "always"
        cases.append(always_third)
        role = self._spec()
        role["experts"][0]["role"] = "writer"
        cases.append(role)
        dup_mod = self._spec()
        dup_mod["experts"][1]["modules"] = ["headings"]
        cases.append(dup_mod)
        collide = self._spec()
        collide["writer"] = {"id": "content"}
        cases.append(collide)
        concrete = self._spec()
        concrete["target"]["value"] = "page-draft"
        cases.append(concrete)
        loopback = self._spec()
        loopback["description"] = "localhost"
        cases.append(loopback)
        for spec in cases:
            with self.subTest(spec=spec):
                with self.assertRaises(gen_harness.SpecError):
                    gen_harness.validate_parallel(spec)

    def test_capability_yaml_is_not_an_orchestra(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "capability.yaml"
            path.write_text(
                "\n".join([
                    'name: "ping-ledger"',
                    'description: "记录一次心跳"',
                    'version: "0.1.0"',
                    "commands:",
                    "  - name: record",
                    '    description: "记录一次心跳"',
                    "    examples:",
                    '      - "ping-ledger record {target}"',
                    "",
                ]),
                encoding="utf-8",
            )
            code = _run(["--parallel-experts", "-o", tmp, str(path)])
            self.assertEqual(code, 1)
            self.assertFalse((Path(tmp) / "harness").exists())

    def test_missing_file_and_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(_run(["--parallel-experts", "-o", tmp, str(Path(tmp) / "missing.yaml")]), 1)
        proc = subprocess.run([sys.executable, str(GEN)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)


class TestCapabilityPathUnchanged(unittest.TestCase):
    def test_still_emits_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "capability.yaml"
            path.write_text(
                "\n".join([
                    'name: "ping-ledger"',
                    'description: "记录一次心跳"',
                    'version: "0.1.0"',
                    "commands:",
                    "  - name: record",
                    '    description: "记录一次心跳"',
                    "    args:",
                    "      - name: target",
                    '        help: "探测目标"',
                    "    examples:",
                    '      - "ping-ledger record {target}"',
                    "",
                ]),
                encoding="utf-8",
            )
            proc = subprocess.run(
                [sys.executable, str(GEN), "--json", "-o", tmp, str(path)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["ok"])
            self.assertNotIn("kind", payload)
            root = Path(tmp) / "harness" / "ping-ledger"
            self.assertTrue((root / "cli.py").is_file())
            self.assertTrue((root / "SKILL.md").is_file())
            self.assertEqual((root / "capability.yaml").read_bytes(), path.read_bytes())
            self.assertFalse((root / "orchestra.yaml").exists())
            help_proc = subprocess.run(
                [sys.executable, str(root / "cli.py"), "--help"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(help_proc.returncode, 0, help_proc.stderr)


if __name__ == "__main__":
    unittest.main()
