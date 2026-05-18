#!/usr/bin/env python3
"""
heading_tree.py -- Render the heading outline as a standalone diagram.

Produces a dark-background PNG showing the heading hierarchy as an
indented tree, color-coded by level, with issue markers.
"""

import argparse, json
from PIL import Image, ImageDraw, ImageFont

LEVEL_COLORS = {
    1: (167, 139, 250),   # purple-300
    2: ( 96, 165, 250),   # blue-300
    3: ( 52, 211, 153),   # emerald-400
    4: ( 74, 222, 128),   # green-400
    5: (251, 191,  36),   # amber-400
    6: (251, 146,  60),   # orange-400
}
BG        = (18,  18,  18)
ROW_BG    = (28,  28,  28)
ROW_ALT   = (34,  34,  34)
ISSUE_CLR = (239,  68,  68)
PASS_CLR  = ( 74, 222, 128)

ROW_H   = 28
INDENT  = 22
PAD_X   = 16
MIN_W   = 600

def load_font(size=12, bold=False):
    candidates = []
    if bold:
        candidates = ["arialbd.ttf",
                      "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    candidates += ["arial.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                   "/System/Library/Fonts/Helvetica.ttc"]
    for path in candidates:
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
            el_issues.append("Empty heading text")
        if prev_level > 0 and lvl > prev_level + 1:
            el_issues.append(f"Skipped level H{prev_level} → H{lvl}")
        if lvl == 1 and h1_count > 1:
            el_issues.append(f"Multiple H1s ({h1_count} found)")
        if el_issues:
            issues[h["index"]] = el_issues
        prev_level = lvl
    return issues

def render(headings, output_path, url=""):
    if not headings:
        print("No headings found — writing empty diagram.")
        img = Image.new("RGB", (MIN_W, 120), BG)
        draw = ImageDraw.Draw(img)
        font = load_font(13)
        draw.text((PAD_X, 48), "No headings found on this page.", fill=(180, 180, 180), font=font)
        img.save(output_path)
        return

    issues = detect_issues(headings)
    font_badge = load_font(11, bold=True)
    font_text  = load_font(12)
    font_issue = load_font(10)
    font_title = load_font(13, bold=True)

    # Calculate width needed
    max_text_len = max(
        len(f"{'  ' * (h['level']-1)}H{h['level']}  {h['text']}") for h in headings
    )
    width = max(MIN_W, PAD_X * 2 + max_text_len * 7 + 200)

    # Count rows (headings + issue sub-rows)
    total_rows = len(headings) + sum(len(v) for v in issues.values())
    title_h = 56
    footer_h = 40
    height = title_h + total_rows * ROW_H + footer_h

    img  = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    # Title bar
    draw.rectangle([0, 0, width, title_h - 4], fill=(28, 28, 28))
    draw.text((PAD_X, 10), "Heading Outline", fill=(240, 240, 240), font=font_title)
    if url:
        draw.text((PAD_X, 32), url, fill=(120, 120, 120), font=font_issue)
    draw.line([0, title_h - 4, width, title_h - 4], fill=(50, 50, 50), width=1)

    row = 0
    for h in headings:
        lvl     = h["level"]
        idx     = h["index"]
        color   = LEVEL_COLORS.get(lvl, (150, 150, 150))
        is_bad  = idx in issues
        row_y   = title_h + row * ROW_H
        row_bg  = ROW_BG if row % 2 == 0 else ROW_ALT
        draw.rectangle([0, row_y, width, row_y + ROW_H - 1], fill=row_bg)

        indent_x = PAD_X + (lvl - 1) * INDENT

        # Connector lines for indented levels
        if lvl > 1:
            draw.line([indent_x - 8, row_y, indent_x - 8, row_y + ROW_H // 2],
                      fill=(60, 60, 60), width=1)
            draw.line([indent_x - 8, row_y + ROW_H // 2, indent_x - 2, row_y + ROW_H // 2],
                      fill=(60, 60, 60), width=1)

        # Level badge
        bx, by = indent_x, row_y + 4
        draw.rectangle([bx, by, bx + 28, by + 20], fill=color)
        draw.text((bx + 4, by + 4), f"H{lvl}", fill=(255, 255, 255), font=font_badge)

        # Heading text
        text = h["text"] if h["text"].strip() else "(empty)"
        text_color = ISSUE_CLR if is_bad else (210, 210, 210)
        draw.text((bx + 36, row_y + 8), text[:80], fill=text_color, font=font_text)

        # Issue marker
        if is_bad:
            draw.text((width - 14, row_y + 8), "⚠", fill=ISSUE_CLR, font=font_text)

        row += 1

        # Issue sub-rows
        if is_bad:
            for issue_text in issues[idx]:
                iy = title_h + row * ROW_H
                draw.rectangle([0, iy, width, iy + ROW_H - 1], fill=(40, 20, 20))
                draw.text((indent_x + 36, iy + 8),
                          f"  ⚠  {issue_text}", fill=ISSUE_CLR, font=font_issue)
                row += 1

    # Footer summary
    fy = height - footer_h
    draw.rectangle([0, fy, width, height], fill=(24, 24, 24))
    total   = len(headings)
    n_bad   = len(issues)
    summary = f"{total} headings  ·  {n_bad} with issues" if n_bad else f"{total} headings  ·  No structural issues found"
    clr     = ISSUE_CLR if n_bad else PASS_CLR
    draw.text((PAD_X, fy + 12), summary, fill=clr, font=font_badge)

    img.save(output_path)
    print(f"Saved: {output_path}  ({total} headings, {n_bad} with issues)")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headings", required=True)
    ap.add_argument("--output",   required=True)
    ap.add_argument("--url",      default="")
    args = ap.parse_args()
    with open(args.headings) as f: headings = json.load(f)
    render(headings, args.output, args.url)

if __name__ == "__main__": main()
