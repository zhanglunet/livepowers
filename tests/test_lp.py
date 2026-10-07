import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from helpers import Workdir  # noqa: E402

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
