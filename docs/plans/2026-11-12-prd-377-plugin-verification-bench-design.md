# PRD-377/T1：插件安检发现验证台设计（安检发现沙箱复现过才进上架审批）

> trend issue #1881。来源：2026-11-12 GitHub 趋势日报（digests/2026-11-12.md）第 5 条，用户 2026-11-13 指令「拍板」采纳。
> 设计日：2026-11-12 · 目标仓库：zhanglunet/livepowers
> 状态：T1 设计草案，待评审。仅设计文档（纯加法 .md）；验证台内核（T2）、闸门（T3）、划界断言（T4）、验收试运行（T5）按本设计后续落地。
> 示例全部虚构占位，不出现真实内部主机名、IP、账号或密钥。

## 0. PR 门槛自查（repos.yaml default_pr_gate）

| 门槛 | 落实 |
|---|---|
| require_integration_point | **接入点：`scripts/market_gate_scan.py::scan_skill` 产出 market-gate-report-v1 的 findings 之后、`scripts/listing_inbox.py::collect(security_reviews=…)`（PRD-363 收件箱）与收录审批之前**——T2 验证台以注入式函数 `verify_finding(finding, skill_dir, recheck_fn)` 供收录流程在 collect 前调用；只把 VERIFIED finding 喂给 security_reviews |
| no_missing_channel | 只消费 scan_skill 既有 findings 结构与技能目录快照注入；复算=对同一技能目录重跑 scan_skill（同一扫描器注入式传入）；验证结论写本地 JSONL 账本（文件落库），零新外部渠道 |
| no_duplicate_module | main 上同类模块盘点：market_gate_scan.py（安检扫描本体）/ market_whitelist.py（白名单）/ listing_inbox.py（363 收件箱）/ install_snapshot.py（279 安装快照）。**本条不另起扫描器**：复算=重跑 scan_skill（注入式传入同一扫描函数），比对 findings 中同 rule_id+location 的发现存在才 VERIFIED |
| impl_requires_devlog | T2~T5 实现 PR 各附 docs/devlog/2026-11-13-prd-377-*.md 开发记录+合规核对；账本落 JSONL 文件（路径注入），不只存内存 |

## 1. 红线

| # | 红线 | 落地方式 |
|---|---|---|
| R1 | **安检发现复现验证过才进上架审批** | scan_skill 的每条 finding 先在同一技能目录快照上重跑扫描器复现（同 rule_id+location 存在）；复现不出 → UNVERIFIED——拦在收录审批外，不进 363 收件箱 |
| R2 | **验证不产生新发现** | 复算=重跑注入的同一扫描器（只读目录快照深拷贝语义——目录只读遍历），零新增检测规则、零 LLM；复现不出=UNVERIFIED 不猜不补 |
| R3 | **机器可读落账** | 每次验证 `{finding_id, rule_id, location, source_ref, dir_fingerprint, finding, reproduce, verdict}` 八件套落 JSONL 账本；缺任一 BENCH_INCOMPLETE 拒绝入账 |
| R4 | **账本 append-only + 修复二次验证才关闭** | 验证账本只增不删；技能目录变更后二次验证落新记录，关闭以最新 VERIFIED 为准 |
| R5 | 占位符纪律 | T5 检查覆盖本文件 |
| R6 | 实现 PR 只开不合并 | 等用户 review |

## 2. 借鉴对象、许可证与不复用红线

openai/codex-security（Apache-2.0，实测）+ cloudflare/security-audit-skill（MIT，实测）——只借鉴「发现→验证→修复→再验证」控制面形态；条目 schema 按本仓安检域自研，零代码复用，不引入原仓依赖。

## 3. 与既有机制划界

| 维度 | PRD-377（本条） | PRD-255 market_gate_scan | PRD-335 genui_gate | PRD-279 安装快照 | PRD-363 收件箱 |
|---|---|---|---|---|---|
| 管什么 | 逐条 **安检发现可复现** | 检出产出 | 渲染判定 | 安装可逆 | 等人审批 |
| 比对 | 发现 vs 重跑扫描器 | 无 | 无 | 版本回滚 | 无 |
| 关系 | scan_skill 之后、collect/审批之前 | 被消费 | 被区分 | 被区分 | 下游：验证过才可进 |

## 4. 验证台设计

### 4.1 条目 schema（T2 预埋）

```json
{"schema": "plugin-verify-bench/v1",
 "items": [{"finding_id": "f-001",
   "rule_id": "M-2-01",
   "location": "SKILL.md（占位）",
   "source_ref": "market-gate-report/v1#findings[0]（占位）",
   "dir_fingerprint": "sha16:…（技能目录快照）",
   "finding": {"rule_id": "M-2-01", "location": "SKILL.md（占位）", "detail": "…（占位）"},
   "reproduce": {"match": true, "detail": "…（占位）"},
   "verdict": "VERIFIED|UNVERIFIED"}]}
```

### 4.2 流程（确定性）

scan_skill findings → 逐条重跑同一扫描器（注入 recheck_fn，同一技能目录）→ 复现包含同 rule_id+location 发现 → VERIFIED / 否则 UNVERIFIED → 落账 → security_reviews 只收 VERIFIED。

## 5. 失败闸门（T3 落地）

| 错误码 | 触发 | 行为 |
|---|---|---|
| BENCH_INCOMPLETE | 八件套缺一/词表外 | 拒绝入账 |
| BENCH_REPRO_MISMATCH | 声称 VERIFIED 但复现不含同 rule_id+location（或反之） | 显形拒绝 |
| BENCH_STALE | 目录指纹与当前技能目录不符 | 拒绝复用旧验证 |

## 6. 衔接

T2 内核（verify_finding + JSONL 账本）；T3 闸门（三码+零网络零安装词面 AST）；T4 划界（与 genui_gate/白名单/收件箱划界钉值+扫描器零 import 注入重跑）；T5 样例全链回放+UNVERIFIED 拦截演练+文档无密钥。

## 7. 开放问题（留待评审/T2）

1. dir_fingerprint 口径（倾向文件清单+字节 sha 摘要，与 install_snapshot.dir_fingerprint 同族——待 T2）；
2. 收录审批侧接入的强制方式（倾向 verify_findings 包装供 collect 调用方显式接入——待 T2）。
