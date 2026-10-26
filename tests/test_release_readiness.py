"""PRD-172/T4：发行前强制对抗验收测试（trend #863）。"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

from check_release_readiness import check_pack, main  # noqa: E402


def _pack(status="published", state="confirmed", exempt_ref=None):
    skill = {"name": "s1", "acceptance": {"state": state, "evidence": "tests/adversarial/s1/findings.json"}}
    if exempt_ref:
        skill["acceptance"]["exempt_ref"] = exempt_ref
    return {"name": "pack-x", "status": status, "skills": [skill]}


class TestReleaseReadiness(unittest.TestCase):
    def test_published_confirmed_passes(self):
        self.assertEqual(check_pack(_pack()), [])

    def test_published_needs_validation_with_valid_exempt_passes(self):
        # 豁免台账存在 EX-01 时放行
        import check_release_readiness as m
        old = m.ENGINEERING_EXEMPTIONS
        try:
            m.ENGINEERING_EXEMPTIONS = "/nonexistent"
            # 无台账时 needs_validation 必须带 exempt_ref——台账读取为空集则拒绝
            r = m.check_pack(_pack(state="needs_validation", exempt_ref="EX-01"), set())
            self.assertEqual(len(r), 1)
            self.assertIn("未在豁免台账", r[0])
        finally:
            m.ENGINEERING_EXEMPTIONS = old

    def test_published_rejected_fails_hard(self):
        r = check_pack(_pack(state="rejected"), {"EX-01"})
        self.assertEqual(len(r), 1)
        self.assertIn("非 confirmed 不可 published", r[0])

    def test_published_pending_fails(self):
        r = check_pack(_pack(state="pending"), set())
        self.assertEqual(len(r), 1)

    def test_draft_pack_not_enforced(self):
        self.assertEqual(check_pack(_pack(status="draft", state="pending")), [])

    def test_safety_rejected_never_exempt(self):
        """safety 条目豁免通道在脚本层就不存在：rejected 无 exempt 可走。"""
        r = check_pack(_pack(state="rejected", exempt_ref="EX-01"), {"EX-01"})
        self.assertEqual(len(r), 1)  # rejected 即使带 exempt_ref 也拒

    def test_main_exit_code_on_real_repo(self):
        """真实仓库：当前 manifest 无 published 包 → 退出码 0。"""
        rc = main([os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "role-packs", "manifest.json")])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
