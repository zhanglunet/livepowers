import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("eval_triggers", Path(__file__).parents[1] / "scripts/eval_triggers.py")
eval_triggers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eval_triggers)

class TestHistory(unittest.TestCase):
    def test_previous_same_name_and_delta(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "canary.jsonl"
            current = {"name": "triggers_eval", "passed": 9, "total": 10}
            self.assertIn("无历史基线", eval_triggers.compare_previous(str(p), current))
            p.write_text("\n".join(json.dumps(r) for r in [
                {"name": "triggers_eval", "passed": 4, "total": 10},
                {"name": "triggers_eval", "passed": 8, "total": 10},
                {"name": "other", "passed": 1, "total": 1}]), encoding="utf-8")
            self.assertIn("+10.0%", eval_triggers.compare_previous(str(p), current))
            current["total"] = 12
            self.assertIn("用例数量变化", eval_triggers.compare_previous(str(p), current))

    def test_model_flag_rejected(self):
        import subprocess
        proc = subprocess.run([__import__("sys").executable, str(Path(eval_triggers.__file__)), "--model", "fake"], capture_output=True)
        self.assertNotEqual(proc.returncode, 0)
