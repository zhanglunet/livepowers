#!/usr/bin/env python3
"""PRD-172/T3：私有市场文档与包内发行物机检（「文档可照做」的兜底）。

被测对象（trend issue #862）：
1. 包内发行物：每包自带 LICENSE（MIT，与仓库根 LICENSE 逐字节一致）、
   README 许可行指向本包 LICENSE——整包 vendored / 单包拷贝都自包含；
2. role-packs/README.md：目录约定与验收状态推进流程在位（包状态机
   planned/draft/published、验收状态 pending/confirmed/exempt/blocked、
   manifest 单一真值源、safety 用例不可豁免），相对链接目标真实存在；
3. docs/role-packs-private-marketplace.md：两条路径、企业市场模板、
   C-03 约束（source 相对路径、不含 `..`）、零 MCP 依赖红线在位，
   示例一律占位符；
4. 泄密兜底：两份文档无 IPv4 字面量、无明文密钥形态字符串
   （仓库级扫描另有 tests/test_repo.py denylist，此处只做文档级快查）。

夹具不涉及真实主机名 / 账号 / 密钥。Python 3.9 兼容。
"""
import os
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROLE_PACKS = REPO / "role-packs"
PACK_IDS = ["livepowers-role-sales", "livepowers-role-finance", "livepowers-role-hr"]
GUIDE = REPO / "docs" / "role-packs-private-marketplace.md"
RP_README = ROLE_PACKS / "README.md"

PACK_STATUS = ("planned", "draft", "published")
ACCEPTANCE_STATES = ("pending", "confirmed", "exempt", "blocked")

IPV4_RE = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
SECRET_RE = re.compile(r"(ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|"
                       r"\b(token|password|secret)\s*[=:]\s*['\"]?[A-Za-z0-9/+-]{16,})",
                       re.IGNORECASE)


def read(path):
    return path.read_text(encoding="utf-8")


def md_rel_links(text):
    """Markdown 相对链接目标（忽略 http(s)/锚点/mailto），归一为仓库相对路径。"""
    out = set()
    for href in re.findall(r"\]\(([^)]+)\)", text):
        if href.startswith(("http://", "https://", "#", "mailto:")):
            continue
        target = href.split("#", 1)[0]
        if target:
            out.add(target)
    return out


class TestPackLicense(unittest.TestCase):
    """包内 LICENSE：整包 / 单包分发都自包含。"""

    def test_pack_license_matches_root(self):
        root = (REPO / "LICENSE").read_bytes()
        self.assertTrue(root.startswith(b"MIT License"), "仓库根 LICENSE 应为 MIT")
        for pack in PACK_IDS:
            lic = ROLE_PACKS / pack / "LICENSE"
            with self.subTest(pack=pack):
                self.assertTrue(lic.is_file(), "缺包内 LICENSE：%s" % lic)
                self.assertEqual(lic.read_bytes(), root,
                                 "包内 LICENSE 应与仓库根 LICENSE 逐字节一致")

    def test_pack_readme_license_line(self):
        for pack in PACK_IDS:
            text = read(ROLE_PACKS / pack / "README.md")
            with self.subTest(pack=pack):
                self.assertIn("MIT", text)
                self.assertIn("`LICENSE`", text, "README 许可行应指向本包 LICENSE")
                self.assertNotIn("见仓库根 LICENSE", text,
                                 "许可行不得只指仓库根（包要自包含）")


class TestRolePacksReadme(unittest.TestCase):
    """目录约定与验收状态推进流程文档在位、链接可达。"""

    def test_readme_exists_with_conventions(self):
        text = read(RP_README)
        self.assertIn("manifest.json", text, "应声明 manifest 单一真值源")
        self.assertIn("单一真值源", text)
        for s in PACK_STATUS:
            self.assertIn("`%s`" % s, text, "包状态机缺 %s" % s)
        for s in ACCEPTANCE_STATES:
            self.assertIn("`%s`" % s, text, "验收状态缺 %s" % s)
        self.assertIn("safety 用例", text, "应写明 safety 用例不可豁免")
        self.assertIn("不可豁免", text)
        self.assertIn("EX-", text, "exempt 应指向工程门豁免台账 EX- ID")
        self.assertIn("published", text)
        self.assertIn("不得标 published", text, "应写明存在 pending/blocked 不得标 published")
        self.assertIn("LICENSE", text, "目录约定应含包内 LICENSE")

    def test_readme_links_resolve(self):
        text = read(RP_README)
        self.assertTrue(md_rel_links(text), "README 应有相对链接（私有市场手册等）")
        for target in md_rel_links(text):
            path = (REPO / target) if not target.startswith("..") else (RP_README.parent / target)
            self.assertTrue(path.exists(), "链接目标不存在：%s" % target)

    def test_guide_linked_from_readme(self):
        self.assertIn("docs/role-packs-private-marketplace.md", read(RP_README))


class TestPrivateMarketplaceGuide(unittest.TestCase):
    """私有市场手册：两条路径 + 模板 + 约束 + 红线，可照做。"""

    def test_two_paths_present(self):
        text = read(GUIDE)
        self.assertIn("路径一", text)
        self.assertIn("路径二", text)
        self.assertIn("整仓 fork / vendored", text)
        self.assertIn("单包技能分发", text)
        self.assertIn("/plugin marketplace add", text, "应有市场添加命令")
        self.assertIn("/plugin install", text, "应有安装命令")

    def test_enterprise_template_and_constraints(self):
        text = read(GUIDE)
        self.assertIn('"name": "<企业市场名>"', text, "企业市场模板应用占位符")
        self.assertIn("marketplace.json", text)
        self.assertIn("C-03", text, "应引用收录门 C-03 口径")
        self.assertIn("不含 `..`", text, "应写明 source 不含 ..")
        self.assertIn("相对路径", text)
        self.assertIn("零 MCP 依赖", text)
        self.assertIn(".mcp.json", text, "应写明不引入 .mcp.json 类配置")

    def test_placeholders_and_verification_checklist(self):
        text = read(GUIDE)
        for ph in ("<企业内部仓库地址>", "<企业市场名>", "<企业/团队名>"):
            self.assertIn(ph, text, "缺占位符 %s" % ph)
        self.assertIn("验证清单", text)
        self.assertGreaterEqual(text.count("- [ ]"), 3, "验证清单条目过少")

    def test_no_leakage(self):
        for path in (GUIDE, RP_README):
            text = read(path)
            with self.subTest(doc=path.name):
                self.assertIsNone(IPV4_RE.search(text), "不应出现 IPv4 字面量")
                self.assertIsNone(SECRET_RE.search(text), "不应出现密钥形态字符串")


if __name__ == "__main__":
    unittest.main()
