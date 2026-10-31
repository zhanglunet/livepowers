# PRD-279/T1：技能安装/升级快照 + 一键恢复设计（install-snapshot-v1）

- 日期：2026-10-29
- 来源：2026-10-28 趋势日报 livepowers 第 1 条（⭐），用户当日拍板采纳
- trend issue：[zhanglunet/trend#1396](https://github.com/zhanglunet/trend/issues/1396)
- 中央 PRD：`trend/adopted/PRD-279-livepowers-skill-install-snapshot.md`
- 状态：T1 设计稿，待评审；实现类任务（T2–T4）只开 PR 不合并
- 同批主题：本批「可逆改动包」14 仓同构——先快照、再改动、一键回上一版

## 1. 目标与非目标

**目标**：装新技能或升级旧技能**之前**，先快照旧版技能目录（目录内容指纹）与已装清单；新版出问题时一键恢复（restore）旧版；恢复后留一条「已回滚到某版」记录（技能名/版本/时间/触发者）。与收录安检互补成完整生命周期：**安检管进门、快照管退出**。

**非目标**：
- **不替代安检（进门照扫）**——PRD-255 收录安检照常先行，快照不是放行手段，恢复也不重扫放行；
- 不做跨机同步——快照/恢复纯本地，零外联；
- **不保存多版本历史（只留上一版）**——每个技能只保留"最近一次变更前"的快照槽位，更早状态靠 git 历史，不做版本库。

## 2. 与既有能力的划界

| 既有能力 | 关系 |
|---|---|
| PRD-247（excel 仓安装安检门） | 同源模式、异仓实现；247 是 excel 分析链进门安检——本仓不含该实现，仅模式同族 |
| PRD-255 市场收录安检（SkillSpector 式） | **安检管进门**：收录流程内 `admission_flow` 先扫，HIGH/CRITICAL 不收录；本条**管退出**：收录通过、安装落地之后可逆。安检不产生回滚能力，快照不产生放行能力（衔接见 3.4） |
| PRD-094 收录 checklist | 收录清单记录"为什么收录"（含 gate_* 字段）；快照记录"装之前长什么样"——清单是准入档案，快照是退出保险，互不替代 |
| PRD-172 角色包 / PRD-003 插件市场 | 角色包与插件是安装对象的两类载体；本条快照以**技能目录**为单位，对两类载体统一适用（按目录指纹，不区分打包形态） |
| PRD-112 并行专家编排 | 无关（运行期编排）；本条只管安装/升级这个落盘动作的可逆 |
| git 历史 | git 记录本仓自带技能的变更历史；快照服务**安装动作的运行时回滚点**（第三方技能安装往往不走 git），两者互为对账不互替 |

## 3. 方案设计

### 3.1 快照对象与时机

**快照对象**（每次安装/升级动作前，按被改动的技能目录）：

| 对象 | 内容 |
|---|---|
| 技能目录 | `skills/<技能名>/` 全量文件（安装/升级的落盘单位） |
| 已装清单 | 机读已装清单 `ops/installed-skills.json`（`installed-manifest-v1`，见 3.3）的完整副本 |
| 触发上下文 | 收录安检报告引用（admission_ref，来自 `admission_flow` 的 checklist/report） |

- **快照时机：挂在确认动作后、落盘动作前强制触发**——`admission_flow` 判定 admitted 之后、技能目录写入之前，快照必须已落盘；快照失败则安装中止（fail-close：宁可装不上，不可回不去）；
- 快照槽位：`ops/install-snapshots/<技能名>/latest/`——**每技能一个槽位，只留上一版**；新快照写入前旧快照自然被覆盖（覆盖事件记入审计），不保存多版本历史；
- 快照以技能目录为单位，可对多技能批量安装逐技能各出一份快照（槽位互不覆盖）。

### 3.2 快照 schema：`install-snapshot-v1`

```json
{
  "schema": "install-snapshot-v1",
  "snapshot_id": "iss-20261029-b2c3d4e5",
  "created_at": "2026-10-29T10:00:00+08:00",
  "skill": { "name": "example-skill", "old_version": "0.3.1", "dir": "skills/example-skill/" },
  "change_kind": "upgrade",
  "dir_fingerprint": {
    "algorithm": "sha256-per-file",
    "files": [
      { "path": "skills/example-skill/SKILL.md", "sha256": "sha256:<占位>", "bytes": 4096 }
    ],
    "fingerprint": "sha256:<占位>"
  },
  "installed_manifest_snapshot_ref": "ops/install-snapshots/example-skill/latest/installed-manifest.json",
  "admission_ref": { "report_ref": "<market-gate-report-v1 存档引用占位>", "decision": "admitted" },
  "notes": []
}
```

- **目录内容指纹**：逐文件 sha256 + 汇总指纹——恢复后重算必须一致，否则恢复失败告警（绝不静默半恢复）；
- `old_version`：被覆盖版本的技能声明版本（SKILL.md frontmatter / 插件元数据；首次安装时为 null，记 `change_kind: "install"`）；
- 快照目录内含 `snapshot.json`（本 schema）+ 旧版技能目录完整副本 + 已装清单副本——**自足可恢复，不依赖网络与外部状态**；
- 已装清单的"快照"= 落盘前的完整副本，恢复时一并还原（防止"目录回去了、清单说新版还在"的漂移）。

### 3.3 已装清单：`installed-manifest-v1`

```json
{
  "schema": "installed-manifest-v1",
  "generated_at": "2026-10-29T10:00:00+08:00",
  "skills": [
    { "name": "example-skill", "version": "0.3.1", "source": "<来源占位：marketplace|local|builtin>", "installed_at": "2026-10-20T08:00:00+08:00" }
  ]
}
```

- 首次启用快照机制时由扫描 `skills/` 现状生成基线（机读，进 git）；
- 每次安装/升级/恢复同步更新；与快照副本互为校验。

### 3.4 与收录流程衔接（admission_flow 通过后自动先快照）

安装唯一入口（T3 实现形态）：

```
install_after_admission(skill_dir, declared, verified, ...):
  1. admission_flow(...)                       # PRD-255/T3：安检，HIGH/CRITICAL 不收录
  2. admitted == False → 终止（不快照不安装）
  3. snapshot_install(skill_dir)               # 本条：强制快照，失败 → 安装中止（fail-close）
  4. 落盘安装 + 更新 installed-manifest-v1     # 之后才允许写技能目录
```

- 快照作为安装动作的**内嵌第一步**，不依赖调用方记得手动快照——"快照遗漏导致不可回滚"由流程结构性排除；
- `admission_flow` 接口形态以 PRD-255/T1 设计文档（docs/plans/2026-10-28-prd-255-market-gate.md）与当次评审结论为准（其实现 PR 尚未合并，本条只依赖其接口契约：返回 `admitted/report/checklist`）；
- 手工安装（绕过入口）没有门：T3 提供机检——快照审计与已装清单对账，发现"清单新增/变更但无对应快照记录"即告警。

### 3.5 restore 接口与「已回滚到某版」记录

**接口（T2 实现）**：

```
snapshot_install(skill_dir, change_kind) -> install-snapshot-v1
restore_install(snapshot_id, reason) -> rollback-record-v1
```

**恢复语义（全部为硬规则）**：

1. 只恢复到该技能槽位内的上一版快照（`snapshot_id` 即 `latest`）；逐字节还原技能目录 + 已装清单副本，还原后重算目录指纹必须与快照一致，不一致即失败告警；
2. **快照槽不因恢复清空**——恢复后槽内内容与目录一致；若要把"回滚前的新版"装回来，重新走收录安检 + 安装流（自动形成新快照），全程留审计，不存在"恢复后无路可走"；
3. 恢复**不重扫放行、不新增任何许可**：恢复旧版 ≠ 安检通过新版——旧版当初装进来时已过安检，恢复只是回到那个已过安检的状态；新版要再进来仍须重新过 `admission_flow`。

**`rollback-record-v1`**（追加进 `ops/install-snapshots/audit.jsonl`，append-only）：

```json
{
  "schema": "rollback-record-v1",
  "rollback_id": "ipr-20261029-c3d4e5f6",
  "at": "2026-10-29T15:00:00+08:00",
  "skill_name": "example-skill",
  "from_version": "0.4.0",
  "to_version": "0.3.1",
  "snapshot_id": "iss-20261029-b2c3d4e5",
  "trigger": { "actor_role": "<operator|system，只记角色不记个人身份>", "reason": "<必填一句话：新版误删引用模板，恢复上一版>" },
  "verify": "passed"
}
```

- **「已回滚到某版」记录四要素必填**：技能名 / 版本（from→to）/ 时间 / 触发者（角色 + 理由）——T4 审计断言逐项校验缺一即测试失败；
- 安装/升级/覆盖快照事件同样入 `audit.jsonl`（append-only），与快照槽位对账。

### 3.6 演练样本（T2 夹具、T5 回放，全虚构）

| 样本 | 内容（全虚构） | 预期 |
|---|---|---|
| P-1 首次安装 | 虚构技能 `example-skill` v0.1.0 通过收录后安装 | 安装前自动快照（`change_kind: install`，old_version null）；清单新增 |
| P-2 升级后回滚 | v0.3.1 → v0.4.0 后新版有问题，一键恢复 | 目录与清单回到 v0.3.1，指纹一致；留「已回滚到 v0.3.1」记录 |
| N-1 跳过快照 | 模拟直接写技能目录不经入口 | 机检对账告警（清单变更无快照记录） |
| N-2 未过安检就装 | 模拟 admission_flow 返回 blocked 仍尝试安装 | 终止：不快照、不安装、清单不变 |
| N-3 恢复后指纹不符 | 人为篡改快照副本一个字节 | restore 报错退出，verify: failed 入审计 |
| N-4 快照含密钥 | 虚构技能文件内嵌 `<REDACTED>` 模式 | 快照前置零密钥扫描拦下（安装同时中止） |

## 4. 安全红线

1. **安检管进门、快照管退出**：快照/恢复不是放行通道——恢复不重扫，新版进入必须过 `admission_flow`；安检不因有快照而放松；
2. **fail-close**：该快照时快不了 ⇒ 安装中止；恢复后指纹对不上 ⇒ 恢复失败告警；
3. 快照/记录零密钥：快照落盘前跑既有零密钥扫描，命中即中止（N-4）；快照目录、审计、文档密钥扫描 0 命中；
4. 本地处理零外联（不做跨机同步，快照自足）；审计 append-only，记录只含角色不含个人身份；
5. 文档与示例无真实内部主机名/IP/账号/密钥，占位符一律 `<占位>` 形态；示例技能名、版本号、快照号全虚构。

## 5. T2–T5 任务拆分（按 PRD）

| 任务 | 内容 | 验收标准（PRD 原文口径） |
|---|---|---|
| T2 | 快照存储与回滚最小实现（snapshot/restore/审计记录） | 样例可快照可回滚，审计可查，有测试 |
| T3 | 与收录流程衔接：admission_flow 通过后安装动作自动先快照 | 安装前快照自动发生，有测试 |
| T4 | 回滚记录审计断言（技能名/版本/时间/触发者） | 审计断言通过 |
| T5 | 验收试运行：样例全流程回放 + 回滚演练 + 文档无密钥 | 快照回滚全链通过；红线断言全过；文档无密钥 |

依赖关系：T1 → T2 → T3 → T4 → T5。

## 6. T5 验收标准

1. P-1/P-2 全链：收录通过 → 安装前快照自动发生 → 落盘 → 升级 → 一键恢复 → 指纹与清单双还原；「已回滚到 v0.3.1」记录四要素齐全；
2. N-1 对账机检告警；N-2 blocked 即终止；N-3 篡改被检出且 verify: failed 入审计；N-4 零密钥扫描拦下快照与安装；
3. `audit.jsonl` 全事件可查（快照/覆盖/恢复），每技能槽位恒只有一份上一版快照（不保存多版本历史）；
4. 恢复动作零外联、不触发任何放行语义；审计 append-only 无改写路径；
5. 全部 schema/记录/文档密钥扫描 0 命中、真实主机名/IP/账号 0 命中；示例全虚构。

## 7. 借鉴划界

- [Gathin23/cleanyourtv](https://github.com/Gathin23/cleanyourtv)：GitHub License API 实测 **NOASSERTION（无协议）**。**仅借鉴「先快照再改动、一键还原」的形态思路，不复用其任何代码与文案**；`install-snapshot-v1` schema、目录内容指纹、已装清单快照、restore 语义（fail-close/槽位保留/不重扫放行）、四要素回滚记录均为本仓原创设计。
- 与日报原文的差异修正：日报未核实许可证，实测无协议——借鉴口径据此收紧为"仅形态思路零复用"（同批 14 仓统一口径）。
