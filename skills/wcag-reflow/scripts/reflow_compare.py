#!/usr/bin/env python3
"""
reflow_compare.py -- Side-by-side comparison image for WCAG 1.4.10 reflow audit.

Left panel:  Desktop screenshot (wide_width, typically 1280px)
Right panel: Narrow screenshot (320px) — actual pixel width, not scaled

Dark background theme with color-coded pass/fail indicators.
"""

import argparse
import json
import os
from PIL import Image, ImageDraw, ImageFont

# Theme
BG_COLOR      = (24, 24, 24)
HEADER_COLOR  = (32, 32, 32)
PASS_GREEN    = (34, 197, 94)
FAIL_RED      = (239, 68, 68)
LABEL_COLOR   = (229, 229, 229)
DIM_COLOR     = (160, 160, 160)
DIVIDER_COLOR = (64, 64, 64)

HEADER_H  = 48   # top label bar
COL_HDR_H = 36   # column header bar
FOOTER_H  = 48   # footer bar
PADDING   = 24   # outer padding
GAP       = 32   # gap between screenshots


def load_font(size=13, bold=False):
    candidates = [
        ("arialbd.ttf" if bold else "arial.ttf"),
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def build_comparison(wide_path, narrow_path, data, output_path, label):
    wide_img   = Image.open(wide_path).convert("RGB")
    narrow_img = Image.open(narrow_path).convert("RGB")

    wide_w, wide_h   = wide_img.size
    narrow_w, narrow_h = narrow_img.size

    # Pad the shorter screenshot so both columns are the same height
    max_h = max(wide_h, narrow_h)

    def pad_image(img, target_h):
        if img.height >= target_h:
            return img
        padded = Image.new("RGB", (img.width, target_h), BG_COLOR)
        padded.paste(img, (0, 0))
        return padded

    wide_img   = pad_image(wide_img,   max_h)
    narrow_img = pad_image(narrow_img, max_h)

    # Canvas dimensions
    canvas_w = PADDING + wide_w + GAP + narrow_w + PADDING
    canvas_h = HEADER_H + COL_HDR_H + max_h + FOOTER_H

    canvas = Image.new("RGB", (canvas_w, canvas_h), BG_COLOR)
    draw   = ImageDraw.Draw(canvas)

    font_bold  = load_font(14, bold=True)
    font_reg   = load_font(13)
    font_sm    = load_font(11)

    # ---- Header bar ----
    draw.rectangle([0, 0, canvas_w, HEADER_H], fill=HEADER_COLOR)
    draw.text((PADDING, (HEADER_H - 16) // 2), label,
              fill=LABEL_COLOR, font=font_bold)

    y_col_hdr = HEADER_H

    # ---- Column headers ----
    draw.rectangle([0, y_col_hdr, canvas_w, y_col_hdr + COL_HDR_H], fill=(28, 28, 28))

    # Left column header
    left_col_label = f"Desktop ({data['wide_width']}px)"
    draw.text((PADDING, y_col_hdr + (COL_HDR_H - 14) // 2),
              left_col_label, fill=(120, 180, 120), font=font_reg)

    # Right column header — pass/fail
    if data["has_horizontal_scroll"]:
        right_col_label = f"{data['narrow_width']}px width — ⚠ Horizontal scroll detected"
        right_col_color = FAIL_RED
    else:
        right_col_label = f"{data['narrow_width']}px width — ✓ No horizontal scroll"
        right_col_color = PASS_GREEN

    right_x = PADDING + wide_w + GAP
    draw.text((right_x, y_col_hdr + (COL_HDR_H - 14) // 2),
              right_col_label, fill=right_col_color, font=font_reg)

    # ---- Screenshots ----
    y_screenshots = HEADER_H + COL_HDR_H
    canvas.paste(wide_img,   (PADDING, y_screenshots))
    canvas.paste(narrow_img, (right_x, y_screenshots))

    # Thin divider between columns
    div_x = PADDING + wide_w + GAP // 2
    draw.line([(div_x, y_screenshots), (div_x, y_screenshots + max_h)],
              fill=DIVIDER_COLOR, width=1)

    # ---- Footer bar ----
    y_footer = HEADER_H + COL_HDR_H + max_h
    draw.rectangle([0, y_footer, canvas_w, canvas_h], fill=HEADER_COLOR)

    overflow_els = data.get("overflow_elements", [])
    if data["has_horizontal_scroll"] or overflow_els:
        n = len(overflow_els)
        parts = []
        for el in overflow_els[:6]:
            ident = ""
            if el.get("id"):
                ident = f"#{el['id']}"
            elif el.get("class"):
                first_cls = el["class"].split()[0] if el["class"].split() else ""
                if first_cls:
                    ident = f".{first_cls}"
            tag_str = f"<{el['tag']}{ident}>"
            parts.append(f"{tag_str} +{el['overflowBy']}px")
        overflow_summary = ", ".join(parts)
        if n > 6:
            overflow_summary += f", +{n - 6} more"

        footer_text  = f"⚠  {n} element(s) overflow: {overflow_summary}" if overflow_summary else f"⚠  Horizontal scroll detected"
        footer_color = FAIL_RED
    else:
        footer_text  = "✓  Content reflows cleanly — WCAG 1.4.10 pass"
        footer_color = PASS_GREEN

    draw.text((PADDING, y_footer + (FOOTER_H - 14) // 2),
              footer_text, fill=footer_color, font=font_bold)

    # ---- Save ----
    canvas.save(output_path, optimize=True)
    print(f"Comparison saved: {output_path}")
    print(f"Canvas size: {canvas_w} x {canvas_h}px")


def main():
    ap = argparse.ArgumentParser(
        description="Generate side-by-side reflow comparison image"
    )
    ap.add_argument("--wide",   required=True, help="Wide (desktop) screenshot path")
    ap.add_argument("--narrow", required=True, help="Narrow screenshot path")
    ap.add_argument("--data",   required=True, help="reflow_data.json path")
    ap.add_argument("--output", required=True, help="Output image path")
    ap.add_argument("--label",  default="Reflow Audit (WCAG 1.4.10)",
                    help="Title label shown in header bar")
    args = ap.parse_args()

    with open(args.data, encoding="utf-8") as f:
        data = json.load(f)

    build_comparison(args.wide, args.narrow, data, args.output, args.label)


if __name__ == "__main__":
    main()
