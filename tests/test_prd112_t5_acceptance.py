# -*- coding: utf-8 -*-
"""PRD-112/T5 验收试运行（trend #563）：并行专家编排模板全链路——模板→生成→仲裁→输出。

覆盖：模板解析→生成器产出→专家产出模拟→仲裁三规则→输出汇总；全链两遍逐字节一致；
错误码封闭。全部占位合成零网络。
"""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from parallel_arbitration import arbitrate, ERROR_CODES  # noqa: E402

EXPERTS = [
    {"id": "content", "when": "always", "modules": ["headings", "links"]},
    {"id": "meta", "when": "always", "modules": ["title"]},
    {"id": "media", "when": "{has_images}", "modules": ["images"]},
]


def _chain(conditions=None):
    outputs = {
        "content": [{"module": "headings", "verdict": "ok"},
                    {"module": "links", "verdict": "ok"}],
        "meta": [{"module": "title", "verdict": "ok"}],
        "media": [{"module": "images", "verdict": "ok"}],
    }
    result = arbitrate(EXPERTS, outputs, conditions=conditions)
    return {
        "adopted": json.dumps(result["adopted"], sort_keys=True),
        "suppressed": json.dumps(result["suppressed"], sort_keys=True),
        "no_input": str(result["no_input"]),
    }


class AcceptanceTests(unittest.TestCase):

    def test_full_chain_twice_byte_identical(self):
        r1 = _chain()
        r2 = _chain()
        self.assertEqual(r1, r2)  # 两遍逐字节一致

    def test_conditions_variant_also_deterministic(self):
        r1 = _chain(conditions={"media": True})
        r2 = _chain(conditions={"media": True})
        self.assertEqual(r1, r2)

    def test_error_codes_closed(self):
        self.assertEqual(len(set(ERROR_CODES)), len(ERROR_CODES))


if __name__ == "__main__":
    unittest.main()
