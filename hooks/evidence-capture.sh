#!/usr/bin/env bash
# PostToolUse(Bash) / Stop：把钩子 stdin 的 JSON 交给 lp hook，自动采集证据。
# 永不阻塞 Agent：出错静默，始终 exit 0。设 LP_HOOK_CAPTURE=0 可关闭。
ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
[ "${LP_HOOK_CAPTURE:-1}" = "0" ] && exit 0
python3 "$ROOT/scripts/lp.py" hook "${1:-post-tool}" >/dev/null 2>&1 || true
exit 0
