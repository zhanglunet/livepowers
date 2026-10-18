#!/usr/bin/env python3
"""Render the livepowers install-demo GIF (PRD-051/T3, trend #238).

What it does
------------
Renders a scripted terminal session as a GIF:

    $ npx -y skills add zhanglunet/livepowers -y   # install
    $ ls .agents/skills | wc -l                    # -> 19
    $ grep -m1 "^description:" .../using-livepowers/SKILL.md   # skill is usable

The command *outputs* embedded below are trimmed (spinner frames removed)
from a REAL run on 2026-10-18 in a clean HOME -- see
docs/plans/2026-10-18-npx-install-t1-report.md. Nothing is fabricated:
every line shown actually appeared in that run.

Deterministic: same input -> byte-identical PNG frames (ffmpeg's GIF
palette step may vary microscopically across versions).

Usage
-----
    python3 scripts/record-demo.py          # writes docs/assets/livepowers-demo.gif

Requires: Pillow, ffmpeg, DejaVuSansMono (system), NotoSansSC
(~/workspace/tools/fonts/NotoSansSC.ttf -- downloaded once by the author).
"""

import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- config

W, H = 960, 540
FPS = 10
BG = (13, 17, 23)          # GitHub dark terminal
FG = (230, 237, 243)       # terminal text
GREEN = (63, 185, 80)      # prompt / checkmarks
DIM = (139, 148, 158)      # secondary text
PAD = 40
FONT_SIZE = 19
LINE_H = 27

MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
CJK = os.path.expanduser("~/workspace/tools/fonts/NotoSansSC.ttf")

# (kind, payload) -- kind in {"type", "out", "pause", "card"}
SCENES = [
    ("type", "$ npx -y skills add zhanglunet/livepowers -y"),
    ("out", [
        "◇  Source: https://github.com/zhanglunet/livepowers.git",
        "◇  Repository cloned",
        "◇  Found 19 skills",
        "●  Installing all 19 skills",
        "◇  Installation complete",
        "◇  Installed 19 skills",
        "  ✓ ./.agents/skills/acceptance-gates",
        "  ✓ ./.agents/skills/using-livepowers",
        "  ✓ … and 17 more",
        "→  Done!  Review skills before use; they run with full agent permissions.",
    ]),
    ("pause", 6),
    ("type", "$ ls .agents/skills | wc -l"),
    ("out", ["19"]),
    ("pause", 6),
    ("type", '$ grep -m1 "^description:" .agents/skills/using-livepowers/SKILL.md'),
    ("out", ["description: Use when starting any conversation that touches business sof…"]),
    ("pause", 8),
    ("card", None),
]
CARD_HOLD = 30  # frames


# ---------------------------------------------------------------- render

def main() -> None:
    mono = ImageFont.truetype(MONO, FONT_SIZE)
    cjk_big = ImageFont.truetype(CJK, 46)
    cjk_mid = ImageFont.truetype(CJK, 24)

    frames_dir = tempfile.mkdtemp(prefix="demo_frames_")
    lines: list[tuple[str, str]] = []  # (text, color-key)

    def draw_terminal(extra_typing: str = "") -> Image.Image:
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        y = PAD
        for text, key in lines:
            color = GREEN if key == "prompt" else (GREEN if text.lstrip().startswith("✓") else FG)
            # prompt part of a typed command line is green
            if key == "cmd":
                d.text((PAD, y), "$ ", font=mono, fill=GREEN)
                d.text((PAD + 2 * _chw(mono), y), text[2:], font=mono, fill=FG)
            else:
                d.text((PAD, y), text, font=mono, fill=color)
            y += LINE_H
        if extra_typing:
            # draw the in-progress line with a block cursor
            if extra_typing.startswith("$ "):
                d.text((PAD, y), "$ ", font=mono, fill=GREEN)
                d.text((PAD + 2 * _chw(mono), y), extra_typing[2:], font=mono, fill=FG)
                cx = PAD + (2 + len(extra_typing) - 2) * _chw(mono)
            else:
                d.text((PAD, y), extra_typing, font=mono, fill=FG)
                cx = PAD + len(extra_typing) * _chw(mono)
            d.rectangle([cx + 2, y + 2, cx + 2 + _chw(mono), y + LINE_H - 4], fill=FG)
        return img

    def draw_card() -> Image.Image:
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        y = 150
        for text, font, color in [
            ("业务智能体的 Superpowers", cjk_big, FG),
            ("19 个强制工作流技能 · 一键安装", cjk_mid, DIM),
        ]:
            bb = d.textbbox((0, 0), text, font=font)
            d.text(((W - (bb[2] - bb[0])) / 2, y), text, font=font, fill=color)
            y += (bb[3] - bb[1]) + 28
        y += 10
        for text, color in [
            ("$ npx skills add zhanglunet/livepowers -y", GREEN),
            ("github.com/zhanglunet/livepowers", DIM),
        ]:
            f = ImageFont.truetype(MONO, 20)
            bb = d.textbbox((0, 0), text, font=f)
            d.text(((W - (bb[2] - bb[0])) / 2, y), text, font=f, fill=color)
            y += (bb[3] - bb[1]) + 18
        return img

    n = 0

    def save(img: Image.Image) -> None:
        nonlocal n
        n += 1
        img.save(os.path.join(frames_dir, f"f{n:04d}.png"))

    for kind, payload in SCENES:
        if kind == "type":
            shown = ""
            # reveal ~2 chars per frame for a snappy typing feel
            for i in range(2, len(payload) + 2, 2):
                shown = payload[:i]
                save(draw_terminal(shown))
            lines.append((payload, "cmd"))
        elif kind == "out":
            for text in payload:
                lines.append((text, "out"))
                for _ in range(3):
                    save(draw_terminal())
        elif kind == "pause":
            for _ in range(payload):
                save(draw_terminal())
        elif kind == "card":
            for _ in range(CARD_HOLD):
                save(draw_card())

    print(f"rendered {n} frames ({n / FPS:.1f}s) -> {frames_dir}")

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_gif = os.path.join(repo_root, "docs", "assets", "livepowers-demo.gif")
    os.makedirs(os.path.dirname(out_gif), exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error",
         "-framerate", str(FPS), "-i", os.path.join(frames_dir, "f%04d.png"),
         "-vf", "scale=960:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=256[p];[s1][p]paletteuse=dither=bayer",
         out_gif],
        check=True,
    )
    size = os.path.getsize(out_gif)
    print(f"wrote {out_gif} ({size / 1024:.0f} KiB)")


def _chw(font: ImageFont.FreeTypeFont) -> int:
    return int(font.getbbox("M")[2])


if __name__ == "__main__":
    sys.exit(main())
