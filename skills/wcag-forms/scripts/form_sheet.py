#!/usr/bin/env python3
"""
form_sheet.py -- Contact sheet of all form fields with label status.

Color coding:
  Green  (good)        -- proper programmatic label present           → PASS
  Amber  (placeholder) -- only placeholder text, no true label        → WARN
  Red    (missing)     -- no label at all                             → FAIL

Usage:
  python form_sheet.py --data form_fields.json --output form_sheet.png [--label "Desktop (1280px)"]
"""

import argparse
import json
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------
COLS   = 4
CELL_W = 260
CELL_H = 140
PAD    = 8
BG     = (24, 24, 24)

# Status colours
STATUS_COLORS = {
    "good":        (0,  185,  80),   # green
    "placeholder": (200, 140,   0),  # amber
    "missing":     (210,  30,  30),  # red
}
STATUS_LABELS = {
    "good":        "PASS",
    "placeholder": "WARN — placeholder only",
    "missing":     "FAIL — no label",
}

AUTOCOMPLETE_CLR = (80, 160, 220)   # blue for autocomplete value
GREY             = (120, 120, 120)
WHITE            = (230, 230, 230)
LIGHT_GREY       = (160, 160, 160)


# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------
def load_font(size: int = 10, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
    if bold:
        candidates += ["arialbd.ttf", "Arial Bold.ttf",
                       "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                       "/System/Library/Fonts/Helvetica.ttc"]
    candidates += [
        "arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def draw_text_clipped(draw: ImageDraw.ImageDraw, xy, text: str, fill, font,
                      max_width: int) -> None:
    """Draw text, truncating with '…' if it exceeds max_width pixels."""
    if not text:
        return
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    if w <= max_width:
        draw.text(xy, text, fill=fill, font=font)
        return
    # Truncate
    while text and w > max_width:
        text = text[:-1]
        bbox = draw.textbbox((0, 0), text + "…", font=font)
        w = bbox[2] - bbox[0]
    draw.text(xy, text + "…", fill=fill, font=font)


def badge_width(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return (bbox[2] - bbox[0]) + 10  # 5px padding each side


# ---------------------------------------------------------------------------
# Sheet builder
# ---------------------------------------------------------------------------
def make_sheet(data: list, output_path: str, label: str = "") -> None:
    if not data:
        print("No form fields to render.")
        return

    n    = len(data)
    cols = min(COLS, n)
    rows = (n + cols - 1) // cols

    title_h  = 48 if label else 0
    footer_h = 36   # counts bar
    sheet_w  = cols * (CELL_W + PAD) + PAD
    sheet_h  = title_h + rows * (CELL_H + PAD) + PAD + footer_h

    sheet = Image.new("RGB", (sheet_w, sheet_h), BG)
    draw  = ImageDraw.Draw(sheet)

    font_hdr = load_font(14, bold=True)
    font_md  = load_font(11)
    font_sm  = load_font(10)
    font_xs  = load_font(9)

    # Header bar
    if label:
        draw.rectangle([0, 0, sheet_w, title_h - 4], fill=(36, 36, 36))
        draw.text((PAD + 4, 13), label, fill=(240, 240, 240), font=font_hdr)

    counts = {"good": 0, "placeholder": 0, "missing": 0}

    for i, item in enumerate(data):
        col = i % cols
        row = i // cols
        cx  = PAD + col * (CELL_W + PAD)
        cy  = title_h + PAD + row * (CELL_H + PAD)

        status = item.get("status", "missing")
        clr    = STATUS_COLORS.get(status, GREY)
        counts[status] = counts.get(status, 0) + 1

        # Cell background + coloured border
        draw.rectangle([cx, cy, cx + CELL_W, cy + CELL_H],
                       fill=(36, 36, 36), outline=clr, width=3)

        inner_x = cx + 6
        inner_w = CELL_W - 12

        # ---- Status badge (top-left) ----
        badge_lbl = STATUS_LABELS.get(status, status)
        bw = badge_width(draw, badge_lbl, font_xs)
        badge_h_px = 16
        badge_x1 = cx + 4
        badge_y1 = cy + 4
        draw.rectangle([badge_x1, badge_y1, badge_x1 + bw, badge_y1 + badge_h_px],
                       fill=clr)
        draw.text((badge_x1 + 5, badge_y1 + 2), badge_lbl,
                  fill=(255, 255, 255), font=font_xs)

        # ---- Field type + index (top-right) ----
        field_tag   = item.get("tag", "input")
        field_type  = item.get("type", "")
        field_index = item.get("index", i)
        type_lbl    = f"{field_tag}[{field_type}] #{field_index}"
        bbox_t      = draw.textbbox((0, 0), type_lbl, font=font_xs)
        tw_t        = bbox_t[2] - bbox_t[0]
        draw.text((cx + CELL_W - tw_t - 6, cy + 6),
                  type_lbl, fill=GREY, font=font_xs)

        # ---- Label text ----
        label_text = item.get("label_text", "") or "(no label)"
        label_y    = cy + 26
        draw_text_clipped(draw, (inner_x, label_y), f'"{label_text}"',
                          fill=WHITE, font=font_md, max_width=inner_w)

        # ---- Label source ----
        source      = item.get("label_source", "none")
        source_disp = f"via {source}" if source not in ("none", "") else "no programmatic label"
        draw.text((inner_x, label_y + 18), source_disp, fill=LIGHT_GREY, font=font_xs)

        # ---- Autocomplete ----
        ac_val = (item.get("autocomplete") or "").strip()
        ac_y   = cy + CELL_H - 38
        if ac_val:
            draw_text_clipped(draw, (inner_x, ac_y),
                              f"autocomplete: {ac_val}",
                              fill=AUTOCOMPLETE_CLR, font=font_sm, max_width=inner_w)
        else:
            draw.text((inner_x, ac_y), "no autocomplete", fill=GREY, font=font_sm)

        # ---- Required indicator ----
        required = item.get("required", False)
        req_y    = cy + CELL_H - 20
        if required:
            draw.text((inner_x, req_y), "* required", fill=(220, 100, 80), font=font_xs)

        # ---- Name attribute (small, bottom-right) ----
        name_val = (item.get("name") or "").strip()
        if name_val:
            name_disp = f"name={name_val[:22]}"
            bbox_n    = draw.textbbox((0, 0), name_disp, font=font_xs)
            nw        = bbox_n[2] - bbox_n[0]
            draw.text((cx + CELL_W - nw - 6, req_y),
                      name_disp, fill=GREY, font=font_xs)

    # ---- Footer counts bar ----
    footer_y = sheet_h - footer_h
    draw.rectangle([0, footer_y, sheet_w, sheet_h], fill=(18, 18, 18))

    total = len(data)
    good  = counts.get("good", 0)
    warn  = counts.get("placeholder", 0)
    fail  = counts.get("missing", 0)

    summary_parts = [
        (f"Total {total}",  LIGHT_GREY),
        (f"PASS: {good}",   STATUS_COLORS["good"]),
        (f"WARN: {warn}",   STATUS_COLORS["placeholder"]),
        (f"FAIL: {fail}",   STATUS_COLORS["missing"]),
    ]
    fx = PAD + 8
    fy = footer_y + (footer_h - 14) // 2
    for text, clr in summary_parts:
        draw.text((fx, fy), text, fill=clr, font=font_md)
        bbox = draw.textbbox((0, 0), text, font=font_md)
        fx += (bbox[2] - bbox[0]) + 28

    sheet.save(output_path)
    print(f"Saved: {output_path}")
    print(f"Total: {total} | PASS: {good} | WARN: {warn} | FAIL: {fail}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate a form-field accessibility contact sheet.")
    ap.add_argument("--data",   required=True, help="Path to form_fields.json")
    ap.add_argument("--output", required=True, help="Output PNG path")
    ap.add_argument("--label",  default="",    help="Sheet header label")
    args = ap.parse_args()

    with open(args.data, encoding="utf-8") as f:
        data = json.load(f)

    make_sheet(data, args.output, args.label)


if __name__ == "__main__":
    main()
