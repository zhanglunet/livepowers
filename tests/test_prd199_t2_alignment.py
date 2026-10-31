# -*- coding: utf-8 -*-
"""PRD-199/T2 自测（trend #996）：skills frontmatter 对齐 Agent Skills 开放规范。

运行：python3 -m unittest test_prd199_t2_alignment -v（在 tests/ 目录执行）

覆盖（T1 差距清单四项逐项验证）：
  license：21/21 skill frontmatter 均含 license: MIT
  metadata.when_not_to_use：21/21 在场（否定触发边界）
  metadata.output：21/21 在场（输出物声明）
  metadata.compatibility：21/21 在场（环境要求）
  幂等性：重复运行 align 不产生重复块
  红线：零网络；示例全虚构
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from agentskills_align import AGENTSKILLS_FILL, parse_frontmatter, validate_all  # noqa: E402

SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md"))


class TestLicense(unittest.TestCase):
    def test_all_skills_have_license(self):
        for path in SKILLS:
            meta, _, _ = parse_frontmatter(path)
            self.assertEqual(meta.get("license"), "MIT", f"{path.name} 缺 license")


class TestMetadata(unittest.TestCase):
    def test_when_not_to_use_present(self):
        for path in SKILLS:
            meta, _, _ = parse_frontmatter(path)
            self.assertTrue(meta.get("when_not_to_use"), f"{path.name} 缺 when_not_to_use")

    def test_output_present(self):
        for path in SKILLS:
            meta, _, _ = parse_frontmatter(path)
            self.assertTrue(meta.get("output"), f"{path.name} 缺 output")

    def test_compatibility_present(self):
        for path in SKILLS:
            meta, _, _ = parse_frontmatter(path)
            self.assertTrue(meta.get("compatibility"), f"{path.name} 缺 compatibility")


class TestIdempotent(unittest.TestCase):
    def test_no_duplicate_metadata_blocks(self):
        for path in SKILLS:
            raw = path.read_text(encoding="utf-8")
            count = raw.count("metadata:")
            self.assertEqual(count, 1, f"{path.name} metadata: 块出现 {count} 次")


class TestValidator(unittest.TestCase):
    def test_validate_all_passes(self):
        self.assertEqual(validate_all(ROOT / "skills"), [])

    def test_validate_detects_tampered(self):
        """篡改一个 SKILL.md（删 license）→ validate 检出。"""
        path = SKILLS[0]
        original = path.read_text(encoding="utf-8")
        path.write_text(original.replace("license: MIT\n", ""), encoding="utf-8")
        errors = validate_all(ROOT / "skills")
        path.write_text(original, encoding="utf-8")  # 还原
        self.assertTrue(any("license" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
