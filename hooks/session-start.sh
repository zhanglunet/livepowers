#!/usr/bin/env bash
# SessionStart：注入 using-livepowers，确保 Agent 在任何任务前先检查技能。
# 按平台输出不同字段：Claude Code → hookSpecificOutput.additionalContext；Cursor → additional_context；其他 → additionalContext
set -euo pipefail
ROOT="${CLAUDE_PLUGIN_ROOT:-${CURSOR_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}}"
SKILL="$ROOT/skills/using-livepowers/SKILL.md"
python3 - "$SKILL" "$ROOT" <<'PY'
import json, os, re, sys
path, root = sys.argv[1], sys.argv[2]
try:
    text = open(path, encoding="utf-8").read()
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
except OSError as e:
    text = f"(无法读取 using-livepowers：{e})"
msg = ("<EXTREMELY_IMPORTANT>\n你已安装 Livepowers。以下是 using-livepowers 技能全文；开始任何任务前，"
       "按其路由表检查并使用相应技能（其他技能用 Skill 工具加载）。脚本位于 " + os.path.join(root, "scripts") + "/。\n\n"
       + text + "\n</EXTREMELY_IMPORTANT>")
if os.environ.get("CURSOR_PLUGIN_ROOT"):
    out = {"additional_context": msg}
elif os.environ.get("CLAUDE_PLUGIN_ROOT") and not os.environ.get("COPILOT_CLI"):
    out = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": msg}}
else:
    out = {"additionalContext": msg}
print(json.dumps(out, ensure_ascii=False))
PY
