"""PRD-147/T5 验收断言（trend #739）。

三条验收标准的机检化：
  1. checklist 入库：docs/engineering-checklist/checklist.md（v0.1）在位，
     条目编号/类别/级别与 scripts/eng_checklist.py 的 ITEMS 登记表逐条一致；
  2. 发布文档引用门禁：根 README 有「发布门禁」节并链接本目录文档；
  3. 无密钥入报告：用 eng_checklist 的同源模式（凭据 + 私有网段 IP）扫描
     engineering-checklist 全部文档（含金样例报告）与根 README，断言 0 命中；
     另带阳性对照（构造泄漏必须被命中，防止断言空转）。
"""
import importlib.util
import os
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

SCRIPT = REPO / "scripts" / "eng_checklist.py"
_spec = importlib.util.spec_from_file_location("eng_checklist", SCRIPT)
ec = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ec)

CHECKLIST = REPO / "docs" / "engineering-checklist" / "checklist.md"
DIR_README = REPO / "docs" / "engineering-checklist" / "README.md"
ROOT_README = REPO / "README.md"

# 条目表行：| E-X01 | 类别 | 级别 | ...（类别/级别列与 ITEMS 登记表同口径）
ROW = re.compile(r"^\|\s*(E-[A-Z]\d{2})\s*\|\s*(\S+)\s*\|\s*(阻断|常规)\s*\|", re.M)


def strip_comments(text):
    """豁免台账的 HTML 注释放构造样例演示格式，不参与扫描（与 load_exemptions 同口径）。"""
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def scan_text(text):
    """返回 (label, 片段) 命中清单；模式与 scripts/eng_checklist.py 同源。"""
    hits = []
    for label, rx in ec.CRED_PATTERNS + [("私有网段 IP", ec.PRIV_IP)]:
        for m in rx.finditer(text):
            hits.append((label, m.group(0)[:40]))
    return hits


class TestChecklistInRepo(unittest.TestCase):
    """验收标准 1：checklist 入库，且与机检脚本登记表一致。"""

    def test_file_exists_with_version(self):
        self.assertTrue(CHECKLIST.is_file(), "缺 %s" % CHECKLIST)
        text = CHECKLIST.read_text(encoding="utf-8")
        self.assertIn("checklist v0.1", text)
        self.assertIn("变更记录", text)

    def test_items_match_script_registry(self):
        text = CHECKLIST.read_text(encoding="utf-8")
        rows = ROW.findall(text)
        self.assertTrue(rows, "checklist.md 未解析到条目表行")
        ids = [r[0] for r in rows]
        self.assertEqual(len(ids), len(set(ids)), "条目编号重复：%s" % ids)
        self.assertEqual(set(ids), set(ec.ITEMS),
                         "条目集不一致：只在文档 %s / 只在脚本 %s"
                         % (sorted(set(ids) - set(ec.ITEMS)),
                            sorted(set(ec.ITEMS) - set(ids))))
        for item, cat, level in rows:
            self.assertEqual((cat, level), ec.ITEMS[item][:2],
                             "%s 的类别/级别与机检登记表不一致" % item)

    def test_blocking_regular_counts(self):
        text = CHECKLIST.read_text(encoding="utf-8")
        rows = ROW.findall(text)
        blocking = sum(1 for r in rows if r[2] == "阻断")
        regular = sum(1 for r in rows if r[2] == "常规")
        exp_blocking = sum(1 for v in ec.ITEMS.values() if v[1] == "阻断")
        exp_regular = sum(1 for v in ec.ITEMS.values() if v[1] == "常规")
        self.assertEqual(blocking, exp_blocking)
        self.assertEqual(regular, exp_regular)
        self.assertEqual(len(rows), len(ec.ITEMS))


class TestReleaseDocsReferenceGate(unittest.TestCase):
    """验收标准 2：发布文档（根 README）引用工程门禁。"""

    def gate_section(self):
        text = ROOT_README.read_text(encoding="utf-8")
        m = re.search(r"^## 发布门禁.*?(?=^## |\Z)", text, re.M | re.S)
        return m.group(0) if m else ""

    def test_readme_has_gate_section(self):
        sec = self.gate_section()
        self.assertTrue(sec, "根 README 缺「发布门禁」节")

    def test_gate_section_links_existing_docs(self):
        sec = self.gate_section()
        links = {h.split("#", 1)[0] for h in re.findall(r"\]\(([^)]+)\)", sec)
                 if not h.startswith(("http://", "https://", "#", "mailto:"))}
        self.assertTrue(links, "发布门禁节没有任何仓内链接")
        for link in sorted(links):
            target = (REPO / link).resolve()
            self.assertTrue(target.exists(), "链接目标不存在：%s" % link)
        self.assertTrue(any("engineering-checklist" in l for l in links),
                        "发布门禁节未链接 docs/engineering-checklist/")

    def test_gate_section_states_criteria_and_sibling_gate(self):
        sec = self.gate_section()
        self.assertIn("阻断级", sec)
        self.assertIn("90%", sec)          # 过门口径：常规级达标率 ≥90%
        self.assertIn("slim_gate", sec)    # 与瘦身门（PRD-148）串联
        self.assertIn("豁免", sec)

    def test_dir_readme_updated_for_t5(self):
        text = DIR_README.read_text(encoding="utf-8")
        self.assertIn("checklist.md", text, "组成表应列出 checklist.md（T5 入库）")
        self.assertNotIn("是 T5 的事", text, "T5 收口后应移除『待 T5』的旧注记")
        self.assertTrue((REPO / "docs" / "engineering-checklist"
                         / "acceptance-t5-2026-10-23.md").is_file(),
                        "缺 T5 验收记录文档")


class TestNoSecretsInReportsAndDocs(unittest.TestCase):
    """验收标准 3：金样例报告与门禁文档无密钥/私有网段 IP（占位符除外）。"""

    def scanned_files(self):
        files = sorted((REPO / "docs" / "engineering-checklist").rglob("*.md"))
        files.append(ROOT_README)
        return files

    def test_no_credential_or_private_ip_hits(self):
        for f in self.scanned_files():
            text = strip_comments(f.read_text(encoding="utf-8"))
            hits = scan_text(text)
            self.assertEqual(hits, [],
                             "%s 命中密钥/私有网段模式：%s" % (f.relative_to(REPO), hits))

    def test_patterns_actually_fire_positive_control(self):
        # 阳性对照（拼接构造，避免测试源码本身命中模式）：模式必须能抓到泄漏，
        # 否则上面的 0 命中断言是空转。
        leak = "api" + "_key = '" + "abcdef0123456789" + "'\n" \
               "db at 192." + "168.1.10\n"
        hits = scan_text(leak)
        labels = {label for label, _ in hits}
        self.assertIn("字面密钥赋值", labels)
        self.assertIn("私有网段 IP", labels)

    def test_placeholder_convention_documented(self):
        text = CHECKLIST.read_text(encoding="utf-8")
        self.assertIn("<HOST>", text)
        self.assertIn("<TOKEN>", text)


if __name__ == "__main__":
    unittest.main()
