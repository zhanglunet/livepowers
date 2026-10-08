#!/usr/bin/env python3
"""活软件参考宿主（零依赖演示）：左侧固定页目录，右侧智能体面板。

- 提问先走 `lp registry find`：命中且带固定页 → 打开固定页（System 1，数据库按公式计算）。
- 未命中 → 次抛展示（System 2）。演示中不调用真实模型：按问题匹配 surfaces/ 下预置的次抛展示面，
  先 `lp surface validate`，再 `lp surface record` 记证据，然后只读执行查询、下发数据。
- "申请固化" → `lp surface promote`。之后的生长步骤见 grow.sh（生成结构、孪生对账、验收、生产部署、注册）。

安全边界：只监听 127.0.0.1；展示面只含数据与组件描述，前端不执行任何来自展示面的代码；
查询只来自通过校验的展示面文件，并以只读方式打开数据库；写操作不经过这里。

用法：python3 examples/living_app/server.py [--workdir DIR] [--port 8765]
"""
import argparse
import contextlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

APP = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(APP))
LP = os.path.join(REPO, "scripts", "lp.py")
SURFACES = os.path.join(APP, "surfaces")
STATIC = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"),
          "/app.css": ("app.css", "text/css")}


def lp(workdir, *args):
    return subprocess.run([sys.executable, LP, *args], cwd=workdir, capture_output=True, text=True,
                          env={**os.environ, "LIVEPOWERS_HOME": ".livepowers"})


def bootstrap(workdir):
    """首次运行：建演示库、初始化 .livepowers、扫描出本体草稿。"""
    os.makedirs(workdir, exist_ok=True)
    if os.path.isdir(os.path.join(workdir, ".livepowers")):
        return
    subprocess.run([sys.executable, os.path.join(REPO, "examples", "make_demo_db.py"), "demo.sqlite"],
                   cwd=workdir, check=True, capture_output=True)
    lp(workdir, "init")
    onto = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "scan_sqlite.py"), "demo.sqlite"],
                          cwd=workdir, check=True, capture_output=True, text=True).stdout
    with open(os.path.join(workdir, ".livepowers", "ontology.draft.yaml"), "w", encoding="utf-8") as f:
        f.write(onto)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def compute(workdir, surface):
    """按展示面里的查询只读计算数据（数字来自数据库，不来自模型）。"""
    uri = "file:" + os.path.join(workdir, "demo.sqlite") + "?mode=ro"
    out = {}
    with contextlib.closing(sqlite3.connect(uri, uri=True)) as con:
        for name, d in surface["data"].items():
            cur = con.execute(d["query"], d.get("params") or {})
            out[name] = {"columns": [c[0] for c in cur.description], "rows": cur.fetchall()}
    return out


def tokens(text):
    return set(re.findall(r"[a-z0-9]+", text.lower())) | {text[i:i + 2] for i in range(len(text) - 1)}


def preset_for(question):
    """演示用：按词与二元组重叠挑一个预置的次抛展示面（真实宿主里由智能体生成）。"""
    q = tokens(question)
    best, score = None, 0
    for fn in sorted(os.listdir(SURFACES)):
        if not fn.endswith(".ephemeral.json"):
            continue
        s = load_json(os.path.join(SURFACES, fn))
        n = len(q & tokens(s.get("intent", "") + " " + s.get("title", "")))
        if n > score:
            best, score = os.path.join(SURFACES, fn), n
    return best


class Handler(BaseHTTPRequestHandler):
    workdir = "."

    def log_message(self, fmt, *args):  # 安静一点
        pass

    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'")
        self.end_headers()
        self.wfile.write(data)

    def pages(self):
        p = lp(self.workdir, "pages", "list")
        return json.loads(p.stdout or "[]")

    def page_payload(self, page):
        s = load_json(page["ui"])
        return {"tier": "fixed", "surface": s, "data": compute(self.workdir, s), "capability": page["capability"],
                "version": page["version"]}

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path in STATIC:
            fn, ctype = STATIC[path]
            with open(os.path.join(APP, "static", fn), "rb") as f:
                return self.send(200, f.read(), ctype)
        if path == "/api/pages":
            return self.send(200, self.pages())
        m = re.match(r"^/api/pages/([\w.\-]+)$", path)
        if m:
            page = next((p for p in self.pages() if p["capability"] == m.group(1)), None)
            return self.send(200, self.page_payload(page)) if page else self.send(404, {"error": "没有这个固定页"})
        return self.send(404, {"error": "not found"})

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def do_POST(self):
        path = urlparse(self.path).path
        req = self.body()
        if path == "/api/ask":
            q = str(req.get("q", "")).strip()
            if not q:
                return self.send(400, {"error": "请输入问题"})
            find = lp(self.workdir, "registry", "find", q)
            if find.returncode == 0:
                hit = re.search(r"(cap_\S+) v", find.stdout)
                page = next((p for p in self.pages() if hit and p["capability"] == hit.group(1)), None)
                if page:
                    return self.send(200, {"route": "System 1：命中固定页", **self.page_payload(page)})
            preset = preset_for(q)
            if not preset:
                return self.send(200, {"route": "System 2：没有可用的演示展示面", "tier": None})
            v = lp(self.workdir, "surface", "validate", preset)
            if v.returncode != 0:
                return self.send(422, {"error": "展示面未通过校验", "detail": v.stdout})
            s = load_json(preset)
            rec = lp(self.workdir, "surface", "record", preset, "--intent", s["intent"], "--db", "demo.sqlite")
            if rec.returncode != 0:
                return self.send(500, {"error": rec.stderr})
            return self.send(200, {"route": "System 2：次抛展示", "tier": "ephemeral", "surface": s,
                                   "data": compute(self.workdir, s), "record": rec.stdout.strip()})
        if path == "/api/promote":
            record = str(req.get("record", ""))
            if not re.match(r"^\.livepowers/surfaces/ephemeral/[\w.\-]+\.json$", record):
                return self.send(400, {"error": "记录路径不合法"})
            p = lp(self.workdir, "surface", "promote", record, "--by", str(req.get("by") or "business-user"))
            if p.returncode != 0:
                return self.send(409, {"error": (p.stderr or p.stdout).strip()})
            return self.send(200, {"task": p.stdout.strip()})
        return self.send(404, {"error": "not found"})


def main():
    ap = argparse.ArgumentParser(description="活软件参考宿主（演示）")
    ap.add_argument("--workdir", default=os.path.join(os.getcwd(), ".living-demo"), help="演示工作目录")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    workdir = os.path.abspath(a.workdir)
    bootstrap(workdir)
    Handler.workdir = workdir
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"活软件演示：http://127.0.0.1:{srv.server_address[1]}/  （工作目录 {workdir}）", flush=True)
    print(f"申请固化后，模拟智能体生长与评审采纳：bash {os.path.join(APP, 'grow.sh')} {workdir}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
