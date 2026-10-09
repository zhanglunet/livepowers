import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from helpers import SCRIPTS, Workdir  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"))
import lp  # noqa: E402


class TestMath(unittest.TestCase):
    def test_breakeven_includes_failure_cost(self):
        n, c2e = lp.breakeven(c2=0.9, c1=0.001, K=30, M=10, p=0.8, h=5)
        self.assertAlmostEqual(c2e, 0.9 / 0.8 + 0.2 * 5 / 0.8)
        self.assertAlmostEqual(n, 40 / (c2e - 0.001))

    def test_breakeven_never_when_s1_not_cheaper(self):
        n, _ = lp.breakeven(c2=1, c1=2, K=1, M=0)
        self.assertEqual(n, float("inf"))

    def test_fvsr_bounds(self):
        self.assertEqual(lp.fvsr(100, 2, 2, True)[0], 10)
        self.assertEqual(lp.fvsr(1, 0, 0, False)[0], 0)

    def test_chinese_match(self):
        cap = {"intents": ["各地区周收入"], "name": "x"}
        self.assertGreaterEqual(lp.score_match("帮我看一下各地区的周收入", cap), 2)
        self.assertLess(lp.score_match("合同审批进度", cap), 2)


class TestCLI(Workdir):
    def test_registry_route_and_retire(self):
        self.lp("init")
        self.lp("registry", "find", "weekly revenue by region", check=2)
        self.lp("registry", "add", "--name", "Weekly revenue", "--kind", "sql",
                "--intents", "weekly revenue by region,各地区周收入", "--entry", "python w.py")
        out = self.lp("registry", "find", "各地区的周收入").stdout
        self.assertIn("HIT", out)
        self.lp("registry", "retire", "cap_weekly_revenue", "--reason", "口径变更")
        self.lp("registry", "find", "各地区的周收入", check=2)

    def test_write_capability_requires_tests_and_separation(self):
        self.lp("init")
        self.lp("registry", "add", "--name", "t", "--kind", "cli", "--intents", "x y", "--entry", "e",
                "--writes-state", check=1)
        self.lp("registry", "add", "--name", "t", "--kind", "cli", "--intents", "x y", "--entry", "e",
                "--generated-by", "a", "--accepted-by", "a", check=1)

    def test_evidence_candidates_and_call_counting(self):
        self.lp("init")
        for _ in range(3):
            self.lp("evidence", "add", "--intent", "stale opp", "--system", "S2", "--outcome", "success",
                    "--cost", "1", "--verifiable")
        cands = json.loads(self.lp("candidates", "--json").stdout)
        self.assertEqual(cands[0]["intent"], "stale opp")
        self.lp("registry", "add", "--name", "Stale", "--id", "cap_s", "--kind", "cli",
                "--intents", "stale opp", "--entry", "e")
        self.lp("evidence", "add", "--intent", "stale opp", "--system", "S1", "--outcome", "fail",
                "--capability", "cap_s")
        self.lp("evidence", "add", "--intent", "stale opp", "--system", "S1", "--outcome", "fail",
                "--capability", "cap_s")
        reg = self.read_json(".livepowers/registry.json")
        self.assertEqual(reg["capabilities"][0]["calls"], 2)
        self.assertIn("连续失败 2 次", self.lp("registry", "review").stdout)
        self.assertEqual(json.loads(self.lp("candidates", "--json").stdout), [])

    def test_review_flags_model_change(self):
        self.lp("init")
        self.lp("registry", "add", "--name", "S", "--id", "cap_k", "--kind", "skill", "--intents", "aa bb",
                "--entry", "e", "--validated-model", "model-a")
        out = self.lp("registry", "review", "--current-model", "model-b").stdout
        self.assertIn("换模型须重跑基准", out)
        self.lp("registry", "verify", "cap_k", "--model", "model-b")
        self.assertIn("无待处理项", self.lp("registry", "review", "--current-model", "model-b").stdout)

    def test_score_exit_codes(self):
        self.lp("score", "--freq", "30", "--verifiable", "2", "--stability", "2", "--c2", "1", "--K", "10", check=0)
        self.lp("score", "--freq", "30", "--verifiable", "0", "--stability", "2", "--c2", "1", "--K", "10", check=3)

    def test_task_board_rules(self):
        self.lp("init")
        t = self.lp("task", "new", "--title", "demo", "--max-loops", "2").stdout.strip()
        self.lp("task", "move", t, "registered", "--by", "x", "--reason", "skip", check=1)  # 非法迁移
        self.lp("task", "move", t, "spec", "--by", "owner", check=1)                         # 缺 reason
        self.lp("task", "move", t, "spec", "--by", "owner", "--reason", "ok")
        self.lp("task", "move", t, "explore", "--by", "gen", "--reason", "r1")
        self.lp("task", "move", t, "verify", "--by", "gen", "--reason", "submit", "--evidence", "p")
        self.lp("task", "move", t, "registered", "--by", "gen", "--reason", "self", "--evidence", "p", check=1)
        self.lp("task", "move", t, "registered", "--by", "rev", "--reason", "ok", check=1)  # 缺证据
        self.lp("task", "move", t, "registered", "--by", "rev", "--reason", "ok", "--evidence", "acc.md")
        # 关联 spec 与 spec_task（必须引用实际存在的任务声明）
        os.makedirs(os.path.join(self.dir, "specs"))
        with open(os.path.join(self.dir, "specs", "demo.md"), "w") as f:
            f.write("## 任务清单\n- T001 Demo\n")
        t2 = self.lp("task", "new", "--title", "spec demo", "--spec", "specs/demo.md", "--spec-task", "T001").stdout.strip()
        task2_json = json.loads(self.lp("task", "show", t2).stdout)
        self.assertEqual(task2_json.get("spec"), "specs/demo.md")
        self.assertEqual(task2_json.get("spec_task"), "T001")


    def test_task_stop_loss(self):
        self.lp("init")
        t = self.lp("task", "new", "--title", "loop", "--max-loops", "2", "--budget", "100").stdout.strip()
        self.lp("task", "move", t, "explore", "--by", "g", "--reason", "1")
        self.lp("task", "move", t, "explore", "--by", "g", "--reason", "2")
        self.lp("task", "move", t, "explore", "--by", "g", "--reason", "3", check=4)
        state = self.read_json(".livepowers/tasks.json")["tasks"][0]["state"]
        self.assertEqual(state, "takeover")

    def test_takeover_cannot_skip_gates_and_can_reopen(self):
        self.lp("init")
        t = self.lp("task", "new", "--title", "loop", "--max-loops", "1").stdout.strip()
        self.lp("task", "move", t, "explore", "--by", "g", "--reason", "1")
        self.lp("task", "move", t, "explore", "--by", "g", "--reason", "2", check=4)   # 止损 → 异常接管
        self.lp("task", "move", t, "running", "--by", "ops", "--reason", "上线", check=1)  # 不能绕过验收
        self.lp("task", "move", t, "explore", "--by", "h", "--reason", "重开", check=4)   # 轮次未重置仍止损
        self.lp("task", "move", t, "explore", "--by", "h", "--reason", "重开", "--reset-loops", "--extend-budget", "50")
        task = self.read_json(".livepowers/tasks.json")["tasks"][0]
        self.assertEqual(task["state"], "explore")
        self.assertEqual(task["loops"], 1)
        self.assertEqual(task["budget"], 50)
        self.lp("task", "move", t, "closed", "--by", "h", "--reason", "放弃")
        self.lp("task", "move", t, "takeover", "--by", "h", "--reason", "x", check=1)  # closed 是终态

    def test_registry_supersedes(self):
        self.lp("init")
        self.lp("registry", "add", "--name", "Weekly revenue", "--kind", "sql", "--intents", "weekly revenue",
                "--entry", "v1.sql")
        self.lp("registry", "add", "--name", "Weekly revenue", "--kind", "sql", "--intents", "weekly revenue",
                "--entry", "v2.sql", check=1)  # 同 id 仍 active
        self.lp("registry", "add", "--name", "Weekly revenue", "--id", "cap_weekly_revenue_v2", "--kind", "sql",
                "--intents", "weekly revenue", "--entry", "v2.sql", "--version", "2.0.0",
                "--supersedes", "cap_weekly_revenue")
        caps = {c["id"]: c for c in self.read_json(".livepowers/registry.json")["capabilities"]}
        self.assertEqual(caps["cap_weekly_revenue"]["status"], "retired")
        self.assertEqual(caps["cap_weekly_revenue"]["superseded_by"], "cap_weekly_revenue_v2")
        self.assertIn("v2.sql", self.lp("registry", "find", "weekly revenue").stdout)

    def test_outcome_direction_and_cost_requires_baseline(self):
        self.lp("init")
        self.lp("outcome", "cost", "--scenario", "s", "--kind", "human", "--amount", "1", check=1)  # 无基线
        self.lp("outcome", "baseline", "--scenario", "s", "--metric", "逾期数", "--value", "40", "--target", "10",
                "--base", "100000", "--direction", "lower")
        self.lp("outcome", "measure", "--scenario", "s", "--metric", "逾期数", "--value", "22")
        out = self.lp("outcome", "report").stdout
        self.assertIn("ΔV = B×u = 100,000×0.4500 = 45,000.00", out)  # 越低越好：u = (40-22)/40

    def test_help_lists_subcommands(self):
        out = self.lp("--help").stdout
        for word in ("evidence", "registry", "task", "outcome", "asset", "report", "证据", "看板"):
            self.assertIn(word, out)
        self.assertIn("--reset-loops", self.lp("task", "move", "--help").stdout)

    def test_canary_record_and_compare(self):
        self.lp("init")
        self.lp("canary", "compare", "--name", "core", check=1)  # 无记录
        self.lp("canary", "record", "--name", "core", "--model", "m1", "--pass", "10", "--total", "10", "--tokens", "1000")
        self.assertIn("首次记录", self.lp("canary", "compare", "--name", "core").stdout)
        self.lp("canary", "record", "--name", "core", "--model", "m2", "--pass", "7", "--total", "10", "--tokens", "1000")
        out = self.lp("canary", "compare", "--name", "core", check=5).stdout
        self.assertIn("通过率", out)
        self.lp("canary", "record", "--name", "core", "--model", "m2", "--pass", "10", "--total", "10", "--tokens", "1500")
        out = self.lp("canary", "compare", "--name", "core", check=5).stdout
        self.assertIn("token", out.lower())
        self.assertIn("core", self.lp("canary", "list").stdout)

    def test_pending_manifest_in_report(self):
        self.lp("init")
        self.lp("pending", "add", "--intent", "weekly revenue", "--score", "8.5", "--n-star", "11.1",
                "--tests", "pytest tests/wr -q", "--result", "pass", "--location", "branch:night/weekly-revenue",
                "--generated-by", "night-agent", "--writes-state")
        m = self.read_json(".livepowers/pending/weekly_revenue/manifest.json")
        self.assertEqual(m["intent"], "weekly revenue")
        self.assertEqual(m["generated_by"], "night-agent")
        self.assertIn("weekly revenue", self.lp("pending", "list").stdout)
        path = self.lp("report").stdout.strip()
        with open(os.path.join(self.dir, path), encoding="utf-8") as f:
            text = f.read()
        for s_ in ("weekly revenue", "8.5", "11.1", "pass", "night-agent", "写操作", "branch:night/weekly-revenue"):
            self.assertIn(s_, text)
        self.lp("pending", "add", "--intent", "weekly revenue", "--score", "1", "--n-star", "1", "--tests", "t",
                "--result", "fail", "--location", "x", "--generated-by", "g", check=1)  # 已存在
        self.lp("pending", "done", "weekly revenue", "--by", "owner", "--accepted")
        self.assertNotIn("weekly revenue", self.lp("pending", "list").stdout)

    # ---- hook 自动采集证据
    def hook(self, event, payload, check=0, env=None):
        e = {**os.environ, "LIVEPOWERS_HOME": ".livepowers", **(env or {})}
        p = subprocess.run([sys.executable, os.path.join(SCRIPTS, "lp.py"), "hook", event], cwd=self.dir,
                           input=json.dumps(payload), capture_output=True, text=True, env=e)
        self.assertEqual(p.returncode, check, p.stderr)
        return p

    def bash_event(self, command, stdout="", stderr="", exit_code=0, sid="s1"):
        return {"session_id": sid, "cwd": self.dir, "hook_event_name": "PostToolUse", "tool_name": "Bash",
                "tool_input": {"command": command},
                "tool_response": {"stdout": stdout, "stderr": stderr, "exit_code": exit_code}}

    def write_transcript(self, out_tokens=100, in_tokens=50):
        path = os.path.join(self.dir, "transcript.jsonl")
        lines = [{"type": "user", "message": {"role": "user", "content": "帮我看周收入"}, "timestamp": "2026-10-07T10:00:00Z"},
                 {"type": "assistant", "message": {"role": "assistant", "usage": {"input_tokens": in_tokens, "output_tokens": out_tokens,
                  "cache_read_input_tokens": 999}}, "timestamp": "2026-10-07T10:00:05Z"},
                 {"type": "assistant", "message": {"role": "assistant", "usage": {"input_tokens": 1, "output_tokens": 1}},
                  "timestamp": "2026-10-07T10:00:09Z"}]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(json.dumps(x) for x in lines) + "\n")
        return path

    def evidence(self):
        with open(os.path.join(self.dir, ".livepowers", "evidence.jsonl"), encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]

    def test_hook_captures_s1_call_and_s2_miss(self):
        self.lp("init")
        self.lp("registry", "add", "--name", "Weekly revenue", "--kind", "cli", "--intents", "weekly revenue",
                "--entry", "python w.py --region {region}")
        # HIT：记下命中的能力；随后调用 entry → 自动记 S1 证据
        self.hook("post-tool", self.bash_event('lp registry find "weekly revenue"',
                  stdout="HIT —— 命中已固化能力\n  [5] cap_weekly_revenue v1.0.0 (cli) entry: python w.py", exit_code=0))
        self.hook("post-tool", self.bash_event("python w.py --region east", stdout="ok"))
        ev = self.evidence()
        self.assertEqual(len(ev), 1)
        self.assertEqual((ev[0]["system"], ev[0]["outcome"], ev[0]["capability"], ev[0]["auto"]),
                         ("S1", "success", "cap_weekly_revenue", True))
        caps = self.read_json(".livepowers/registry.json")["capabilities"]
        self.assertEqual(caps[0]["calls"], 1)
        # entry 调用报错 → fail
        self.hook("post-tool", self.bash_event("python w.py --region west", stderr="Traceback", exit_code=1))
        self.assertEqual(self.evidence()[-1]["outcome"], "fail")
        # MISS 后 Agent 没记证据 → Stop 自动补记 S2 partial，token 来自 transcript
        self.hook("post-tool", self.bash_event('lp registry find "transfer stale"', stdout="MISS —— 未命中", exit_code=2))
        self.hook("stop", {"session_id": "s1", "cwd": self.dir, "transcript_path": self.write_transcript(),
                           "hook_event_name": "Stop"})
        last = self.evidence()[-1]
        self.assertEqual((last["intent"], last["system"], last["outcome"], last["auto"]), ("transfer stale", "S2", "partial", True))
        self.assertEqual(last["tokens"], 152)
        self.assertIn("auto", last["note"])
        n = len(self.evidence())
        # 同一会话再次 Stop 不重复补记
        self.hook("stop", {"session_id": "s1", "cwd": self.dir, "transcript_path": self.write_transcript()})
        self.assertEqual(len(self.evidence()), n)
        # MISS 后 Agent 自己记了证据 → Stop 不补记
        self.hook("post-tool", self.bash_event('lp registry find "another thing"', stdout="MISS", exit_code=2))
        self.hook("post-tool", self.bash_event('lp evidence add --intent "another thing" --system S2 --outcome success', stdout="ev_x"))
        self.hook("stop", {"session_id": "s1", "cwd": self.dir, "transcript_path": self.write_transcript()})
        self.assertEqual(len(self.evidence()), n)
        # 晨报与 stats 标出自动补记
        self.assertIn("自动补记", self.lp("evidence", "stats").stdout)
        path = self.lp("report").stdout.strip()
        with open(os.path.join(self.dir, path), encoding="utf-8") as f:
            self.assertIn("自动采集", f.read())

    def test_hook_is_harmless(self):
        # 未 init 的项目：不创建任何文件；坏输入：仍 exit 0
        self.hook("post-tool", self.bash_event('lp registry find "x"', stdout="MISS", exit_code=2))
        self.assertFalse(os.path.exists(os.path.join(self.dir, ".livepowers")))
        p = subprocess.run([sys.executable, os.path.join(SCRIPTS, "lp.py"), "hook", "stop"], cwd=self.dir,
                           input="not json", capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        self.lp("init")
        self.hook("post-tool", self.bash_event('lp registry find "x"', stdout="MISS", exit_code=2), env={"LP_HOOK_CAPTURE": "0"})
        self.hook("stop", {"session_id": "s1", "cwd": self.dir}, env={"LP_HOOK_CAPTURE": "0"})
        self.assertEqual(self.evidence(), [])

    def test_confidence_shown_and_reviewed(self):
        self.lp("init")
        self.lp("registry", "add", "--name", "Flaky", "--id", "cap_f", "--kind", "cli", "--intents", "flaky thing", "--entry", "f")
        for o in ("fail", "success", "fail"):
            self.lp("evidence", "add", "--intent", "flaky thing", "--system", "S1", "--outcome", o, "--capability", "cap_f")
        self.assertIn("置信度=0.40", self.lp("registry", "list").stdout)
        self.assertIn("置信度", self.lp("registry", "find", "flaky thing").stdout)
        self.assertIn("置信度 0.40", self.lp("registry", "review").stdout)

    def test_intents_alias_merges_evidence_and_routing(self):
        self.lp("init")
        self.lp("registry", "add", "--name", "Weekly revenue", "--kind", "sql", "--intents", "weekly revenue by region",
                "--entry", "w.sql")
        self.lp("registry", "find", "按区域的每周营收", check=2)                      # 别名登记前 MISS
        self.lp("evidence", "add", "--intent", "按区域的每周营收", "--system", "S2", "--outcome", "success")
        self.lp("evidence", "add", "--intent", "各地区周收入", "--system", "S2", "--outcome", "success")
        self.lp("intents", "alias", "weekly revenue by region", "按区域的每周营收", "--by", "ops")
        self.lp("intents", "alias", "weekly revenue by region", "各地区周收入")
        self.lp("intents", "alias", "按区域的每周营收", "x", check=1)               # 别名不能再当规范名
        out = self.lp("intents", "list").stdout
        self.assertIn("weekly revenue by region", out)
        self.assertIn("按区域的每周营收", out)
        self.assertIn("证据 2", out)
        # 路由：别名命中整组同义词
        self.assertIn("HIT", self.lp("registry", "find", "按区域的每周营收").stdout)
        self.assertIn("HIT", self.lp("registry", "find", "各地区周收入怎么样").stdout)
        # 新证据：别名落盘为规范名，原话保留
        self.lp("evidence", "add", "--intent", "各地区周收入", "--system", "S2", "--outcome", "success", "--verifiable")
        last = self.evidence()[-1]
        self.assertEqual((last["intent"], last["intent_raw"]), ("weekly revenue by region", "各地区周收入"))
        # 旧记录读取时归并：stats 与 candidates 按规范名
        stats = self.lp("evidence", "stats").stdout
        self.assertIn("weekly revenue by region", stats)
        self.assertNotIn("按区域的每周营收", stats.split("总计")[0])
        self.assertRegex(stats, r"weekly revenue by region\s+3\b")                 # 2 条旧别名记录 + 1 条新记录
        self.assertEqual(json.loads(self.lp("candidates", "--json").stdout), [])  # 已固化的意图不再是候选
        # task / pending 也规范化
        t = self.lp("task", "new", "--title", "t", "--intent", "各地区周收入").stdout.strip()
        self.assertEqual(self.read_json(".livepowers/tasks.json")["tasks"][0]["intent"], "weekly revenue by region")
        self.lp("pending", "add", "--intent", "各地区周收入", "--score", "8", "--n-star", "5", "--tests", "t",
                "--result", "pass", "--location", "l", "--generated-by", "g")
        self.assertIn("weekly revenue by region", self.lp("pending", "list").stdout)

    def test_intents_suggest(self):
        self.lp("init")
        for i in ("weekly revenue by region", "weekly revenue per region", "逾期商机移交", "转交逾期商机", "客户流失预警"):
            self.lp("evidence", "add", "--intent", i, "--system", "S2", "--outcome", "success")
        out = self.lp("intents", "suggest").stdout
        self.assertIn("weekly revenue by region", out)
        self.assertIn("weekly revenue per region", out)
        self.assertIn("逾期商机移交", out)
        self.assertNotIn("客户流失预警", out)
        self.assertIn("lp intents alias", out)

    def test_outcome_ledger(self):
        self.lp("init")
        self.lp("outcome", "measure", "--scenario", "s", "--metric", "m", "--value", "1", check=1)  # 无基线
        self.lp("outcome", "baseline", "--scenario", "s", "--metric", "m", "--value", "100", "--base", "1000000")
        self.lp("outcome", "cost", "--scenario", "s", "--kind", "human", "--amount", "300")
        self.lp("outcome", "cost", "--scenario", "s", "--kind", "rework", "--amount", "100")
        self.lp("evidence", "add", "--intent", "i", "--system", "S2", "--outcome", "fail", "--cost", "100",
                "--note", "scenario=s")
        self.lp("outcome", "accept", "--scenario", "s", "--by", "owner", "--first")
        self.lp("outcome", "accept", "--scenario", "s", "--by", "owner")
        self.lp("outcome", "accept", "--scenario", "s", "--by", "owner", "--rejected")
        self.lp("outcome", "measure", "--scenario", "s", "--metric", "m", "--value", "105")
        out = self.lp("outcome", "report").stdout
        self.assertIn("验收任务平均成本 = 250.00", out)      # (300+100+100)/2，失败成本也计入
        self.assertIn("ΔV = B×u = 1,000,000×0.0500 = 50,000.00", out)
        self.assertIn("首次价值交付时间", out)

    def test_outcome_naive_confirmed_at(self):
        self.lp("init")
        self.lp("outcome", "baseline", "--scenario", "s", "--metric", "m", "--value", "1",
                "--confirmed-at", "2026-01-01")
        self.lp("outcome", "baseline", "--scenario", "s", "--metric", "n", "--value", "1",
                "--confirmed-at", "not-a-date", check=1)
        self.lp("outcome", "accept", "--scenario", "s", "--by", "o", "--first")
        self.assertIn("首次价值交付时间", self.lp("outcome", "report").stdout)
        self.lp("report")

    def test_asset_gates(self):
        self.lp("init")
        self.lp("asset", "add", "--name", "Skill A", "--id", "a1")
        self.lp("asset", "add", "--name", "Client data", "--id", "c1", "--ownership", "client")
        self.lp("asset", "add", "--name", "Skill B", "--id", "b1")
        self.lp("asset", "gate", "a1", "evaluated", "--by", "r", check=1)  # 须依次通过
        for g in ("abstractable", "versioned", "evaluated", "reusable"):
            self.lp("asset", "gate", "a1", g, "--by", "r")
        self.lp("asset", "gate", "c1", "abstractable", "--by", "r", check=1)
        self.lp("asset", "reuse", "b1", "--project", "p2", check=1)
        self.lp("asset", "reuse", "a1", "--project", "p2", "--verified")
        self.assertIn("1/3 = 33%", self.lp("asset", "list").stdout)

    def test_job_validate(self):
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.lp("job", "validate", os.path.join(repo, "templates", "job-contract.json"))
        bad = {"model_horizon_minutes": {"small": 30}, "jobs": [
            {"job_id": "a", "dependency": ["b"], "model_capability": "small", "expected_minutes": 90,
             "handoff": {"actual_end_state": "x"}},
            {"job_id": "b", "dependency": ["a"]}]}
        p = os.path.join(self.dir, "bad.json")
        with open(p, "w") as f:
            json.dump(bad, f)
        out = self.lp("job", "validate", p, check=1).stdout
        self.assertIn("可稳定时长", out)
        self.assertIn("checker", out)
        self.assertIn("不是 DAG", out)
        # 校验 spec 文件及任务 ID 存在性
        spec_file = os.path.join(self.dir, "spec1.md")
        with open(spec_file, "w", encoding="utf-8") as f:
            f.write("# Spec\n\n## 任务清单\n- T001 [P] 数据库建表\n")
        good_job = {"jobs": [{"job_id": "j1", "tenant": "t", "stage_id": "s", "dependency": [], "priority": 1,
                              "deadline": "08:00", "model_capability": "m", "resources": {}, "max_cost": 10,
                              "retry_limit": 1, "stop_condition": "stop", "checkpoint": "c", "preemptible": True,
                              "resume_policy": "r", "data_classification": "d", "acceptance": "a",
                              "handoff": {"actual_end_state": "x", "checker": "c"}, "expected_minutes": 10,
                              "spec": spec_file, "spec_task": "T001"}]}
        gp = os.path.join(self.dir, "good.json")
        with open(gp, "w") as f:
            json.dump(good_job, f)
        self.lp("job", "validate", gp, check=0)

        # 任务 ID 不存在
        bad_task_job = dict(good_job)
        bad_task_job["jobs"] = [dict(good_job["jobs"][0], spec_task="T999")]
        bp = os.path.join(self.dir, "bad_task.json")
        with open(bp, "w") as f:
            json.dump(bad_task_job, f)
        out_bad = self.lp("job", "validate", bp, check=1).stdout
        self.assertIn("未找到任务 ID：T999", out_bad)


    def test_spec_task_declarations_reject_prose_and_duplicates(self):
        path = os.path.join(self.dir, "spec.md")
        with open(path, "w") as f:
            f.write("# Spec\nT009 已删除\n## 任务清单\n- T002 active\n## Notes\n- T009 prose\n")
        self.assertEqual(lp.spec_task_ids(path), {"T002"})
        self.lp("task", "new", "--title", "test", "--spec", path, "--spec-task", "T009", check=1)
        with open(path, "w") as f:
            f.write("## 任务清单\n- T002 first\n- T002 duplicate\n")
        with self.assertRaises(ValueError):
            lp.spec_task_ids(path)

    def test_report(self):
        self.lp("init")
        self.lp("evidence", "add", "--intent", "x", "--system", "S2", "--outcome", "success")
        path = self.lp("report").stdout.strip()
        with open(os.path.join(self.dir, path), encoding="utf-8") as f:
            text = f.read()
        for h in ("固化候选", "能力复核", "任务看板", "结果台账", "需要人决定的事"):
            self.assertIn(h, text)


if __name__ == "__main__":
    unittest.main()
