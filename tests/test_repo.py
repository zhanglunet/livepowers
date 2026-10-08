"""仓库结构检查：技能格式、路由表覆盖、清单版本一致、钩子输出、示例可运行、无敏感信息。"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(REPO, "skills")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def frontmatter(path):
    text = read(path)
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, f"{path} 缺少 frontmatter"
    fm = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip()
    return fm, text[m.end():]


class TestSkills(unittest.TestCase):
    def setUp(self):
        self.names = sorted(d for d in os.listdir(SKILLS) if os.path.isdir(os.path.join(SKILLS, d)))

    def test_frontmatter(self):
        for n in self.names:
            fm, body = frontmatter(os.path.join(SKILLS, n, "SKILL.md"))
            self.assertEqual(fm.get("name"), n)
            d = fm.get("description", "")
            self.assertTrue(d.startswith("Use when") or d.startswith("Use before") or d.startswith("Use at")
                            or d.startswith("Use whenever"), f"{n}: description 应以触发条件开头")
            self.assertLessEqual(len(d), 1024, n)
            # 只写触发条件：不概括流程（writing-livepowers-skills 的规则）
            self.assertNotRegex(d, r"\s—\s", f"{n}: description 不要用破折号接流程摘要")
            self.assertNotRegex(d, r"\b(runs|produces|enforces|turns|builds|specifies|evolves|compiles|registers|"
                                   r"checks the|picks|reviews the|sets exploration|applies)\b",
                                f"{n}: description 只写何时使用，不要概括流程")
            self.assertLessEqual(len(d), 400, f"{n}: description 过长（{len(d)}），只保留触发条件")
            self.assertGreater(len(body.strip()), 200, n)

    def test_router_and_readme_cover_all(self):
        router = read(os.path.join(SKILLS, "using-livepowers", "SKILL.md"))
        readme = read(os.path.join(REPO, "README.md"))
        for n in self.names:
            if n != "using-livepowers":
                self.assertIn(f"`{n}`", router, f"路由表缺 {n}")
            self.assertIn(f"`{n}`", readme, f"README 缺 {n}")

    def test_cross_references_exist(self):
        allow = {"model-a", "model-b"}
        for n in self.names:
            text = read(os.path.join(SKILLS, n, "SKILL.md"))
            for ref in re.findall(r"`([a-z0-9]+(?:-[a-z0-9]+)+)`", text):
                if ref not in allow:
                    self.assertIn(ref, self.names, f"{n} 引用了不存在的技能 {ref}")


class TestManifests(unittest.TestCase):
    def test_versions_consistent(self):
        vs = set()
        for p in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", ".cursor-plugin/plugin.json"):
            vs.add(json.loads(read(os.path.join(REPO, p)))["version"])
        vs.add(json.loads(read(os.path.join(REPO, ".claude-plugin/marketplace.json")))["plugins"][0]["version"])
        vs.add(json.loads(read(os.path.join(REPO, "package.json")))["version"])
        sys.path.insert(0, os.path.join(REPO, "scripts"))
        import lp
        vs.add(lp.__version__)
        self.assertEqual(len(vs), 1, vs)
        self.assertIn(f"## [{vs.pop()}]", read(os.path.join(REPO, "CHANGELOG.md")))

    def test_session_start_hook(self):
        for env, key in (({"CLAUDE_PLUGIN_ROOT": REPO}, "hookSpecificOutput"),
                         ({"CURSOR_PLUGIN_ROOT": REPO}, "additional_context"),
                         ({}, "additionalContext")):
            e = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_PLUGIN_ROOT", "CURSOR_PLUGIN_ROOT")}
            e.update(env)
            out = subprocess.run(["bash", os.path.join(REPO, "hooks", "session-start.sh")], env=e,
                                 capture_output=True, text=True, check=True).stdout
            data = json.loads(out)
            self.assertIn(key, data)
            self.assertIn("七条铁律", json.dumps(data, ensure_ascii=False))


    def test_panorama_svg_in_sync_with_site(self):
        site = read(os.path.join(REPO, "docs", "index.html"))
        inline = re.search(r'<figure class="pano">\s*<svg[^>]*>(.*?)</svg>', site, re.S).group(1)
        standalone = read(os.path.join(REPO, "docs", "panorama.svg"))
        body = re.search(r"<svg[^>]*>(.*?)</svg>", standalone, re.S).group(1)
        body = re.sub(r"<style>.*?</style>\s*<rect width=\"1000\" height=\"770\"[^>]*/>\s*", "", body, flags=re.S)
        self.assertEqual(body.strip(), inline.strip(), "docs/panorama.svg 与网站内联全景图不一致，请重新生成")
        self.assertIn("panorama.svg", read(os.path.join(REPO, "README.md")))

    def test_tool_card_template(self):
        content = read(os.path.join(REPO, "templates", "tool-card.md"))
        self.assertIn("后置条件", content)
        self.assertIn("禁止动作", content)


    def test_evidence_capture_hook(self):
        hooks = json.loads(read(os.path.join(REPO, "hooks", "hooks.json")))["hooks"]
        self.assertEqual(hooks["PostToolUse"][0]["matcher"], "Bash")
        self.assertIn("evidence-capture.sh", json.dumps(hooks["PostToolUse"]))
        self.assertIn("evidence-capture.sh", json.dumps(hooks["Stop"]))
        script = os.path.join(REPO, "hooks", "evidence-capture.sh")
        self.assertTrue(os.access(script, os.X_OK))
        with tempfile.TemporaryDirectory() as d:
            subprocess.run([sys.executable, os.path.join(REPO, "scripts", "lp.py"), "init"], cwd=d, check=True,
                           capture_output=True)
            payload = {"session_id": "h", "cwd": d, "tool_name": "Bash", "tool_input": {"command": 'lp registry find "q"'},
                       "tool_response": {"stdout": "MISS", "stderr": "", "exit_code": 2}}
            env = {**os.environ, "CLAUDE_PLUGIN_ROOT": REPO}
            p = subprocess.run(["bash", script, "post-tool"], cwd=d, input=json.dumps(payload), capture_output=True,
                               text=True, env=env)
            self.assertEqual(p.returncode, 0)
            p = subprocess.run(["bash", script, "stop"], cwd=d, input=json.dumps({"session_id": "h", "cwd": d}),
                               capture_output=True, text=True, env=env)
            self.assertEqual((p.returncode, p.stdout.strip()), (0, ""))
            self.assertIn('"auto": true', read(os.path.join(d, ".livepowers", "evidence.jsonl")))


class TestExample(unittest.TestCase):
    def test_walkthrough(self):
        p = subprocess.run(["bash", os.path.join(REPO, "examples", "walkthrough.sh")], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("HIT", p.stdout)
        self.assertIn("环境漂移", p.stdout)


class TestNoIdentifyingInfo(unittest.TestCase):
    """发布内容不得包含具体组织、人员、客户或内部项目信息。黑名单从环境变量 LP_DENYLIST（逗号分隔）读取。"""

    def test_denylist(self):
        words = [w for w in os.environ.get("LP_DENYLIST", "").split(",") if w]
        if not words:
            self.skipTest("未设置 LP_DENYLIST")
        hits = []
        for root, dirs, files in os.walk(REPO):
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
            for f in files:
                p = os.path.join(root, f)
                try:
                    text = read(p)
                except (UnicodeDecodeError, OSError):
                    continue
                hits += [(os.path.relpath(p, REPO), w) for w in words if w in text]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
