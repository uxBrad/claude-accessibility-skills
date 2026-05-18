#!/usr/bin/env python3
"""
link_overlay.py -- Highlight links with vague or missing accessible names.

WCAG 2.4.4 requires link purpose to be determinable from the link text alone
or from link text plus its context. This script flags links that fail that test.

Failure categories:
  vague   -- link text is a known non-descriptive phrase ("click here", "read more", etc.)
  empty   -- link has no text and no aria-label (icon-only link, invisible to screen readers)
  url     -- link text is a raw URL (valid but poor UX for screen readers)
  short   -- 1-3 character text that isn't meaningful (e.g. ">", "»", lone letters)

Warning category:
  generic -- text that might be OK in context but is ambiguous out of context
             ("more", "details", "view", "continue", "go", "info")
"""

import argparse, json, re
from PIL import Image, ImageDraw, ImageFont

VAGUE_EXACT = {
    "click here", "here", "read more", "more info", "more information",
    "learn more", "see more", "view more", "find out more",
    "this", "this link", "link", "button", "click", "press", "tap",
    "go", "continue", "next", "previous", "prev",
    "details", "detail", "info", "information",
    "see details", "view details", "click here for details",
}
GENERIC_WORDS = {"more", "view", "see", "get", "open", "show", "check", "visit"}
URL_RE = re.compile(r"^https?://|^www\.", re.IGNORECASE)

FAIL_COLOR  = (210,  30,  30, 230)
WARN_COLOR  = (200, 120,   0, 230)
FAIL_FILL   = (210,  30,  30,  40)
WARN_FILL   = (200, 120,   0,  30)

LEGEND = [
    (FAIL_COLOR, "Fail — vague/empty link text"),
    (WARN_COLOR, "Warn — ambiguous out of context"),
]

def classify_link(text, aria_label, href):
    effective = (aria_label or text or "").strip()
    if not effective:
        return "empty"
    low = effective.lower().strip(".,!?;: ")
    if low in VAGUE_EXACT:
        return "vague"
    if URL_RE.match(low) and " " not in low:
        return "url"
    words = low.split()
    if len(words) <= 2 and all(w in GENERIC_WORDS for w in words):
        return "generic"
    if len(effective) <= 3 and effective not in {"ok", "no", "go"}:
        return "short"
    return "ok"

def load_font(size=10):
    for path in ["arial.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/System/Library/Fonts/Helvetica.ttc"]:
        try: return ImageFont.truetype(path, size)
        except: pass
    return ImageFont.load_default()

def generate(screenshot_path, links, output_path, label=""):
    img = Image.open(screenshot_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = load_font(9)
    font_lbl = load_font(11)
    img_w, img_h = img.size

    flagged = [l for l in links if l.get("flag") in ("vague","empty","url","short","generic")]

    for lnk in flagged:
        x, y, w, h = lnk["x"], lnk["y"], lnk["w"], lnk["h"]
        if y + h < 0 or y > img_h or x + w < 0 or x > img_w: continue

        flag = lnk["flag"]
        is_fail = flag in ("vague", "empty", "url", "short")
        fill  = FAIL_FILL  if is_fail else WARN_FILL
        color = FAIL_COLOR if is_fail else WARN_COLOR

        draw.rectangle([x, y, x + w, y + h], fill=fill, outline=color, width=2)

        # Badge above element
        display = lnk.get("text", "")[:30] or "(no text)"
        badge_text = f"{flag.upper()}: {display}"
        bw = len(badge_text) * 6 + 8
        bx = max(0, min(x, img_w - bw))
        by = max(0, y - 18)
        draw.rectangle([bx, by, bx + bw, by + 16], fill=color[:3] + (220,))
        draw.text((bx + 4, by + 2), badge_text, fill=(255, 255, 255, 255), font=font)

    # Legend
    pad, row_h = 10, 22
    lw = 340
    lh = len(LEGEND) * row_h + pad * 2
    lx, ly = img_w - lw - pad, img_h - lh - pad
    draw.rectangle([lx, ly, lx + lw, ly + lh], fill=(20, 20, 20, 200))
    for i, (color, text) in enumerate(LEGEND):
        ry = ly + pad + i * row_h
        draw.rectangle([lx + pad, ry + 3, lx + pad + 14, ry + 15], fill=color[:3] + (200,))
        draw.text((lx + pad + 20, ry + 2), text, fill=(220, 220, 220, 220), font=font_lbl)

    if label:
        draw.rectangle([0, 0, img_w, 30], fill=(20, 20, 20, 210))
        draw.text((10, 7), label, fill=(255, 255, 255, 230), font=font_lbl)

    Image.alpha_composite(img, overlay).convert("RGB").save(output_path)

    total   = len(links)
    n_flag  = len(flagged)
    n_fail  = sum(1 for l in flagged if l["flag"] in ("vague","empty","url","short"))
    n_warn  = n_flag - n_fail
    print(f"Saved: {output_path}")
    print(f"Total links: {total}  Flagged: {n_flag} (fail: {n_fail}, warn: {n_warn})")

    if flagged:
        print("\nFlagged links:")
        for lnk in flagged:
            txt = lnk.get("text","")[:50] or "(no text)"
            print(f"  {lnk['flag'].upper():<8} <{lnk['tag']}> \"{txt}\"  href={lnk.get('href','')[:40]}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--screenshot", required=True)
    ap.add_argument("--links",      required=True)
    ap.add_argument("--output",     required=True)
    ap.add_argument("--label",      default="")
    args = ap.parse_args()
    with open(args.links) as f: links = json.load(f)
    # Classify any links not already classified
    for lnk in links:
        if "flag" not in lnk:
            lnk["flag"] = classify_link(
                lnk.get("text",""), lnk.get("aria_label",""), lnk.get("href",""))
    generate(args.screenshot, links, args.output, args.label)

if __name__ == "__main__": main()
