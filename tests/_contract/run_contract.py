#!/usr/bin/env python3
"""skill 包结构契约测试（L1）。只读不执行被测文件。

检查项（错误会让 CI 打回，警告只提示）：
  错误：
    - 缺 SKILL.md / 缺 frontmatter / frontmatter 解析失败
    - frontmatter 出现未知字段（白名单之外）
    - 缺必填字段 name / description
    - frontmatter 的 name 与目录名不一致
    - 反引号引用的 kebab 词指向不存在的 skill（引用必须存在）
    - 文本里 `skills/<name>` 路径引用指向不存在的目录
  警告：
    - SKILL.md 超过 500 行
    - `lp <cmd>` 附近 200/400 字符窗口内没有"退出码"说明
      （防"只给命令不给语义"；很多历史 skill 没写，全量补是后续工作）

用法：
    python3 tests/_contract/run_contract.py [skills 目录]
退出码：有错误 -> 1；只有警告或全过 -> 0。
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ALLOWED_FM = {"name", "description", "license", "compatibility",
              "allowed-tools", "metadata"}
MAX_LINES = 500


def parse_frontmatter(text):
    """返回 (dict|None, [问题])."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return None, ["缺 frontmatter（文件开头 --- ... ---）"]
    fm, problems = {}, []
    for i, raw in enumerate(m.group(1).splitlines(), 1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if ":" not in s:
            problems.append("frontmatter 第%d行无法解析：%s" % (i, s))
            continue
        k, v = s.split(":", 1)
        fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, problems


def known_skills(skills_root):
    return {p.name for p in skills_root.iterdir() if p.is_dir()}


def check_skill(skill_dir, skills_root, known):
    """返回 (errors, warnings) 两个字符串列表。"""
    errors, warnings = [], []
    md = skill_dir / "SKILL.md"
    if not md.is_file():
        return ["缺 SKILL.md"], []
    text = md.read_text(encoding="utf-8")

    fm, probs = parse_frontmatter(text)
    errors.extend(probs)
    if fm is None:
        return errors, warnings
    for k in fm:
        if k not in ALLOWED_FM:
            errors.append("未知 frontmatter 字段：%s" % k)
    for req in ("name", "description"):
        if req not in fm:
            errors.append("缺必填字段：%s" % req)
    if fm.get("name") != skill_dir.name:
        errors.append("name=%r 与目录名 %r 不一致"
                      % (fm.get("name"), skill_dir.name))
    if len(text.splitlines()) > MAX_LINES:
        warnings.append("SKILL.md 超过 %d 行（%d 行）"
                        % (MAX_LINES, len(text.splitlines())))

    # 反引号引用的 kebab 词若指向 skill，必须真实存在（引用必须存在）。
    # 例：`env-scan-ontology` 合法；`env-scan-ontolog`（拼写错误）报错。
    for tok in set(re.findall(r"`([a-z][a-z0-9-]{2,})`", text)):
        if "-" in tok and tok not in known:
            errors.append("引用的 skill 不存在：`%s`" % tok)

    # 文本里 skills/<name> 路径引用必须存在。
    for ref in set(re.findall(r"skills/([a-z0-9-]+)", text)):
        if ref not in known:
            errors.append("引用的 skills/%s 目录不存在" % ref)

    # `lp <cmd>` 出现时，同段必须有退出码说明（防"只给命令不给语义"）。
    for m in re.finditer(r"`(lp [a-z ]+)`", text):
        cmd = m.group(1).strip()
        window = text[max(0, m.start() - 200):m.end() + 400]
        if "退出码" not in window:
            warnings.append("`%s` 附近缺退出码说明" % cmd)

    return errors, warnings


def main(argv):
    skills_root = Path(argv[1]) if len(argv) > 1 else REPO / "skills"
    known = known_skills(skills_root)
    total_errors, total_warnings = 0, 0
    failed = []
    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        errors, warnings = check_skill(skill_dir, skills_root, known)
        total_errors += len(errors)
        total_warnings += len(warnings)
        if errors:
            failed.append(skill_dir.name)
            print("FAIL %s" % skill_dir.name)
            for e in errors:
                print("     [错误] %s" % e)
        else:
            print("PASS %s" % skill_dir.name)
        for w in warnings:
            print("     [警告] %s" % w)
    print("-" * 40)
    print("共 %d 个 skill：%d 个 FAIL，错误 %d 条，警告 %d 条"
          % (len(known), len(failed), total_errors, total_warnings))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
