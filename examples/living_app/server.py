#!/usr/bin/env python3
"""活软件参考宿主（零依赖演示）：左侧固定页目录，右侧智能体面板。

- 提问先走 `lp registry find`：命中且带固定页 → 打开固定页（System 1，数据库按公式计算）。
- 未命中 → 次抛展示（System 2）。演示中不调用真实模型：按问题匹配 surfaces/ 下预置的次抛展示面，
  `lp surface record` 记证据，`lp surface a2ui` 校验并只读计算数据，以 A2UI v0.9.1 消息下发。
- 展示面上的「申请固化」是 A2UI Button 事件 → `lp surface promote`；「模拟生长」运行 grow.sh
  （生成结构、孪生对账、验收、生产部署、注册），只执行这个固定脚本，不接受任何输入。

安全边界：只监听 127.0.0.1；展示面只含数据与组件描述，前端不执行任何来自展示面的代码；
查询只来自通过校验的展示面文件，并以只读方式打开数据库；写操作不经过这里。

用法：python3 examples/living_app/server.py [--workdir DIR] [--port 8765]
"""
import argparse
import json
import os
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

APP = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(APP))
LP = os.path.join(REPO, "scripts", "lp.py")
SURFACES = os.path.join(APP, "surfaces")
STATIC = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"),
          "/a2ui.js": ("a2ui.js", "text/javascript"),
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


def a2ui(workdir, surface_path, surface_id, promotable=False, version=""):
    """调 lp surface a2ui：校验展示面、只读计算数据、转成 A2UI v0.9.1 消息（数字来自数据库，不来自模型）。"""
    args = ["surface", "a2ui", surface_path, "--db", "demo.sqlite", "--surface-id", surface_id]
    if promotable:
        args.append("--promotable")
    if version:
        args += ["--version", version]
    p = lp(workdir, *args)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip())
    return [json.loads(x) for x in p.stdout.splitlines() if x.strip()]


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
    records = {}     # surfaceId → 次抛记录路径（申请固化时用）
    counter = [0]

    def log_message(self, fmt, *args):  # 安静一点
        pass

    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'")
        self.end_headers()
        self.wfile.write(data)

    def next_id(self, base):
        self.counter[0] += 1
        return f"{base}-{self.counter[0]}"

    def pages(self):
        p = lp(self.workdir, "pages", "list")
        return json.loads(p.stdout or "[]")

    def page_payload(self, page, route):
        msgs = a2ui(self.workdir, page["ui"], self.next_id(page["capability"]), version=page["version"])
        return {"kind": "fixed", "route": route, "capability": page["capability"], "messages": msgs,
                "text": f"这是固定页「{page['name']}」，由已固化的视图直接计算，不需要重新分析。"}

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
            if not page:
                return self.send(404, {"error": "没有这个固定页"})
            return self.send(200, self.page_payload(page, "System 1 · 固定页"))
        return self.send(404, {"error": "not found"})

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def do_POST(self):
        path = urlparse(self.path).path
        req = self.body()
        try:
            if path == "/api/ask":
                return self.ask(str(req.get("q", "")).strip())
            if path == "/api/action":
                return self.action(str(req.get("surfaceId", "")), str(req.get("name", "")))
            if path == "/api/grow":
                return self.grow()
        except RuntimeError as e:
            return self.send(422, {"error": str(e)})
        return self.send(404, {"error": "not found"})

    def ask(self, q):
        if not q:
            return self.send(400, {"error": "请输入问题"})
        find = lp(self.workdir, "registry", "find", q)
        if find.returncode == 0:
            hit = re.search(r"(cap_\S+) v", find.stdout)
            page = next((p for p in self.pages() if hit and p["capability"] == hit.group(1)), None)
            if page:
                return self.send(200, self.page_payload(page, "System 1 · 命中固定页"))
        preset = preset_for(q)
        if not preset:
            return self.send(200, {"kind": "none", "route": "System 2 · 未命中",
                                   "text": "没有固定页能回答这个问题。演示里只预置了「各地区在途商机金额」这一个次抛分析。"})
        s = load_json(preset)
        rec = lp(self.workdir, "surface", "record", preset, "--intent", s["intent"], "--db", "demo.sqlite")
        if rec.returncode != 0:
            raise RuntimeError((rec.stderr or rec.stdout).strip())
        sid = self.next_id(s["id"])
        self.records[sid] = rec.stdout.strip()
        return self.send(200, {"kind": "ephemeral", "route": "System 2 · 次抛展示", "messages": a2ui(
            self.workdir, preset, sid, promotable=True),
            "text": "没有现成的固定页，我当场做了一次分析（演示中为预置展示面，数字由数据库按查询计算）。"
                    "觉得以后常看，可以点「申请固化」。"})

    def action(self, surface_id, name):
        if name != "promote_surface" or surface_id not in self.records:
            return self.send(400, {"error": "未知的操作或展示面"})
        p = lp(self.workdir, "surface", "promote", self.records[surface_id], "--by", "business-user")
        if p.returncode != 0:
            return self.send(409, {"error": (p.stderr or p.stdout).strip()})
        return self.send(200, {"task": p.stdout.strip(), "text": f"已申请固化，看板任务 {p.stdout.strip()}。"
                               "接下来由智能体生成新结构、评审采纳——演示里点左侧「模拟生长」。"})

    def grow(self):
        g = subprocess.run(["bash", os.path.join(APP, "grow.sh"), self.workdir], capture_output=True, text=True)
        if g.returncode != 0:
            return self.send(409, {"error": "生长失败：" + (g.stderr or g.stdout).strip()[-400:], "log": g.stdout})
        return self.send(200, {"text": "已长成新的固定页「各地区在途商机」：视图已部署到生产并通过核验。"
                                       "再问一次同样的问题，会直接走固定页。", "log": g.stdout})


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
