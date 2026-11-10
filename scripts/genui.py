#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-335/T2（trend issue #1614 的 T2 环节）：生成式 UI 最小实现。

按 T1 设计（docs/plans/2026-11-09-prd-335-genui-design.md）§3.1/§3.2/§3.3/§4
实现：

  - COMPONENT_VOCAB：组件类型封闭词表五类（文本标签/字段行/分组框/分隔线/
    提示条），每类属性白名单+必填+枚举——**模型不能发明组件**（R2）；
  - validate_tree(tree)：逐节点校验（R1）——类型词表外整节点拒绝（R2）；
    白名单外属性丢弃+dropped[] 显形（不静默吞）；必填被丢整节点拒；
    枚举越界回退默认+dropped 记录；深度 6/节点数 50 上限整树拒绝；
  - render(tree)：**同一渲染函数**产出文本行序列——预览与最终同一组件库
    （R3，T4 断言渲染函数单一来源）；确定性（同树同输出逐字节一致）；
  - 零执行语义（R4）：属性白名单不含事件/脚本/URL——模型产出声明不产出
    代码（T4 断言预埋）。

零网络；示例全虚构占位。
测试：tests/test_prd335_t2_genui.py
"""
from __future__ import annotations

from typing import Any

MAX_DEPTH = 6
MAX_NODES = 50

#: 组件类型封闭词表（R2）：type → {required, optional, enums}
COMPONENT_VOCAB: dict[str, dict[str, Any]] = {
    "文本标签": {"required": ["text"],
                 "optional": ["size"], "enums": {"size": ["标准", "大", "小"]}},
    "字段行": {"required": ["label", "value"],
               "optional": [], "enums": {}},
    "分组框": {"required": ["title"], "optional": ["children"], "enums": {}},
    "分隔线": {"required": [], "optional": [], "enums": {}},
    "提示条": {"required": ["text"], "optional": ["tone"],
               "enums": {"tone": ["提示", "警告"]}},
}
DEFAULTS = {"文本标签": {"size": "标准"}, "提示条": {"tone": "提示"}}


class TreeRejected(ValueError):
    """组件树整树/整节点拒绝（R2 类型词表外/超深/超节点数）。"""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}：{detail}")
        self.code = code


def validate_tree(tree: Any) -> dict[str, Any]:
    """逐节点校验（R1/R2）：返回 {clean_tree, dropped[], rejected_nodes[]}。

    - 类型词表外 → 整节点拒绝（进 rejected_nodes，不入 clean_tree）；
    - 白名单外属性 → 丢弃 + dropped[] 显形（不静默吞）；
    - 枚举越界 → 回退默认 + dropped[] 记录；
    - 必填缺失 → 整节点拒绝；
    - 深度 6 / 节点数 50 上限 → 整树拒绝（TreeRejected）。
    """
    dropped: list[dict[str, str]] = []
    rejected_nodes: list[dict[str, str]] = []
    node_count = 0

    def walk(node: Any, depth: int, path: str) -> Any:
        nonlocal node_count
        node_count += 1
        if node_count > MAX_NODES:
            raise TreeRejected("NODE_LIMIT", f"节点数超上限 {MAX_NODES}（防爆炸）")
        if depth > MAX_DEPTH:
            raise TreeRejected("DEPTH_LIMIT", f"嵌套深度超上限 {MAX_DEPTH}（防失控）")
        if not isinstance(node, dict):
            rejected_nodes.append({"path": path, "reason": "节点须为对象"})
            return {"type": "文本标签", "props": {"text": "[无效节点已剔除]（占位）"},
                    "children": []}
        ntype = node.get("type")
        spec = COMPONENT_VOCAB.get(ntype)
        if spec is None:
            rejected_nodes.append({"path": path,
                                   "reason": f"类型词表外：{ntype!r}（R2 封闭词表）"})
            return {"type": "文本标签", "props": {"text": "[未知类型已剔除]（占位）"},
                    "children": []}
        props_in = node.get("props") or {}
        clean_props: dict[str, Any] = {}
        for key, value in props_in.items():
            if key in spec["required"] or key in spec["optional"]:
                clean_props[key] = value
            else:
                dropped.append({"path": path, "prop": key,
                                "reason": "白名单外属性丢弃（R1 显形）"})
        for req in spec["required"]:
            if clean_props.get(req) in (None, ""):
                rejected_nodes.append({"path": path,
                                       "reason": f"必填属性 {req} 缺失"})
                return {"type": "文本标签", "props": {"text": "[缺必填已剔除]（占位）"},
                        "children": []}
        for enum_key, allowed in spec["enums"].items():
            if enum_key in clean_props and clean_props[enum_key] not in allowed:
                dropped.append({"path": path, "prop": enum_key,
                                "reason": f"枚举越界回退默认：{clean_props[enum_key]!r}"})
                clean_props[enum_key] = allowed[0]
        children_in = node.get("children") or []
        clean_children = [walk(c, depth + 1, f"{path}/{i}")
                          for i, c in enumerate(children_in)]
        return {"type": ntype, "props": clean_props, "children": clean_children}

    clean_tree = walk(tree, 0, "root")
    return {"clean_tree": clean_tree, "dropped": dropped,
            "rejected_nodes": rejected_nodes}


def render(tree: dict[str, Any]) -> list[str]:
    """同一渲染函数（R3）：组件树 → 文本行序列（预览与最终唯一入口）。

    确定性：同树同输出逐字节一致。
    """
    lines: list[str] = []

    def walk(node: dict[str, Any], indent: str) -> None:
        ntype = node.get("type")
        props = node.get("props") or {}
        children = node.get("children") or []
        if ntype == "文本标签":
            size = props.get("size", "标准")
            mark = {"大": "■ ", "小": "· "}.get(size, "")
            lines.append(f"{indent}{mark}{props.get('text', '')}")
        elif ntype == "字段行":
            lines.append(f"{indent}{props.get('label', '')}：{props.get('value', '')}")
        elif ntype == "分组框":
            lines.append(f"{indent}【{props.get('title', '')}】")
            for c in children:
                walk(c, indent + "  ")
            return
        elif ntype == "分隔线":
            lines.append(f"{indent}{'-' * 20}")
        elif ntype == "提示条":
            tone = props.get("tone", "提示")
            mark = "⚠" if tone == "警告" else "ℹ"
            lines.append(f"{indent}{mark} {props.get('text', '')}")
        for c in children:
            if ntype != "分组框":
                walk(c, indent)

    walk(tree, "")
    return lines


def render_roots(roots: list[dict[str, Any]]) -> list[str]:
    """流式形态：逐根渲染拼接（前缀不变——流式喂入不改变最终输出）。"""
    out: list[str] = []
    for root in roots:
        out.extend(render(root))
    return out
