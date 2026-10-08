// Cloudflare Pages Function：/api/agent —— 把业务问题交给模型，只换回一份展示面 JSON（查询 + 组件）。
// 不绑定具体模型：任何兼容 OpenAI Chat Completions 的接口都可以，由环境变量决定（在 Cloudflare 后台配置）：
//   LP_MODEL_BASE_URL   接口地址，如 https://api.example.com/v1
//   LP_MODEL_NAME       模型名
//   LP_MODEL_API_KEY    密钥（只在服务端，永远不下发给页面）
//   LP_LIMITS           D1 数据库绑定：限流计数（必需；临时不要限流时设 LP_ALLOW_NO_RATE_LIMIT=1）。
//                       用单条 upsert 原子加一，并发请求不会丢计数（KV 的读改写做不到，且同一键每秒只能写一次）
//   LP_RATE_PER_HOUR    每个 IP 每小时次数，默认 20
//   LP_RATE_PER_DAY     全站每天次数，默认 300
//   LP_MODEL_JSON_MODE  设为 1 时请求 response_format=json_object（接口支持时再开）
// 没配置时 GET 返回 {configured:false}，页面退回预置展示面。模型只编排查询和挑组件；
// 页面会按与 lp surface validate 相同的规则校验，通过后在浏览器的 SQLite 里执行——数字永远由数据库计算。

const SCHEMA = `表（SQLite，演示数据全部虚构）：
- owners(id, name, region)            负责人；region 取值 east / south（phone 为敏感字段，禁止读取）
- customers(id, name, tier, region)   客户；tier 取值 A / B；region 取值 east / south
- opportunities(id, customer_id → customers.id, owner_id → owners.id, amount 金额（元）,
    stage 取值 lead / qualified / proposal / won / lost, last_followup_at 'YYYY-MM-DD' 最近跟进日期, version)
- activities(id, opportunity_id → opportunities.id, kind, created_at)
- v_pipeline_by_region(region, amount, n)   视图：各地区在途（未成交且未丢单）商机金额与个数（仅在已生长后存在）`;

const SYSTEM = `你是一个业务应用里的分析智能体。用户提出业务问题，你只输出一份 JSON 展示面，不输出任何其他文字。
${SCHEMA}

输出格式（严格 JSON）：
{"id":"kebab-case-id","title":"简短中文标题","tier":"ephemeral","intent":"规范化意图",
 "data":{"<名称>":{"source":{"type":"table","name":"<主表名>"},"query":"<一条只读 SELECT>"}},
 "components":[{"type":"kpi|table|bar|line","data":"<名称>","value|x|y|columns":"..."}],
 "provenance":{"ontology_version":"0.1.0-draft","generated_by":"model"}}
规则：
1. 查询只能是一条 SELECT（可用 WITH，但不能递归），只能引用上面列出的表或视图，SQLite 语法，不要分号以外的多语句。
2. 不读取敏感字段（phone 等）。不要编造数字，所有数字必须来自查询。
3. 组件：kpi 需要 value（数值列，取合计）；bar/line 需要 x 与 y；table 可给 columns。最多 4 个组件。
4. 列名用英文别名（如 region、amount、n、month），方便组件引用。
5. 问题与上述数据无关、或需要写数据时，只输出 {"unsupported":"一句中文说明"}。`;

const json = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" } });

const configured = (env) => Boolean(env.LP_MODEL_BASE_URL && env.LP_MODEL_NAME && env.LP_MODEL_API_KEY);

export async function onRequestGet({ env }) {
  return json({ configured: configured(env) });
}

let tableReady = false;

// 原子加一并返回新值：先计数再判断，被拒的请求也计入，宁可保守
async function bump(db, key, now) {
  const row = await db.prepare("INSERT INTO lp_rate (k, n, ts) VALUES (?1, 1, ?2) " +
    "ON CONFLICT(k) DO UPDATE SET n = n + 1 RETURNING n").bind(key, now).first();
  return Number(row && row.n);
}

async function rateLimited(env, ip) {
  const db = env.LP_LIMITS;
  if (!db) return env.LP_ALLOW_NO_RATE_LIMIT === "1" ? null : "服务端未配置限流存储（LP_LIMITS），暂不开放";
  try {
    if (!tableReady) {
      await db.exec("CREATE TABLE IF NOT EXISTS lp_rate (k TEXT PRIMARY KEY, n INTEGER NOT NULL, ts INTEGER NOT NULL)");
      tableReady = true;
    }
    const now = Date.now(), iso = new Date(now).toISOString();
    const h = await bump(db, `ip:${ip}:${iso.slice(0, 13)}`, now);
    if (h > Number(env.LP_RATE_PER_HOUR || 20)) return "提问太频繁了，请一小时后再试";
    const d = await bump(db, `day:${iso.slice(0, 10)}`, now);
    if (d > Number(env.LP_RATE_PER_DAY || 300)) return "今天的演示额度已用完，请明天再试";
    if (Math.random() < 0.02) await db.prepare("DELETE FROM lp_rate WHERE ts < ?1").bind(now - 2 * 86400000).run();
    return null;
  } catch {
    return "限流存储暂时不可用，请稍后再试";   // 拿不到计数就不放行，避免绕过上限
  }
}

export function extractJson(text) {
  const s = String(text || "").replace(/^\s*```(?:json)?/i, "").replace(/```\s*$/, "").trim();
  const start = s.indexOf("{"), end = s.lastIndexOf("}");
  if (start < 0 || end <= start) throw new Error("模型没有返回 JSON");
  return JSON.parse(s.slice(start, end + 1));
}

export async function onRequestPost({ request, env }) {
  if (!configured(env)) return json({ configured: false, error: "未接入模型" }, 503);
  let body;
  try { body = await request.json(); } catch { return json({ error: "请求格式不对" }, 400); }
  const q = String((body && body.q) || "").trim();
  if (!q || q.length > 200) return json({ error: "问题不能为空，且不超过 200 字" }, 400);
  const limited = await rateLimited(env, request.headers.get("cf-connecting-ip") || "unknown");
  if (limited) return json({ error: limited }, 429);
  const payload = { model: env.LP_MODEL_NAME, temperature: 0, max_tokens: 900,
    messages: [{ role: "system", content: SYSTEM }, { role: "user", content: q }] };
  if (env.LP_MODEL_JSON_MODE === "1") payload.response_format = { type: "json_object" };
  let resp;
  try {
    resp = await fetch(`${env.LP_MODEL_BASE_URL.replace(/\/+$/, "")}/chat/completions`, {
      method: "POST",
      headers: { "content-type": "application/json", authorization: `Bearer ${env.LP_MODEL_API_KEY}` },
      body: JSON.stringify(payload),
    });
  } catch { return json({ error: "模型服务连不上" }, 502); }
  if (!resp.ok) return json({ error: `模型服务返回 ${resp.status}` }, 502);
  let out;
  try {
    const r = await resp.json();
    out = extractJson(r.choices && r.choices[0] && r.choices[0].message && r.choices[0].message.content);
  } catch (e) { return json({ error: `模型输出无法解析：${e.message}` }, 502); }
  if (out && typeof out.unsupported === "string") return json({ unsupported: out.unsupported.slice(0, 200) });
  if (!out || typeof out !== "object" || !out.data || !out.components) return json({ error: "模型输出不是展示面" }, 502);
  out.tier = "ephemeral";   // 模型产出的永远是次抛，固化只能走生长通道
  out.provenance = { ...(out.provenance || {}), generated_by: "model", model: env.LP_MODEL_NAME };
  return json({ surface: out });   // 页面会再按完整规则校验后才执行
}
