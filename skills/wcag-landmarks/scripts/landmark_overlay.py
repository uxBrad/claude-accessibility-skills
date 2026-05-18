#!/usr/bin/env python3
"""
landmark_overlay.py -- Annotate a screenshot with ARIA landmark regions.

Draws semi-transparent colored overlays for each landmark element on the page.
Color-coded by landmark role: banner, navigation, main, complementary,
contentinfo, search, form, region.

Landmarks are drawn largest-to-smallest so nested/smaller regions remain visible.
"""

import argparse, json
from PIL import Image, ImageDraw, ImageFont

# (R, G, B) fill colors per landmark role
ROLE_COLORS = {
    "banner":        (130,  60, 220),   # purple
    "navigation":    ( 30, 100, 220),   # blue
    "main":          ( 20, 160,  80),   # green
    "complementary": (  0, 160, 180),   # teal
    "contentinfo":   (200, 100,  20),   # orange
    "search":        (200, 180,   0),   # yellow
    "form":          (200,  50,  50),   # red
    "region":        (140, 140, 140),   # grey
}
FILL_ALPHA   = 40    # translucent fill
BORDER_ALPHA = 220   # solid-ish border
BORDER_PX    = 3

ROLE_LABELS = {
    "banner":        "Banner / Header",
    "navigation":    "Navigation",
    "main":          "Main",
    "complementary": "Complementary / Aside",
    "contentinfo":   "Content Info / Footer",
    "search":        "Search",
    "form":          "Form",
    "region":        "Region / Section",
}


def load_font(size=11):
    candidates = [
        "arialbd.ttf", "arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def color_with_alpha(rgb, alpha):
    return (rgb[0], rgb[1], rgb[2], alpha)


def generate(screenshot_path, landmarks, output_path, label=""):
    img = Image.open(screenshot_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    img_w, img_h = img.size

    font_bold = load_font(12)
    font_sm   = load_font(11)
    font_xs   = load_font(10)

    # Sort largest area first so smaller landmarks are drawn on top
    sorted_landmarks = sorted(
        landmarks,
        key=lambda lm: lm.get("w", 0) * lm.get("h", 0),
        reverse=True,
    )

    for lm in sorted_landmarks:
        x, y, w, h = lm.get("x", 0), lm.get("y", 0), lm.get("w", 0), lm.get("h", 0)

        # Skip if off-screen
        if y + h < 0 or y > img_h or x + w < 0 or x > img_w:
            continue
        # Skip zero-size
        if w == 0 or h == 0:
            continue

        role  = lm.get("role", "region")
        rgb   = ROLE_COLORS.get(role, (140, 140, 140))
        name  = lm.get("accessible_name", "")

        # Clamp coordinates to image bounds
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(img_w - 1, x + w)
        y2 = min(img_h - 1, y + h)

        # Semi-transparent fill
        fill_color = color_with_alpha(rgb, FILL_ALPHA)
        draw.rectangle([x1, y1, x2, y2], fill=fill_color)

        # Colored border
        border_color = color_with_alpha(rgb, BORDER_ALPHA)
        for i in range(BORDER_PX):
            draw.rectangle(
                [x1 + i, y1 + i, x2 - i, y2 - i],
                outline=border_color,
            )

        # Badge label in top-left of the landmark
        badge_role = role
        badge_text = badge_role
        if name:
            truncated = name[:30] + ("…" if len(name) > 30 else "")
            badge_text = f"{badge_role}: {truncated}"

        # Measure badge text size
        try:
            bbox = draw.textbbox((0, 0), badge_text, font=font_bold)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        except AttributeError:
            tw, th = draw.textsize(badge_text, font=font_bold)

        pad_x, pad_y = 6, 4
        bw = tw + pad_x * 2
        bh = th + pad_y * 2

        bx = x1 + 4
        by = y1 + 4
        # Clamp badge inside image
        bx = min(bx, img_w - bw - 2)
        by = min(by, img_h - bh - 2)

        draw.rectangle(
            [bx, by, bx + bw, by + bh],
            fill=color_with_alpha(rgb, 220),
        )
        draw.text(
            (bx + pad_x, by + pad_y),
            badge_text,
            fill=(255, 255, 255, 255),
            font=font_bold,
        )

    # ── Header bar ──────────────────────────────────────────────────────────
    header_h = 32
    draw.rectangle([0, 0, img_w, header_h], fill=(24, 24, 24, 210))
    if label:
        draw.text((10, 8), label, fill=(255, 255, 255, 230), font=font_sm)

    # ── Legend at bottom ────────────────────────────────────────────────────
    roles_found = list(dict.fromkeys(
        lm.get("role", "region") for lm in landmarks
        if lm.get("role", "region") in ROLE_COLORS
    ))

    if roles_found:
        swatch_size = 14
        col_gap     = 16
        row_h       = 22
        pad_x_leg   = 12
        pad_y_leg   = 8

        # Compute legend dimensions
        max_label_w = 0
        for role in roles_found:
            role_label = ROLE_LABELS.get(role, role)
            try:
                bbox = draw.textbbox((0, 0), role_label, font=font_xs)
                lw = bbox[2] - bbox[0]
            except AttributeError:
                lw, _ = draw.textsize(role_label, font=font_xs)
            max_label_w = max(max_label_w, lw)

        col_w    = swatch_size + 6 + max_label_w + col_gap
        n_cols   = max(1, min(4, len(roles_found)))
        n_rows   = (len(roles_found) + n_cols - 1) // n_cols
        leg_w    = n_cols * col_w + pad_x_leg * 2
        leg_h    = n_rows * row_h + pad_y_leg * 2

        leg_x = (img_w - leg_w) // 2
        leg_y = img_h - leg_h - 8

        draw.rectangle(
            [leg_x, leg_y, leg_x + leg_w, leg_y + leg_h],
            fill=(24, 24, 24, 210),
        )

        for i, role in enumerate(roles_found):
            col_i = i % n_cols
            row_i = i // n_cols
            sx = leg_x + pad_x_leg + col_i * col_w
            sy = leg_y + pad_y_leg + row_i * row_h + (row_h - swatch_size) // 2

            rgb = ROLE_COLORS.get(role, (140, 140, 140))
            draw.rectangle(
                [sx, sy, sx + swatch_size, sy + swatch_size],
                fill=color_with_alpha(rgb, 230),
            )

            role_label = ROLE_LABELS.get(role, role)
            draw.text(
                (sx + swatch_size + 6, sy + 1),
                role_label,
                fill=(220, 220, 220, 220),
                font=font_xs,
            )

    # Composite and save
    result = Image.alpha_composite(img, overlay).convert("RGB")
    result.save(output_path)
    print(f"Saved: {output_path}")
    print(f"Landmarks: {len(landmarks)}  Roles found: {roles_found}")


def main():
    ap = argparse.ArgumentParser(description="Overlay landmark regions on a screenshot.")
    ap.add_argument("--screenshot", required=True,  help="Input screenshot path")
    ap.add_argument("--landmarks",  required=True,  help="JSON file with landmark data")
    ap.add_argument("--output",     required=True,  help="Output annotated image path")
    ap.add_argument("--label",      default="",     help="Header bar label text")
    args = ap.parse_args()

    with open(args.landmarks) as f:
        landmarks = json.load(f)

    if not landmarks:
        print("Warning: landmark list is empty — copying screenshot as-is.")
        img = Image.open(args.screenshot).convert("RGB")
        img.save(args.output)
        return

    generate(args.screenshot, landmarks, args.output, args.label)


if __name__ == "__main__":
    main()
