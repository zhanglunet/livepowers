"""活软件展示面：validate / record / promote / reconcile / deploy / pages list，以及注册门禁。"""
import copy
import json
import os
import shutil
import subprocess
import sys

from helpers import REPO, Workdir

APP = os.path.join(REPO, "examples", "living_app")
EPH = os.path.join(APP, "surfaces", "pipeline-by-region.ephemeral.json")
FIXED = os.path.join(APP, "surfaces", "pipeline-by-region.fixed.json")
DDL = os.path.join(APP, "ddl", "v_pipeline_by_region.sql")
ROLLBACK = os.path.join(APP, "ddl", "v_pipeline_by_region.rollback.sql")


class TestSurface(Workdir):
    def setUp(self):
        super().setUp()
        subprocess.run([sys.executable, os.path.join(REPO, "examples", "make_demo_db.py"), "demo.sqlite"],
                       cwd=self.dir, check=True, capture_output=True)
        self.lp("init")
        onto = self.run_script("scan_sqlite.py", "demo.sqlite", check=0).stdout
        with open(os.path.join(self.dir, ".livepowers", "ontology.draft.yaml"), "w", encoding="utf-8") as f:
            f.write(onto + "\nviews:\n  - name: v_pipeline_by_region\n")

    def text(self, rel):
        with open(os.path.join(self.dir, rel), encoding="utf-8") as f:
            return f.read()

    def load(self, path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def write(self, name, obj):
        p = os.path.join(self.dir, name)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
        return p

    def invalid(self, surface, expect):
        out = self.lp("surface", "validate", self.write("s.json", surface), check=1).stdout
        self.assertIn(expect, out)

    def deploy(self, db, env, *extra, check=0):
        return self.lp("surface", "deploy", FIXED, "--env", env, "--by", "agent-a", "--db", db,
                       "--ddl", DDL, "--rollback", ROLLBACK, *extra, check=check)

    def test_examples_validate(self):
        self.lp("surface", "validate", EPH)
        self.lp("surface", "validate", FIXED)

    def test_validate_rejects_code_outside_objects_writes_and_inline_rows(self):
        base = self.load(EPH)
        s = copy.deepcopy(base)
        s["components"][0]["onClick"] = "fetch('/x')"
        self.invalid(s, "可执行代码")
        s = copy.deepcopy(base)
        s["components"][0]["label"] = "<script>alert(1)</script>"
        self.invalid(s, "可执行代码")
        s = copy.deepcopy(base)
        s["data"]["pipeline"]["query"] = "SELECT * FROM salaries"
        self.invalid(s, "本体外的对象 salaries")
        s = copy.deepcopy(base)
        s["data"]["pipeline"]["source"]["name"] = "salaries"
        self.invalid(s, "不在本体里")
        s = copy.deepcopy(base)
        s["data"]["pipeline"]["query"] = "SELECT 1 FROM opportunities; DELETE FROM opportunities"
        self.invalid(s, "DELETE")
        s = copy.deepcopy(base)
        s["data"]["pipeline"]["rows"] = [["east", 1, 1]]
        self.invalid(s, "不内嵌结果数据")
        s = copy.deepcopy(base)
        s["components"].append({"type": "button", "data": "pipeline"})
        self.invalid(s, "type 不支持")
        # 次抛引用写操作能力
        self.lp("registry", "add", "--name", "Transfer", "--id", "cap_t", "--kind", "cli", "--intents", "transfer",
                "--entry", "crm transfer", "--writes-state", "--tests", "t.py")
        s = copy.deepcopy(base)
        s["data"]["pipeline"] = {"source": {"type": "capability", "name": "cap_t"}}
        self.invalid(s, "写操作能力 cap_t")

    def test_validate_needs_ontology(self):
        os.remove(os.path.join(self.dir, ".livepowers", "ontology.draft.yaml"))
        out = self.lp("surface", "validate", EPH, check=1).stdout
        self.assertIn("找不到本体", out)

    def test_record_keeps_metadata_only_and_writes_evidence(self):
        rec_path = self.lp("surface", "record", EPH, "--intent", "pipeline by region", "--db", "demo.sqlite").stdout.strip()
        raw = self.text(rec_path)
        rec = json.loads(raw)
        st = rec["stats"]["pipeline"]
        self.assertEqual(st["rows"], 2)
        self.assertEqual(st["sums"]["amount"], 5400000.0)
        # 明细行（地区值、单行金额）不得落盘：只有查询文本、行数、哈希与合计
        for leaked in ("'east'", '"east"', '"south"', "3000000", "2400000"):
            self.assertNotIn(leaked, raw)
        ev = [json.loads(x) for x in self.text(".livepowers/evidence.jsonl").splitlines() if x.strip()]
        self.assertEqual((ev[-1]["intent"], ev[-1]["system"], ev[-1]["id"]), ("pipeline by region", "S2", rec["evidence"]))
        # 固化展示面不能 record
        self.lp("surface", "record", FIXED, "--intent", "x", check=1)
        # 缓存目录不进 git
        self.assertIn("cache/", self.text(".livepowers/.gitignore"))

    def test_promote_creates_task_and_candidate(self):
        rec = self.lp("surface", "record", EPH, "--intent", "pipeline by region", "--db", "demo.sqlite").stdout.strip()
        tid = self.lp("surface", "promote", rec, "--by", "sales-ops").stdout.strip()
        task = json.loads(self.lp("task", "show", tid).stdout)
        self.assertEqual((task["intent"], task["state"]), ("pipeline by region", "clarify"))
        cands = json.loads(self.lp("candidates", "--json").stdout)
        self.assertEqual(cands[0]["intent"], "pipeline by region")
        self.assertEqual(cands[0]["promoted"], [tid])
        self.lp("surface", "promote", rec, "--by", "sales-ops", check=1)  # 不能重复申请

    def test_reconcile_detects_match_and_mismatch(self):
        rec = self.lp("surface", "record", EPH, "--intent", "pipeline by region", "--db", "demo.sqlite").stdout.strip()
        shutil.copy(os.path.join(self.dir, "demo.sqlite"), os.path.join(self.dir, "twin.sqlite"))
        self.deploy("twin.sqlite", "twin", "--twin")
        self.assertIn("对账一致", self.lp("surface", "reconcile", rec, FIXED, "--db", "twin.sqlite").stdout)
        wrong = self.load(FIXED)
        wrong["data"]["pipeline"]["query"] = "SELECT region, amount, n FROM v_pipeline_by_region WHERE region = 'east'"
        out = self.lp("surface", "reconcile", rec, self.write("wrong.json", wrong), "--db", "twin.sqlite", check=1).stdout
        self.assertIn("行数 2 → 1", out)
        self.assertIn("amount 合计", out)

    def test_deploy_rolls_back_on_failure(self):
        bad_ddl = os.path.join(self.dir, "bad.sql")
        with open(bad_ddl, "w", encoding="utf-8") as f:
            f.write("CREATE VIEW v_other AS SELECT 1 AS x;")
        out = self.lp("surface", "deploy", FIXED, "--env", "prod", "--by", "ops", "--db", "demo.sqlite",
                      "--ddl", bad_ddl, "--rollback", ROLLBACK, check=1).stdout
        self.assertIn("回滚", out)
        receipt = self.read_json(".livepowers/deployments/pipeline_by_region/prod.json")
        self.assertFalse(receipt["verified"])
        self.assertIn("error", receipt)
        self.lp("surface", "deploy", FIXED, "--env", "prod", "--by", "ops", "--external", check=1)  # 缺核验人
        self.lp("surface", "deploy", FIXED, "--env", "prod", "--by", "ops", "--external", "--verified-by", "ops", check=1)

    def test_registry_requires_prod_receipt_and_pages_list(self):
        reg = ["registry", "add", "--name", "Pipeline", "--id", "cap_pipeline", "--kind", "view",
               "--intents", "pipeline by region,各地区在途商机", "--entry", "v_pipeline_by_region", "--ui", FIXED,
               "--generated-by", "agent-a", "--accepted-by", "reviewer-b"]
        self.lp(*reg, check=1)  # 没有任何回执
        shutil.copy(os.path.join(self.dir, "demo.sqlite"), os.path.join(self.dir, "twin.sqlite"))
        self.deploy("twin.sqlite", "twin", "--twin")
        self.assertIn("生产部署回执", self.lp(*reg, check=1).stderr)  # 孪生回执不算
        self.assertEqual(json.loads(self.lp("pages", "list").stdout), [])
        self.deploy("demo.sqlite", "prod")
        self.lp(*reg)
        pages = json.loads(self.lp("pages", "list").stdout)
        self.assertEqual([p["capability"] for p in pages], ["cap_pipeline"])
        self.assertEqual(pages[0]["deployed"][0]["env"], "prod")
        self.assertIn("固定页", self.lp("registry", "find", "各地区在途商机").stdout)
        # 次抛展示面不能注册为固定页
        self.lp("registry", "add", "--name", "x", "--id", "cap_x", "--kind", "view", "--intents", "x",
                "--entry", "x", "--ui", EPH, check=1)
        self.lp("registry", "retire", "cap_pipeline", "--reason", "口径变更")
        self.assertEqual(json.loads(self.lp("pages", "list").stdout), [])

    def test_template_validates(self):
        with open(os.path.join(self.dir, ".livepowers", "ontology.draft.yaml"), "a", encoding="utf-8") as f:
            f.write("  - name: v_weekly_revenue\n")
        self.lp("surface", "validate", os.path.join(REPO, "templates", "surface.json"))


class TestLivingApp(Workdir):
    """参考宿主：次抛 → 申请固化 → grow.sh → 再问同一问题命中固定页。"""

    def setUp(self):
        super().setUp()
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        self.port = s.getsockname()[1]
        s.close()
        self.proc = subprocess.Popen([sys.executable, os.path.join(APP, "server.py"), "--workdir", self.dir,
                                      "--port", str(self.port)], stdout=subprocess.PIPE, text=True)
        self.proc.stdout.readline()  # 启动完成

    def tearDown(self):
        self.proc.terminate()
        self.proc.wait()
        self.proc.stdout.close()
        super().tearDown()

    def call(self, path, body=None):
        import urllib.error
        import urllib.request
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}",
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read())

    def test_ephemeral_promote_grow_then_fixed(self):
        self.assertEqual(self.call("/api/pages"), (200, []))
        code, r = self.call("/api/ask", {"q": "各地区在途商机金额"})
        self.assertEqual((code, r["tier"]), (200, "ephemeral"))
        self.assertEqual(r["data"]["pipeline"]["rows"], [["east", 3000000.0, 4], ["south", 2400000.0, 4]])
        self.assertEqual(self.call("/api/promote", {"record": "../../etc/passwd"})[0], 400)
        code, p = self.call("/api/promote", {"record": r["record"]})
        self.assertEqual(code, 200)
        self.assertTrue(p["task"].startswith("t_"))
        g = subprocess.run(["bash", os.path.join(APP, "grow.sh"), self.dir], capture_output=True, text=True)
        self.assertEqual(g.returncode, 0, g.stdout + g.stderr)
        code, r2 = self.call("/api/ask", {"q": "各地区在途商机金额"})
        self.assertEqual((r2["tier"], r2["capability"]), ("fixed", "cap_pipeline_by_region"))
        self.assertEqual(r2["data"], r["data"])  # 固化结构与次抛结果一致
        self.assertEqual(self.call("/api/pages/cap_pipeline_by_region")[1]["tier"], "fixed")

    def test_frontend_never_executes_surface_content(self):
        with open(os.path.join(APP, "static", "app.js"), encoding="utf-8") as f:
            js = f.read()
        for bad in ("innerHTML", "eval(", "new Function", "insertAdjacentHTML", "document.write"):
            self.assertNotIn(bad, js)
