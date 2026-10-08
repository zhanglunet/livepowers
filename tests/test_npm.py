"""npm 安装包：livepowers install / uninstall / list / path，lp 转发，打包内容。需要 node。"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from helpers import REPO  # noqa: E402

BIN = os.path.join(REPO, "bin")
NODE = shutil.which("node")
SKILL_NAMES = sorted(d for d in os.listdir(os.path.join(REPO, "skills"))
                     if os.path.isfile(os.path.join(REPO, "skills", d, "SKILL.md")))
START, END = "<!-- livepowers:start -->", "<!-- livepowers:end -->"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


@unittest.skipUnless(NODE, "未安装 node")
class TestInstaller(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self._tmp.name, "home")
        self.proj = os.path.join(self._tmp.name, "proj")
        os.makedirs(self.home)
        os.makedirs(self.proj)

    def tearDown(self):
        self._tmp.cleanup()

    def cli(self, *args, check=0, bin="livepowers.js"):
        env = {**os.environ, "HOME": self.home, "USERPROFILE": self.home}
        p = subprocess.run([NODE, os.path.join(BIN, bin), *args], cwd=self.proj,
                           capture_output=True, text=True, env=env)
        if check is not None:
            self.assertEqual(p.returncode, check, msg=f"{args}\nstdout={p.stdout}\nstderr={p.stderr}")
        return p

    def assert_skills(self, dest):
        for n in SKILL_NAMES:
            self.assertTrue(os.path.isfile(os.path.join(dest, n, "SKILL.md")), n)

    def test_default_installs_claude_personal_with_manifest(self):
        out = self.cli("install").stdout
        dest = os.path.join(self.home, ".claude", "skills")
        self.assert_skills(dest)
        manifest = json.loads(read(os.path.join(dest, ".livepowers-manifest.json")))
        self.assertEqual(sorted(manifest["skills"]), SKILL_NAMES)
        pkg = json.loads(read(os.path.join(REPO, "package.json")))
        self.assertEqual(manifest["version"], pkg["version"])
        self.assertIn("/plugin install", out)
        self.assertTrue(os.path.isfile(os.path.join(dest, "using-livepowers", "templates", "spec.md")))

    def test_existing_skill_skipped_unless_force(self):
        self.cli("install")
        skill = os.path.join(self.home, ".claude", "skills", "system1-first", "SKILL.md")
        write(skill, "local edit")
        out = self.cli("install").stdout
        self.assertIn("跳过", out)
        self.assertEqual(read(skill), "local edit")
        self.cli("install", "--force")
        self.assertNotEqual(read(skill), "local edit")

    def test_cursor_and_project_targets(self):
        self.cli("install", "--target", "cursor")
        self.assert_skills(os.path.join(self.home, ".cursor", "skills"))
        self.assertFalse(os.path.exists(os.path.join(self.proj, ".cursor", "rules", "livepowers.mdc")))
        self.cli("install", "--target", "claude", "--project")
        self.assert_skills(os.path.join(self.proj, ".claude", "skills"))
        other = os.path.join(self._tmp.name, "other")
        os.makedirs(other)
        self.cli("install", "--target", "agents", "--project", other)
        self.assert_skills(os.path.join(other, ".agents", "skills"))
        # Cursor 项目级安装生成 .cursor/rules/livepowers.mdc，uninstall 清理
        self.cli("install", "--target", "cursor", "--project")
        self.assert_skills(os.path.join(self.proj, ".cursor", "skills"))
        mdc = os.path.join(self.proj, ".cursor", "rules", "livepowers.mdc")
        self.assertTrue(os.path.isfile(mdc))
        content = read(mdc)
        self.assertIn("alwaysApply: true", content)
        self.assertIn("七条铁律", content)
        self.assertIn("路由表", content)
        self.assertIn(START, content)
        self.assertIn(END, content)
        self.cli("uninstall", "--target", "cursor", "--project")
        self.assertFalse(os.path.exists(mdc))


    def test_codex_project_merges_agents_md_and_uninstall_cleans_up(self):
        agents = os.path.join(self.proj, "AGENTS.md")
        write(agents, "# My project\n\nkeep me\n")
        foreign = os.path.join(self.proj, ".agents", "skills", "my-own-skill", "SKILL.md")
        write(foreign, "mine")
        self.cli("install", "--target", "codex", "--project")
        self.cli("install", "--target", "codex", "--project", "--force")
        text = read(agents)
        self.assertIn("keep me", text)
        self.assertEqual(text.count(START), 1)
        self.assertIn("lp registry find", text)
        self.assertIn(".agents/skills/using-livepowers/SKILL.md", text)
        self.assertNotIn("python scripts/lp.py", text)
        self.assertNotIn("开发本仓库", text)
        self.assert_skills(os.path.join(self.proj, ".agents", "skills"))

        self.cli("uninstall", "--target", "codex", "--project")
        self.assertNotIn(START, read(agents))
        self.assertIn("keep me", read(agents))
        self.assertFalse(os.path.exists(os.path.join(self.proj, ".agents", "skills", "system1-first")))
        self.assertTrue(os.path.isfile(foreign))

    def test_dry_run_writes_nothing(self):
        out = self.cli("install", "--target", "codex", "--project", "--dry-run").stdout
        self.assertIn("system1-first", out)
        self.assertEqual(os.listdir(self.proj), [])
        self.assertEqual(os.listdir(self.home), [])

    def test_list_and_path(self):
        self.assertIn("未安装", self.cli("list").stdout)
        self.cli("install")
        out = self.cli("list").stdout
        self.assertIn(".claude", out)
        self.assertIn(str(len(SKILL_NAMES)), out)
        self.assertEqual(os.path.realpath(self.cli("path").stdout.strip()), os.path.realpath(REPO))

    def test_bad_usage_exits_2(self):
        self.cli("install", "--target", "vim", check=2)
        self.cli("frobnicate", check=2)

    def test_lp_forwards_to_python(self):
        pkg = json.loads(read(os.path.join(REPO, "package.json")))
        out = self.cli("--version", bin="lp.js").stdout
        self.assertIn(pkg["version"], out)


@unittest.skipUnless(shutil.which("npm"), "未安装 npm")
class TestPackContents(unittest.TestCase):
    def test_pack_includes_runtime_files_only(self):
        p = subprocess.run(["npm", "pack", "--dry-run", "--json"], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        files = {f["path"] for f in json.loads(p.stdout)[0]["files"]}
        for need in ("bin/livepowers.js", "bin/lp.js", "scripts/lp.py", "skills/system1-first/SKILL.md",
                     "templates/spec.md", "AGENTS.md", "LICENSE", "README.md", "package.json"):
            self.assertIn(need, files)
        for f in files:
            self.assertFalse(f.startswith(("tests/", "docs/", "examples/", ".github/", "dist/")), f)
            self.assertNotIn("__pycache__", f)


if __name__ == "__main__":
    unittest.main()
