#!/usr/bin/env python3
"""
target_heatmap.py -- Overlay interactive element sizes on a screenshot.

Color coding:
  Green  -- passes WCAG 2.5.5 AAA (>= 44 x 44 px)
  Yellow -- passes WCAG 2.5.8 AA  (>= 24 x 24 px, both dimensions)
  Red    -- fails WCAG 2.5.8 AA   (< 24 px in width or height)
"""

import argparse, json
from PIL import Image, ImageDraw, ImageFont

AAA_FILL   = (  0, 180,  80,  55)
AAA_BORDER = (  0, 160,  60, 230)
AA_FILL    = (240, 180,   0,  55)
AA_BORDER  = (200, 140,   0, 230)
FAIL_FILL  = (210,  30,  30,  55)
FAIL_BORDER= (210,  30,  30, 230)

LEGEND = [
    (AAA_BORDER, ">= 44x44px  WCAG 2.5.5 AAA pass"),
    (AA_BORDER,  ">= 24x24px  WCAG 2.5.8 AA pass"),
    (FAIL_BORDER,"< 24x24px   WCAG 2.5.8 AA FAIL"),
]

def pick_colors(status):
    if status == "aaa":   return AAA_FILL, AAA_BORDER
    if status == "aa":    return AA_FILL,  AA_BORDER
    return FAIL_FILL, FAIL_BORDER

def load_font(size=11):
    for path in ["arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/System/Library/Fonts/Helvetica.ttc"]:
        try: return ImageFont.truetype(path, size)
        except: pass
    return ImageFont.load_default()

def generate(screenshot_path, elements, output_path, label=""):
    img = Image.open(screenshot_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = load_font(11)
    font_sm = load_font(9)
    img_w, img_h = img.size

    for el in elements:
        x, y, w, h = el["x"], el["y"], el["w"], el["h"]
        if y + h < 0 or y > img_h or x + w < 0 or x > img_w: continue
        fill, border = pick_colors(el["status"])
        draw.rectangle([x, y, x+w, y+h], fill=fill, outline=border, width=2)
        draw.text((x+3, y+3), f"{w}x{h}", fill=(255,255,255,220), font=font_sm)

    # Legend
    pad, row_h = 10, 22
    lw, lh = 340, len(LEGEND)*row_h + pad*2
    lx, ly = img_w - lw - pad, img_h - lh - pad
    draw.rectangle([lx, ly, lx+lw, ly+lh], fill=(20,20,20,200))
    for i, (color, text) in enumerate(LEGEND):
        ry = ly + pad + i*row_h
        draw.rectangle([lx+pad, ry+3, lx+pad+14, ry+15], fill=color)
        draw.text((lx+pad+20, ry+2), text, fill=(255,255,255,220), font=font)

    # Title bar
    if label:
        draw.rectangle([0,0,img_w,30], fill=(20,20,20,210))
        draw.text((10,7), label, fill=(255,255,255,230), font=font)

    Image.alpha_composite(img, overlay).convert("RGB").save(output_path)
    print(f"Saved: {output_path}")

    total = len(elements)
    aaa   = sum(1 for e in elements if e["status"]=="aaa")
    aa    = sum(1 for e in elements if e["status"]=="aa")
    fail  = sum(1 for e in elements if e["status"]=="fail")
    print(f"Total: {total}  AAA: {aaa}  AA: {aa}  Fail: {fail}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--screenshot", required=True)
    ap.add_argument("--elements",   required=True)
    ap.add_argument("--output",     required=True)
    ap.add_argument("--label",      default="")
    args = ap.parse_args()
    with open(args.elements) as f: elements = json.load(f)
    generate(args.screenshot, elements, args.output, args.label)

if __name__ == "__main__": main()