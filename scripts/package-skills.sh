#!/usr/bin/env bash
# 把每个技能单独打成 zip（用于在 Claude.ai 等界面上传），并打一个完整包。输出到 dist/。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VER=$(python3 -c "import sys; sys.path.insert(0,'$ROOT/scripts'); import lp; print(lp.__version__)")
OUT="$ROOT/dist"; rm -rf "$OUT"; mkdir -p "$OUT/skills"
cd "$ROOT/skills"
for d in */; do (zip -qr "$OUT/skills/${d%/}.zip" "$d"); done
cd "$ROOT/.."
NAME="$(basename "$ROOT")"
zip -qr "$OUT/livepowers-v$VER.zip" "$NAME" -x "$NAME/.git/*" "$NAME/dist/*" "$NAME/**/__pycache__/*" "$NAME/.livepowers/*"
ls -1 "$OUT" "$OUT/skills"
