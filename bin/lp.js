#!/usr/bin/env node
// lp：转发给自带的 scripts/lp.py（需要 Python 3.9+）。
"use strict";
const { spawnSync } = require("child_process");
const path = require("path");

const script = path.resolve(__dirname, "..", "scripts", "lp.py");
const candidates = process.platform === "win32" ? ["py", "python", "python3"] : ["python3", "python"];

for (const py of candidates) {
  const args = py === "py" ? ["-3", script] : [script];
  const r = spawnSync(py, [...args, ...process.argv.slice(2)], { stdio: "inherit" });
  if (r.error && r.error.code === "ENOENT") continue;
  if (r.error) throw r.error;
  process.exit(r.status === null ? 1 : r.status);
}
console.error("lp: 需要 Python 3.9+，但没有找到 python3 / python。请先安装 Python：https://www.python.org/downloads/");
process.exit(127);
