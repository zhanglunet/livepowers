#!/usr/bin/env node
// livepowers：把技能装进 Claude Code / Codex / Cursor 等客户端的技能目录。零依赖。
"use strict";
const fs = require("fs");
const os = require("os");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const VERSION = require(path.join(ROOT, "package.json")).version;
const MANIFEST = ".livepowers-manifest.json";
const START = "<!-- livepowers:start -->";
const END = "<!-- livepowers:end -->";
const TARGETS = {
  claude: ".claude/skills",
  cursor: ".cursor/skills",
  codex: ".agents/skills",
  agents: ".agents/skills",
};

const USAGE = `livepowers ${VERSION} · 活产品范式技能包

用法：
  livepowers install   [--target <t>] [--project [目录]] [--force] [--dry-run]
  livepowers uninstall [--target <t>] [--project [目录]] [--dry-run]
  livepowers list
  livepowers path

  --target    claude（默认）| codex | cursor | agents
  --project   装到项目目录（默认当前目录）；不加则装到个人目录 ~
  --force     覆盖已存在的同名技能
  --dry-run   只打印将要做的事，不写任何文件

codex / agents 加 --project 时，会把入口说明合并进项目的 AGENTS.md。
cursor 加 --project 时，会在项目的 .cursor/rules/ 生成 livepowers.mdc 入口规则。
lp 命令：npm i -g livepowers 后可直接运行 lp。
官网：https://livepowers.pages.dev`;

class UsageError extends Error {}

function parse(argv) {
  const opts = { cmd: argv[0], target: "claude", project: null, force: false, dryRun: false };
  for (let i = 1; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--target") {
      opts.target = argv[++i];
      if (!TARGETS[opts.target]) throw new UsageError(`未知的 --target：${opts.target}（可选 ${Object.keys(TARGETS).join(" / ")}）`);
    } else if (a === "--project") {
      const next = argv[i + 1];
      opts.project = next && !next.startsWith("--") ? path.resolve(argv[++i]) : process.cwd();
    } else if (a === "--force") opts.force = true;
    else if (a === "--dry-run") opts.dryRun = true;
    else throw new UsageError(`未知参数：${a}`);
  }
  return opts;
}

function skillNames() {
  const dir = path.join(ROOT, "skills");
  return fs.readdirSync(dir)
    .filter((n) => fs.existsSync(path.join(dir, n, "SKILL.md")))
    .sort();
}

function destOf(opts) {
  return path.join(opts.project || os.homedir(), TARGETS[opts.target]);
}

function readManifest(dest) {
  try {
    return JSON.parse(fs.readFileSync(path.join(dest, MANIFEST), "utf8"));
  } catch {
    return null;
  }
}

function agentsBlock() {
  const text = fs.readFileSync(path.join(ROOT, "AGENTS.md"), "utf8");
  const from = text.indexOf("本项目按");
  const to = text.indexOf("## 开发本仓库");
  const body = text.slice(from, to === -1 ? undefined : to).trim()
    .split("python scripts/lp.py").join("lp")
    .split("`scripts/").join("`$(livepowers path)/scripts/")
    .split("`skills/").join("`.agents/skills/");
  return `${START}\n## Livepowers\n\n${body}\n${END}`;
}

function stripBlock(text) {
  const s = text.indexOf(START);
  const e = text.indexOf(END);
  if (s === -1 || e === -1) return null;
  return (text.slice(0, s).trimEnd() + "\n\n" + text.slice(e + END.length).trimStart()).trim();
}

function withAgentsMd(opts) {
  return opts.project && (opts.target === "codex" || opts.target === "agents");
}

function withCursorRule(opts) {
  return opts.project && opts.target === "cursor";
}

function isManagedCursorRule(file) {
  if (!fs.existsSync(file)) return true;
  const text = fs.readFileSync(file, "utf8");
  return text.includes(START) && text.includes(END);
}

function cursorMdcContent() {
  const text = fs.readFileSync(path.join(ROOT, "skills", "using-livepowers", "SKILL.md"), "utf8");
  const body = text.replace(/^---[\s\S]*?---\n/, "").trim();
  return `---
description: Livepowers 活产品范式入口规则与技能路由表
alwaysApply: true
---

${START}
${body}
${END}
`;
}

function install(opts) {
  const dest = destOf(opts);
  const prev = readManifest(dest);
  const ours = new Set(prev ? prev.skills : []);
  const tag = opts.dryRun ? "[dry-run] " : "";
  let installed = 0;
  for (const name of skillNames()) {
    const to = path.join(dest, name);
    if (fs.existsSync(to) && !opts.force) {
      console.log(`${tag}跳过 ${name}（已存在，加 --force 覆盖）`);
      continue;
    }
    console.log(`${tag}安装 ${name} → ${to}`);
    if (!opts.dryRun) {
      fs.rmSync(to, { recursive: true, force: true });
      fs.cpSync(path.join(ROOT, "skills", name), to, { recursive: true });
      // 模板随入口技能一起安装，技能正文里的 templates/ 才有落点
      if (name === "using-livepowers") fs.cpSync(path.join(ROOT, "templates"), path.join(to, "templates"), { recursive: true });
    }
    ours.add(name);
    installed++;
  }
  if (!opts.dryRun) {
    fs.mkdirSync(dest, { recursive: true });
    const manifest = { version: VERSION, target: opts.target, installedAt: new Date().toISOString(), skills: [...ours].sort() };
    fs.writeFileSync(path.join(dest, MANIFEST), JSON.stringify(manifest, null, 2) + "\n");
  }
  console.log(`${tag}完成：安装 ${installed} 个技能到 ${dest}`);

  if (withAgentsMd(opts)) {
    const file = path.join(opts.project, "AGENTS.md");
    const old = fs.existsSync(file) ? fs.readFileSync(file, "utf8") : "";
    const rest = stripBlock(old) ?? old.trim();
    const next = (rest ? rest + "\n\n" : "") + agentsBlock() + "\n";
    console.log(`${tag}更新 ${file}（Livepowers 入口说明）`);
    if (!opts.dryRun) fs.writeFileSync(file, next);
  } else if (opts.target === "codex" || opts.target === "agents") {
    console.log("提示：在项目里运行 `livepowers install --target codex --project`，可把入口说明合并进项目的 AGENTS.md。");
  }

  if (withCursorRule(opts)) {
    const rulesDir = path.join(opts.project, ".cursor", "rules");
    const file = path.join(rulesDir, "livepowers.mdc");
    if (!isManagedCursorRule(file)) {
      console.log(`${tag}跳过 ${file}（保留未标记的用户规则）`);
    } else {
    console.log(`${tag}生成 ${file}（Cursor 入口规则）`);
    if (!opts.dryRun) {
      fs.mkdirSync(rulesDir, { recursive: true });
      fs.writeFileSync(file, cursorMdcContent());
    }
    }
  } else if (opts.target === "cursor") {
    console.log("提示：在项目里运行 `livepowers install --target cursor --project`，可在项目的 .cursor/rules/ 生成 livepowers.mdc 入口规则。");
  }

  if (opts.target === "claude") {
    console.log("提示：想在会话启动时自动注入入口技能，推荐用插件方式安装：\n  /plugin marketplace add zhanglunet/livepowers\n  /plugin install livepowers@livepowers-marketplace");
  }
  console.log("技能中的 lp 命令：npm i -g livepowers（需要 Python 3.9+）");
}

function uninstall(opts) {
  const dest = destOf(opts);
  const tag = opts.dryRun ? "[dry-run] " : "";
  const manifest = readManifest(dest);
  if (!manifest) {
    console.log(`${dest} 下没有 Livepowers 安装记录`);
  } else {
    for (const name of manifest.skills) {
      console.log(`${tag}删除 ${path.join(dest, name)}`);
      if (!opts.dryRun) fs.rmSync(path.join(dest, name), { recursive: true, force: true });
    }
    if (!opts.dryRun) fs.rmSync(path.join(dest, MANIFEST), { force: true });
    console.log(`${tag}完成：卸载 ${manifest.skills.length} 个技能`);
  }
  if (withAgentsMd(opts)) {
    const file = path.join(opts.project, "AGENTS.md");
    const rest = fs.existsSync(file) ? stripBlock(fs.readFileSync(file, "utf8")) : null;
    if (rest !== null) {
      console.log(`${tag}从 ${file} 移除 Livepowers 入口说明`);
      if (!opts.dryRun) {
        if (rest) fs.writeFileSync(file, rest + "\n");
        else fs.rmSync(file);
      }
    }
  }
  if (withCursorRule(opts)) {
    const file = path.join(opts.project, ".cursor", "rules", "livepowers.mdc");
    if (fs.existsSync(file) && !isManagedCursorRule(file)) {
      console.log(`${tag}跳过 ${file}（保留未标记的用户规则）`);
    } else if (fs.existsSync(file)) {
      console.log(`${tag}删除 ${file}（Cursor 入口规则）`);
      if (!opts.dryRun) fs.rmSync(file, { force: true });
    }
  }
}

function list() {
  const dirs = new Set();
  for (const base of [os.homedir(), process.cwd()]) {
    for (const rel of Object.values(TARGETS)) dirs.add(path.join(base, rel));
  }
  let found = 0;
  for (const dest of dirs) {
    const m = readManifest(dest);
    if (!m) continue;
    found++;
    console.log(`${dest}：${m.skills.length} 个技能（v${m.version}）`);
  }
  if (!found) console.log("未安装（运行 livepowers install）");
}

function main(argv) {
  if (!argv.length || argv[0] === "-h" || argv[0] === "--help" || argv[0] === "help") {
    console.log(USAGE);
    return 0;
  }
  if (argv[0] === "-v" || argv[0] === "--version") {
    console.log(VERSION);
    return 0;
  }
  const opts = parse(argv);
  switch (opts.cmd) {
    case "install": install(opts); return 0;
    case "uninstall": uninstall(opts); return 0;
    case "list": list(); return 0;
    case "path": console.log(ROOT); return 0;
    default: throw new UsageError(`未知命令：${opts.cmd}`);
  }
}

try {
  process.exitCode = main(process.argv.slice(2));
} catch (e) {
  if (!(e instanceof UsageError)) throw e;
  console.error(`livepowers: ${e.message}\n\n${USAGE}`);
  process.exitCode = 2;
}
