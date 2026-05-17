#!/usr/bin/env python3
"""
contrast_overlay.py -- Overlay WCAG contrast ratio results on a screenshot.

Draws a red outlined badge on text elements that fail AA contrast.
Elements that pass AA get a subtle green border (optional, controlled by --show-passes).

WCAG thresholds:
  Normal text: AA=4.5:1  AAA=7.0:1
  Large text (>=18pt or >=14pt bold): AA=3.0:1  AAA=4.5:1
"""

import argparse, json
from PIL import Image, ImageDraw, ImageFont

FAIL_FILL   = (210,  30,  30,  40)
FAIL_BORDER = (210,  30,  30, 240)
AA_FILL     = (240, 180,   0,  25)
AA_BORDER   = (200, 140,   0, 160)
AAA_FILL    = (  0, 180,  80,  15)
AAA_BORDER  = (  0, 160,  60, 100)

def relative_luminance(r, g, b):
    def linearize(c):
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126*linearize(r) + 0.7152*linearize(g) + 0.0722*linearize(b)

def contrast_ratio(fg, bg):
    l1 = relative_luminance(*fg)
    l2 = relative_luminance(*bg)
    lighter, darker = max(l1,l2), min(l1,l2)
    return (lighter + 0.05) / (darker + 0.05)

def grade(ratio, is_large):
    aa  = 3.0 if is_large else 4.5
    aaa = 4.5 if is_large else 7.0
    if ratio >= aaa: return "aaa"
    if ratio >= aa:  return "aa"
    return "fail"

def load_font(size=10):
    for path in ["arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/System/Library/Fonts/Helvetica.ttc"]:
        try: return ImageFont.truetype(path, size)
        except: pass
    return ImageFont.load_default()

def generate(screenshot_path, elements, output_path, label="", show_passes=False):
    img = Image.open(screenshot_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    font = load_font(9)
    font_label = load_font(11)
    img_w, img_h = img.size

    graded = []
    for el in elements:
        if "fg" not in el or "bg" not in el: continue
        try:
            ratio = contrast_ratio(el["fg"], el["bg"])
        except Exception:
            continue
        status = grade(ratio, el.get("isLarge", False))
        graded.append({**el, "ratio": ratio, "status": status})

    for el in graded:
        x, y, w, h = el["x"], el["y"], el["w"], el["h"]
        if y+h < 0 or y > img_h or x+w < 0 or x > img_w: continue
        status = el["status"]
        ratio  = el["ratio"]

        if status == "fail":
            draw.rectangle([x,y,x+w,y+h], fill=FAIL_FILL, outline=FAIL_BORDER, width=2)
            badge = f"{ratio:.1f}:1"
            bw = len(badge)*6 + 6
            draw.rectangle([x, y-14, x+bw, y], fill=(210,30,30,230))
            draw.text((x+3, y-13), badge, fill=(255,255,255,255), font=font)
        elif status == "aa" and show_passes:
            draw.rectangle([x,y,x+w,y+h], fill=AA_FILL, outline=AA_BORDER, width=1)
        elif status == "aaa" and show_passes:
            draw.rectangle([x,y,x+w,y+h], fill=AAA_FILL, outline=AAA_BORDER, width=1)

    # Legend
    pad, row_h = 10, 22
    legends = [
        (FAIL_BORDER, "Fail (below AA threshold)"),
        (AA_BORDER,   "AA pass (4.5:1 or 3:1 large)"),
        (AAA_BORDER,  "AAA pass (7:1 or 4.5:1 large)"),
    ]
    lw, lh = 300, len(legends)*row_h + pad*2
    lx, ly = img_w - lw - pad, img_h - lh - pad
    draw.rectangle([lx,ly,lx+lw,ly+lh], fill=(20,20,20,200))
    for i, (color, text) in enumerate(legends):
        ry = ly + pad + i*row_h
        draw.rectangle([lx+pad, ry+3, lx+pad+14, ry+15], fill=color)
        draw.text((lx+pad+20, ry+2), text, fill=(255,255,255,220), font=font_label)

    if label:
        draw.rectangle([0,0,img_w,30], fill=(20,20,20,210))
        draw.text((10,7), label, fill=(255,255,255,230), font=font_label)

    Image.alpha_composite(img, overlay).convert("RGB").save(output_path)

    total = len(graded)
    fail  = sum(1 for e in graded if e["status"]=="fail")
    aa    = sum(1 for e in graded if e["status"]=="aa")
    aaa   = sum(1 for e in graded if e["status"]=="aaa")
    print(f"Saved: {output_path}")
    print(f"Total text elements: {total}  AAA: {aaa}  AA only: {aa}  Fail: {fail}")

    # Print worst offenders
    failures = sorted([e for e in graded if e["status"]=="fail"], key=lambda e: e["ratio"])
    if failures:
        print("\nFailing elements (worst first):")
        for e in failures[:20]:
            large = " [large]" if e.get("isLarge") else ""
            need  = 3.0 if e.get("isLarge") else 4.5
            print(f"  {e['ratio']:.2f}:1{large}  <{e['tag']}> \"{e.get('text','')[:40]}\"  (need {need}:1)")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--screenshot",   required=True)
    ap.add_argument("--elements",     required=True)
    ap.add_argument("--output",       required=True)
    ap.add_argument("--label",        default="")
    ap.add_argument("--show-passes",  action="store_true")
    args = ap.parse_args()
    with open(args.elements) as f: elements = json.load(f)
    generate(args.screenshot, elements, args.output, args.label, args.show_passes)

if __name__ == "__main__": main()