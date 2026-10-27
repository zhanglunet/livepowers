# PRD-255/T1：SkillSpector 式市场收录安检设计（对齐 PRD-094 收录清单）

- 日期：2026-10-28
- 来源：2026-10-27 趋势日报 livepowers 第 1 条（⭐），用户当日拍板采纳
- trend issue：[zhanglunet/trend#1275](https://github.com/zhanglunet/trend/issues/1275)
- 中央 PRD：`trend/adopted/PRD-255-livepowers-skillspector-market-gate.md`
- 状态：T1 设计稿，待评审；实现类任务（T2–T4）只开 PR 不合并

## 1. 目标与非目标

**目标**：技能进市场收录流程时先过安检——风险分 + 严重度，**HIGH 及以上不收录**；安检报告随收录清单（PRD-094）一起存档；误报走白名单（理由 + 复核人签字）。本条是 PRD-094 收录 checklist 里**自动化的安检项**。

**非目标**：
- 不替代 PRD-094 清单本身——安检是清单中的一项，其余人工检查项不动；
- 不重复 excel/contract 两仓的安检实现（模式同源，各自落地；本仓聚焦收录场景与清单字段映射）；
- 不外传技能内容，扫描本地执行。

## 2. 与既有能力的划界

| 既有能力 | 关系 |
|---|---|
| PRD-094 收录 checklist | 本条是清单里的自动化安检项；报告存档字段与清单字段一一映射（3.2） |
| PRD-112 并行专家编排 | 无关（那是编排）；本条只管收录前的技能安检 |
| livepowers 既有 slim_gate / adversarial gate | 闸门形态同族（退出码+JSON 报告），安检作为收录流程的新闸门接入同套门禁纪律 |

## 3. 方案设计

### 3.1 扫描维度与门槛（收录场景）

| # | 维度 | 检查方式（T2 静态适配） | 基础权重 |
|---|---|---|---|
| M-1 | 隐藏指令与注入 | SKILL.md 不可见字符、零宽字符、base64 大块、范围外指令 | 25 |
| M-2 | 过度授权 | 权限面（写/网络/exec）超出技能声明用途 | 25 |
| M-3 | 凭据访问 | 环境密钥名、`.env`、凭证路径触碰 | 25 |
| M-4 | 收录材料一致性 | 技能声明（name/version/description/license）与收录申请材料不一致；license 字段缺失或与上游实测不符 | 25 |

- 0–100 分；`CRITICAL ≥ 80 / HIGH ≥ 60 / MEDIUM ≥ 30 / LOW`；`floor: HIGH` 支持（M-3 命中凭证路径）；
- **门槛：HIGH/CRITICAL 不收录**；被拦进待复核清单，可经白名单放行或修正后重扫。

### 3.2 报告存档字段与 PRD-094 清单映射（T1 核心交付）

`market-gate-report-v1`（JSON，形态对齐既有闸门报告）：

```json
{
  "schema": "market-gate-report-v1",
  "scanned_at": "<ISO8601>",
  "skill": { "name": "...", "version": "...", "license_declared": "MIT", "license_verified": "MIT" },
  "score": 0, "severity": "HIGH", "decision": "blocked",
  "findings": [ { "rule_id": "M-4-01", "severity_suggest": "HIGH", "evidence": "<占位符化>", "deduct": 25 } ],
  "whitelist_applied": [],
  "scan_version": "0.1.0"
}
```

与 PRD-094 收录清单的字段映射（收录清单新增"安检列"）：

| 收录清单字段（新增） | 来源（报告字段） | 说明 |
|---|---|---|
| `gate_report_ref` | 报告存档路径 | 报告本体随清单归档 |
| `gate_score / gate_severity / gate_decision` | score / severity / decision | 快照冗余，清单自足可读 |
| `gate_whitelist` | whitelist_applied[].entry_id | 放行留痕（w/ 理由+复核人在白名单文件中） |
| `gate_scan_version` | scan_version | 规则表版本，重扫可比对 |

`evidence` 占位符化硬规则（密钥/内网名替换 `<REDACTED>`）；M-4 的 license 实测以 GitHub License API 结果为准，**收录申请单声明的 license 与实测不符直接 HIGH**。

### 3.3 白名单与复核签字（T4）

条目：`entry_id / rule_id / scope(技能名+版本) / reason(必填) / reviewer(必填) / decided_at / expires_at(默认 90 天)`；只放行单条规则；命中留痕进清单 `gate_whitelist`；过期回拦。复核签字落既有审计记录机制。

### 3.4 正负样本清单（T2 夹具、T5 回放）

| 样本 | 内容（全虚构） | 预期 |
|---|---|---|
| P-1 干净技能 | 声明与实测一致、无危险模式 | LOW，收录 |
| N-1 隐藏指令 | 零宽字符指令外传 | M-1，HIGH，不收录 |
| N-2 过度授权 | 申请写共享目录 | M-2，HIGH，不收录 |
| N-3 凭据触碰 | 读 `<HOME>/.env` | M-3（floor HIGH），HIGH，不收录 |
| N-4 license 不符 | 声明 MIT、实测无协议 | M-4，HIGH，不收录（**许可证红线场景**） |

## 4. 安全红线

1. HIGH+ 不收录（硬闸门）；被拦可复核（白名单/修正重扫），不是自动销毁；
2. 报告与清单无真实密钥/内网主机名（占位符化）；
3. **license 实测优先于声明**（不信自述，License API 为准）——本条同时服务许可证红线；
4. 白名单 reason+reviewer 必填、90 天过期；
5. 扫描零外联（漏洞/license 信息用本地快照缓存 + 显式 API 调用记录）。

## 5. T2–T5 任务拆分（按 PRD）

| 任务 | 内容 | 验收标准（PRD 原文口径） |
|---|---|---|
| T2 | 安检适配最小实现 | 正负样本可产出报告 |
| T3 | 接入收录流程：HIGH 不收录 | 闸门有测试 |
| T4 | 误报白名单 + 复核人签字 | 可审计 |
| T5 | 验收试运行：收录样例全流程 | HIGH 不收录；报告随清单；无密钥 |

## 6. T5 验收标准

1. N-1…N-4 全部不收录（HIGH），P-1 收录通过；
2. 每个收录条目的清单带 `gate_*` 五字段，报告本体随清单归档可回放；
3. 白名单放行 N 类误报演示：`gate_whitelist` 留痕 + 白名单文件签字齐全；
4. license 声明与实测不符样例（N-4）被拦——许可证红线断言；
5. 报告/清单/白名单密钥扫描 0 命中。

## 7. 借鉴划界

- [NVIDIA/SkillSpector](https://github.com/NVIDIA/SkillSpector)：License API 实测 **Apache-2.0**。仅借鉴"安检先行、分数门槛、白名单"模式，不复制代码/规则表/文案；M 维度与清单映射设计为本仓原创。
- 与日报原文的差异修正：无。
