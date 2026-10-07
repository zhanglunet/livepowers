import json
import os
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

    def run_script(self, script, *args, check=None):
        p = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args], cwd=self.dir,
                           capture_output=True, text=True, env={**os.environ, "LIVEPOWERS_HOME": ".livepowers"})
        if check is not None:
            self.assertEqual(p.returncode, check, msg=f"{script} {args}\nstdout={p.stdout}\nstderr={p.stderr}")
        return p

    def lp(self, *args, check=0):
        return self.run_script("lp.py", *args, check=check)

    def read_json(self, rel):
        with open(os.path.join(self.dir, rel), encoding="utf-8") as f:
            return json.load(f)
