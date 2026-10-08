// 活软件演示前端：只渲染展示面描述（组件 + 数据），不执行任何来自展示面的代码；全部用 textContent 写入。
"use strict";
const $ = (id) => document.getElementById(id);
const SVG = "http://www.w3.org/2000/svg";
let current = null;

function el(tag, text, cls) {
  const e = document.createElement(tag);
  if (text !== undefined) e.textContent = text;
  if (cls) e.className = cls;
  return e;
}
function svgEl(tag, attrs) {
  const e = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs || {})) e.setAttribute(k, v);
  return e;
}
const fmt = (v) => (typeof v === "number" ? v.toLocaleString("zh-CN") : String(v));

async function api(path, body) {
  const r = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body) } : {});
  return r.json();
}

async function loadPages() {
  const pages = await api("/api/pages");
  const ul = $("pages");
  ul.replaceChildren();
  $("pages-empty").hidden = pages.length > 0;
  for (const p of pages) {
    const b = el("button", p.name);
    b.type = "button";
    b.addEventListener("click", async () => show(await api("/api/pages/" + encodeURIComponent(p.capability)),
      "System 1：固定页"));
    const li = el("li"); li.append(b); ul.append(li);
  }
}

function rowsOf(data, filters) {
  return data.rows.filter((r) => Object.entries(filters).every(([col, val]) => !val ||
    String(r[data.columns.indexOf(col)]) === val));
}

function chart(type, data, rows, x, y) {
  const W = 520, H = 220, L = 70, B = 28, T = 10;
  const xi = data.columns.indexOf(x), yi = data.columns.indexOf(y);
  const max = Math.max(1, ...rows.map((r) => Number(r[yi]) || 0));
  const s = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", role: "img", "aria-label": `${y} 按 ${x}` });
  s.append(svgEl("line", { x1: L, y1: H - B, x2: W, y2: H - B, class: "axis" }));
  for (const f of [0, 0.5, 1]) {
    const yy = H - B - f * (H - B - T);
    const t = svgEl("text", { x: L - 6, y: yy + 4, "text-anchor": "end" }); t.textContent = fmt(Math.round(max * f));
    s.append(t);
  }
  const step = (W - L) / Math.max(1, rows.length);
  const pts = [];
  rows.forEach((r, i) => {
    const v = Number(r[yi]) || 0, h = (v / max) * (H - B - T), cx = L + step * i + step / 2;
    const tip = svgEl("title"); tip.textContent = `${fmt(r[xi])}：${fmt(v)}`;
    if (type === "bar") {
      const bw = Math.min(48, step - 2);  // 相邻柱之间留 2px 以上间隙
      const g = svgEl("rect", { x: cx - bw / 2, y: H - B - h, width: bw, height: h, rx: 4, class: "mark" });
      g.append(tip); s.append(g);
    } else {
      pts.push(`${cx},${H - B - h}`);
      const dot = svgEl("circle", { cx, cy: H - B - h, r: 4, class: "mark" }); dot.append(tip); s.append(dot);
    }
    const lab = svgEl("text", { x: cx, y: H - B + 16, "text-anchor": "middle" }); lab.textContent = fmt(r[xi]);
    s.append(lab);
  });
  if (type === "line" && pts.length) s.insertBefore(svgEl("polyline", { points: pts.join(" "), class: "series" }), s.children[1]);
  return s;
}

function table(data, rows, cols) {
  const t = el("table"), head = el("tr");
  const use = cols && cols.length ? cols : data.columns;
  for (const c of use) {
    const th = el("th", c); if (rows.length && typeof rows[0][data.columns.indexOf(c)] === "number") th.className = "num";
    head.append(th);
  }
  t.append(head);
  for (const r of rows) {
    const tr = el("tr");
    for (const c of use) {
      const v = r[data.columns.indexOf(c)];
      tr.append(el("td", fmt(v), typeof v === "number" ? "num" : ""));
    }
    t.append(tr);
  }
  return t;
}

function render() {
  const { surface, data } = current;
  const box = $("components");
  box.replaceChildren();
  for (const c of surface.components) {
    const wrap = el("div", undefined, "comp");
    if (c.label) wrap.append(el("h3", c.label));
    if (c.type === "filter") {
      const sel = el("select"); sel.append(new Option("全部", ""));
      for (const o of c.options || []) sel.append(new Option(o, o));
      sel.value = current.filters[c.param] || "";
      sel.addEventListener("change", () => { current.filters[c.param] = sel.value; render(); });
      wrap.append(sel); box.append(wrap); continue;
    }
    const d = data[c.data];
    if (!d) continue;
    const rows = rowsOf(d, current.filters);
    if (c.type === "kpi") {
      const i = d.columns.indexOf(c.value);
      wrap.append(el("div", fmt(rows.reduce((a, r) => a + (Number(r[i]) || 0), 0)), "kpi"));
    } else if (c.type === "table") wrap.append(table(d, rows, c.columns));
    else wrap.append(chart(c.type, d, rows, c.x, c.y));
    box.append(wrap);
  }
}

function show(res, route) {
  $("route").textContent = res.error ? res.error : (res.route || route || "");
  if (!res.surface) { $("surface").hidden = true; return; }
  current = { ...res, filters: {} };
  $("surface").hidden = false;
  $("title").textContent = res.surface.title || res.surface.id;
  const eph = res.tier === "ephemeral";
  $("badge").textContent = eph ? "次抛，未经验收" : `固化 v${res.version}`;
  $("badge").className = "badge " + (eph ? "ephemeral" : "fixed");
  const p = res.surface.provenance || {};
  $("provenance").textContent = `本体 ${p.ontology_version || "?"}` + (res.capability ? ` · 能力 ${res.capability}` : "") +
    " · 数字由数据库按查询计算";
  $("promote-row").hidden = !eph;
  $("promote-msg").textContent = "";
  render();
}

$("ask").addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = $("q").value.trim();
  if (q) show(await api("/api/ask", { q }));
});
$("promote").addEventListener("click", async () => {
  const r = await api("/api/promote", { record: current.record });
  $("promote-msg").textContent = r.task ? `已申请固化：看板任务 ${r.task}（运行 grow.sh 模拟生长与采纳）` : r.error;
});
loadPages();
