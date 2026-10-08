import json
import os
import socket
import subprocess
import sys
import time
import unittest
from urllib import request

sys.path.insert(0, os.path.dirname(__file__))
from helpers import REPO, SCRIPTS, Workdir  # noqa: E402

EXAMPLES = os.path.join(REPO, "examples")


class TestScan(Workdir):
    def test_scan_sql_identifier_quoting_and_mysql_auth(self):
        sys.path.insert(0, SCRIPTS)
        import scan_sql
        self.assertEqual(scan_sql.quote_identifier('order`items', 'mysql'), '`order``items`')
        self.assertEqual(scan_sql.quote_identifier('order"items', 'postgres'), '"order""items"')

        calls = []
        def fake_run(cmd, **kwargs):
            calls.append((cmd, kwargs))
            return subprocess.CompletedProcess(cmd, 0, stdout='value\n1\n', stderr='')
        old_which, old_run = scan_sql.shutil.which, scan_sql.subprocess.run
        try:
            scan_sql.shutil.which = lambda name: '/usr/bin/mysql' if name == 'mysql' else None
            scan_sql.subprocess.run = fake_run
            info = scan_sql.parse_dsn('mysql://user:secret@localhost/db')
            self.assertEqual(scan_sql.run_query(info, 'SELECT 1'), (['value'], [['1']]))
            cmd, kwargs = calls[-1]
            self.assertFalse(any(arg == '-p' or arg.startswith('-p') for arg in cmd))
            self.assertNotIn('secret', cmd)
            self.assertEqual(kwargs['env']['MYSQL_PWD'], 'secret')

            calls.clear()
            info = scan_sql.parse_dsn('mysql://user@localhost/db')
            scan_sql.run_query(info, 'SELECT 1')
            cmd, kwargs = calls[-1]
            self.assertFalse(any(arg == '-p' or arg.startswith('-p') for arg in cmd))
            self.assertEqual(kwargs['env']['MYSQL_PWD'], '')
            self.assertIn('--connect-timeout=10', cmd)
        finally:
            scan_sql.shutil.which, scan_sql.subprocess.run = old_which, old_run

    def test_scan_sql_postgres_composite_foreign_key_pairing(self):
        sys.path.insert(0, SCRIPTS)
        import scan_sql
        observed_fk_sql = []
        def executor(info, sql, params=None):
            clean = ' '.join(sql.split())
            if 'information_schema.tables' in clean:
                return ['table_name'], [['parents'], ['children']]
            if 'information_schema.columns' in clean:
                return [], [
                    ['parents', 'a', 'integer', 'NO', 1], ['parents', 'b', 'integer', 'NO', 1],
                    ['children', 'a', 'integer', 'NO', 0], ['children', 'b', 'integer', 'NO', 0],
                ]
            if 'information_schema.constraint_column_usage' in clean:
                observed_fk_sql.append(clean)
                # Simulate the rows after ordinal pairing; the old unconstrained join produces 4.
                return [], [['children', 'a', 'parents', 'b'], ['children', 'b', 'parents', 'a']]
            if 'count(*)' in clean:
                return [], [['0']]
            return [], []
        fp = scan_sql.scan('postgres://user@localhost/db', query_executor=executor)
        self.assertEqual(fp['tables']['children']['fks'], [['a', 'parents', 'b'], ['b', 'parents', 'a']])
        self.assertIn('position_in_unique_constraint', observed_fk_sql[0])
        self.assertIn('ordinal_position', observed_fk_sql[0])

    def test_draft_fingerprint_and_drift(self):
        db = os.path.join(self.dir, "d.sqlite")
        subprocess.run([sys.executable, os.path.join(EXAMPLES, "make_demo_db.py"), db], check=True, capture_output=True)
        out = self.run_script("scan_sqlite.py", db, "--fingerprint", "fp1.json", check=0).stdout
        self.assertIn("evidence: name_inferred", out)          # owner_id → owners
        self.assertIn("evidence: foreign_key", out)            # customer_id
        self.assertIn("敏感字段", out)                          # phone 不抽样
        self.assertNotIn("000-0000", out)
        fp = self.read_json("fp1.json")
        self.assertIn("lead", fp["tables"]["opportunities"]["columns"]["stage"]["status_values"])
        self.assertEqual(self.run_script("scan_sqlite.py", "--diff", "fp1.json", "fp1.json", check=0).stdout.strip(), "无漂移")
        subprocess.run([sys.executable, os.path.join(EXAMPLES, "make_demo_db.py"), db, "--drift"], check=True,
                       capture_output=True)
        self.run_script("scan_sqlite.py", db, "--fingerprint", "fp2.json", check=0)
        out = self.run_script("scan_sqlite.py", "--diff", "fp1.json", "fp2.json", check=5).stdout
        self.assertIn("新增列 industry", out)
        self.assertIn("on_hold", out)

    def test_scan_sql_mock_and_diff(self):
        # 验证 scan_sql.py 的数据解析、指纹生成同构性与跨脚本 --diff
        sys.path.insert(0, SCRIPTS)
        import scan_sql

        def mock_executor(dsn_info, sql, params=None):
            sql_clean = " ".join(sql.strip().split())
            if "information_schema.tables" in sql_clean:
                return ["table_name"], [["customers"], ["orders"]]
            if "information_schema.columns" in sql_clean:
                # 返回 (table_name, column_name, data_type, is_nullable, is_pk)
                rows = [
                    ["customers", "id", "integer", "NO", "1"],
                    ["customers", "name", "varchar", "YES", "0"],
                    ["customers", "phone", "varchar", "YES", "0"],
                    ["orders", "id", "integer", "NO", "1"],
                    ["orders", "customer_id", "integer", "NO", "0"],
                    ["orders", "status", "varchar", "NO", "0"],
                    ["orders", "created_at", "timestamp", "NO", "0"],
                ]
                return ["table_name", "column_name", "data_type", "is_nullable", "is_pk"], rows
            if "information_schema.key_column_usage" in sql_clean or "constraint_column_usage" in sql_clean:
                # 返回 (table_name, column_name, foreign_table_name, foreign_column_name)
                rows = [
                    ["orders", "customer_id", "customers", "id"]
                ]
                return ["table_name", "column_name", "foreign_table_name", "foreign_column_name"], rows
            if "count(*)" in sql_clean.lower():
                return ["count"], [["10"]]
            if "select distinct" in sql_clean.lower():
                return ["status"], [["pending"], ["completed"]]
            return [], []

        fp = scan_sql.scan("postgres://user:pass@localhost:5432/mydb", sample=20, query_executor=mock_executor)
        self.assertEqual(fp["source"], "postgres:mydb")
        self.assertIn("customers", fp["tables"])
        self.assertIn("orders", fp["tables"])
        self.assertTrue(fp["tables"]["customers"]["columns"]["phone"].get("sensitive"))
        self.assertEqual(fp["tables"]["orders"]["columns"]["status"]["status_values"], ["completed", "pending"])
        self.assertTrue(fp["tables"]["orders"]["columns"]["created_at"].get("time"))
        self.assertEqual(fp["tables"]["orders"]["fks"], [["customer_id", "customers", "id"]])

        # 检查 YAML 输出结构
        yaml_out = scan_sql.to_yaml(fp)
        self.assertIn("ontology_version: 0.1.0-draft", yaml_out)
        self.assertIn("evidence: foreign_key", yaml_out)
        self.assertIn("敏感字段", yaml_out)

        # 校验跨指纹 diff 与 scan_sqlite.py 完全一致
        fp_file1 = os.path.join(self.dir, "sql_fp1.json")
        fp_file2 = os.path.join(self.dir, "sql_fp2.json")
        with open(fp_file1, "w", encoding="utf-8") as f:
            json.dump(fp, f)

        # 模拟漂移
        fp2 = json.loads(json.dumps(fp))
        fp2["tables"]["orders"]["columns"]["status"]["status_values"].append("cancelled")
        with open(fp_file2, "w", encoding="utf-8") as f:
            json.dump(fp2, f)

        # 用 scan_sql 比对
        out_diff = self.run_script("scan_sql.py", "--diff", fp_file1, fp_file2, check=5).stdout
        self.assertIn("cancelled", out_diff)
        # 用 scan_sqlite 也能跨脚本解析比对
        out_diff2 = self.run_script("scan_sqlite.py", "--diff", fp_file1, fp_file2, check=5).stdout
        self.assertIn("cancelled", out_diff2)



def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class TestSwitch(Workdir):
    def test_relay_policy_replay_verify_audit(self):
        port = free_port()
        log = os.path.join(self.dir, "comms.jsonl")
        srv = subprocess.Popen([sys.executable, os.path.join(SCRIPTS, "agent_switch.py"), "serve", "--port", str(port),
                                "--log", log], cwd=self.dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            url = f"http://127.0.0.1:{port}"
            for _ in range(50):
                try:
                    with request.urlopen(url + "/health"):
                        break
                except OSError:
                    time.sleep(0.1)
            sw = lambda *a, check=0: self.run_script("agent_switch.py", *a, check=check)
            sw("send", "--from", "sup", "--to", "exe", "--type", "task", "--body", "do #12", "--trace", "t1",
               "--task", "t_1", "--contract", "c@1", "--url", url)
            sw("send", "--from", "exe", "--to", "rev", "--type", "gossip", "--body", "psst", "--trace", "t1",
               "--url", url, check=1)
            sw("send", "--from", "exe", "--to", "rev", "--type", "result", "--body", "x" * 5000, "--trace", "t1",
               "--url", url, check=1)
            sw("send", "--from", "exe", "--to", "rev", "--type", "result", "--body", "done", "--trace", "t1",
               "--url", url)
            with request.urlopen(url + "/inbox/exe") as resp:
                inbox = json.loads(resp.read())
            self.assertEqual(inbox[0]["task_id"], "t_1")
        finally:
            srv.terminate()
            srv.wait()
        sw = lambda *a, check=0: self.run_script("agent_switch.py", *a, check=check)
        sw("sidecar-log", "--log", log, "--from", "rev", "--to", "sup", "--type", "review", "--body", "LGTM",
           "--trace", "t1", "--ref", "git:abc")
        rep = sw("replay", "--log", log, "--trace", "t1").stdout
        self.assertIn("unknown type gossip", rep)
        self.assertIn("body too large", rep)
        sw("verify", "--log", log)
        audit = sw("audit", "--log", log).stdout
        self.assertIn("被拒绝 2 条", audit)
        self.assertIn("无产物引用 1 条", audit)
        with open(log, encoding="utf-8") as f:
            lines = f.read().splitlines()
        rec = json.loads(lines[0])
        rec["body"] = "tampered"
        lines[0] = json.dumps(rec, ensure_ascii=False)
        with open(log, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        self.assertIn("哈希链断裂", sw("verify", "--log", log, check=1).stdout)


if __name__ == "__main__":
    unittest.main()
