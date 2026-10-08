// 展示面校验规则（浏览器演示与 Node 测试共用）。与 scripts/lp.py 的 surface_problems 同一套规则：
// 只读单条查询、只引用本体内对象、不带可执行代码、不内嵌结果、组件类型受限；外加演示专用的两条：
// 不允许递归 CTE（防止浏览器卡死），不允许读敏感列。
"use strict";
(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.SurfaceRules = api;
})(typeof self !== "undefined" ? self : this, function () {
  const COMPONENTS = { kpi: ["data", "value"], table: ["data"], bar: ["data", "x", "y"], line: ["data", "x", "y"], filter: ["param"] };
  const CODE_KEYS = new Set(["script", "code", "html", "js", "javascript", "eval", "function", "handler", "onclick"]);
  const CODE_VALUE = /<\s*script|javascript:|\bon[a-z]+\s*=\s*["']|=>|\bfunction\s*\(|\beval\s*\(/i;
  const SQL_WRITE = /\b(insert|update|delete|drop|alter|create|replace|truncate|attach|detach|pragma|grant|revoke|merge|call|exec|execute|vacuum|reindex|copy|recursive)\b/i;
  const SQL_REF = /\b(?:from|join)\s+([A-Za-z_][\w.]*)/gi;
  const SQL_CTE = /(?:\bwith|,)\s*([A-Za-z_]\w*)\s+as\s*\(/gi;
  const SENSITIVE = /\b(phone|mobile|email|password|id_?card|address|salary)\b/i;
  const WILDCARD = /\bselect\s+(?:distinct\s+)?\*|[\w"\]]\.\*|,\s*\*/i;   // 不允许 SELECT * / t.*（count(*) 不受影响）

  function sqlProblems(sql, allowed) {
    const errs = [];
    const s = String(sql).replace(/'(?:[^']|'')*'/g, "''").trim().replace(/;\s*$/, "");
    if (!/^(select|with)\b/i.test(s)) errs.push("查询必须以 SELECT 或 WITH 开头（只读）");
    if (s.includes(";")) errs.push("查询只能有一条语句");
    const w = s.match(SQL_WRITE);
    if (w) errs.push(`查询含不允许的关键字 ${w[1].toUpperCase()}`);
    if (SENSITIVE.test(s)) errs.push("查询读取了敏感字段");
    if (WILDCARD.test(s)) errs.push("不允许 SELECT *，请列出需要的列（避免带出敏感字段）");
    const ctes = new Set([...s.matchAll(SQL_CTE)].map((m) => m[1].toLowerCase()));
    for (const m of s.matchAll(SQL_REF)) {
      const name = m[1].toLowerCase().split(".").pop();
      if (!ctes.has(name) && !allowed.has(name)) errs.push(`查询引用了本体外的对象 ${m[1]}`);
    }
    return errs;
  }

  function codeProblems(obj, path) {
    const errs = [];
    if (Array.isArray(obj)) obj.forEach((v, i) => errs.push(...codeProblems(v, `${path}[${i}]`)));
    else if (obj && typeof obj === "object") {
      for (const [k, v] of Object.entries(obj)) {
        if (CODE_KEYS.has(k.toLowerCase()) || /^on[A-Z_]/.test(k)) { errs.push(`${path}.${k}：不允许携带代码或事件处理器`); continue; }
        if (k !== "query") errs.push(...codeProblems(v, `${path}.${k}`));
      }
    } else if (typeof obj === "string" && CODE_VALUE.test(obj)) errs.push(`${path}：值里出现疑似代码`);
    return errs;
  }

  // 校验一份展示面；allowed 是本体里可引用的表 / 视图名（小写）
  function validate(s, allowed) {
    if (!s || typeof s !== "object" || Array.isArray(s)) return ["展示面必须是 JSON 对象"];
    const errs = [];
    for (const k of ["id", "tier", "data", "components"]) if (!(k in s)) errs.push(`缺少字段 ${k}`);
    if (errs.length) return errs;
    if (!["ephemeral", "fixed"].includes(s.tier)) errs.push("tier 只能是 ephemeral / fixed");
    errs.push(...codeProblems(s, "$"));
    const data = s.data && typeof s.data === "object" && !Array.isArray(s.data) ? s.data : {};
    const names = Object.keys(data);
    if (!names.length || names.length > 3) errs.push("data 需要 1–3 个数据源");
    for (const [name, d] of Object.entries(data)) {
      const src = (d && d.source) || {};
      if (!["table", "view"].includes(src.type)) errs.push(`data.${name}.source.type 只能是 table / view`);
      else if (!allowed.has(String(src.name || "").toLowerCase())) errs.push(`data.${name} 的来源 ${src.name} 不在本体里`);
      if (!d || typeof d.query !== "string" || !d.query.trim()) errs.push(`data.${name} 缺少 query`);
      else if (d.query.length > 2000) errs.push(`data.${name} 的查询过长`);
      else errs.push(...sqlProblems(d.query, allowed).map((e) => `data.${name}：${e}`));
      if (d && ("rows" in d || "values" in d)) errs.push(`data.${name}：不内嵌结果数据`);
    }
    const comps = Array.isArray(s.components) ? s.components : [];
    if (!comps.length || comps.length > 6) errs.push("components 需要 1–6 个组件");
    const strList = (v) => Array.isArray(v) && v.length <= 20 && v.every((x) => typeof x === "string");
    comps.forEach((c, i) => {
      const need = COMPONENTS[c && c.type];
      if (!need) { errs.push(`components[${i}].type 不支持：${c && c.type}`); return; }
      for (const f of need) if (!c[f]) errs.push(`components[${i}]（${c.type}）缺少 ${f}`);
      for (const f of ["data", "value", "x", "y", "param", "label", "id"])
        if (f in c && typeof c[f] !== "string") errs.push(`components[${i}].${f} 必须是字符串`);
      for (const f of ["columns", "options"])
        if (f in c && !strList(c[f])) errs.push(`components[${i}].${f} 必须是字符串数组`);
      if (c.data && !(c.data in data)) errs.push(`components[${i}] 引用了未定义的数据 ${c.data}`);
    });
    return errs;
  }

  function tokens(t) {
    const s = new Set(String(t).toLowerCase().match(/[a-z0-9]+/g) || []);
    const cjk = String(t).replace(/[^一-鿿]/g, "");
    for (let i = 0; i < cjk.length - 1; i++) s.add(cjk.slice(i, i + 2));
    return s;
  }

  // 问题被候选文本覆盖的比例（0–1）：用来判断预置展示面是否真的回答了这个问题，避免答非所问
  function coverage(question, candidate) {
    const q = tokens(question), c = tokens(candidate);
    if (!q.size) return 0;
    let n = 0;
    q.forEach((x) => { if (c.has(x)) n++; });
    return n / q.size;
  }

  // 执行后再查一遍结果列：别名或其他写法绕过了查询文本检查时，在下发前拦下
  function resultProblems(columns) {
    const bad = (columns || []).filter((c) => SENSITIVE.test(String(c)));
    return bad.length ? [`结果包含敏感字段：${bad.join(", ")}`] : [];
  }

  return { validate, sqlProblems, resultProblems, coverage, tokens, COMPONENTS };
});
