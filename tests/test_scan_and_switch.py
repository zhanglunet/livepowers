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
