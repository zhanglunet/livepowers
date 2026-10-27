#!/usr/bin/env python3
"""PRD-172/T5 验收（trend #864）：三包安装演示 / 清单与验收状态一致 / 无密钥与术语统一。

被测对象：role-packs/ 发行面（销售/财务/人力三包 + manifest.json +
docs/role-packs-private-marketplace.md）。三条验收标准的机检：

1. **三包安装演示（栏目可浏览）**：市场形态（marketplace.json 条目 source 可解析、
   plugin.json 自包含、README/LICENSE 齐全）、仅技能形态（每包 skills/ 全带
   SKILL.md）、私有市场照做演示（按 T3 手册模板在临时目录搭企业最小仓库并装包，
   手册可照做）；
2. **清单与验收状态一致**：manifest 每个 skill 条目的 acceptance.state 与
   tests/adversarial/ 现实双向一致（pending ⇔ 无 findings.json；非 pending 必须
   有可过机检的 findings 支撑，不得虚报 confirmed/exempt）；published 硬门禁
   （T4 check_release_readiness）真实仓库 exit 0 + 负向对照（pending 成员被拦）；
3. **无密钥 / 内网信息 + 术语统一**：发行面全量扫描（密钥形态 / 非回环 IPv4 /
   .mcp.json / CONNECTORS，带阳性对照；127.0.0.1 为 agent_switch 本地回环默认
   端口，显式放行）；对照 PRD-102 双语口径走查术语（角色包/发行清单/市场清单/
   对抗验收统一，双语描述成对，技能名反引号可解析）。

夹具一律占位符（<企业内部仓库地址> 等），不含真实主机名 / 账号 / 密钥。
Python 3.9 兼容。
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import adversarial_verify as av  # noqa: E402
import check_release_readiness as crr  # noqa: E402

ROLE_PACKS = REPO / "role-packs"
MANIFEST = ROLE_PACKS / "manifest.json"
MARKETPLACE = REPO / ".claude-plugin" / "marketplace.json"
GUIDE = REPO / "docs" / "role-packs-private-marketplace.md"
READINESS = REPO / "scripts" / "check_release_readiness.py"

PACK_IDS = ["livepowers-role-sales", "livepowers-role-finance", "livepowers-role-hr"]
ENTRY = "using-livepowers"

# 术语表（对照 PRD-102 双语验收口径的统一约定）：发行单元叫「角色包」，
# manifest.json 叫「发行清单」，根 .claude-plugin/marketplace.json 叫「市场清单」，
# PRD-171 的动态证伪程序叫「对抗验收」。
GLOSSARY_PRESENT = ("角色包", "发行清单", "私有市场", "对抗验收")
GLOSSARY_FORBIDDEN = ("角色插件包", "岗位包", "职业包", "知识包", "skill 包体")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
ROLE_PACK_EN_RE = re.compile(r"[Rr]ole pack")
TOKEN_RE = re.compile(r"`([a-z][a-z0-9]*(?:-[a-z0-9]+)+)`")
FRONTMATTER_NAME = re.compile(r"^name:\s*(\S+)\s*$", re.M)

# 密钥 / 内网信息扫描口径：回环地址 127.0.0.1 是 agent_switch 的本地默认
# （scripts/agent_switch.py --host 127.0.0.1），显式放行；其余 IPv4 一律算命中。
SECRET_PATTERNS = (
    ("aws_key", r"AKIA[0-9A-Z]{16}"),
    ("github_token", r"gh[pousr]_[A-Za-z0-9]{20,}"),
    ("api_key", r"sk-[A-Za-z0-9]{16,}"),
    ("bearer", r"Authorization:\s*Bearer\s+[A-Za-z0-9._-]{8,}"),
    ("password", r"(?i)(password|passwd)\s*[:=]\s*\S+"),
    ("token_assign", r"(?i)(token|secret)\s*[:=]\s*['\"]?[A-Za-z0-9/+]{16,}"),
    ("private_key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("ssh_target", r"\b(?:ssh|scp)\s+\S+@"),
)
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
LOOPBACK = "127.0.0.1"


def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def distribution_files():
    """发行面全量：role-packs/ 下所有文件 + 私有市场手册。"""
    out = sorted(p for p in ROLE_PACKS.rglob("*") if p.is_file())
    out.append(GUIDE)
    return out


def scan_secrets(text):
    hits = []
    for name, pat in SECRET_PATTERNS:
        for m in re.finditer(pat, text):
            line = text.count("\n", 0, m.start()) + 1
            hits.append((name, line, m.group(0)[:24]))
    for m in IPV4_RE.finditer(text):
        if m.group(0) != LOOPBACK:
            line = text.count("\n", 0, m.start()) + 1
            hits.append(("ipv4_non_loopback", line, m.group(0)))
    return hits


class TestInstallDemo(unittest.TestCase):
    """验收标准「三包安装演示」：市场形态 / 仅技能形态 / 私有市场照做。"""

    def setUp(self):
        self.manifest = load_json(MANIFEST)
        self.market = load_json(MARKETPLACE)
        self.entries = {e["name"]: e for e in self.market["plugins"]}

    def test_marketplace_form_browsable_and_installable(self):
        """市场形态：条目可浏览（栏目在列）且 source 可解析到自包含包。"""
        listed = [e["name"] for e in self.market["plugins"]
                  if e.get("source", "").startswith("./role-packs/")]
        self.assertEqual(sorted(listed), sorted(PACK_IDS),
                         "市场栏目应恰好列出三个角色包")
        for pack in self.manifest["packs"]:
            pid = pack["pack_id"]
            with self.subTest(pack=pid):
                self.assertTrue(pack.get("marketplace_entry"))
                entry = self.entries[pid]
                source = entry["source"]
                self.assertTrue(source.startswith("./role-packs/"))
                self.assertNotIn("..", source, "C-03：source 不得含 ..")
                pdir = REPO / source
                self.assertTrue(pdir.is_dir(), "source 指向的包目录不存在")
                meta = load_json(pdir / ".claude-plugin" / "plugin.json")
                self.assertEqual(meta["name"], pid)
                self.assertEqual(meta["version"], pack["version"])
                self.assertEqual(entry["version"], pack["version"])
                self.assertEqual(meta["license"], "MIT")
                self.assertTrue((pdir / "README.md").is_file())
                self.assertTrue((pdir / "LICENSE").is_file())

    def test_skills_only_form_installable(self):
        """仅技能形态：每包 skills/ 全带 SKILL.md，frontmatter name 与目录一致。"""
        for pack in self.manifest["packs"]:
            pdir = ROLE_PACKS / pack["pack_id"]
            for sdir in sorted((pdir / "skills").iterdir()):
                if not sdir.is_dir():
                    continue
                with self.subTest(pack=pack["pack_id"], skill=sdir.name):
                    smd = sdir / "SKILL.md"
                    self.assertTrue(smd.is_file(), "缺 SKILL.md：%s" % smd)
                    m = FRONTMATTER_NAME.search(smd.read_text(encoding="utf-8"))
                    self.assertIsNotNone(m, "SKILL.md 缺 frontmatter name")
                    self.assertEqual(m.group(1), sdir.name)

    def test_private_marketplace_manual_replay(self):
        """照做 T3 手册：按模板在临时目录搭企业最小仓库并「安装」一个角色包。"""
        doc = GUIDE.read_text(encoding="utf-8")
        blocks = re.findall(r"```json\n(.*?)```", doc, re.S)
        self.assertEqual(len(blocks), 1, "手册应嵌一份企业市场清单模板")
        template = json.loads(blocks[0])  # 占位符值也是合法 JSON 字符串
        with tempfile.TemporaryDirectory() as tmp:
            ent = Path(tmp)
            (ent / ".claude-plugin").mkdir()
            # 手册第 1–2 步：拷包 + 只保留所需角色包条目，name 换企业市场名
            shutil.copytree(ROLE_PACKS / "livepowers-role-sales",
                            ent / "role-packs" / "livepowers-role-sales")
            template["name"] = "<企业市场名>"
            template["plugins"] = [p for p in template["plugins"]
                                   if p["name"] == "livepowers-role-sales"]
            (ent / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
            # 手册「安装后验证清单」的静态等价：清单合法、source 解析、包自包含
            market = load_json(ent / ".claude-plugin" / "marketplace.json")
            for e in market["plugins"]:
                target = ent / e["source"]
                self.assertTrue(target.is_dir(), "装不上：source 目录不存在")
                meta = load_json(target / ".claude-plugin" / "plugin.json")
                self.assertEqual(meta["name"], e["name"])
                self.assertEqual(e["license"], "MIT")
                self.assertTrue((target / "skills" / ENTRY / "SKILL.md").is_file())
                self.assertFalse(list(target.rglob(".mcp.json")),
                                 "角色包零 MCP 依赖")
            self.assertEqual(market["name"], "<企业市场名>")
            self.assertNotIn("..", market["plugins"][0]["source"])


class TestManifestAcceptanceConsistency(unittest.TestCase):
    """验收标准「清单与验收状态一致」：manifest 双向对照现实，不虚报、不漏记。"""

    def setUp(self):
        self.manifest = load_json(MANIFEST)
        self.ledger = av.load_exempt_ledger(
            str(REPO / "docs" / "engineering-checklist" / "exemptions.md"))

    def _findings_path(self, skill):
        return REPO / "tests" / "adversarial" / skill / "findings.json"

    def test_evidence_path_format(self):
        for pack in self.manifest["packs"]:
            for s in pack["skills"]:
                with self.subTest(pack=pack["pack_id"], skill=s["name"]):
                    self.assertEqual(
                        s["acceptance"]["evidence"],
                        "tests/adversarial/%s/findings.json" % s["name"])

    def test_pending_means_no_findings(self):
        """state=pending ⇔ findings.json 不存在（未跑验收就如实记 pending）。"""
        for pack in self.manifest["packs"]:
            for s in pack["skills"]:
                exists = self._findings_path(s["name"]).is_file()
                with self.subTest(pack=pack["pack_id"], skill=s["name"]):
                    if s["acceptance"]["state"] == "pending":
                        self.assertFalse(exists,
                                         "%s 已有 findings.json，清单仍记 pending"
                                         % s["name"])
                    else:
                        self.assertTrue(exists,
                                        "%s 记 %s 但无 findings.json 支撑"
                                        % (s["name"], s["acceptance"]["state"]))

    def test_non_pending_backed_by_valid_findings(self):
        """非 pending 必须有可过机检的 findings 支撑：confirmed=过门；
        exempt=台账登记且对象为本 skill；blocked=存在 rejected。"""
        for pack in self.manifest["packs"]:
            for s in pack["skills"]:
                state = s["acceptance"]["state"]
                if state == "pending":
                    continue
                path = self._findings_path(s["name"])
                with self.subTest(pack=pack["pack_id"], skill=s["name"]):
                    cases, _, errs = av.load_cases(str(REPO), s["name"])
                    self.assertEqual(errs, [])
                    by_id = {c["case_id"]: c for c in cases}
                    rec_errs = av.check_records(str(REPO), s["name"], by_id, self.ledger)
                    self.assertEqual(rec_errs, [])
                    if state == "confirmed":
                        ok = av.gate_skill(str(REPO), s["name"], by_id, self.ledger)[0]
                        self.assertTrue(ok, "%s 记 confirmed 但门禁未过" % s["name"])
                    elif state == "exempt":
                        ref = s["acceptance"].get("exempt_ref")
                        self.assertTrue(ref and ref in self.ledger)
                        self.assertEqual(self.ledger[ref], "skill:" + s["name"])
                    else:  # blocked
                        data = load_json(path)
                        self.assertTrue(any(r["verdict"] == "rejected"
                                            for r in data["records"]))

    def test_release_readiness_green_on_real_repo(self):
        """T4 硬门禁真实仓库冒烟：三包均 draft、状态 pending → exit 0。"""
        p = subprocess.run([sys.executable, str(READINESS)],
                           capture_output=True, text=True, cwd=str(REPO))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("发行就绪检查", p.stdout)
        for pack in self.manifest["packs"]:
            self.assertEqual(pack["status"], "draft")
            self.assertEqual({s["acceptance"]["state"] for s in pack["skills"]},
                             {"pending"})

    def test_published_gate_blocks_pending_member(self):
        """负向对照（故意失败被拦）：published 包带 pending 成员 → 违规。"""
        pack = {"pack_id": "livepowers-role-demo",
                "status": "published",
                "skills": [{"name": "system1-first",
                            "acceptance": {"state": "pending",
                                           "evidence": "tests/adversarial/system1-first/findings.json"}}]}
        r = crr.check_pack(pack, set())
        self.assertEqual(len(r), 1)
        self.assertIn("非 confirmed 不可 published", r[0])


class TestT4ReadinessFixes(unittest.TestCase):
    """T4 脚本两处口径修正的回归（本 PR 修复，见 PR 说明）：

    1. 违规标签用 manifest 实际字段 pack_id（原取 name，真实清单上显示 "?"）；
    2. 清单 schema 的 exempt 状态（带有效 exempt_ref）应放行——与
       「state ≠ confirmed 且无有效豁免不得 published」的硬门禁口径一致。
    """

    def _pack(self, state, ref=None):
        acc = {"state": state, "evidence": "tests/adversarial/s1/findings.json"}
        if ref:
            acc["exempt_ref"] = ref
        return {"pack_id": "livepowers-role-demo", "status": "published",
                "skills": [{"name": "s1", "acceptance": acc}]}

    def test_violation_label_uses_pack_id(self):
        r = crr.check_pack(self._pack("pending"), set())
        self.assertEqual(len(r), 1)
        self.assertTrue(r[0].startswith("livepowers-role-demo/"),
                        "违规标签应取 pack_id：%s" % r[0])

    def test_exempt_with_valid_ref_passes(self):
        self.assertEqual(crr.check_pack(self._pack("exempt", "EX-20261027-01"),
                                        {"EX-20261027-01"}), [])

    def test_exempt_without_ref_fails(self):
        r = crr.check_pack(self._pack("exempt"), set())
        self.assertEqual(len(r), 1)
        self.assertIn("exempt_ref", r[0])

    def test_exempt_unregistered_ref_fails(self):
        r = crr.check_pack(self._pack("exempt", "EX-20990101-99"), {"EX-20261027-01"})
        self.assertEqual(len(r), 1)
        self.assertIn("未在豁免台账登记", r[0])


class TestBilingualAndTerms(unittest.TestCase):
    """验收「术语统一」：对照 PRD-102 双语口径走查发行面与文档。"""

    def setUp(self):
        self.manifest = load_json(MANIFEST)
        self.market = load_json(MARKETPLACE)
        self.entries = {e["name"]: e for e in self.market["plugins"]}

    def test_pack_descriptions_bilingual(self):
        """包描述成对：中文句（含「角色包」）+ 英文技术句（含 role pack），
        对齐 PRD-102「slogan 式中文 + 英文技术描述」口径。"""
        for pack in self.manifest["packs"]:
            pid = pack["pack_id"]
            with self.subTest(pack=pid):
                desc = load_json(ROLE_PACKS / pid / ".claude-plugin" / "plugin.json")["description"]
                self.assertTrue(CJK_RE.search(desc) and "角色包" in desc,
                                "中文描述缺角色包称谓：%s" % desc)
                self.assertTrue(ROLE_PACK_EN_RE.search(desc), "缺英文技术描述：%s" % desc)
                entry = self.entries[pid]["description"]
                self.assertTrue(CJK_RE.search(entry) and "角色包" in entry)
                self.assertTrue(ROLE_PACK_EN_RE.search(entry))

    def test_glossary_consistent_across_surface(self):
        """术语表四词在位、混杂变体零命中（角色包/发行清单/私有市场/对抗验收）。"""
        texts = {p.name: p.read_text(encoding="utf-8")
                 for p in (ROLE_PACKS / "README.md", GUIDE)}
        for pack in PACK_IDS:
            texts[pack] = (ROLE_PACKS / pack / "README.md").read_text(encoding="utf-8")
        for name, text in texts.items():
            with self.subTest(doc=name):
                for term in GLOSSARY_FORBIDDEN:
                    self.assertNotIn(term, text, "混杂术语变体：%s" % term)
        for term in GLOSSARY_PRESENT:
            joined = "\n".join(texts.values())
            self.assertIn(term, joined, "术语表缺 %s" % term)

    def test_backticked_skill_names_resolve(self):
        """README 里反引号的连字符小写 token 必须是真实 skill 名（防笔误）。"""
        skills = {d.name for d in (REPO / "skills").iterdir() if d.is_dir()}
        skills |= set(PACK_IDS) | {"livepowers-marketplace"}
        bad = []
        for readme in [ROLE_PACKS / "README.md"] + \
                [ROLE_PACKS / p / "README.md" for p in PACK_IDS]:
            text = readme.read_text(encoding="utf-8")
            for tok in TOKEN_RE.findall(text):
                if tok not in skills:
                    bad.append("%s: %s" % (readme.name, tok))
        self.assertEqual(bad, [], "反引号技能名不可解析：%s" % bad)

    def test_pack_readme_title_matches_manifest(self):
        for pack in self.manifest["packs"]:
            text = (ROLE_PACKS / pack["pack_id"] / "README.md").read_text(encoding="utf-8")
            with self.subTest(pack=pack["pack_id"]):
                self.assertIn(pack["pack_id"], text.splitlines()[0])
                self.assertIn(pack["title"], text)


class TestNoSecretsDistribution(unittest.TestCase):
    """验收「无密钥 / 内网信息」：发行面全量扫描 0 命中，带阳性对照。"""

    def test_positive_control(self):
        planted = "AKIA" + "IOSFODNN7EXAMPLE"  # 拼接构造，避免本文件自身命中
        self.assertEqual([h[0] for h in scan_secrets(planted)], ["aws_key"])

    def test_distribution_surface_clean(self):
        for f in distribution_files():
            hits = scan_secrets(f.read_text(encoding="utf-8"))
            self.assertEqual(hits, [], "%s 含疑似密钥/内网信息：%s" % (f, hits))

    def test_loopback_only_ipv4(self):
        """发行面出现的 IPv4 只允许回环 127.0.0.1（agent_switch 本地默认）。"""
        ips = set()
        for f in distribution_files():
            ips |= set(IPV4_RE.findall(f.read_text(encoding="utf-8")))
        self.assertEqual(ips - {LOOPBACK}, set(), "出现非回环 IPv4：%s" % (ips - {LOOPBACK}))

    def test_no_mcp_or_connectors(self):
        for f in ROLE_PACKS.rglob("*"):
            if f.is_file():
                self.assertNotIn(f.name, (".mcp.json", "CONNECTORS.md"),
                                 "角色包不得携带 MCP/CONNECTORS 配置：%s" % f)
                if f.suffix == ".json":
                    self.assertNotIn("mcpServers", f.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
