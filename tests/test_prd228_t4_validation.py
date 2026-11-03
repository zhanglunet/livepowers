# -*- coding: utf-8 -*-
"""PRD-228/T4 自测（trend #1143）：配置校验与默认值——坏配置可检出并回退。

运行：uv run --with pytest python -m pytest tests/test_prd228_t4_validation.py -q

覆盖（T1 设计）：validate_source 字段级校验（合法通过/各字段坏值逐项检出/
非对象拒）、sanitize_source 坏配置回退默认（逐字段回退+corrections 可查、
合法字段保留）、validate_generated 四工具产物完整性（缺文件/空文件/坏 JSON
检出）。零网络；确定性；全占位。
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from config_validation import (  # noqa: E402
    DEFAULT_SOURCE,
    sanitize_source,
    validate_generated,
    validate_source,
)

GOOD = {"skills_root": "~/.livepowers/skills", "model": "glm-5.3-flash",
        "allowed_commands": ["lp hook watch"], "telemetry_enabled": False}


class ValidateSourceTests(unittest.TestCase):
    def test_good_source_passes(self):
        assert validate_source(GOOD)["ok"] is True

    def test_each_field_bad_detected(self):
        for field, bad in (("skills_root", ""), ("model", None),
                           ("allowed_commands", ["", "  "]),
                           ("telemetry_enabled", "yes")):
            source = dict(GOOD, **{field: bad})
            result = validate_source(source)
            assert result["ok"] is False
            assert any(field in e for e in result["errors"]), field

    def test_non_object_rejected(self):
        result = validate_source("not-a-dict")
        assert result["ok"] is False
        assert "对象" in result["errors"][0]


class TestSanitize:
    def test_good_source_no_corrections(self):
        result = sanitize_source(GOOD)
        assert result["corrections"] == []
        assert result["source"] == GOOD

    def test_bad_fields_fall_back_to_defaults(self):
        """坏配置回退默认：坏字段回退+corrections 登记（检出并回退）。"""
        result = sanitize_source({"skills_root": "", "model": 42,
                                  "allowed_commands": "not-a-list",
                                  "telemetry_enabled": "yes",
                                  "skills_root_note": "x"})
        assert result["source"]["skills_root"] == DEFAULT_SOURCE["skills_root"]
        assert result["source"]["model"] == DEFAULT_SOURCE["model"]
        assert result["source"]["allowed_commands"] == []
        assert result["source"]["telemetry_enabled"] is False
        fields = {c["field"] for c in result["corrections"]}
        assert fields == {"skills_root", "model", "allowed_commands",
                          "telemetry_enabled"}
        for c in result["corrections"]:
            assert "original" in c and "fallback" in c

    def test_partial_fallback_keeps_good_fields(self):
        """合法字段保留、仅坏字段回退。"""
        result = sanitize_source({"skills_root": "~/.livepowers/skills",
                                  "model": None})
        assert result["source"]["skills_root"] == "~/.livepowers/skills"
        assert result["source"]["model"] == DEFAULT_SOURCE["model"]

    def test_non_object_falls_back_entirely(self):
        result = sanitize_source(None)
        assert result["source"] == DEFAULT_SOURCE


class TestValidateGenerated:
    def test_generated_configs_complete(self):
        import tempfile
        from tool_config_gen import generate_tool_configs
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "dist"
            generate_tool_configs(GOOD, out)
            report = validate_generated(out)
            assert report["ok"] is True
            assert len(report["checks"]) == 4

    def test_missing_and_broken_detected(self):
        import tempfile
        from tool_config_gen import generate_tool_configs
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "dist"
            generate_tool_configs(GOOD, out)
            (out / "claude" / "settings.json").write_text("{broken", encoding="utf-8")
            (out / "pi" / "agent.toml").unlink()  # agent.toml 缺失
            report = validate_generated(out)
            assert report["ok"] is False
            bad = {c["tool"]: c for c in report["checks"] if not c["ok"]}
            assert "JSON 不可解析" in bad["claude"]["reason"]
            assert "缺失" in bad["pi"]["reason"]

    def test_deterministic(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "dist"
            from tool_config_gen import generate_tool_configs
            generate_tool_configs(GOOD, out)
            one = json.dumps(validate_generated(out), sort_keys=True)
            two = json.dumps(validate_generated(out), sort_keys=True)
            assert one == two


if __name__ == "__main__":
    unittest.main()
