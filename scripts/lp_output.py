#!/usr/bin/env python3
"""简洁输出开关（PRD-046/T3）。

口径（docs/plans/2026-10-17-concise-output-spec.md §4）：
- 环境变量 LIVEPOWERS_VERBOSE=1，或配置文件 verbose: true → 全量输出。
- 默认：简洁模式开启（结论先行、关键信息 Top N、详情折叠）。
- 调试/排障时可用 LIVEPOWERS_VERBOSE=1 临时恢复全量输出。

配置文件位置：<LIVEPOWERS_HOME>/config.yaml（默认 .livepowers/config.yaml），
与 registry.json 等同级——仓库惯例是全部状态都放在 .livepowers/ 下，
且 LIVEPOWERS_HOME 可整体搬移工作区，配置跟人走。

只用 Python 标准库。YAML 只认顶层 `verbose:` 一行（极简解析）。
"""

import contextlib
import os

ENV_FLAG = "LIVEPOWERS_VERBOSE"
FOLD_HINT = "（LIVEPOWERS_VERBOSE=1 显示全部）"


def _root():
    return os.environ.get("LIVEPOWERS_HOME", ".livepowers")


def _config_verbose():
    """读 <root>/config.yaml 的顶层 verbose 键。文件不存在/解析失败 → False。"""
    path = os.path.join(_root(), "config.yaml")
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if s.startswith("verbose:"):
                    return s.split(":", 1)[1].strip().lower() in ("1", "true", "yes", "on")
                # 顶层出现其他键后仍继续找（容忍注释与空行穿插）
    except OSError:
        pass
    return False


_override = None  # 测试 / 报告内捕获用；None = 按环境与配置判定


def is_verbose():
    """全量输出？环境变量或配置文件任一开启即为 True。"""
    if _override is not None:
        return _override
    if os.environ.get(ENV_FLAG) == "1":
        return True
    return _config_verbose()


@contextlib.contextmanager
def verbose_mode(on=True):
    """临时强制开关（供 lp report 捕获子命令时保持文件内容稳定）。"""
    global _override
    old = _override
    _override = on
    try:
        yield
    finally:
        _override = old


def fold(lines, limit, what="条"):
    """简洁模式下超限折叠：留前 limit 行 + 折叠提示；verbose 或未超限 → 原样。

    lines: 字符串列表；返回新列表（不改动入参）。
    """
    lines = list(lines)
    if is_verbose() or len(lines) <= limit:
        return lines
    return lines[:limit] + [f"…共 {len(lines)} {what}，已折叠{FOLD_HINT}"]


def should_summarize_scan():
    """scan 脚本：只有"人直接看终端（tty）且非 verbose"时才打摘要行；
    管道/重定向（机器消费 YAML）时保持原样。"""
    return sys_stdout_isatty() and not is_verbose()


def sys_stdout_isatty():
    import sys
    try:
        return sys.stdout.isatty()
    except Exception:
        return False
