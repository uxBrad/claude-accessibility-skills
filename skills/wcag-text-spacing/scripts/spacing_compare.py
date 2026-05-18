#!/usr/bin/env python3
"""
spacing_compare.py -- Side-by-side before/after comparison image for WCAG 1.4.12 text spacing audit.

Produces a single image with:
  - Dark header bar with audit label
  - Two column headers (before / after)
  - Both screenshots side by side, shorter one padded to match height
  - Footer bar showing overflow status and page height increase
"""

import argparse
import json
import os
from PIL import Image, ImageDraw, ImageFont

# Dark background
BG_COLOR = (24, 24, 24)

# Column header colours
BEFORE_HEADER_COLOR = (30, 100, 60)   # dark green
AFTER_HEADER_COLOR  = (30, 60, 140)   # dark blue

# Footer colours
FOOTER_OK_COLOR   = (30, 110, 60)
FOOTER_WARN_COLOR = (150, 40, 40)

HEADER_H = 48
COL_HDR_H = 34
FOOTER_H = 54
GAP = 12  # gap between columns


def load_font(size=14, bold=False):
    candidates = [
        "arialbd.ttf" if bold else "arial.ttf",
        "Arial Bold.ttf" if bold else "Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def draw_centered_text(draw, text, x, y, w, h, font, color):
    """Draw text centered within a rectangle."""
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except AttributeError:
        tw, th = draw.textsize(text, font=font)
    tx = x + (w - tw) // 2
    ty = y + (h - th) // 2
    draw.text((tx, ty), text, fill=color, font=font)


def build_comparison(before_path, after_path, data, output_path, label):
    before_img = Image.open(before_path).convert("RGB")
    after_img  = Image.open(after_path).convert("RGB")

    bw, bh = before_img.size
    aw, ah = after_img.size

    # Scale both to the same width (use before width as reference)
    col_w = bw
    if aw != col_w:
        scale = col_w / aw
        ah = int(ah * scale)
        after_img = after_img.resize((col_w, ah), Image.LANCZOS)
        aw = col_w

    content_h = max(bh, ah)

    # Pad shorter screenshot to match height
    if bh < content_h:
        padded = Image.new("RGB", (col_w, content_h), BG_COLOR)
        padded.paste(before_img, (0, 0))
        before_img = padded
    if ah < content_h:
        padded = Image.new("RGB", (col_w, content_h), BG_COLOR)
        padded.paste(after_img, (0, 0))
        after_img = padded

    total_w = col_w * 2 + GAP
    total_h = HEADER_H + COL_HDR_H + content_h + FOOTER_H

    canvas = Image.new("RGB", (total_w, total_h), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    font_lg  = load_font(18, bold=True)
    font_md  = load_font(14, bold=True)
    font_sm  = load_font(12)
    font_sm2 = load_font(11)

    # --- Header bar ---
    draw.rectangle([0, 0, total_w, HEADER_H], fill=(36, 36, 36))
    draw_centered_text(draw, label, 0, 0, total_w, HEADER_H, font_lg, (230, 230, 230))

    # --- Column headers ---
    col_hdr_y = HEADER_H
    draw.rectangle([0, col_hdr_y, col_w, col_hdr_y + COL_HDR_H], fill=BEFORE_HEADER_COLOR)
    draw_centered_text(draw, "Before (default spacing)", 0, col_hdr_y, col_w, COL_HDR_H,
                       font_md, (200, 240, 210))

    draw.rectangle([col_w + GAP, col_hdr_y, total_w, col_hdr_y + COL_HDR_H], fill=AFTER_HEADER_COLOR)
    draw_centered_text(draw, "After (WCAG 1.4.12 overrides)", col_w + GAP, col_hdr_y,
                       col_w, COL_HDR_H, font_md, (200, 215, 255))

    # --- Screenshots ---
    img_y = HEADER_H + COL_HDR_H
    canvas.paste(before_img, (0, img_y))
    canvas.paste(after_img, (col_w + GAP, img_y))

    # --- Footer bar ---
    footer_y = img_y + content_h
    has_scroll   = data.get("has_horizontal_scroll", False)
    n_overflow   = len(data.get("overflowing_elements", []))
    before_h_px  = data.get("before_height", 0)
    after_h_px   = data.get("after_height", 0)
    inc_px       = data.get("height_increase_px", after_h_px - before_h_px)
    inc_pct      = data.get("height_increase_pct",
                            round(inc_px / before_h_px * 100, 1) if before_h_px else 0)

    has_issues = has_scroll or n_overflow > 0
    footer_color = FOOTER_WARN_COLOR if has_issues else FOOTER_OK_COLOR
    draw.rectangle([0, footer_y, total_w, total_h], fill=footer_color)

    if has_issues:
        parts = []
        if has_scroll:
            parts.append("horizontal scroll")
        if n_overflow:
            parts.append(f"{n_overflow} overflowing element{'s' if n_overflow != 1 else ''}")
        status_line = "⚠  Issues found: " + ", ".join(parts)
        status_color = (255, 220, 180)
    else:
        status_line = "✓  No overflow issues — content reflows cleanly"
        status_color = (200, 255, 215)

    height_line = (
        f"Page height +{inc_pct}%  "
        f"({before_h_px}px → {after_h_px_display(after_h_px)})"
    )

    line1_y = footer_y + 8
    line2_y = footer_y + 28
    draw.text((16, line1_y), status_line, fill=status_color, font=font_md)
    draw.text((16, line2_y), height_line, fill=(200, 200, 200), font=font_sm)

    canvas.save(output_path)
    print(f"Comparison saved: {output_path}")


def after_h_px_display(h):
    return f"{h}px"


def main():
    ap = argparse.ArgumentParser(
        description="Create a side-by-side before/after comparison for WCAG 1.4.12 text spacing."
    )
    ap.add_argument("--before",  required=True, help="Path to before.png")
    ap.add_argument("--after",   required=True, help="Path to after.png")
    ap.add_argument("--data",    required=True, help="Path to spacing_data.json")
    ap.add_argument("--output",  required=True, help="Output path for comparison image")
    ap.add_argument("--label",   default="WCAG 1.4.12 Text Spacing Audit",
                    help="Label shown in the header bar")
    args = ap.parse_args()

    # Load data
    data = {}
    if os.path.exists(args.data):
        try:
            with open(args.data, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Warning: could not load {args.data}: {e}")
    else:
        print(f"Warning: data file not found: {args.data} — proceeding without metrics")

    build_comparison(args.before, args.after, data, args.output, args.label)


if __name__ == "__main__":
    main()
