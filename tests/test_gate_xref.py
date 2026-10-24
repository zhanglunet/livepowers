"""PRD-148/T4：门禁文档交叉引用网（选题→瘦身→工程门禁→收录）断言。

三份文档各含"相关门禁"小节并互指（谁在哪个阶段拦什么）：
  docs/slim-gate/README.md（瘦身门，PRD-148）
  docs/engineering-checklist/README.md（工程门禁，PRD-147）
  docs/PRD-094-store-checklist.md（收录，PRD-094）
断言：① 小节在位；② 小节内仓内相对链接目标存在；③ 三份互指另外两份；
④ PRD-078 选题审计成果（在 trend 仓库，livepowers 零改动）以外部 URL 引用。
外部 URL 只做字符串断言，不访问网络。
"""
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DOCS = [
    "docs/slim-gate/README.md",
    "docs/engineering-checklist/README.md",
    "docs/PRD-094-store-checklist.md",
]

PEERS = {
    "docs/slim-gate/README.md": [
        "docs/engineering-checklist/README.md",
        "docs/PRD-094-store-checklist.md",
    ],
    "docs/engineering-checklist/README.md": [
        "docs/slim-gate/README.md",
        "docs/PRD-094-store-checklist.md",
    ],
    "docs/PRD-094-store-checklist.md": [
        "docs/slim-gate/README.md",
        "docs/engineering-checklist/README.md",
    ],
}

PRD078_URL = ("https://github.com/zhanglunet/trend/blob/main/adopted/"
              "PRD-078-final-report.md")


def read(path):
    with open(os.path.join(REPO, path), encoding="utf-8") as f:
        return f.read()


def gate_section(text):
    m = re.search(r"^## 相关门禁.*?(?=^## |\Z)", text, re.M | re.S)
    return m.group(0) if m else ""


def repo_links(section_text, doc_path):
    """小节内的仓内相对链接（忽略 http(s)/锚点/mailto），归一为仓库相对路径。"""
    base = os.path.dirname(doc_path)
    out = set()
    for href in re.findall(r"\]\(([^)]+)\)", section_text):
        if href.startswith(("http://", "https://", "#", "mailto:")):
            continue
        target = href.split("#", 1)[0]
        if not target:
            continue
        out.add(os.path.normpath(os.path.join(base, target)))
    return out


class TestGateCrossRefs(unittest.TestCase):

    def test_sections_present(self):
        for doc in DOCS:
            with self.subTest(doc=doc):
                self.assertTrue(gate_section(read(doc)),
                                "缺『相关门禁』小节：%s" % doc)

    def test_in_repo_link_targets_exist(self):
        for doc in DOCS:
            links = repo_links(gate_section(read(doc)), doc)
            self.assertTrue(links, "%s 的相关门禁小节没有任何仓内链接" % doc)
            for link in sorted(links):
                with self.subTest(doc=doc, link=link):
                    self.assertTrue(
                        os.path.exists(os.path.join(REPO, link)),
                        "%s 链接目标不存在：%s" % (doc, link))

    def test_gate_docs_peer_linked(self):
        for doc, peers in PEERS.items():
            links = repo_links(gate_section(read(doc)), doc)
            for peer in peers:
                with self.subTest(doc=doc, peer=peer):
                    self.assertIn(peer, links, "%s 未互指 %s" % (doc, peer))

    def test_prd078_referenced_as_trend_url(self):
        # PRD-078 只审计不动代码：成果（审计卡/总报告/待办清单）在 trend 仓库，
        # livepowers 侧以链接引用，不复制文档。
        for doc in DOCS:
            with self.subTest(doc=doc):
                self.assertIn(PRD078_URL, gate_section(read(doc)),
                              "%s 应以 trend 仓库 URL 引用 PRD-078 成果" % doc)


if __name__ == "__main__":
    unittest.main()
