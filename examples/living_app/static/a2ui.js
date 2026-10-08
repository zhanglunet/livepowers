// 极简 A2UI v0.9.1 渲染器（只认 livepowers 展示面用到的组件）。
// 只处理数据与组件描述：全部用 textContent / SVG 属性写入，不执行任何来自消息的代码。
// 组件：Card / Column / Row / Text / Button（与 A2UI 基础组件同形）+ Badge / Kpi / Table / BarChart / LineChart / Filter（自定义组件库）。
"use strict";
(function (global) {
  const SVG = "http://www.w3.org/2000/svg";
  const fmt = (v) => (typeof v === "number" ? v.toLocaleString("zh-CN") : String(v ?? ""));
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
  function pointer(obj, path) {  // RFC 6901
    if (!path || path === "/") return obj;
    return path.split("/").slice(1).reduce((o, k) => (o == null ? undefined : o[k.replace(/~1/g, "/").replace(/~0/g, "~")]), obj);
  }
  function setPointer(obj, path, value) {
    const keys = path.split("/").slice(1);
    let o = obj;
    keys.slice(0, -1).forEach((k) => { o = o[k] = o[k] && typeof o[k] === "object" ? o[k] : {}; });
    o[keys[keys.length - 1]] = value;
  }

  function chart(kind, rows, x, y, label) {
    const W = 520, H = 210, L = 72, B = 28, T = 10;
    const max = Math.max(1, ...rows.map((r) => Number(r[y]) || 0));
    const s = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", role: "img", "aria-label": label || `${y} 按 ${x}` });
    s.append(svgEl("line", { x1: L, y1: H - B, x2: W, y2: H - B, class: "axis" }));
    for (const f of [0, 0.5, 1]) {
      const t = svgEl("text", { x: L - 6, y: H - B - f * (H - B - T) + 4, "text-anchor": "end" });
      t.textContent = fmt(Math.round(max * f)); s.append(t);
    }
    const step = (W - L) / Math.max(1, rows.length), pts = [];
    rows.forEach((r, i) => {
      const v = Number(r[y]) || 0, h = (v / max) * (H - B - T), cx = L + step * i + step / 2;
      const tip = svgEl("title"); tip.textContent = `${fmt(r[x])}：${fmt(v)}`;
      let m;
      if (kind === "BarChart") {
        const bw = Math.min(48, step - 2);
        m = svgEl("rect", { x: cx - bw / 2, y: H - B - h, width: bw, height: h, rx: 4, class: "mark" });
      } else {
        pts.push(`${cx},${H - B - h}`);
        m = svgEl("circle", { cx, cy: H - B - h, r: 4, class: "mark" });
      }
      m.append(tip); s.append(m);
      const lab = svgEl("text", { x: cx, y: H - B + 16, "text-anchor": "middle" }); lab.textContent = fmt(r[x]); s.append(lab);
    });
    if (kind === "LineChart" && pts.length) s.insertBefore(svgEl("polyline", { points: pts.join(" "), class: "series" }), s.children[1]);
    return s;
  }

  class A2UIClient {
    constructor({ onAction } = {}) { this.surfaces = {}; this.onAction = onAction || (() => {}); }

    // 处理一条 A2UI 消息；返回该 surface 的根元素（新建时）
    process(msg) {
      if (msg.createSurface) {
        const { surfaceId, catalogId } = msg.createSurface;
        const host = el("div", undefined, "a2ui-surface");
        this.surfaces[surfaceId] = { catalogId, components: {}, data: {}, host };
        return host;
      }
      const body = msg.updateComponents || msg.updateDataModel || msg.deleteSurface;
      const sf = body && this.surfaces[body.surfaceId];
      if (!sf) return null;
      if (msg.updateComponents) for (const c of msg.updateComponents.components) sf.components[c.id] = c;
      if (msg.updateDataModel) setPointer(sf.data, msg.updateDataModel.path, msg.updateDataModel.value);
      if (msg.deleteSurface) { sf.host.remove(); delete this.surfaces[body.surfaceId]; return null; }
      this.render(body.surfaceId);
      return null;
    }

    rows(sf, binding) {
      const rows = (binding && pointer(sf.data, binding.path)) || [];
      const filters = sf.data._filters || {};
      return rows.filter((r) => Object.entries(filters).every(([k, v]) => !v || !(k in r) || String(r[k]) === v));
    }

    render(surfaceId) {
      const sf = this.surfaces[surfaceId];
      if (!sf.components.root) return;  // 规范：root 到达前缓冲
      sf.host.replaceChildren(this.node(surfaceId, sf, "root"));
    }

    node(surfaceId, sf, id) {
      const c = sf.components[id];
      if (!c) return el("span");
      const kids = (ids) => (ids || []).map((k) => this.node(surfaceId, sf, k));
      switch (c.component) {
        case "Card": { const d = el("div", undefined, "a2ui-card"); d.append(this.node(surfaceId, sf, c.child)); return d; }
        case "Column": case "Row": {
          const d = el("div", undefined, c.component === "Row" ? "a2ui-row" : "a2ui-col"); d.append(...kids(c.children)); return d;
        }
        case "Text": return el(c.variant === "h2" ? "h2" : c.variant === "caption" ? "p" : "div", c.text,
          c.variant === "caption" ? "a2ui-caption" : "");
        case "Badge": return el("span", c.text, "a2ui-badge " + (c.tone || ""));
        case "Button": {
          const b = el("button", undefined, "a2ui-button"); b.type = "button";
          b.append(this.node(surfaceId, sf, c.child));
          b.addEventListener("click", () => this.onAction({ surfaceId, sourceComponentId: c.id,
            name: c.action && c.action.event && c.action.event.name, button: b }));
          return b;
        }
        case "Kpi": {
          const d = el("div", undefined, "a2ui-block"); if (c.label) d.append(el("h3", c.label));
          const total = this.rows(sf, c.rows).reduce((a, r) => a + (Number(r[c.value]) || 0), 0);
          d.append(el("div", fmt(total), "a2ui-kpi")); return d;
        }
        case "BarChart": case "LineChart": {
          const d = el("div", undefined, "a2ui-block"); if (c.label) d.append(el("h3", c.label));
          d.append(chart(c.component, this.rows(sf, c.rows), c.x, c.y, c.label)); return d;
        }
        case "Table": {
          const d = el("div", undefined, "a2ui-block"); if (c.label) d.append(el("h3", c.label));
          const rows = this.rows(sf, c.rows), cols = c.columns || Object.keys(rows[0] || {});
          const t = el("table"), head = el("tr");
          cols.forEach((k) => head.append(el("th", k, rows.length && typeof rows[0][k] === "number" ? "num" : "")));
          t.append(head);
          rows.forEach((r) => { const tr = el("tr"); cols.forEach((k) => tr.append(el("td", fmt(r[k]), typeof r[k] === "number" ? "num" : ""))); t.append(tr); });
          d.append(t); return d;
        }
        case "Filter": {
          const d = el("div", undefined, "a2ui-block"); if (c.label) d.append(el("h3", c.label));
          const sel = el("select"); sel.append(new Option("全部", ""));
          (c.options || []).forEach((o) => sel.append(new Option(o, o)));
          sel.value = pointer(sf.data, c.value.path) || "";
          sel.addEventListener("change", () => { setPointer(sf.data, c.value.path, sel.value); this.render(surfaceId); });
          d.append(sel); return d;
        }
        default: return el("div", `不支持的组件：${c.component}`, "a2ui-caption");
      }
    }
  }
  global.A2UIClient = A2UIClient;
})(window);
