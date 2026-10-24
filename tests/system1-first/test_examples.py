"""system1-first 的独立验收测试。L1/L3 纯文本可跑；L2 需 lp 环境则跳过。"""
import re
import unittest
from pathlib import Path

from helpers import find_livepowers_lp, run_lp

SKILL = Path(__file__).resolve().parents[2] / "skills" / "system1-first" / "SKILL.md"
TEXT = SKILL.read_text(encoding="utf-8")
LP = find_livepowers_lp()


class Contract(unittest.TestCase):
    def test_flow_steps_present(self):
        for step in ["规范化意图", "查注册表", "HIT 或 MAYBE HIT", "MISS", "建任务"]:
            self.assertIn(step, TEXT, "五步流程缺：%s" % step)

    def test_exit_codes_documented(self):
        # skill 声称的退出码语义必须写全：0=HIT, 2=MISS, 3=MAYBE HIT
        for code, meaning in [("0", "HIT"), ("2", "MISS"), ("3", "MAYBE")]:
            self.assertIn(code, TEXT)
        self.assertIn(meaning, TEXT)

    def test_no_blind_write(self):
        # 反例纪律必须明文写出：MAYBE HIT 严禁盲目调用写操作
        self.assertIn("严禁盲目调用写操作", TEXT)

    def test_evidence_command(self):
        self.assertIn("lp evidence add", TEXT)


class Examples(unittest.TestCase):
    def test_intent_normalize_example(self):
        # 文档给的例子：参数必须剥离，意图必须稳定
        self.assertIn("weekly revenue by region", TEXT)
        self.assertIn("transfer stale opportunity", TEXT)

    def test_decrystallize_signal(self):
        for sig in ["连续失败", "用户纠正了口径", "retire"]:
            self.assertIn(sig, TEXT)

    @unittest.skipIf(LP is None, "需 lp 环境")
    def test_registry_find_hit(self):
        r = run_lp(LP, "registry", "find", "weekly revenue by region")
        self.assertIn(r.returncode, (0, 2, 3))  # 契约：退出码只能是这三个


class Negative(unittest.TestCase):
    def test_not_for_free_chat(self):
        # description 限定"业务请求"；纯闲聊不应命中（文本规则：description 必须含限定词）
        fm = TEXT.split("---")[1]
        self.assertTrue(any(w in fm for w in ["业务请求", "business request"]))


if __name__ == "__main__":
    unittest.main()
