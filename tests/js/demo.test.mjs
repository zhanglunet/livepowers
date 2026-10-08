// 在线演示的校验规则、匹配阈值与模型通道（Cloudflare Pages Function）测试：node --test tests/js
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import path from "node:path";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const require = createRequire(import.meta.url);
const Rules = require(path.join(ROOT, "examples/living_app/web/surface-rules.js"));
const surface = (f) => JSON.parse(readFileSync(path.join(ROOT, "examples/living_app/surfaces", f), "utf8"));
const ONTO = new Set(["owners", "customers", "opportunities", "activities"]);
const agentSrc = readFileSync(path.join(ROOT, "functions/api/agent.js"), "utf8");
const agent = await import("data:text/javascript;base64," + Buffer.from(agentSrc).toString("base64"));

test("预置展示面通过校验", () => {
  assert.deepEqual(Rules.validate(surface("pipeline-by-region.ephemeral.json"), ONTO), []);
  assert.deepEqual(Rules.validate(surface("followup-by-month.ephemeral.json"), ONTO), []);
  assert.deepEqual(Rules.validate(surface("pipeline-by-region.fixed.json"), new Set([...ONTO, "v_pipeline_by_region"])), []);
});

test("校验拒绝写语句、管理语句、递归、敏感字段、本体外对象、代码、内嵌数据、未知组件", () => {
  const base = surface("pipeline-by-region.ephemeral.json");
  const bad = (mut, expect) => {
    const s = structuredClone(base); mut(s);
    const errs = Rules.validate(s, ONTO).join("\n");
    assert.match(errs, expect);
  };
  bad((s) => { s.data.pipeline.query = "SELECT 1 FROM opportunities; DELETE FROM opportunities"; }, /DELETE|一条语句/);
  bad((s) => { s.data.pipeline.query = "PRAGMA user_version=1"; }, /SELECT 或 WITH/);
  bad((s) => { s.data.pipeline.query = "WITH RECURSIVE r(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM r) SELECT x FROM r"; }, /RECURSIVE/);
  bad((s) => { s.data.pipeline.query = "SELECT name, phone FROM owners"; }, /敏感/);
  bad((s) => { s.data.pipeline.query = "SELECT * FROM salaries"; }, /本体外的对象 salaries/);
  bad((s) => { s.data.pipeline.source.name = "salaries"; }, /不在本体里/);
  bad((s) => { s.components[0].onClick = "x"; }, /事件处理器/);
  bad((s) => { s.components[0].label = "<script>alert(1)</script>"; }, /疑似代码/);
  bad((s) => { s.data.pipeline.rows = [[1]]; }, /不内嵌结果/);
  bad((s) => { s.components.push({ type: "button", data: "pipeline" }); }, /不支持/);
});

test("匹配阈值：相近但不同的问题不再被硬套", () => {
  const p = surface("pipeline-by-region.ephemeral.json"), m = surface("followup-by-month.ephemeral.json");
  const cov = (q, s) => Rules.coverage(q, s.intent + " " + s.title);
  assert.ok(cov("各地区在途商机金额", p) >= 0.6);
  assert.ok(cov("在途商机金额", p) >= 0.6);
  assert.ok(cov("每月跟进的商机金额", m) >= 0.6);
  assert.ok(cov("各地区客户数量", p) < 0.6);
  assert.ok(cov("合同审批进度", p) < 0.6 && cov("合同审批进度", m) < 0.6);
});

const req = (body) => new Request("https://x/api/agent", { method: "POST", body: JSON.stringify(body),
  headers: { "content-type": "application/json", "cf-connecting-ip": "1.2.3.4" } });
const MODEL = { LP_MODEL_BASE_URL: "https://model.example/v1/", LP_MODEL_NAME: "m-1", LP_MODEL_API_KEY: "sk-secret" };
const kv = (init = {}) => { const m = new Map(Object.entries(init)); return { get: async (k) => m.get(k) ?? null, put: async (k, v) => { m.set(k, v); }, m }; };
function mockModel(content, status = 200) {
  const calls = [];
  globalThis.fetch = async (url, init) => { calls.push({ url, init }); return new Response(JSON.stringify({ choices: [{ message: { content } }] }), { status }); };
  return calls;
}

test("未配置模型：GET 报告未接入，POST 返回 503", async () => {
  assert.deepEqual(await (await agent.onRequestGet({ env: {} })).json(), { configured: false });
  assert.equal((await agent.onRequestPost({ request: req({ q: "x" }), env: {} })).status, 503);
  assert.deepEqual(await (await agent.onRequestGet({ env: MODEL })).json(), { configured: true });
});

test("没有限流存储时默认拒绝，显式放开才调用模型", async () => {
  const calls = mockModel("{}");
  const r = await agent.onRequestPost({ request: req({ q: "各地区客户数量" }), env: MODEL });
  assert.equal(r.status, 429);
  assert.equal(calls.length, 0);
});

test("模型输出：去掉代码围栏、强制为次抛、标注来源；密钥只出现在请求头里", async () => {
  const s = surface("pipeline-by-region.ephemeral.json");
  s.tier = "fixed";
  const calls = mockModel("```json\n" + JSON.stringify(s) + "\n```");
  const env = { ...MODEL, LP_RATE: kv() };
  const r = await agent.onRequestPost({ request: req({ q: "各地区客户数量" }), env });
  const body = await r.json();
  assert.equal(r.status, 200);
  assert.equal(body.surface.tier, "ephemeral");
  assert.equal(body.surface.provenance.generated_by, "model");
  assert.equal(calls[0].url, "https://model.example/v1/chat/completions");
  assert.equal(calls[0].init.headers.authorization, "Bearer sk-secret");
  assert.ok(!JSON.stringify(body).includes("sk-secret"));
  assert.equal(JSON.parse(calls[0].init.body).temperature, 0);
});

test("unsupported、坏输出、上游错误、超长问题与限流", async () => {
  const env = { ...MODEL, LP_RATE: kv() };
  mockModel('{"unsupported":"需要写数据"}');
  assert.deepEqual(await (await agent.onRequestPost({ request: req({ q: "删掉所有商机" }), env })).json(), { unsupported: "需要写数据" });
  mockModel("我不知道");
  assert.equal((await agent.onRequestPost({ request: req({ q: "x" }), env })).status, 502);
  mockModel("{}", 500);
  assert.equal((await agent.onRequestPost({ request: req({ q: "x" }), env })).status, 502);
  assert.equal((await agent.onRequestPost({ request: req({ q: "长".repeat(201) }), env })).status, 400);
  const hour = new Date().toISOString().slice(0, 13);
  const full = { ...MODEL, LP_RATE: kv({ [`ip:1.2.3.4:${hour}`]: "20" }) };
  assert.equal((await agent.onRequestPost({ request: req({ q: "x" }), env: full })).status, 429);
});
