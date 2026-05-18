#!/usr/bin/env python3
"""
heading_overlay.py -- Annotate a screenshot with heading levels.

Draws a colored level badge (H1-H6) beside each heading on the page.
Flags structural issues: skipped levels, multiple H1s, empty headings.

Color scheme by level:
  H1 = deep purple   H2 = blue      H3 = teal
  H4 = green         H5 = amber     H6 = orange
"""

import argparse, json
from PIL import Image, ImageDraw, ImageFont

LEVEL_COLORS = {
    1: (109,  40, 217, 230),   # purple
    2: ( 29,  78, 216, 230),   # blue
    3: (  5, 150, 105, 230),   # teal
    4: ( 22, 163,  74, 230),   # green
    5: (180, 120,   0, 230),   # amber
    6: (194,  65,  12, 230),   # orange
}
ISSUE_COLOR  = (210, 30, 30, 240)
BADGE_W, BADGE_H = 36, 20

def load_font(size=11):
    for path in ["arialbd.ttf", "arial.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/System/Library/Fonts/Helvetica.ttc"]:
        try: return ImageFont.truetype(path, size)
        except: pass
    return ImageFont.load_default()

def detect_issues(headings):
    issues = {}
    h1_count = sum(1 for h in headings if h["level"] == 1)
    prev_level = 0
    for h in headings:
        lvl = h["level"]
        el_issues = []
        if not h["text"].strip():
            el_issues.append("empty heading")
        if prev_level > 0 and lvl > prev_level + 1:
            el_issues.append(f"skipped level (H{prev_level}→H{lvl})")
        if lvl == 1 and h1_count > 1:
            el_issues.append("multiple H1s on page")
        if el_issues:
            issues[h["index"]] = el_issues
        prev_level = lvl
    return issues

def generate(screenshot_path, headings, output_path, label=""):
    img = Image.open(screenshot_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font_bold = load_font(11)
    font_sm   = load_font(10)
    img_w, img_h = img.size

    issues = detect_issues(headings)

    for h in headings:
        x, y, w, hh = h["x"], h["y"], h["w"], h["h"]
        if y + hh < 0 or y > img_h: continue

        lvl   = h["level"]
        color = LEVEL_COLORS.get(lvl, (100, 100, 100, 230))
        is_issue = h["index"] in issues

        # Underline the heading text area
        line_color = ISSUE_COLOR if is_issue else color
        draw.rectangle([x, y + hh - 2, x + min(w, img_w - x), y + hh], fill=line_color)

        # Badge to left of heading (or inline if at left edge)
        bx = max(2, x - BADGE_W - 6)
        by = y + (hh - BADGE_H) // 2
        badge_fill = ISSUE_COLOR if is_issue else color
        draw.rectangle([bx, by, bx + BADGE_W, by + BADGE_H], fill=badge_fill)
        draw.text((bx + 4, by + 3), f"H{lvl}", fill=(255, 255, 255, 255), font=font_bold)

        # Issue marker
        if is_issue:
            draw.text((bx + BADGE_W + 3, by + 3), "!", fill=ISSUE_COLOR, font=font_bold)

    # Legend
    pad, col_w = 10, 100
    lw = len(LEVEL_COLORS) * col_w + pad * 2
    lh = 36
    lx, ly = img_w - lw - pad, img_h - lh - pad
    draw.rectangle([lx, ly, lx + lw, ly + lh], fill=(20, 20, 20, 200))
    for i, (lvl, color) in enumerate(LEVEL_COLORS.items()):
        cx = lx + pad + i * col_w
        draw.rectangle([cx, ly + 8, cx + 28, ly + 26], fill=color)
        draw.text((cx + 32, ly + 10), f"H{lvl}", fill=(220, 220, 220, 220), font=font_sm)

    # Issue legend entry
    draw.rectangle([lx + pad, ly + lh - 14, lx + pad + 28, ly + lh - 2],
                   fill=ISSUE_COLOR[:3] + (200,))
    draw.text((lx + pad + 32, ly + lh - 13), "Issue", fill=(220, 220, 220, 220), font=font_sm)

    if label:
        draw.rectangle([0, 0, img_w, 30], fill=(20, 20, 20, 210))
        draw.text((10, 7), label, fill=(255, 255, 255, 230), font=font_sm)

    Image.alpha_composite(img, overlay).convert("RGB").save(output_path)
    print(f"Saved: {output_path}")
    print(f"Headings: {len(headings)}  Issues: {sum(len(v) for v in issues.values())} on {len(issues)} elements")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--screenshot", required=True)
    ap.add_argument("--headings",   required=True)
    ap.add_argument("--output",     required=True)
    ap.add_argument("--label",      default="")
    args = ap.parse_args()
    with open(args.headings) as f: headings = json.load(f)
    generate(args.screenshot, headings, args.output, args.label)

if __name__ == "__main__": main()
