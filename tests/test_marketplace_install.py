#!/usr/bin/env python3
"""PRD-003/T3：插件市场安装链路验证（静态安装模拟）。

真机 `/plugin install` 需要 Claude Code 客户端，本机没有；这里模拟
"用户装完某个插件后，对应 skill 能不能用"：逐个插件检查自包含性——

1. marketplace.json 合法，每个 plugins 条目的 source 目录真实存在，
   且 `./plugins/<name>/.claude-plugin/plugin.json` 的 name 与条目一致；
2. 插件 skills/ 下所有 md 文件里出现的 `${CLAUDE_PLUGIN_ROOT}/<路径>` 与
   `templates/<文件>` 引用，在插件目录内真实存在（装完不会 404）；
3. 有 hooks/ 的插件：hooks.json 合法，引用的 .sh 存在且可执行；
4. 有 commands/ 的插件：每个 .md 有 frontmatter 且 description 非空；
5. 5 个插件的 skill 集合恰好覆盖根 skills/ 的 21 个（不多、不少、不重复）；
6. 插件 scripts/*.py 对仓库内兄弟模块的 import（如 lp.py → lp_output）在插件
   scripts/ 内能找到，装完运行不会 ModuleNotFoundError；
7. 仓库文档与安装器里的 `/plugin install <名>@livepowers-marketplace` 只指向
   marketplace.json 中真实存在的插件；
8. marketplace.json 除 5 个主题插件外还登记角色包（source ./role-packs/<pack>，
   PRD-172）；skill 覆盖统计只统计 ./plugins/ 条目，角色包机检在
   tests/test_role_packs.py。

CI 每次 push/PR 自动跑（`python -m unittest discover -s tests`）。
Python 3.9 兼容。
"""
import json
import os
import re
import stat
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MARKETPLACE = REPO / ".claude-plugin" / "marketplace.json"
PLUGINS_DIR = REPO / "plugins"
ROOT_SKILLS = REPO / "skills"
EXPECTED_SKILL_COUNT = 21  # 2026-10-20 盘点数（新增 delivery-chain）；增减 skill 时同步改

PLUGIN_ROOT_REF = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)")
TEMPLATE_REF = re.compile(r"templates/([A-Za-z0-9_.-]+)")
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def load_marketplace():
    with open(MARKETPLACE, encoding="utf-8") as f:
        return json.load(f)


SOURCE_PREFIXES = ("./plugins/", "./role-packs/")


def marketplace_entries():
    return load_marketplace()["plugins"]


def plugin_names():
    """主题插件（./plugins/ 条目）；角色包条目由 tests/test_role_packs.py 管辖。"""
    return [p["name"] for p in marketplace_entries()
            if p.get("source", "").startswith("./plugins/")]


def md_files(plugin_dir):
    skills = plugin_dir / "skills"
    if not skills.is_dir():
        return []
    return sorted(skills.rglob("*.md"))


def parse_frontmatter(text):
    m = FRONTMATTER.match(text)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def hook_commands(obj):
    """递归收集 hooks.json 里所有含 CLAUDE_PLUGIN_ROOT 的命令字符串。"""
    found = []
    if isinstance(obj, dict):
        for v in obj.values():
            found.extend(hook_commands(v))
    elif isinstance(obj, list):
        for v in obj:
            found.extend(hook_commands(v))
    elif isinstance(obj, str) and "CLAUDE_PLUGIN_ROOT" in obj:
        found.append(obj)
    return found


class TestMarketplaceManifest(unittest.TestCase):
    def test_manifest_valid(self):
        m = load_marketplace()
        self.assertIn("plugins", m)
        self.assertIsInstance(m["plugins"], list)
        self.assertGreater(len(m["plugins"]), 0)

    def test_each_entry_resolves(self):
        for entry in marketplace_entries():
            name = entry["name"]
            with self.subTest(plugin=name):
                self.assertIn("source", entry)
                src = entry["source"]
                self.assertTrue(src.startswith(SOURCE_PREFIXES),
                                f"source 应为 {SOURCE_PREFIXES} 之一，实际 {src!r}")
                self.assertNotIn("..", src, f"source 不得含 ..：{src}")
                pdir = REPO / src[2:]
                self.assertTrue(pdir.is_dir(), f"source 目录不存在：{src}")
                pj = pdir / ".claude-plugin" / "plugin.json"
                self.assertTrue(pj.is_file(), f"缺 plugin.json：{pj}")
                with open(pj, encoding="utf-8") as f:
                    meta = json.load(f)
                self.assertEqual(meta.get("name"), name,
                                 f"plugin.json 的 name={meta.get('name')!r} 与条目 {name!r} 不一致")


class TestPluginSelfContained(unittest.TestCase):
    """skill 文档里写到的插件内路径，装完必须真实存在。"""

    def test_plugin_root_refs_exist(self):
        for name in plugin_names():
            pdir = PLUGINS_DIR / name
            with self.subTest(plugin=name):
                missing = []
                for md in md_files(pdir):
                    text = md.read_text(encoding="utf-8")
                    for ref in set(PLUGIN_ROOT_REF.findall(text)):
                        target = pdir / ref.rstrip("/")
                        if not target.exists():
                            missing.append(f"{md.name}: ${{CLAUDE_PLUGIN_ROOT}}/{ref}")
                self.assertEqual(missing, [], f"引用缺失：{missing}")

    def test_template_refs_exist(self):
        for name in plugin_names():
            pdir = PLUGINS_DIR / name
            with self.subTest(plugin=name):
                missing = []
                for md in md_files(pdir):
                    text = md.read_text(encoding="utf-8")
                    for ref in set(TEMPLATE_REF.findall(text)):
                        target = pdir / "templates" / ref
                        if not target.is_file():
                            missing.append(f"{md.name}: templates/{ref}")
                self.assertEqual(missing, [], f"模板缺失：{missing}")


class TestPluginHooks(unittest.TestCase):
    def test_hooks_json_and_scripts(self):
        for name in plugin_names():
            pdir = PLUGINS_DIR / name
            hooks = pdir / "hooks"
            if not hooks.is_dir():
                continue
            with self.subTest(plugin=name):
                hj = hooks / "hooks.json"
                self.assertTrue(hj.is_file(), "有 hooks/ 目录但缺 hooks.json")
                with open(hj, encoding="utf-8") as f:
                    cfg = json.load(f)  # 非法 JSON 直接抛错即失败
                cmds = hook_commands(cfg)
                self.assertGreater(len(cmds), 0, "hooks.json 里没找到任何 hook 命令")
                for cmd in cmds:
                    for ref in set(PLUGIN_ROOT_REF.findall(cmd)):
                        sh = pdir / ref.rstrip("/")
                        self.assertTrue(sh.is_file(), f"hook 引用的脚本不存在：{ref}")
                        mode = os.stat(sh).st_mode
                        self.assertTrue(mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH),
                                        f"hook 脚本不可执行（缺 x 位）：{ref}")


class TestPluginCommands(unittest.TestCase):
    def test_commands_have_frontmatter(self):
        for name in plugin_names():
            pdir = PLUGINS_DIR / name
            cmds = pdir / "commands"
            if not cmds.is_dir():
                continue
            with self.subTest(plugin=name):
                files = sorted(cmds.glob("*.md"))
                self.assertGreater(len(files), 0)
                for md in files:
                    fm = parse_frontmatter(md.read_text(encoding="utf-8"))
                    self.assertIsNotNone(fm, f"{md.name} 缺 frontmatter")
                    self.assertTrue(fm.get("description"),
                                    f"{md.name} 的 description 为空")


class TestSkillCoverage(unittest.TestCase):
    def test_five_plugins_cover_all_root_skills(self):
        root = sorted(d.name for d in ROOT_SKILLS.iterdir() if d.is_dir())
        self.assertEqual(len(root), EXPECTED_SKILL_COUNT,
                         f"根 skills/ 有 {len(root)} 个，与预期的 {EXPECTED_SKILL_COUNT} 不符")
        seen = {}
        for name in plugin_names():
            skills = [d.name for d in (PLUGINS_DIR / name / "skills").iterdir()
                      if d.is_dir()]
            for s in skills:
                self.assertNotIn(s, seen, f"skill {s!r} 在 {seen.get(s)} 和 {name} 重复")
                seen[s] = name
        self.assertEqual(sorted(seen), root,
                         f"插件 skill 集合与根 skills/ 不一致："
                         f"缺 {sorted(set(root) - set(seen))}，多 {sorted(set(seen) - set(root))}")


SIBLING_IMPORT = re.compile(r"^\s*(?:import|from)\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)
INSTALL_REF = re.compile(r"/plugin install ([A-Za-z0-9_.-]+)@livepowers-marketplace")
INSTALL_DOCS = ["README.md", "README.en.md", "bin/livepowers.js", "docs/index.html",
                "docs/lightweight.md"]


class TestPluginScripts(unittest.TestCase):
    def test_sibling_imports_shipped(self):
        root_modules = {p.stem for p in (REPO / "scripts").glob("*.py")}
        for name in plugin_names():
            sdir = PLUGINS_DIR / name / "scripts"
            if not sdir.is_dir():
                continue
            with self.subTest(plugin=name):
                shipped = {p.stem for p in sdir.glob("*.py")}
                missing = []
                for py in sorted(sdir.glob("*.py")):
                    mods = set(SIBLING_IMPORT.findall(py.read_text(encoding="utf-8")))
                    for mod in sorted((mods & root_modules) - shipped):
                        missing.append(f"{py.name} → {mod}.py")
                self.assertEqual(missing, [], f"插件 scripts/ 缺少被 import 的兄弟模块：{missing}")


class TestInstallInstructions(unittest.TestCase):
    def test_install_refs_point_to_real_plugins(self):
        names = set(plugin_names())
        bad = []
        for rel in INSTALL_DOCS + [str(p.relative_to(REPO)) for p in sorted(PLUGINS_DIR.glob("*/README.md"))]:
            f = REPO / rel
            if not f.is_file():
                continue
            for ref in INSTALL_REF.findall(f.read_text(encoding="utf-8")):
                if ref not in names:
                    bad.append(f"{rel}: {ref}")
        self.assertEqual(bad, [], f"安装命令指向不存在的插件：{bad}")


if __name__ == "__main__":
    unittest.main()
