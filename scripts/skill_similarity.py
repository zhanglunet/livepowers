#!/usr/bin/env python3
"""skill_similarity —— 相似 skill 检测（PRD-148/T3，最小实现）。

给瘦身门 Q2（能否并入已有 skill）/ Q3（触发边界是否冲突）提供输入：
**只提示、不判定、不自动删**（PRD-148 风险节红线；发布处置一律人工终审）。
与 scripts/slim_gate.py 不强耦合：本脚本可独立运行，退出码恒 0（提示不拦截）。

输入（T1 §5 + issue #742 口径）：skills/*/SKILL.md 的
  - frontmatter name；
  - description：英文触发段与中文一句话**分开比对，取较高值**；
  - 正文标题串（# / ## / ### 依序拼接，即"步骤标题"的结构面）；
  - 触发词：英文段 + name 分词后去停用词，用于报告重叠词。

算法：两两 difflib.SequenceMatcher（零依赖，Python 3.9+ 标准库，只读）；
每对得分 = 四个字段（name / en / zh / headings）各自 ratio 的**最大值**，
并注明主相似字段。阈值（T1 §5，可用参数覆盖）：
  ≥ --hint（默认 0.60）提示；≥ --strong（默认 0.80）强提示。

输出：按得分降序（同分按 skill 名字典序，可复现）的 Top-K 列表，
行格式（T1 §5）：相似对：A × B（0.72）| 重叠触发词：a, b
并列出"重复度"指标：得分 ≥hint 的 skill 对数（T1 §6 度量的首跑基线来源）。

用法：
    python3 scripts/skill_similarity.py                 # 全库 Top 20，阈值 0.60/0.80
    python3 scripts/skill_similarity.py --top 0         # 全部相似对
    python3 scripts/skill_similarity.py --format markdown --out report.md
    python3 scripts/skill_similarity.py --skills-dir <dir> --format json
明确不做：模型调用/语义嵌入；自动合并或自动改路由表；对已发布 skill 的任何自动处置。
"""
import argparse
import difflib
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HINT = 0.60
STRONG = 0.80

FIELDS = ("name", "en", "zh", "headings")

# 触发词分词的停用词（英文触发段的功能词 + 泛触发词，无业务含义）。
STOPWORDS = {
    "use", "when", "the", "a", "an", "or", "and", "has", "have", "been",
    "being", "asked", "asks", "says", "said", "user", "users", "with",
    "for", "from", "that", "this", "what", "which", "how", "are", "is",
    "it", "to", "of", "at", "on", "by", "in", "if", "can", "will",
    "should", "would", "do", "does", "did", "day", "someone", "else",
    "not", "into", "about", "you", "your", "their", "its", "than", "then",
    "them", "there", "here", "be", "was", "were", "as", "must", "may",
    "might", "shall", "any", "all", "each", "every", "some", "who",
}

CJK = re.compile(r"[\u4e00-\u9fff]")
HEADING = re.compile(r"^#{1,6} +(.+?)\s*$", re.M)


def split_description(desc):
    """description -> (英文触发段, 中文一句话)。以第一个 CJK 字符为界。"""
    if not desc:
        return "", ""
    m = CJK.search(desc)
    if not m:
        return desc.strip(), ""
    return desc[:m.start()].strip(), desc[m.start():].strip()


def tokenize(text):
    """小写分词：字母/数字串；去停用词与单字符。"""
    return {t for t in re.findall(r"[a-z0-9][a-z0-9-]{1,}", text.lower())
            if t not in STOPWORDS and len(t) >= 2}


def load_skill(path):
    """读 SKILL.md -> {name, en, zh, headings, tokens}；不可解析返回 None。"""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return None
    fm = {}
    for raw in m.group(1).splitlines():
        if ":" in raw:
            k, v = raw.split(":", 1)
            fm[k.strip()] = v.strip()
    name = fm.get("name", "")
    en, zh = split_description(fm.get("description", ""))
    headings = "\n".join(HEADING.findall(text[m.end():]))
    tokens = tokenize(en) | tokenize(name.replace("-", " "))
    return {"name": name, "en": en, "zh": zh, "headings": headings,
            "tokens": tokens}


def load_skills(skills_dir):
    """枚举 skills/<dir>/SKILL.md（目录名排序，输出可复现）。"""
    out = []
    for entry in sorted(os.listdir(skills_dir)):
        path = os.path.join(skills_dir, entry, "SKILL.md")
        if not os.path.isfile(path):
            continue
        info = load_skill(path)
        if info and info["name"]:
            info["_dir"] = entry
            out.append(info)
    return out


def ratio(a, b):
    """空串不参与比对（返回 0，避免空 × 空 = 1.0 的假高分）。"""
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def similarity(pair_a, pair_b):
    """返回 (score, 主相似字段)。score = 四字段 ratio 的最大值。"""
    best_field, best = "name", 0.0
    for f in FIELDS:
        r = ratio(pair_a[f], pair_b[f])
        if r > best:
            best_field, best = f, r
    return best, best_field


def scan(skills, hint=HINT, strong=STRONG, top=20):
    """两两比对，返回 (相似对列表, 统计头)。只读，不修改任何输入。"""
    pairs = []
    for i in range(len(skills)):
        for j in range(i + 1, len(skills)):
            a, b = skills[i], skills[j]
            score, field = similarity(a, b)
            if score < hint:
                continue
            overlap = sorted(a["tokens"] & b["tokens"])
            pairs.append({
                "a": a["name"], "b": b["name"],
                "score": round(score, 2), "field": field,
                "strong": score >= strong,
                "overlap": overlap,
            })
    # 得分降序；同分按名字字典序（可复现）。
    pairs.sort(key=lambda p: (-p["score"], p["a"], p["b"]))
    stats = {
        "skills": len(skills),
        "pairs_total": len(skills) * (len(skills) - 1) // 2,
        "pairs_hint": len(pairs),
        "pairs_strong": sum(1 for p in pairs if p["strong"]),
        "hint": hint, "strong": strong,
    }
    return (pairs if top is None or top <= 0 else pairs[:top]), stats


def render_text(pairs, stats):
    lines = ["相似 skill 检测（PRD-148/T3）：只提示、不判定、不自动删"]
    lines.append("skills：%d 个；两两 %d 对；≥%.2f 提示 %d 对（重复度指标），≥%.2f 强提示 %d 对"
                 % (stats["skills"], stats["pairs_total"], stats["hint"],
                    stats["pairs_hint"], stats["strong"], stats["pairs_strong"]))
    lines.append("-" * 64)
    if not pairs:
        lines.append("（无 ≥%.2f 的相似对）" % stats["hint"])
        return lines
    for p in pairs:
        mark = "★★" if p["strong"] else "○"
        words = ", ".join(p["overlap"]) if p["overlap"] else "—"
        lines.append("%s 相似对：%s × %s（%.2f）[%s] | 重叠触发词：%s"
                     % (mark, p["a"], p["b"], p["score"], p["field"], words))
    return lines


def render_markdown(pairs, stats):
    lines = ["# 相似 skill 检测报告（PRD-148/T3）", "",
             "- skills：%d 个；两两 %d 对" % (stats["skills"], stats["pairs_total"]),
             "- 重复度（≥%.2f 的对数）：%d；强提示（≥%.2f）：%d"
             % (stats["hint"], stats["pairs_hint"], stats["strong"],
                stats["pairs_strong"]),
             "- 只提示、不判定、不自动删；处置走瘦身门 Q2/Q3 人工终审", ""]
    if not pairs:
        lines.append("（无 ≥%.2f 的相似对）" % stats["hint"])
        return lines
    lines += ["| 强提示 | skill A | skill B | 得分 | 主相似字段 | 重叠触发词 |",
              "|---|---|---|---|---|---|"]
    for p in pairs:
        lines.append("| %s | `%s` | `%s` | %.2f | %s | %s |"
                     % ("是" if p["strong"] else "—", p["a"], p["b"],
                        p["score"], p["field"],
                        ", ".join(p["overlap"]) or "—"))
    return lines


def render_json(pairs, stats):
    return [json.dumps({"stats": stats, "pairs": pairs},
                       ensure_ascii=False, indent=2)]


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="PRD-148 相似 skill 检测（只读提示，供瘦身门 Q2/Q3 参考）")
    ap.add_argument("--skills-dir", default=os.path.join(REPO, "skills"),
                    help="skills 目录（默认仓库 skills/）")
    ap.add_argument("--hint", type=float, default=HINT,
                    help="提示阈值（默认 %.2f）" % HINT)
    ap.add_argument("--strong", type=float, default=STRONG,
                    help="强提示阈值（默认 %.2f）" % STRONG)
    ap.add_argument("--top", type=int, default=20,
                    help="最多输出对数（0=全部，默认 20）")
    ap.add_argument("--format", choices=("text", "markdown", "json"),
                    default="text")
    ap.add_argument("--out", help="写入文件（默认打印 stdout）")
    args = ap.parse_args(argv)

    skills = load_skills(args.skills_dir)
    if len(skills) < 2:
        print("可解析的 skill 少于 2 个（%s），无相似对可比。" % args.skills_dir)
        return 0
    pairs, stats = scan(skills, args.hint, args.strong, args.top)
    lines = {"text": render_text, "markdown": render_markdown,
             "json": render_json}[args.format](pairs, stats)
    text = "\n".join(lines) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print("已写入 %s（相似对 %d，重复度 %d）"
              % (args.out, len(pairs), stats["pairs_hint"]))
    else:
        print(text, end="")
    # 退出码恒 0：本工具只提示不判定，不作为 CI 门禁。
    return 0


if __name__ == "__main__":
    sys.exit(main())
