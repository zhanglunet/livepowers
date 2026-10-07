#!/usr/bin/env bash
# 五分钟体验：环境扫描 → 路由 MISS → 探索留证据 → 评分 → 任务看板 → 独立验收 → 注册 → 路由 HIT → 漂移 → 晨报
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; LP="python3 $HERE/../scripts/lp.py"
WORK="$(mktemp -d)"; cd "$WORK"; echo "工作目录：$WORK"
python3 "$HERE/make_demo_db.py" demo.sqlite >/dev/null
$LP init
mkdir -p .livepowers/env
python3 "$HERE/../scripts/scan_sqlite.py" demo.sqlite --fingerprint .livepowers/env/fp-1.json > .livepowers/ontology.draft.yaml
echo "--- 本体草稿（节选）"; head -20 .livepowers/ontology.draft.yaml
$LP outcome baseline --scenario stale-opps --metric "逾期重点商机数" --value 40 --target 10 --owner sales-ops
$LP registry find "把逾期的重点商机转给主管" || echo "（MISS → System 2）"
T=$($LP task new --title "逾期重点商机移交" --intent "transfer stale opportunity" --owner sales-ops --max-loops 3)
$LP task move "$T" spec --by sales-ops --reason "规格确认：逾期=30天无有效跟进"
for i in 1 2 3; do
  $LP task move "$T" explore --by agent-a --reason "第 $i 轮探索" --cost 0.8 2>/dev/null || true
  $LP evidence add --intent "transfer stale opportunity" --system S2 --outcome success --cost 0.8 \
     --verifiable --writes-state --task "$T" --note "scenario=stale-opps" >/dev/null
done
$LP candidates
$LP score --freq 30 --verifiable 2 --stability 2 --writes-state --c2 0.8 --c1 0.001 --K 20 --M 5 --p 0.8 --h 5 || true
$LP task move "$T" verify --by agent-a --reason "提交验收" --evidence pending/transfer/
$LP task move "$T" registered --by reviewer-b --reason "四道门通过" --evidence pending/transfer/acceptance.md
$LP registry add --name "转交逾期商机" --kind cli --intents "transfer stale opportunity,转交逾期商机,逾期重点商机转给主管" \
  --entry "crm opp transfer-stale --days {days}" --writes-state --tests "pytest tests/test_transfer.py" \
  --generated-by agent-a --accepted-by reviewer-b
$LP registry find "把逾期的重点商机转给主管"
$LP outcome accept --scenario stale-opps --task "$T" --by sales-ops --first
$LP outcome measure --scenario stale-opps --metric "逾期重点商机数" --value 22
$LP outcome report
python3 "$HERE/make_demo_db.py" demo.sqlite --drift >/dev/null
python3 "$HERE/../scripts/scan_sqlite.py" demo.sqlite --fingerprint .livepowers/env/fp-2.json > /dev/null
python3 "$HERE/../scripts/scan_sqlite.py" --diff .livepowers/env/fp-1.json .livepowers/env/fp-2.json || true
R=$($LP report); echo "--- 晨报：$R"; cat "$R"
