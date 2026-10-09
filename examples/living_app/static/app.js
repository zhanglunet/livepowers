// 对话式外壳：用户提问 → 服务端返回路由说明 + A2UI 消息 → a2ui.js 渲染进对话。
"use strict";
const $ = (id) => document.getElementById(id);
const thread = $("thread");
const client = new A2UIClient({ onAction });

function el(tag, text, cls) {
  const e = document.createElement(tag);
  if (text !== undefined) e.textContent = text;
  if (cls) e.className = cls;
  return e;
}
async function api(path, body) {
  const r = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body) } : {});
  return r.json();
}
function bubble(role, text) {
  const m = el("div", undefined, "msg " + role);
  if (text) m.append(el("p", text));
  thread.append(m);
  m.scrollIntoView({ block: "end", behavior: "smooth" });
  return m;
}

function showAssistant(res) {
  const m = bubble("assistant", res.text || res.error || "");
  if (res.route) m.prepend(el("div", res.route, "route " + (res.kind || "")));
  for (const msg of res.messages || []) {
    const host = client.process(msg);
    if (host) m.append(host);
  }
  if (res.messages && res.messages.length) {
    const d = el("details"); d.append(el("summary", "查看 A2UI 消息"));
    d.append(el("pre", res.messages.map((x) => JSON.stringify(x)).join("\n")));
    m.append(d);
  }
  m.scrollIntoView({ block: "end", behavior: "smooth" });
}

async function onAction({ surfaceId, name, button }) {
  if (name !== "promote_surface") return;
  button.disabled = true;
  const r = await api("/api/action", { surfaceId, name });
  bubble("assistant", r.text || r.error);
  if (r.text) $("grow").disabled = false;
}

async function loadPages() {
  const pages = await api("/api/pages");
  const ul = $("pages");
  ul.replaceChildren();
  $("pages-empty").hidden = pages.length > 0;
  for (const p of pages) {
    const b = el("button", p.name); b.type = "button";
    b.addEventListener("click", async () => {
      bubble("user", `打开固定页：${p.name}`);
      showAssistant(await api("/api/pages/" + encodeURIComponent(p.capability)));
    });
    const li = el("li"); li.append(b); ul.append(li);
  }
}

$("ask").addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = $("q").value.trim();
  if (!q) return;
  $("q").value = "";
  bubble("user", q);
  showAssistant(await api("/api/ask", { q }));
});

$("grow").addEventListener("click", async () => {
  $("grow").disabled = true;
  bubble("assistant", "正在生长：生成视图 DDL 与固化展示面 → 孪生库部署 → 与次抛结果对账 → 评审采纳 → 生产部署 → 注册……");
  const r = await api("/api/grow", {});
  const m = bubble("assistant", r.text || r.error);
  if (r.log) { const d = el("details"); d.append(el("summary", "查看生长过程（lp 命令输出）")); d.append(el("pre", r.log)); m.append(d); }
  await loadPages();
});

const hello = bubble("assistant", "你好，我是这个业务应用里的智能体。先查固定页；没有就当场做一次次抛分析——觉得有用，可以申请固化，让它长成新的固定页。");
const chips = el("div", undefined, "chips");
for (const s of ["各地区在途商机金额"]) {
  const c = el("button", s, "chip"); c.type = "button";
  c.addEventListener("click", () => { $("q").value = s; $("ask").requestSubmit(); });
  chips.append(c);
}
hello.append(chips);
loadPages();
