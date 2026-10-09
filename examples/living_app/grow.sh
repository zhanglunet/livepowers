#!/usr/bin/env bash
# 模拟"生长"：次抛已申请固化后，智能体生成新结构、孪生对账、评审采纳、生产部署、注册为固定页。
# 用法：bash examples/living_app/grow.sh <工作目录>   （工作目录里要有 demo.sqlite 与 .livepowers/，且已有一次 promote）
# 演示中"智能体生成"的产物是预置文件：ddl/ 下的视图与回滚脚本、surfaces/ 下的固化展示面。
set -euo pipefail
APP="$(cd "$(dirname "$0")" && pwd)"; LP="python3 $APP/../../scripts/lp.py"
cd "$1"
FIXED="$APP/surfaces/pipeline-by-region.fixed.json"; DDL="$APP/ddl/v_pipeline_by_region.sql"
RB="$APP/ddl/v_pipeline_by_region.rollback.sql"
REC=$(grep -l '"promoted": {' .livepowers/surfaces/ephemeral/pipeline_by_region-*.json | tail -1)
T=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['promoted']['task'])" "$REC")
echo "== 申请固化的次抛：${REC}（看板任务 ${T}）"

echo "== 1-2 规格与本体变更：新视图 v_pipeline_by_region 进本体"
grep -q "v_pipeline_by_region" .livepowers/ontology.draft.yaml || \
  printf '\nviews:\n  - name: v_pipeline_by_region   # 各地区在途商机金额（由次抛固化）\n' >> .livepowers/ontology.draft.yaml
$LP task move "$T" spec --by sales-ops --reason "规格确认：在途=未成交且未丢单，按客户地区汇总"
$LP task move "$T" explore --by agent-a --reason "生成视图 DDL、回滚脚本与固化展示面"

echo "== 3-5 孪生演练与对账"
cp demo.sqlite twin.sqlite
$LP surface validate "$FIXED"
$LP surface deploy "$FIXED" --env twin --twin --by agent-a --db twin.sqlite --ddl "$DDL" --rollback "$RB"
$LP surface reconcile "$REC" "$FIXED" --db twin.sqlite

echo "== 6 独立验收（采纳人 ≠ 生成者）"
$LP task move "$T" verify --by agent-a --reason "孪生对账一致" --evidence "$REC"
$LP task move "$T" registered --by reviewer-b --reason "四道门通过" --evidence .livepowers/deployments/pipeline_by_region/twin.json

echo "== 7 生产迁移（失败自动回滚），留部署回执"
$LP surface deploy "$FIXED" --env prod --by ops --db demo.sqlite --ddl "$DDL" --rollback "$RB"

echo "== 8 注册为固定页"
$LP registry add --name "各地区在途商机" --id cap_pipeline_by_region --kind view \
  --intents "pipeline by region,各地区在途商机,在途商机金额" --entry "v_pipeline_by_region" --ui "$FIXED" \
  --ontology-version 0.2.0-draft --generated-by agent-a --accepted-by reviewer-b
$LP pages list
