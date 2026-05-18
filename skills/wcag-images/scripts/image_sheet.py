#!/usr/bin/env python3
"""
image_sheet.py -- Contact sheet of all images with alt text and status.

Color coding:
  Green  -- good descriptive alt text
  Yellow -- alt="" (decorative, needs manual verify)
  Red    -- missing alt attribute entirely (WCAG 1.1.1 fail)
  Orange -- generic or filename-like alt text (needs improvement)
"""

import argparse, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

STATUS_COLORS = {
    "good":       (  0, 180,  80),   # green
    "decorative": (200, 140,   0),   # amber
    "missing":    (210,  30,  30),   # red
    "filename":   (200,  80,   0),   # orange
    "generic":    (200,  80,   0),   # orange
}
STATUS_LABELS = {
    "good":       "Good alt",
    "decorative": "Decorative (verify)",
    "missing":    "Missing alt — FAIL",
    "filename":   "Filename as alt",
    "generic":    "Generic alt",
}

BG     = (22, 22, 22)
CELL_W = 220
CELL_H = 160
COLS   = 5
PAD    = 6
TEXT_H = 52   # height of label area below each image

def load_font(size=10, bold=False):
    candidates = (["arialbd.ttf"] if bold else []) + [
        "arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        try: return ImageFont.truetype(path, size)
        except: pass
    return ImageFont.load_default()

def make_sheet(crops_dir: Path, data: list, output_path: str, label=""):
    valid = [d for d in data
             if d.get("crop_file") and (crops_dir / d["crop_file"]).exists()]
    if not valid:
        print("No valid image crops to assemble.")
        return

    n    = len(valid)
    cols = min(COLS, n)
    rows = (n + cols - 1) // cols

    title_h  = 46 if label else 0
    legend_h = 32
    sheet_w  = cols * (CELL_W + PAD) + PAD
    sheet_h  = title_h + rows * (CELL_H + TEXT_H + PAD) + PAD + legend_h
    sheet    = Image.new("RGB", (sheet_w, sheet_h), BG)
    draw     = ImageDraw.Draw(sheet)
    font     = load_font(10)
    font_lg  = load_font(13, bold=True)
    font_sm  = load_font(9)
    font_alt = load_font(9)

    if label:
        draw.text((PAD, 12), label, fill=(240, 240, 240), font=font_lg)

    for i, item in enumerate(valid):
        col = i % cols
        row = i // cols
        cx  = PAD + col * (CELL_W + PAD)
        cy  = title_h + PAD + row * (CELL_H + TEXT_H + PAD)

        status = item.get("status", "missing")
        clr    = STATUS_COLORS.get(status, (150, 150, 150))

        # Cell image area
        draw.rectangle([cx, cy, cx + CELL_W, cy + CELL_H],
                       fill=(40, 40, 40), outline=clr, width=3)

        # Thumbnail
        try:
            crop = Image.open(crops_dir / item["crop_file"]).convert("RGB")
            crop.thumbnail((CELL_W - 8, CELL_H - 8), Image.LANCZOS)
            tw, th = crop.size
            sheet.paste(crop, (cx + 4 + (CELL_W - 8 - tw) // 2,
                                cy + 4 + (CELL_H - 8 - th) // 2))
        except Exception:
            draw.text((cx + 8, cy + CELL_H // 2 - 8),
                      "(load error)", fill=(120, 120, 120), font=font_sm)

        # Index badge
        idx_txt = str(item["index"] + 1)
        draw.rectangle([cx + 3, cy + 3, cx + 3 + len(idx_txt) * 7 + 6, cy + 19], fill=clr)
        draw.text((cx + 6, cy + 4), idx_txt, fill=(255, 255, 255), font=font)

        # Label area
        lx, ly = cx, cy + CELL_H + 1
        draw.rectangle([lx, ly, lx + CELL_W, ly + TEXT_H], fill=(32, 32, 32))

        # Status badge
        status_lbl = STATUS_LABELS.get(status, status)
        draw.rectangle([lx + 3, ly + 3, lx + CELL_W - 3, ly + 17], fill=clr)
        draw.text((lx + 6, ly + 4), status_lbl, fill=(255, 255, 255), font=font_sm)

        # Alt text value
        alt = item.get("alt")
        if alt is None:
            alt_display = "(no alt attribute)"
        elif alt == "":
            alt_display = '(alt=""  decorative)'
        else:
            alt_display = f'"{alt[:36]}"'
        draw.text((lx + 4, ly + 21), alt_display, fill=(180, 180, 180), font=font_alt)

        # Src filename
        src_short = item.get("src_short", "")[:36]
        draw.text((lx + 4, ly + 36), src_short, fill=(100, 100, 100), font=font_alt)

    # Legend
    legend_y = sheet_h - legend_h
    draw.rectangle([0, legend_y, sheet_w, sheet_h], fill=(16, 16, 16))
    lx = PAD
    for status, clr in STATUS_COLORS.items():
        if status == "filename": continue  # same color as generic, skip duplicate
        draw.rectangle([lx, legend_y + 8, lx + 14, legend_y + 22], fill=clr)
        draw.text((lx + 18, legend_y + 8),
                  STATUS_LABELS[status], fill=(160, 160, 160), font=font)
        lx += 155

    sheet.save(output_path)
    counts = {}
    for d in valid:
        s = d.get("status", "?")
        counts[s] = counts.get(s, 0) + 1
    print(f"Saved: {output_path}")
    print(f"Counts: {counts}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crops-dir", required=True)
    ap.add_argument("--data",      required=True)
    ap.add_argument("--output",    required=True)
    ap.add_argument("--label",     default="")
    args = ap.parse_args()
    crops_dir = Path(args.crops_dir)
    with open(args.data) as f: data = json.load(f)
    make_sheet(crops_dir, data, args.output, args.label)

if __name__ == "__main__": main()
