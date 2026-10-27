"""PRD-171/T4：对抗验收 ↔ 工程/收录 checklist 映射机检（trend #858）。"""
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAPPING = os.path.join(REPO, "docs", "engineering-checklist", "adversarial-mapping.md")
ENG = os.path.join(REPO, "scripts", "eng_checklist.py")
ADV = os.path.join(REPO, "scripts", "adversarial_verify.py")
STORE = os.path.join(REPO, "docs", "PRD-094-store-checklist.md")


class TestAdversarialMapping(unittest.TestCase):
    def test_mapping_doc_exists_with_required_sections(self):
        text = open(MAPPING, encoding="utf-8").read()
        self.assertIn("字段映射（findings 条目", text)
        self.assertIn("verdict → 门禁级别映射", text)
        for verdict in ("confirmed", "needs_validation", "rejected"):
            self.assertIn(verdict, text)

    def test_referenced_ids_exist_both_sides(self):
        """映射引用的 E/C ID 必须在两侧真实存在。"""
        text = open(MAPPING, encoding="utf-8").read()
        eng_src = open(ENG, encoding="utf-8").read()
        store_doc = open(STORE, encoding="utf-8").read()
        for eid in re.findall(r"E-[A-Z]\d{2}", text):
            self.assertIn(eid, eng_src, f"{eid} 不在 eng_checklist.py")
        for cid in re.findall(r"C-\d{2}", text):
            self.assertIn(cid, store_doc, f"{cid} 不在 PRD-094 收录清单")

    def test_verdicts_match_verifier(self):
        """映射表的 verdict 词表与 adversarial_verify 逐字一致。"""
        text = open(MAPPING, encoding="utf-8").read()
        adv_src = open(ADV, encoding="utf-8").read()
        m = re.search(r'VERDICTS = \(([^)]+)\)', adv_src)
        self.assertIsNotNone(m)
        for v in re.findall(r'"(\w+)"', m.group(1)):
            self.assertIn(v, text, f"verdict {v} 未在映射表出现")


if __name__ == "__main__":
    unittest.main()
