// 浏览器内的"lp"：与仓库里的 lp surface record / promote / reconcile / deploy / a2ui 同样的规则，数据全部虚构。
const $ = (id) => document.getElementById(id);
const thread = $("thread");
const state = { db: null, ontology: new Set(["owners", "customers", "opportunities", "activities"]),
  registry: [], records: {}, promoted: null, counter: 0, evidence: 0, model: false };
const MATCH = 0.6;   // 问题被预置展示面 / 固定页意图覆盖的比例达到这个值才算命中，否则不硬套
const client = new A2UIClient({ onAction });

function el(tag, text, cls) { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (cls) e.className = cls; return e; }

function makeDemoDb(SQL) {  // 与 examples/make_demo_db.py 相同的虚构数据
  const db = new SQL.Database();
  db.run(`create table owners(id integer primary key, name text, region text, phone text);
    create table customers(id integer primary key, name text, tier text, region text);
    create table opportunities(id integer primary key, customer_id integer references customers(id), owner_id integer,
      amount real, stage text, last_followup_at text, version integer default 1);
    create table activities(id integer primary key, opportunity_id integer, kind text, created_at text);`);
  db.run("insert into owners values (1,'Owner A','east','000-0000'),(2,'Owner B','south','000-0001')");
  db.run("insert into customers values (1,'Customer X','A','east'),(2,'Customer Y','B','south')");
  const stages = ["lead", "qualified", "proposal", "won", "lost"];
  for (let i = 1; i <= 12; i++) {
    db.run("insert into opportunities(id,customer_id,owner_id,amount,stage,last_followup_at) values (?,?,?,?,?,?)",
      [i, 1 + i % 2, 1 + i % 2, 100000 * i, stages[i % 5], `2026-0${1 + i % 9}-1${i % 9}`]);
  }
  return db;
}

function query(db, sql) {
  const res = db.exec(sql);
  if (!res.length) return { columns: [], rows: [] };
  return { columns: res[0].columns, rows: res[0].values };
}

function refsOk(s) {  // 与 lp surface validate 同一套规则（surface-rules.js）
  return SurfaceRules.validate(s, state.ontology).join("；");
}

function computeData(db, s) {
  const out = {};
  for (const [name, d] of Object.entries(s.data)) out[name] = query(db, d.query);
  return out;
}

function toA2UI(s, data, sid, promotable, version) {  // 与 lp surface a2ui 相同的映射
  const V = "v0.9.1", eph = s.tier === "ephemeral", prov = s.provenance || {};
  const kinds = { kpi: "Kpi", table: "Table", bar: "BarChart", line: "LineChart", filter: "Filter" };
  const comps = [
    { id: "root", component: "Card", child: "body" },
    { id: "title", component: "Text", text: s.title || s.id, variant: "h2" },
    { id: "badge", component: "Badge", tone: s.tier, text: eph ? "次抛，未经验收" : `固化 v${version || "?"}` },
    { id: "provenance", component: "Text", variant: "caption", text: `本体 ${prov.ontology_version || "?"} · 数字由数据库按查询计算` },
  ];
  const body = ["title", "badge", "provenance"];
  s.components.forEach((c, i) => {
    const cid = `c${i}-${c.id || c.type}`, comp = { id: cid, component: kinds[c.type], label: c.label || "" };
    if (c.type === "filter") Object.assign(comp, { param: c.param, options: c.options || [], value: { path: `/_filters/${c.param}` } });
    else {
      comp.rows = { path: `/${c.data}` };
      for (const k of ["value", "x", "y", "columns"]) if (k in c) comp[k] = c[k];
      if (c.type === "kpi") comp.aggregate = "sum";
    }
    comps.push(comp); body.push(cid);
  });
  if (eph && promotable) {
    comps.push({ id: "promote-text", component: "Text", text: "申请固化" },
      { id: "promote", component: "Button", child: "promote-text", action: { event: { name: "promote_surface" } } });
    body.push("promote");
  }
  comps.splice(1, 0, { id: "body", component: "Column", children: body });
  const msgs = [{ version: V, createSurface: { surfaceId: sid, catalogId: "urn:livepowers:a2ui-catalog:surface:1" } },
    { version: V, updateComponents: { surfaceId: sid, components: comps } }];
  for (const [name, d] of Object.entries(data))
    msgs.push({ version: V, updateDataModel: { surfaceId: sid, path: `/${name}`,
      value: d.rows.map((r) => Object.fromEntries(d.columns.map((c, i) => [c, r[i]]))) } });
  return msgs;
}

const coverage = SurfaceRules.coverage;

function bubble(role, text) { const m = el("div", undefined, "msg " + role); if (text) m.append(el("p", text)); thread.append(m); m.scrollIntoView({ block: "end" }); return m; }

function assistant({ route, kind, text, messages, log }) {
  const m = bubble("assistant", text);
  if (route) m.prepend(el("div", route, "route " + (kind || "")));
  for (const msg of messages || []) { const host = client.process(msg); if (host) m.append(host); }
  if (messages && messages.length) {
    const d = el("details"); d.append(el("summary", "查看 A2UI 消息"));
    d.append(el("pre", messages.map((x) => JSON.stringify(x)).join("\n"))); m.append(d);
  }
  if (log) { const d = el("details"); d.open = true; d.append(el("summary", "生长过程（与 lp 命令同样的检查）")); d.append(el("pre", log)); m.append(d); }
  m.scrollIntoView({ block: "end" });
}

function openPage(page, route) {
  const s = SURFACES[page.surface];
  assistant({ route, kind: "fixed", text: `这是固定页「${page.name}」，由已固化的视图直接计算，不需要重新分析。`,
    messages: toA2UI(s, computeData(state.db, s), `${page.id}-${++state.counter}`, false, page.version) });
}

function showEphemeral(s, key, route, text) {
  const err = refsOk(s);
  if (err) return assistant({ route, kind: "none", text: `展示面未通过校验，没有执行：${err}` });
  let data;
  try { data = computeData(state.db, s); } catch (e) { return assistant({ route, kind: "none", text: `查询执行失败：${e.message}` }); }
  const sid = `${s.id}-${++state.counter}`;
  state.records[sid] = { key, intent: s.intent, stats: data };   // 只记摘要：演示里直接保留计算结果用于对账
  state.evidence++;
  assistant({ route, kind: "ephemeral", messages: toA2UI(s, data, sid, true), text });
}

async function ask(q) {
  bubble("user", q);
  const hit = state.registry.map((p) => [Math.max(...p.intents.map((i) => coverage(q, i))), p]).sort((a, b) => b[0] - a[0])[0];
  if (hit && hit[0] >= MATCH) return openPage(hit[1], "System 1 · 命中固定页");
  const best = Object.entries(SURFACES).filter(([, s]) => s.tier === "ephemeral")
    .map(([k, s]) => [coverage(q, s.intent + " " + s.title), k, s]).sort((a, b) => b[0] - a[0])[0];
  if (best && best[0] >= MATCH) return showEphemeral(best[2], best[1], "System 2 · 次抛展示（预置）",
    "没有现成的固定页，我当场做了一次分析（预置展示面；数字由 SQLite 按查询计算）。觉得以后常看，可以申请固化。");
  if (!state.model) return assistant({ route: "System 2 · 未命中", kind: "none",
    text: "演示里没有这个问题的预置分析，模型也还没接入，所以不硬套一个相近的结果。可以试试：各地区在途商机金额、每月跟进商机金额。" });
  const wait = bubble("assistant", "正在让模型写查询和挑图表……");
  let res;
  try {
    const r = await fetch("/api/agent", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ q }) });
    res = await r.json();
  } catch (e) { res = { error: "模型服务连不上" }; }
  wait.remove();
  if (res.unsupported) return assistant({ route: "System 2 · 模型", kind: "none", text: `模型认为这个问题不在演示数据范围内：${res.unsupported}` });
  if (!res.surface) return assistant({ route: "System 2 · 模型", kind: "none", text: res.error || "模型没有给出展示面" });
  showEphemeral(res.surface, null, "System 2 · 次抛展示（模型生成，已按规则校验）",
    "模型写了查询、挑了组件；校验通过后由 SQLite 计算出这些数字。觉得以后常看，可以申请固化。");
}

function onAction({ surfaceId, name, button }) {
  if (name !== "promote_surface" || !state.records[surfaceId]) return;
  button.disabled = true;
  const rec = state.records[surfaceId];
  if (!rec.key || !SURFACES[rec.key.replace(".ephemeral", ".fixed")]) {
    return assistant({ text: "已登记为固化候选。这个演示只为「各地区在途商机金额」预置了生长产物，其他分析停在候选状态。" });
  }
  state.promoted = { ...rec, task: "t_" + Math.random().toString(16).slice(2, 10) };
  assistant({ text: `已申请固化，看板任务 ${state.promoted.task}。接下来由智能体生成新结构、评审采纳——点左侧「模拟生长」。` });
  $("grow").disabled = false;
}

function hashRows(d) { return JSON.stringify([...d.rows].map((r) => JSON.stringify(r)).sort()); }

function grow() {
  $("grow").disabled = true;
  const rec = state.promoted, fixedKey = rec.key.replace(".ephemeral", ".fixed"), fixed = SURFACES[fixedKey];
  const steps = [...document.querySelectorAll("#steps li")], log = [];
  const done = (i, line) => { steps[i].classList.add("done"); log.push(line); };
  state.ontology.add("v_pipeline_by_region");
  done(0, "1 规格确认；本体新增 views: v_pipeline_by_region（ontology 0.2.0-draft）");
  done(1, "2 生成 DDL：\n" + DDL.up.trim() + "\n  回滚：" + DDL.down.trim());
  const twin = new SQL_.Database(state.db.export());
  twin.run(DDL.up);
  const err = refsOk(fixed);
  const base = computeData(twin, SURFACES[rec.key]), next = computeData(twin, fixed);
  const same = Object.keys(base).every((k) => hashRows(base[k]) === hashRows(next[k]));
  twin.close();
  if (err || !same) { log.push("✗ 对账不一致或校验失败：" + (err || "结果不同")); return assistant({ text: "生长中止。", log: log.join("\n") }); }
  done(2, `3 孪生库部署 ✓；对账：${base.pipeline.rows.length} 行，结果与次抛一致 ✓`);
  done(3, "4 四道门通过：生成者 agent-a，采纳人 reviewer-b");
  try {
    state.db.run(DDL.up);
    const ok = query(state.db, "select count(*) from sqlite_master where type = 'view' and name = 'v_pipeline_by_region'").rows[0][0];
    if (!ok) throw new Error("视图不存在");
    computeData(state.db, fixed);
  } catch (e) { state.db.run(DDL.down); log.push("✗ 生产部署失败，已回滚：" + e.message); return assistant({ text: "生长中止。", log: log.join("\n") }); }
  done(4, "5 生产部署 ✓；核验：view v_pipeline_by_region 存在，查询可执行；已写部署回执");
  state.registry.push({ id: "cap_pipeline_by_region", name: "各地区在途商机", version: "1.0.0", surface: fixedKey,
    intents: ["pipeline by region", "各地区在途商机", "各地区在途商机金额", "在途商机金额"] });
  done(5, "6 注册 cap_pipeline_by_region v1.0.0（kind=view，ui → 固化展示面）");
  renderPages();
  assistant({ text: "已长成新的固定页「各地区在途商机」。再问一次同样的问题，会直接走固定页。", log: log.join("\n") });
}

function renderPages() {
  const ul = $("pages"); ul.replaceChildren();
  $("pages-empty").hidden = state.registry.length > 0;
  for (const p of state.registry) {
    const b = el("button", p.name); b.type = "button";
    b.addEventListener("click", () => { bubble("user", `打开固定页：${p.name}`); openPage(p, "System 1 · 固定页"); });
    const li = el("li"); li.append(b); ul.append(li);
  }
}

let SQL_;
initSqlJs().then((SQL) => {
  SQL_ = SQL; state.db = makeDemoDb(SQL);
  thread.replaceChildren();
  const hello = bubble("assistant", "你好，我是这个业务应用里的智能体。先查固定页；没有就当场做一次次抛分析，觉得有用可以申请固化，让它长成新的固定页。");
  const chips = el("div", undefined, "chips");
  for (const s of ["各地区在途商机金额", "每月跟进商机金额"]) {
    const c = el("button", s, "chip"); c.type = "button";
    c.addEventListener("click", () => ask(s)); chips.append(c);
  }
  hello.append(chips);
  renderPages();
  fetch("/api/agent").then((r) => (r.ok ? r.json() : { configured: false })).catch(() => ({ configured: false }))
    .then((r) => { state.model = Boolean(r && r.configured); $("model-status").textContent = state.model
      ? "模型：已接入。预置分析覆盖不到的问题会交给模型，输出先校验再执行。"
      : "模型：未接入。只能回答预置的两个分析；接入方法见仓库 examples/living_app/README.md。"; });
}).catch((e) => { $("loading").textContent = "SQLite 加载失败：" + e.message; });

$("ask").addEventListener("submit", (e) => { e.preventDefault(); const q = $("q").value.trim(); if (!q || !state.db) return; $("q").value = ""; ask(q); });
$("grow").addEventListener("click", grow);
