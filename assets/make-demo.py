#!/usr/bin/env python3
"""Generate assets/demo.gif — a terminal-style animated tutorial showing how to
install and use the magento-claude-skills commands. Reproducible: re-run to rebuild.

    python assets/make-demo.py
"""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 760, 430
PAD_X, TOP = 22, 70
LINE_H = 27
CHARS_PER_FRAME = 3

BG = (13, 17, 23)
BAR = (22, 27, 34)
DOTS = [(255, 95, 86), (255, 189, 46), (39, 201, 63)]
GREEN = (63, 185, 80)
BLUE = (121, 192, 255)
GRAY = (139, 148, 158)
WHITE = (230, 237, 243)
CURSOR = (63, 185, 80)

FONT_PATH = r"C:\Windows\Fonts\consola.ttf"
FONT_BOLD = r"C:\Windows\Fonts\consolab.ttf"
font = ImageFont.truetype(FONT_PATH, 16)
font_b = ImageFont.truetype(FONT_BOLD, 16)
title_font = ImageFont.truetype(FONT_BOLD, 14)

# (kind, prompt, text, color) — kind: "type" | "out" | "blank"
STEPS = [
    ("type", "$ ", "npx skills add staksoft/magento-claude-skills -a claude-code", BLUE),
    ("out",  "",   "  # Installed 3 skills: magento-module, magento-hyva, magento-audit", GRAY),
    ("blank", "", "", GRAY),
    ("type", "> ", "/magento-module Acme_GiftMessage", BLUE),
    ("out",  "",   "  scaffold #   setup:di:compile #   phpcs #", GRAY),
    ("blank", "", "", GRAY),
    ("type", "> ", "/magento-hyva Acme/storefront", BLUE),
    ("out",  "",   "  # Hyva child theme + Tailwind build ready", GRAY),
    ("blank", "", "", GRAY),
    ("type", "> ", "/magento-audit https://store.example/", BLUE),
    ("out",  "",   "  # Audit report: 3 findings (1 critical FPC leak)", GRAY),
]

CHAR_W = font.getlength("M")


def draw_check(draw: ImageDraw.ImageDraw, x: float, y: float, col) -> None:
    """Draw a small check mark inside one character cell (Consolas lacks U+2713)."""
    draw.line([(x + 1, y + 9), (x + 4, y + 14), (x + 10, y + 3)], fill=col, width=2)


def draw_text_checks(draw: ImageDraw.ImageDraw, x: float, y: float, text: str, col):
    """Draw text, rendering any '#' sentinel as a drawn green check mark."""
    for i, part in enumerate(text.split("#")):
        draw.text((x, y), part, font=font, fill=col)
        x += CHAR_W * len(part)
        if i < len(text.split("#")) - 1:
            draw_check(draw, x, y, GREEN)
            x += CHAR_W
    return x


def base_frame() -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 40], fill=BAR)
    for i, c in enumerate(DOTS):
        cx = 22 + i * 22
        d.ellipse([cx, 15, cx + 11, 26], fill=c)
    d.text((W // 2 - 120, 13), "magento-claude-skills  —  zsh", font=title_font, fill=GRAY)
    return img


def draw_lines(draw: ImageDraw.ImageDraw, lines, partial=None):
    """lines: list of (prompt, prompt_color, text, text_color). partial appended live."""
    all_lines = list(lines)
    if partial is not None:
        all_lines.append(partial)
    for i, (prompt, pcol, text, tcol) in enumerate(all_lines):
        y = TOP + i * LINE_H
        x = PAD_X
        if prompt:
            draw.text((x, y), prompt, font=font_b, fill=pcol)
            x += int(CHAR_W * len(prompt))
        is_partial = partial is not None and i == len(all_lines) - 1
        if is_partial:
            draw.text((x, y), text, font=font, fill=tcol)
            cx = x + int(CHAR_W * len(text))
            draw.rectangle([cx + 1, y + 2, cx + 9, y + 19], fill=CURSOR)
        else:
            draw_text_checks(draw, x, y, text, tcol)


frames: list[Image.Image] = []
durations: list[int] = []
completed: list[tuple] = []

for kind, prompt, text, color in STEPS:
    if kind == "blank":
        completed.append(("", GRAY, "", GRAY))
        continue
    if kind == "type":
        for n in range(0, len(text) + 1, CHARS_PER_FRAME):
            img = base_frame()
            draw_lines(ImageDraw.Draw(img), completed,
                       partial=(prompt, GREEN, text[:n], color))
            frames.append(img)
            durations.append(50)
        completed.append((prompt, GREEN, text, color))
        # brief hold after the command is fully typed
        img = base_frame(); draw_lines(ImageDraw.Draw(img), completed); frames.append(img); durations.append(350)
    elif kind == "out":
        completed.append(("", GRAY, text, color))
        img = base_frame(); draw_lines(ImageDraw.Draw(img), completed)
        frames.append(img); durations.append(900)

# final hold
img = base_frame(); draw_lines(ImageDraw.Draw(img), completed)
frames.append(img); durations.append(2600)

out = Path(__file__).with_name("demo.gif")
# quantize to a small shared palette to keep the file lean
pal_frames = [f.convert("P", palette=Image.ADAPTIVE, colors=64) for f in frames]
pal_frames[0].save(
    out, save_all=True, append_images=pal_frames[1:],
    duration=durations, loop=0, optimize=True, disposal=2,
)
print(f"wrote {out}  ({out.stat().st_size // 1024} KB, {len(frames)} frames)")
