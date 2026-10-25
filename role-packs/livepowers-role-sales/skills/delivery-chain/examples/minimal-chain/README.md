# 最小链示例 minimal-chain

示范链 `delivery-chain` 有五段（含人工验收门），第一次接触链形态时偏重。
本示例只保留它的前两段，是能独立跑通的最小链：

| 段 id | skill | 输入 | 产出 |
|---|---|---|---|
| scan | env-scan-ontology | 链输入 request | ontology-draft |
| specify | ontology-grounded-spec | ontology-draft | spec-doc |

无人工门、无可跳段，一次运行即全链完成。适合用来对照《链式 skill 使用指南》
逐项核对 chain.yaml 字段、运行产物目录与 manifest 结构。

## 试跑（在仓库根目录执行）

```bash
# 校验（本示例不在 skills/ 顶层，运行器靠当前目录定位仓库根；
# 不在仓库根时改用 --repo-root <仓库根>）
python scripts/chain_runner.py validate skills/delivery-chain/examples/minimal-chain

# 运行（产物落 <工作区>/.livepowers/chains/minimal-chain/runs/<run-id>/）
python scripts/chain_runner.py run skills/delivery-chain/examples/minimal-chain \
  --workspace . --param request="统计本月退款率"

# 查看状态
python scripts/chain_runner.py status <run-id> --workspace .
```

三条命令的退出码：校验通过 / 全链完成 / 查询成功均为 0；
退出码全表（0–4）见使用指南「退出码」一节。
