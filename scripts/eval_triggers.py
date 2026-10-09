#!/usr/bin/env python3
"""
eval_triggers —— 技能触发率评测脚本：
基于 tests/triggers/*.jsonl 用例集，对技能触发率与混淆情况进行评测。
只支持确定性打分（零依赖，复用 intent_sim）；真实模型评测留待第二阶段。
可记录金丝雀结果，并与上一条同名记录比较。
"""
import argparse
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(REPO, "skills")
TRIGGERS_DIR = os.path.join(REPO, "tests", "triggers")
SCRIPTS_DIR = os.path.join(REPO, "scripts")
sys.path.insert(0, SCRIPTS_DIR)
import lp


def load_skill_descriptions():
    descs = {}
    for d in sorted(os.listdir(SKILLS_DIR)):
        p = os.path.join(SKILLS_DIR, d, "SKILL.md")
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                content = f.read()
            m = re.search(r"description:\s*(.*)", content)
            descs[d] = m.group(1).strip() if m else ""
    return descs


def run_deterministic_eval(descs):
    skills = sorted(descs)
    stats = {s: {"pos_total": 0, "pos_hit": 0, "neg_total": 0, "neg_ok": 0, "confused_with": {}} for s in skills}
    overall_pos_total = 0
    overall_pos_hit = 0

    for s in skills:
        p = os.path.join(TRIGGERS_DIR, f"{s}.jsonl")
        if not os.path.isfile(p):
            continue
        with open(p, encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]

        for item in lines:
            prompt = item["prompt"]
            expect = item["expect"]
            reject = item.get("reject", [])
            scores = sorted([(name, lp.intent_sim(prompt, desc)) for name, desc in descs.items()],
                            key=lambda x: -x[1])
            top1 = scores[0][0]
            top2 = [x[0] for x in scores[:2]]

            # 正例统计
            if s in expect:
                stats[s]["pos_total"] += 1
                overall_pos_total += 1
                if any(e in top2 for e in expect):
                    stats[s]["pos_hit"] += 1
                    overall_pos_hit += 1
                else:
                    confused = top1
                    stats[s]["confused_with"][confused] = stats[s]["confused_with"].get(confused, 0) + 1

            # 反例统计
            if s in reject:
                stats[s]["neg_total"] += 1
                if top1 != s:
                    stats[s]["neg_ok"] += 1

    return stats, overall_pos_total, overall_pos_hit


def compare_previous(path, current):
    """Compare the latest same-name run; never compare invented zero baselines."""
    previous = next((r for r in reversed(lp.jsonl_read(path))
                     if r.get("name") == current["name"]), None)
    if previous is None:
        return "历史比较: 首次记录，无历史基线"
    if not previous.get("total"):
        return "历史比较: 上一条记录分母无效，无法比较"
    delta = current["passed"] / current["total"] - previous["passed"] / previous["total"]
    warning = "（用例数量变化，仅供参考）" if previous["total"] != current["total"] else ""
    return f"历史比较: {previous['passed']}/{previous['total']} → {current['passed']}/{current['total']}; 触发率差值 {delta:+.1%}{warning}"


def main():
    parser = argparse.ArgumentParser(description="技能触发率自动评测")
    parser.add_argument("--record-canary", action="store_true", help="把结果记录进 .livepowers/canary.jsonl")
    args = parser.parse_args()

    descs = load_skill_descriptions()
    stats, total_pos, total_hit = run_deterministic_eval(descs)

    print("=" * 70)
    print("Livepowers 技能触发率评测结果（基于 tests/triggers/*.jsonl）")
    print("模式: 确定性打分（零依赖，词集/二元组重叠）")
    print("=" * 70)
    print(f"{'技能名称':<32} {'正例 Top-2 命中率':<18} {'反例排斥率':<12} {'主要混淆'}")
    print("-" * 70)

    for s, st in sorted(stats.items()):
        pos_rate = f"{st['pos_hit']}/{st['pos_total']} ({st['pos_hit']/st['pos_total']:.0%})" if st['pos_total'] else "N/A"
        neg_rate = f"{st['neg_ok']}/{st['neg_total']} ({st['neg_ok']/st['neg_total']:.0%})" if st['neg_total'] else "N/A"
        conf = ", ".join(f"{k}({v})" for k, v in st["confused_with"].items()) or "—"
        print(f"{s:<32} {pos_rate:<18} {neg_rate:<12} {conf}")

    print("=" * 70)
    overall_rate = total_hit / total_pos if total_pos else 0
    print(f"总计正例: {total_hit}/{total_pos}（总体 Top-2 触发率: {overall_rate:.1%}）")

    if args.record_canary:
        canary_file = os.path.join(REPO, ".livepowers", "canary.jsonl")
        os.makedirs(os.path.dirname(canary_file), exist_ok=True)
        rec = {
            "ts": lp.now(),
            "name": "triggers_eval",
            "model": "deterministic-sim",
            "passed": total_hit,
            "total": total_pos,
            "tokens": 0,
            "seconds": 0,
            "note": "tests/triggers eval"
        }
        print(compare_previous(canary_file, rec))
        lp.jsonl_append(canary_file, rec)
        print(f"已记录至 {canary_file}: {total_hit}/{total_pos}")


if __name__ == "__main__":
    main()
