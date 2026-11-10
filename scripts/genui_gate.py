# -*- coding: utf-8 -*-
"""PRD-335/T3（trend issue #1614 的 T3 环节）：生成式 UI 丢弃闸门。

按 T1 设计（docs/plans/2026-11-09-prd-335-genui-design.md）§3.3/R1 落地，
消费 T2 genui 校验与渲染产物（注入式只读）：

  - GATE_CODES 词表封闭：OK / DROPPED_PROPS / REJECTED_NODES / TREE_REJECTED；
  - tree_gate(tree)：丢弃闸门单一入口——validate_tree → render（同一渲染
    函数 R3 预览即最终）→ 产物 genui-product/v1：**dropped[] 与
    rejected_nodes[] 随产物输出**（§3.3 规则 4 丢弃显形给人工复核不静默）；
    gate 判定：零丢弃零剔除 → OK；有丢弃/剔除 → DROPPED_PROPS/
    REJECTED_NODES 且 needs_review=True（产物可出，人工复核留痕）；
    TreeRejected（深度/节点数越限）→ TREE_REJECTED 整树拒绝零渲染；
  - review_digest(product)：人工复核摘要——每条丢弃/剔除逐行显形（复核
    面板直读，零静默吞）。

零执行语义红线继承（零事件脚本零 URL——T4 AST 同表预埋）；零网络；
示例全虚构占位。
测试：tests/test_prd335_t3_genui_gate.py
"""
from __future__ import annotations

from typing import Any

from genui import TreeRejected, render, validate_tree

PRODUCT_SCHEMA = "genui-product/v1"
GATE_CODES = ("OK", "DROPPED_PROPS", "REJECTED_NODES", "TREE_REJECTED")


def tree_gate(tree: Any) -> dict[str, Any]:
    """丢弃闸门（§3.3 规则 4）：校验 → 同一渲染函数 → 产物带丢弃清单。"""
    try:
        validation = validate_tree(tree)
    except TreeRejected as exc:
        return {"schema": PRODUCT_SCHEMA, "gate": "TREE_REJECTED",
                "code_detail": {"code": exc.code, "detail": str(exc)},
                "lines": [], "dropped": [], "rejected_nodes": [],
                "needs_review": True,
                "review_note": "整树拒绝零渲染——修正树后重提"}
    dropped = validation.get("dropped", [])
    rejected = validation.get("rejected_nodes", [])
    lines = render(validation["clean_tree"])
    if dropped and rejected:
        code = "REJECTED_NODES"   # 剔除优先级高于丢弃（节点级 > 属性级）
    elif rejected:
        code = "REJECTED_NODES"
    elif dropped:
        code = "DROPPED_PROPS"
    else:
        code = "OK"
    note = "零丢弃零剔除——直接可用"
    if code == "DROPPED_PROPS":
        note = (f"{len(dropped)} 条属性丢弃——产物可出，人工复核后采用（R1 显形）")
    elif code == "REJECTED_NODES":
        note = (f"{len(rejected)} 个节点剔除/{len(dropped)} 条属性丢弃——"
                "产物可出但需人工复核（剔除节点已用占位文本标记）")
    return {"schema": PRODUCT_SCHEMA, "gate": code, "code_detail": None,
            "lines": lines, "dropped": dropped,
            "rejected_nodes": rejected,
            "needs_review": code != "OK", "review_note": note}


def review_digest(product: dict[str, Any]) -> list[str]:
    """人工复核摘要：每条丢弃/剔除逐行显形（零静默）。"""
    out: list[str] = []
    for d in product.get("dropped", []):
        out.append(f"[丢弃] {d.get('path')} 属性 {d.get('prop')}：{d.get('reason')}")
    for r in product.get("rejected_nodes", []):
        out.append(f"[剔除] {r.get('path')}：{r.get('reason')}")
    if product.get("code_detail"):
        out.append(f"[整树拒绝] {product['code_detail'].get('code')}："
                   f"{product['code_detail'].get('detail')}")
    return out
