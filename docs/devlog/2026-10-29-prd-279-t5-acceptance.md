# PRD-279/T5 验收试运行记录：技能安装/升级快照全流程演练 + 回滚审计 + 文档无密钥

- 日期：2026-10-30
- trend issue：[zhanglunet/trend#1400](https://github.com/zhanglunet/trend/issues/1400)
- 中央 PRD：`trend/adopted/PRD-279-livepowers-skill-install-snapshot.md`
- 全链：T1 #1396（设计 `docs/plans/2026-10-29-prd-279-install-snapshot.md`）→ T2 #1397（`install_snapshot.py`）→ T3 #1398（收录流程衔接 `install_flow.py`）→ T4 #1399（回滚审计断言）→ 本任务 T5
- 验收测试：`tests/test_prd279_acceptance.py`（11 例，tests/ 目录 `python3 -m unittest test_prd279_acceptance`）
- 状态：验收通过；实现类 PR 只开不合并，等用户 review

## 验收标准逐条核验（issue #1400）

### 1. 安装/升级可回滚（全链通过）— 通过

虚构技能全流程演练：`install_with_snapshot`（admitted True：先
`take_snapshot` 快照——技能名/旧版本/目录内容指纹/已装清单；再安装）→
模拟新版本出问题 → `restore` 目录级还原（指纹校验 fail-close）→
回滚记录四要素（skill_name/from_version→to_version/at/actor）齐全。

### 2. 红线断言全过 — 通过

- 安检管进门、快照管退出：admitted False 直接拒绝且**无快照**（不占槽）
- 审计序列有序：install-performed → rolled-back
- 单槽覆盖：同技能连续安装覆盖旧槽、slot-overwritten 入审计
- 空目录拒绝（无从还原）
- 零网络（纯 stdlib，无请求原语）

### 3. 文档无密钥 — 通过

交付面（install_snapshot.py/install_flow.py/验收测试）扫描零密钥、零真实主机名。

## 运行记录

`python3 -m unittest test_prd279_acceptance`（tests/ 目录）→ 11 tests OK。

## 结论

PRD-279 全链（T1–T5）验收通过；只开不合并，等用户 review。
