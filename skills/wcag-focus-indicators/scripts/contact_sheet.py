#!/usr/bin/env python3
"""
contact_sheet.py -- Assemble per-element focus crops into a contact sheet grid.

Each cell shows the focused element state with:
  Green border  -- focus indicator was detected (PASS)
  Red border    -- no focus indicator detected (FAIL)
  Grey border   -- error during capture

Usage:
  python contact_sheet.py --crops-dir <dir> --data <focus_data.json> --output <sheet.png> [--label "Desktop"]
"""

import argparse, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

CELL_W  = 220
CELL_H  = 150
COLS    = 5
PAD     = 6
LABEL_H = 34
BG      = (28, 28, 28)
CELL_BG = (48, 48, 48)

PASS_CLR  = (  0, 180,  80)
FAIL_CLR  = (210,  30,  30)
ERROR_CLR = (120, 120, 120)

def load_font(size=10):
    for path in ["arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/System/Library/Fonts/Helvetica.ttc"]:
        try: return ImageFont.truetype(path, size)
        except: pass
    return ImageFont.load_default()

def status_color(status):
    if status == "pass":  return PASS_CLR
    if status == "fail":  return FAIL_CLR
    return ERROR_CLR

def make_sheet(crops_dir: Path, data: list, output_path: str, label=""):
    valid = [d for d in data
             if d.get("crop_file") and (crops_dir / d["crop_file"]).exists()]

    if not valid:
        print("No valid crops to assemble.")
        return

    n    = len(valid)
    cols = min(COLS, n)
    rows = (n + cols - 1) // cols

    title_h  = 44 if label else 0
    sheet_w  = cols * (CELL_W + PAD) + PAD
    sheet_h  = title_h + rows * (CELL_H + LABEL_H + PAD) + PAD + 30  # +30 for legend
    sheet    = Image.new("RGB", (sheet_w, sheet_h), BG)
    draw     = ImageDraw.Draw(sheet)
    font     = load_font(10)
    font_lg  = load_font(13)
    font_sm  = load_font(9)

    if label:
        draw.text((PAD, 12), label, fill=(240,240,240), font=font_lg)

    for i, item in enumerate(valid):
        col = i % cols
        row = i // cols
        cx  = PAD + col * (CELL_W + PAD)
        cy  = title_h + PAD + row * (CELL_H + LABEL_H + PAD)

        clr = status_color(item.get("status","error"))

        # Cell background + border
        draw.rectangle([cx, cy, cx+CELL_W, cy+CELL_H], fill=CELL_BG, outline=clr, width=3)

        # Crop thumbnail
        crop = Image.open(crops_dir / item["crop_file"]).convert("RGB")
        crop.thumbnail((CELL_W-8, CELL_H-8), Image.LANCZOS)
        tw, th = crop.size
        sheet.paste(crop, (cx+4+(CELL_W-8-tw)//2, cy+4+(CELL_H-8-th)//2))

        # Index badge (top-left)
        badge = str(item["index"]+1)
        bw = len(badge)*7 + 8
        draw.rectangle([cx+3, cy+3, cx+3+bw, cy+19], fill=clr)
        draw.text((cx+6, cy+4), badge, fill=(255,255,255), font=font)

        # Diff score badge (top-right)
        score_text = f"d={item.get('diff_score',0):.0f}"
        draw.text((cx+CELL_W-45, cy+4), score_text, fill=(180,180,180), font=font_sm)

        # Label row below cell
        draw.rectangle([cx, cy+CELL_H+1, cx+CELL_W, cy+CELL_H+LABEL_H], fill=(38,38,38))
        tag_lbl = f"<{item.get('tag','?')}> {item.get('label','')[:26]}"
        draw.text((cx+4, cy+CELL_H+5), tag_lbl, fill=(200,200,200), font=font)
        status_lbl = ("Focus visible" if item.get("status")=="pass"
                      else "No focus indicator" if item.get("status")=="fail"
                      else "Capture error")
        draw.text((cx+4, cy+CELL_H+19), status_lbl, fill=clr, font=font)

    # Legend strip at bottom
    legend_y = sheet_h - 26
    draw.rectangle([0, legend_y, sheet_w, sheet_h], fill=(18,18,18))
    items_legend = [
        (PASS_CLR,  "Focus visible"),
        (FAIL_CLR,  "No focus indicator"),
        (ERROR_CLR, "Capture error"),
    ]
    lx = PAD
    for clr, text in items_legend:
        draw.rectangle([lx, legend_y+6, lx+14, legend_y+20], outline=clr, width=3)
        draw.text((lx+18, legend_y+6), text, fill=(170,170,170), font=font)
        lx += 140

    sheet.save(output_path)
    passed = sum(1 for d in valid if d.get("status")=="pass")
    failed = sum(1 for d in valid if d.get("status")=="fail")
    print(f"Saved: {output_path}")
    print(f"Pass: {passed}  Fail: {failed}  Total: {len(valid)}")

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