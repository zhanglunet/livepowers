#!/usr/bin/env python3
"""生成网站上的活软件演示页 docs/demo/index.html（单文件，零构建依赖）。

页面复用参考宿主的 A2UI 渲染器（static/a2ui.js）、预置展示面（surfaces/）与生长用的 DDL（ddl/），
外壳与浏览器内的演示逻辑在 web/。改了这些文件后运行：python3 examples/living_app/build_site.py
（tests/test_surface.py 会检查 docs/demo/index.html 与源文件同步）。
"""
import json
import os
import sys

APP = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(os.path.dirname(APP)), "docs", "demo", "index.html")
SURFACES = {"pipeline.ephemeral": "pipeline-by-region.ephemeral.json",
            "pipeline.fixed": "pipeline-by-region.fixed.json",
            "monthly.ephemeral": "followup-by-month.ephemeral.json"}


def read(*parts):
    with open(os.path.join(APP, *parts), encoding="utf-8") as f:
        return f.read()


def build():
    surfaces = {k: json.loads(read("surfaces", fn)) for k, fn in SURFACES.items()}
    ddl = {"up": read("ddl", "v_pipeline_by_region.sql"), "down": read("ddl", "v_pipeline_by_region.rollback.sql")}
    return (read("web", "page.html")
            .replace("/*A2UI*/", read("static", "a2ui.js"))
            .replace("/*SURFACES*/", json.dumps(surfaces, ensure_ascii=False))
            .replace("/*DDL*/", json.dumps(ddl, ensure_ascii=False))
            .replace("/*APP*/", read("web", "demo.js")))


if __name__ == "__main__":
    html = build()
    if "--check" in sys.argv:
        with open(OUT, encoding="utf-8") as f:
            sys.exit(0 if f.read() == html else 1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(OUT)
