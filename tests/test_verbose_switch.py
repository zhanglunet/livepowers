"""PRD-046/T3：简洁输出开关（LIVEPOWERS_VERBOSE / config.yaml）的回归测试。

约定：
- 存量测试（tests/helpers.py）默认跑 LIVEPOWERS_VERBOSE=1，锁定"全量输出与改造前逐字节一致"。
- 本文件覆盖简洁模式（verbose=False）与开关本身的行为。
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from helpers import SCRIPTS, Workdir  # noqa: E402

sys.path.insert(0, SCRIPTS)
import lp_output  # noqa: E402


class TestSwitch(Workdir):
    def test_env_flag_on(self):
        env = {**os.environ, "LIVEPOWERS_VERBOSE": "1"}
        self.assertTrue(_is_verbose_in(self.dir, env))

    def test_env_flag_off_by_default(self):
        env = {k: v for k, v in os.environ.items() if k != "LIVEPOWERS_VERBOSE"}
        self.assertFalse(_is_verbose_in(self.dir, env))

    def test_env_empty_string_is_not_verbose(self):
        env = {**os.environ, "LIVEPOWERS_VERBOSE": ""}
        self.assertFalse(_is_verbose_in(self.dir, env))

    def test_config_file_enables_verbose(self):
        os.makedirs(os.path.join(self.dir, ".livepowers"), exist_ok=True)
        with open(os.path.join(self.dir, ".livepowers", "config.yaml"), "w", encoding="utf-8") as f:
            f.write("# livepowers 配置\nverbose: true\n")
        env = {k: v for k, v in os.environ.items() if k != "LIVEPOWERS_VERBOSE"}
        env["LIVEPOWERS_HOME"] = ".livepowers"
        self.assertTrue(_is_verbose_in(self.dir, env))

    def test_config_file_false_stays_concise(self):
        os.makedirs(os.path.join(self.dir, ".livepowers"), exist_ok=True)
        with open(os.path.join(self.dir, ".livepowers", "config.yaml"), "w", encoding="utf-8") as f:
            f.write("verbose: false\n")
        env = {k: v for k, v in os.environ.items() if k != "LIVEPOWERS_VERBOSE"}
        env["LIVEPOWERS_HOME"] = ".livepowers"
        self.assertFalse(_is_verbose_in(self.dir, env))

    def test_fold_hint_names_the_switch(self):
        lines = lp_output.fold(["a", "b", "c"], 2)
        self.assertEqual(len(lines), 3)
        self.assertIn("LIVEPOWERS_VERBOSE=1", lines[2])


def _is_verbose_in(workdir, env):
    """在子进程里求 is_verbose()（隔离环境变量）。"""
    import subprocess
    code = ("import os, sys; sys.path.insert(0, %r); "
            "import lp_output; print(lp_output.is_verbose())" % SCRIPTS)
    p = subprocess.run([sys.executable, "-c", code], cwd=workdir,
                       capture_output=True, text=True,
                       env={**env, "LIVEPOWERS_HOME": ".livepowers"})
    assert p.returncode == 0, p.stderr
    return p.stdout.strip() == "True"


class TestConciseCommands(Workdir):
    def setUp(self):
        super().setUp()
        self.lp("init")
        for i in range(6):
            self.lp("registry", "add", "--name", f"Cap{i}", "--id", f"cap_{i}",
                    "--kind", "cli", "--intents", f"意图{i}", "--entry", "run")

    def test_find_hit_keeps_marker_and_folds(self):
        out = self.lp("registry", "find", "意图", "--top", "10", verbose=False).stdout
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith("HIT"), lines[0])
        self.assertIn("…共 6 个候选，已折叠", out)
        vout = self.lp("registry", "find", "意图", "--top", "10", verbose=True).stdout
        self.assertNotIn("已折叠", vout)
        self.assertIn("entry: run", vout)  # 全量保留详情

    def test_find_miss_keeps_exit_code(self):
        p = self.lp("registry", "find", "火星殖民计划abc123", check=2, verbose=False)
        self.assertTrue(p.stdout.splitlines()[0].startswith("MISS"))
        p2 = self.lp("registry", "find", "火星殖民计划abc123", check=2, verbose=True)
        self.assertEqual(p.stdout, p2.stdout)

    def test_review_conclusion_first_and_folds(self):
        for i in range(6):
            for _ in range(2):
                self.lp("evidence", "add", "--intent", f"意图{i}", "--system", "S1",
                        "--outcome", "fail", "--capability", f"cap_{i}")
        out = self.lp("registry", "review", verbose=False).stdout
        self.assertTrue(out.splitlines()[0].startswith("复核完成：6 项待处理"), out)
        self.assertIn("已折叠", out)
        vout = self.lp("registry", "review", verbose=True).stdout
        self.assertTrue(vout.startswith("复核发现："), vout)
        self.assertNotIn("已折叠", vout)

    def test_review_empty_conclusion(self):
        out = self.lp("registry", "review", verbose=False).stdout
        self.assertEqual(out.strip(), "复核完成：无待处理项")
        vout = self.lp("registry", "review", verbose=True).stdout
        self.assertEqual(vout.strip(), "复核：无待处理项。")

    def test_score_conclusion_first_and_exit_codes(self):
        p = self.lp("score", "--freq", "30", "--verifiable", "2", "--stability", "2",
                    "--c2", "1", "--K", "10", check=0, verbose=False)
        self.assertTrue(p.stdout.startswith("建议固化："), p.stdout)
        p2 = self.lp("score", "--freq", "30", "--verifiable", "0", "--stability", "2",
                     "--c2", "1", "--K", "10", check=3, verbose=False)
        self.assertTrue(p2.stdout.startswith("建议保持 System 2：V=0 一票否决"), p2.stdout)

    def test_candidates_json_byte_identical(self):
        for _ in range(4):
            self.lp("evidence", "add", "--intent", "candX", "--system", "S2",
                    "--outcome", "success", "--verifiable")
        a = self.lp("candidates", "--json", verbose=False).stdout
        b = self.lp("candidates", "--json", verbose=True).stdout
        self.assertEqual(a, b)
        self.assertTrue(json.loads(a))

    def test_candidates_list_folds(self):
        for j in range(7):
            for _ in range(4):
                self.lp("evidence", "add", "--intent", f"cand{j}", "--system", "S2",
                        "--outcome", "success", "--verifiable")
        out = self.lp("candidates", verbose=False).stdout
        self.assertIn("…共 7 条，已折叠", out)
        vout = self.lp("candidates", verbose=True).stdout
        self.assertNotIn("已折叠", vout)

    def test_evidence_stats_conclusion_first(self):
        for i in range(5):
            self.lp("evidence", "add", "--intent", f"意图{i}", "--system", "S2",
                    "--outcome", "success")
        out = self.lp("evidence", "stats", verbose=False).stdout
        self.assertTrue(out.splitlines()[0].startswith("共 "), out)
        self.assertIn("S2 占比", out.splitlines()[0])

    def test_intents_list_folds(self):
        for i in range(25):
            self.lp("intents", "alias", f"a{i:02d}", f"别名{i:02d}")
        out = self.lp("intents", "list", verbose=False).stdout
        self.assertIn("已折叠", out)
        vout = self.lp("intents", "list", verbose=True).stdout
        self.assertNotIn("已折叠", vout)
        self.assertEqual(len(vout.splitlines()), 25)

    def test_report_file_gets_summary_section(self):
        p = self.lp("report", verbose=False)
        path = p.stdout.strip()
        with open(os.path.join(self.dir, path), encoding="utf-8") as f:
            body = f.read()
        self.assertIn("## 结论摘要", body)
        # 既有章节不动
        self.assertIn("## 待人工验收的固化产物", body)
        self.assertIn("## 自动采集待确认", body)

    def test_report_file_verbose_has_no_summary(self):
        p = self.lp("report", verbose=True)
        path = p.stdout.strip()
        with open(os.path.join(self.dir, path), encoding="utf-8") as f:
            body = f.read()
        self.assertNotIn("## 结论摘要", body)

    def test_outcome_report_conclusion(self):
        self.lp("outcome", "baseline", "--scenario", "s", "--metric", "m",
                "--value", "100", "--base", "1000", "--owner", "o")
        self.lp("outcome", "measure", "--scenario", "s", "--metric", "m", "--value", "120")
        out = self.lp("outcome", "report", verbose=False).stdout
        self.assertIn("场景 s：ΔV=", out)
        self.assertIn("…完整台账已折叠", out)


class TestSwitchScripts(Workdir):
    def test_scan_diff_piped_keeps_yaml_in_both_modes(self):
        import sqlite3
        db = os.path.join(self.dir, "t.db")
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        con.commit()
        con.close()
        a = self.run_script("scan_sqlite.py", "t.db", verbose=False).stdout
        b = self.run_script("scan_sqlite.py", "t.db", verbose=True).stdout
        self.assertEqual(a, b)  # 管道（非 tty）时两边都是 YAML 原文
        self.assertIn("objects:", a)

    def test_scan_diff_folds_and_keeps_exit_code(self):
        fp1 = {"tables": {"t": {"columns": {"a": {"type": "INT"}}}}}
        fp2 = {"tables": {"t": {"columns": {f"c{i}": {"type": "TEXT"} for i in range(8)}}}}
        with open(os.path.join(self.dir, "f1.json"), "w") as f:
            json.dump(fp1, f)
        with open(os.path.join(self.dir, "f2.json"), "w") as f:
            json.dump(fp2, f)
        p = self.run_script("scan_sqlite.py", "--diff", "f1.json", "f2.json",
                            check=5, verbose=False)
        self.assertTrue(p.stdout.splitlines()[0].startswith("环境漂移："))
        self.assertIn("已折叠", p.stdout)
        q = self.run_script("scan_sqlite.py", "--diff", "f1.json", "f2.json",
                            check=5, verbose=True)
        self.assertNotIn("已折叠", q.stdout)
        r = self.run_script("scan_sqlite.py", "--diff", "f1.json", "f1.json",
                            check=0, verbose=False)
        self.assertEqual(r.stdout.strip(), "无漂移")

    def test_audit_conclusion_first(self):
        self._seed_comms(25)
        out = self.run_script("agent_switch.py", "audit", "--log", "comms.jsonl",
                              verbose=False).stdout
        self.assertTrue(out.splitlines()[0].startswith("审计完成："), out)
        vout = self.run_script("agent_switch.py", "audit", "--log", "comms.jsonl",
                               verbose=True).stdout
        self.assertTrue(vout.splitlines()[0].startswith("消息 "), vout)

    def test_replay_conclusion_and_head_tail(self):
        self._seed_comms(25)
        out = self.run_script("agent_switch.py", "replay", "--log", "comms.jsonl",
                              verbose=False).stdout
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith("回放 25 条消息"), lines[0])
        self.assertIn("…共 25 条，已折叠", out)

    def test_verify_output_untouched(self):
        self._seed_comms(5)
        a = self.run_script("agent_switch.py", "verify", "--log", "comms.jsonl",
                            verbose=False).stdout
        b = self.run_script("agent_switch.py", "verify", "--log", "comms.jsonl",
                            verbose=True).stdout
        self.assertEqual(a, b)
        self.assertIn("哈希链完整", a)

    def _seed_comms(self, n):
        import hashlib
        prev = "0" * 64
        with open(os.path.join(self.dir, "comms.jsonl"), "w", encoding="utf-8") as f:
            for i in range(1, n + 1):
                rec = {"seq": i, "ts": f"2026-10-18T10:{i:02d}:00+08:00",
                       "trace_id": "tr0", "task_id": "t", "contract_version": "1",
                       "from": "a", "to": "b",
                       "type": "result" if i % 2 else "task",
                       "body": f"m{i}", "ref": "",
                       "policy": {"decision": "deny" if i == 3 else "allow", "reason": ""},
                       "prev_hash": prev}
                payload = json.dumps({k: rec[k] for k in sorted(rec) if k != "hash"},
                                     ensure_ascii=False, sort_keys=True)
                rec["hash"] = hashlib.sha256(payload.encode()).hexdigest()
                prev = rec["hash"]
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    unittest.main()
