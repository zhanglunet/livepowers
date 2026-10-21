#!/usr/bin/env python3
"""PRD-112/T1：并行专家编排模板的结构契约。

只检查模板文件是否自包含、字段是否齐全、占位符是否干净。
不启动编排，也不要求存在运行器。Python 3.9 兼容。
"""
import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TPL = REPO / "templates" / "parallel-experts"

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

TOP_LEVEL_KEYS = (
    "name:",
    "description:",
    "version:",
    "target:",
    "phases:",
    "experts:",
    "writer:",
    "merge:",
    "output:",
)

PHASES = ("detect", "dispatch", "synthesize", "write")
SEVERITY = ["critical", "high", "medium", "low", "info"]
FINDING_REQUIRED = ["id", "expert", "module", "severity", "summary", "evidence", "falsify"]
REPORT_REQUIRED = ["orchestra", "run_id", "target", "experts", "findings", "generated_by"]

# 真实地址、回环地址、邮箱样字符串、常见密钥前缀。占位符 {token} 不命中。
FORBIDDEN = re.compile(
    r"https?://|ftp://|\b(?:\d{1,3}\.){3}\d{1,3}\b|\blocalhost\b"
    r"|@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    r"|ghp_|github_pat_|sk-|AKIA|xox[baprs]-|-----BEGIN ",
    re.I,
)


def read(rel):
    return (TPL / rel).read_text(encoding="utf-8")


class TestTemplateLayout(unittest.TestCase):
    def test_required_files_exist(self):
        missing = [rel for rel in REQUIRED if not (TPL / rel).is_file()]
        self.assertEqual(missing, [])

    def test_readme_names_every_file(self):
        text = read("README.md")
        for rel in REQUIRED:
            if rel == "README.md":
                continue
            self.assertIn(rel, text)

    def test_no_real_endpoints_or_secrets(self):
        hits = []
        for path in TPL.rglob("*"):
            if not path.is_file():
                continue
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if FORBIDDEN.search(line):
                    hits.append("%s:%d" % (path.relative_to(TPL), i))
        self.assertEqual(hits, [])

    def test_notice_requires_copyright_when_reused(self):
        text = read("NOTICE")
        self.assertIn("MIT", text)
        self.assertIn("版权声明", text)
        self.assertIn("不得删除", text)
        self.assertIn("没有粘贴上游源码", text)


class TestOrchestraDescriptor(unittest.TestCase):
    def setUp(self):
        self.text = read("orchestra.yaml")

    def test_top_level_keys(self):
        for key in TOP_LEVEL_KEYS:
            self.assertIn("\n" + key, "\n" + self.text)

    def test_phases_and_roles(self):
        for phase in PHASES:
            self.assertIn("id: %s" % phase, self.text)
        self.assertEqual(self.text.count("role: readonly"), 3)
        self.assertEqual(self.text.count("role: writer"), 1)
        self.assertIn("gate: confirm-write", self.text)
        self.assertIn("keep: \"highest-severity\"", self.text)
        self.assertIn("dedupe_key: \"id\"", self.text)
        for level in SEVERITY:
            self.assertIn("- %s" % level, self.text)

    def test_placeholders_and_output_root(self):
        for token in ("{orchestra-name}", "{target}", "{run-id}", "{expert-a}", "{writer-id}"):
            self.assertIn(token, self.text)
        self.assertIn(
            ".livepowers/orchestras/{orchestra-name}/runs/{run-id}",
            self.text,
        )


class TestAgentBoundaries(unittest.TestCase):
    def test_readonly_tools(self):
        specialist = read("agents/specialist.md")
        orchestrator = read("orchestrator.md")
        self.assertIn("tools: Read, Grep, Glob", specialist)
        self.assertIn("tools: Read, Grep, Glob", orchestrator)
        self.assertNotIn("Write", specialist.split("---", 2)[1])
        self.assertNotIn("Edit", specialist.split("---", 2)[1])

    def test_writer_is_gated(self):
        writer = read("agents/writer.md")
        self.assertIn("tools: Read, Edit, Write", writer)
        self.assertIn("confirm-write", writer)
        self.assertIn("{write-root}", writer)

    def test_envelope_fields(self):
        text = read("envelope.md")
        for field in (
            "orchestra:",
            "run_dir:",
            "target:",
            "context_file:",
            "modules:",
            "prior_findings:",
            "return:",
        ):
            self.assertIn(field, text)


class TestSchemas(unittest.TestCase):
    def test_finding_schema(self):
        data = json.loads(read("schema/finding.schema.json"))
        self.assertEqual(data["required"], FINDING_REQUIRED)
        self.assertEqual(data["properties"]["severity"]["enum"], SEVERITY)
        self.assertFalse(data["additionalProperties"])

    def test_report_schema(self):
        data = json.loads(read("schema/report.schema.json"))
        self.assertEqual(data["required"], REPORT_REQUIRED)
        item = data["properties"]["findings"]["items"]
        self.assertEqual(item["required"], FINDING_REQUIRED)
        self.assertEqual(item["properties"]["severity"]["enum"], SEVERITY)


if __name__ == "__main__":
    unittest.main()
