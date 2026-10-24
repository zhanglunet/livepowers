import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, "scripts")


class Workdir(unittest.TestCase):
    """每个测试一个临时工作目录。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def run_script(self, script, *args, check=None, verbose=True):
        # 默认 verbose=1：存量测试断言的都是全量输出；PRD-046/T3 要求 verbose 下
        # 输出与改造前逐字节一致，所以回归测试跑全量模式。简洁模式由
        # tests/concise-output/ 专门覆盖（传 verbose=False）。
        env = {**os.environ, "LIVEPOWERS_HOME": ".livepowers"}
        if verbose:
            env["LIVEPOWERS_VERBOSE"] = "1"
        else:
            env.pop("LIVEPOWERS_VERBOSE", None)
        p = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args], cwd=self.dir,
                           capture_output=True, text=True, env=env)
        if check is not None:
            self.assertEqual(p.returncode, check, msg=f"{script} {args}\nstdout={p.stdout}\nstderr={p.stderr}")
        return p

    def lp(self, *args, check=0, verbose=True):
        return self.run_script("lp.py", *args, check=check, verbose=verbose)

    def read_json(self, rel):
        with open(os.path.join(self.dir, rel), encoding="utf-8") as f:
            return json.load(f)


def _is_livepowers_lp(path):
    """PATH 里的 lp 是否为 Livepowers：`lp --version` 须输出 "lp X.Y.Z"。

    macOS 自带 CUPS 打印命令 /usr/bin/lp，不能只凭名字判断。
    """
    try:
        p = subprocess.run([path, "--version"], capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return False
    return p.returncode == 0 and re.match(r"lp \d+\.\d+\.\d+", p.stdout.strip()) is not None


def find_livepowers_lp():
    """返回调用 Livepowers lp 的命令列表；找不到返回 None（L2 用例据此跳过）。

    优先用仓库内 scripts/lp.py；仓库脚本缺失时，才用 PATH 里经版本号校验的 lp。
    """
    script = os.path.join(SCRIPTS, "lp.py")
    if os.path.isfile(script):
        return [sys.executable, script]
    path = shutil.which("lp")
    if path and _is_livepowers_lp(path):
        return [path]
    return None


def run_lp(cmd, *args):
    """在临时目录里执行 lp，避免 L2 用例往仓库写 .livepowers/。"""
    with tempfile.TemporaryDirectory() as d:
        env = {**os.environ, "LIVEPOWERS_HOME": ".livepowers"}
        return subprocess.run([*cmd, *args], cwd=d, env=env, capture_output=True, text=True)
