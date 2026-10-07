#!/usr/bin/env python3
"""
agent_switch —— 最小可用的「智能体交换机」：所有 Agent 间消息经此中转，
落盘为 append-only JSONL（带哈希链，防篡改），并支持回放。

用法：
  python agent_switch.py serve --port 7070 --log .livepowers/comms.jsonl
      启动 HTTP 交换机。Agent 通过 POST /send 发送、GET /inbox/<agent> 取消息。
  python agent_switch.py send --to reviewer --from executor --type result --body "MR !12 ready"
      （客户端示例）
  python agent_switch.py replay --log .livepowers/comms.jsonl [--speed 0]
      按时间顺序回放全部通信；--speed 1 为真实节奏，0 为立即输出。
  python agent_switch.py verify --log .livepowers/comms.jsonl
      校验哈希链完整性。
  python agent_switch.py sidecar-log --log ... --from a --to b --type ... --body ...
      旁路（Sidecar）模式：不经中转，仅由 Agent 框架插件在收发时调用落盘。

消息信封（envelope）：
  {seq, ts, trace_id, task_id, contract_version, from, to, type, body, ref, policy, prev_hash, hash}
  type ∈ {task, result, question, review, control, receipt}
  - 协调线走交换机：body 超过 SWITCH_MAX_BODY 字符（默认 4000）会被拒绝，大块内容请放共享工作空间，用 --ref 传引用。
  - result 类消息若声称完成，应附 --ref 指向真实回执或产物；智能体的自我声明只是待检查信息。
仅依赖标准库。
"""
import argparse, hashlib, json, os, sys, time, threading, uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import request as urlreq

TYPES = {"task", "result", "question", "review", "control", "receipt"}
MAX_BODY = int(os.environ.get("SWITCH_MAX_BODY", "4000"))
BLOCK_WORDS = [w for w in os.environ.get("SWITCH_BLOCK_WORDS", "").split(",") if w]
_lock = threading.Lock()


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


def last_hash_and_seq(path):
    if not os.path.exists(path):
        return "0" * 64, 0
    h, seq = "0" * 64, 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                h, seq = r["hash"], r["seq"]
    return h, seq


def append(path, env):
    with _lock:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        prev, seq = last_hash_and_seq(path)
        env["seq"] = seq + 1
        env["prev_hash"] = prev
        payload = json.dumps({k: env[k] for k in sorted(env) if k != "hash"}, ensure_ascii=False, sort_keys=True)
        env["hash"] = hashlib.sha256(payload.encode()).hexdigest()
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(env, ensure_ascii=False) + "\n")
    return env


def policy_check(env):
    if env.get("type") not in TYPES:
        return "deny", f"unknown type {env.get('type')}"
    body = str(env.get("body", ""))
    if len(body) > MAX_BODY:
        return "deny", f"body too large ({len(body)}>{MAX_BODY}); put content in shared workspace and send --ref"
    for w in BLOCK_WORDS:
        if w and w in body:
            return "deny", f"blocked word: {w}"
    return "allow", ""


def make_handler(log):
    inbox = defaultdict(deque)

    class H(BaseHTTPRequestHandler):
        def _json(self, code, obj):
            data = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

        def do_POST(self):
            if self.path != "/send":
                return self._json(404, {"error": "not found"})
            n = int(self.headers.get("Content-Length", 0))
            env = json.loads(self.rfile.read(n) or b"{}")
            env.setdefault("trace_id", uuid.uuid4().hex[:12])
            env["ts"] = now()
            decision, why = policy_check(env)
            env["policy"] = {"decision": decision, "reason": why}
            env = append(log, env)  # 被拒绝的消息同样落盘，便于审计
            if decision == "allow":
                inbox[env["to"]].append(env)
                return self._json(200, {"ok": True, "seq": env["seq"]})
            return self._json(403, {"ok": False, "reason": why, "seq": env["seq"]})

        def do_GET(self):
            if self.path.startswith("/inbox/"):
                who = self.path.split("/", 2)[2]
                msgs = []
                while inbox[who]:
                    msgs.append(inbox[who].popleft())
                return self._json(200, msgs)
            if self.path == "/health":
                return self._json(200, {"ok": True})
            return self._json(404, {"error": "not found"})

    return H


def cmd_serve(a):
    srv = ThreadingHTTPServer((a.host, a.port), make_handler(a.log))
    print(f"agent_switch 监听 http://{a.host}:{a.port}  日志 {a.log}")
    srv.serve_forever()


def cmd_send(a):
    env = {"from": a.sender, "to": a.to, "type": a.type, "body": a.body, "trace_id": a.trace or uuid.uuid4().hex[:12],
           "task_id": a.task, "contract_version": a.contract, "ref": a.ref}
    req = urlreq.Request(a.url.rstrip("/") + "/send", data=json.dumps(env, ensure_ascii=False).encode(),
                         headers={"Content-Type": "application/json"})
    try:
        print(urlreq.urlopen(req).read().decode())
    except Exception as e:
        print(f"发送失败: {e}", file=sys.stderr); sys.exit(1)


def cmd_sidecar(a):
    env = {"from": a.sender, "to": a.to, "type": a.type, "body": a.body,
           "trace_id": a.trace or uuid.uuid4().hex[:12], "task_id": a.task, "contract_version": a.contract,
           "ref": a.ref, "ts": now(), "mode": "sidecar"}
    decision, why = policy_check(env)
    env["policy"] = {"decision": decision, "reason": why}
    env = append(a.log, env)
    print(env["seq"])


def cmd_replay(a):
    prev_t = None
    for line in open(a.log, encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        if a.trace and r.get("trace_id") != a.trace:
            continue
        t = datetime.fromisoformat(r["ts"])
        if a.speed and prev_t:
            time.sleep(max(0, (t - prev_t).total_seconds() / a.speed))
        prev_t = t
        mark = "" if r["policy"]["decision"] == "allow" else f"  ⛔ {r['policy']['reason']}"
        ref = f"  ↗ {r['ref']}" if r.get("ref") else ""
        print(f"#{r['seq']:>4} {r['ts'][11:23]} [{r.get('trace_id')}] {r['from']} → {r['to']} ({r['type']}): {r['body']}{ref}{mark}")


def cmd_verify(a):
    prev = "0" * 64
    for i, line in enumerate(open(a.log, encoding="utf-8"), 1):
        if not line.strip():
            continue
        r = json.loads(line)
        payload = json.dumps({k: r[k] for k in sorted(r) if k != "hash"}, ensure_ascii=False, sort_keys=True)
        if r["prev_hash"] != prev or hashlib.sha256(payload.encode()).hexdigest() != r["hash"]:
            print(f"✗ 第 {i} 行哈希链断裂（seq={r.get('seq')}）——日志可能被篡改")
            sys.exit(1)
        prev = r["hash"]
    print("✓ 哈希链完整")


def cmd_audit(a):
    recs = [json.loads(l) for l in open(a.log, encoding="utf-8") if l.strip()]
    denied = [r for r in recs if r["policy"]["decision"] != "allow"]
    traces = {}
    for r in recs:
        traces.setdefault(r.get("trace_id"), []).append(r)
    open_traces = [t for t, rs in traces.items() if not any(x["type"] in ("review", "receipt") for x in rs)]
    no_ref = [r for r in recs if r["type"] == "result" and r["policy"]["decision"] == "allow" and not r.get("ref")]
    print(f"消息 {len(recs)} 条；trace {len(traces)} 个")
    print(f"被拒绝 {len(denied)} 条" + "".join(f"\n  - #{r['seq']} {r['from']}→{r['to']}: {r['policy']['reason']}" for r in denied))
    print(f"未见审查 / 回执的 trace {len(open_traces)} 个：{open_traces}")
    print(f"声称结果但无产物引用 {len(no_ref)} 条：{[r['seq'] for r in no_ref]}")
    agents = {}
    for r in recs:
        agents[r["from"]] = agents.get(r["from"], 0) + 1
    print("按 Agent 计消息数：" + ", ".join(f"{k}={v}" for k, v in sorted(agents.items())))


def main():
    p = argparse.ArgumentParser(prog="agent_switch")
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("serve"); s.add_argument("--host", default="127.0.0.1"); s.add_argument("--port", type=int, default=7070)
    s.add_argument("--log", default=".livepowers/comms.jsonl"); s.set_defaults(fn=cmd_serve)
    for name, fn in (("send", cmd_send), ("sidecar-log", cmd_sidecar)):
        c = sp.add_parser(name)
        c.add_argument("--from", dest="sender", required=True); c.add_argument("--to", required=True)
        c.add_argument("--type", required=True); c.add_argument("--body", required=True); c.add_argument("--trace")
        c.add_argument("--task", help="共享任务标识"); c.add_argument("--contract", help="契约版本")
        c.add_argument("--ref", help="内容线引用：产物 / 回执位置")
        c.add_argument("--url", default="http://127.0.0.1:7070"); c.add_argument("--log", default=".livepowers/comms.jsonl")
        c.set_defaults(fn=fn)
    r = sp.add_parser("replay"); r.add_argument("--log", default=".livepowers/comms.jsonl")
    r.add_argument("--speed", type=float, default=0); r.add_argument("--trace"); r.set_defaults(fn=cmd_replay)
    st = sp.add_parser("audit", help="审计：被拒消息、未闭合 trace、声称完成却无回执引用")
    st.add_argument("--log", default=".livepowers/comms.jsonl"); st.set_defaults(fn=cmd_audit)
    v = sp.add_parser("verify"); v.add_argument("--log", default=".livepowers/comms.jsonl"); v.set_defaults(fn=cmd_verify)
    a = p.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
