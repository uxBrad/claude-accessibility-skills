#!/usr/bin/env python3
"""
capture_spacing.py -- Apply WCAG 1.4.12 text-spacing overrides and capture before/after screenshots.

WCAG 1.4.12 Text Spacing (AA) requires that no loss of content or functionality
occurs when the following CSS properties are overridden:
  - line-height: 1.5 (relative to font-size)
  - letter-spacing: 0.12em
  - word-spacing: 0.16em
  - paragraph / block spacing: 2em margin-bottom
"""

import argparse
import json
import os
from playwright.sync_api import sync_playwright

SPACING_CSS = """
*, *::before, *::after {
    line-height: 1.5 !important;
    letter-spacing: 0.12em !important;
    word-spacing: 0.16em !important;
}
p, li, dt, dd, blockquote, label, legend {
    margin-bottom: 2em !important;
}
"""


def capture(url, viewport, output_dir):
    w, h = (1280, 900) if viewport == "desktop" else (390, 844)
    width_label = w

    os.makedirs(output_dir, exist_ok=True)
    before_path = os.path.join(output_dir, "before.png")
    after_path = os.path.join(output_dir, "after.png")
    data_path = os.path.join(output_dir, "spacing_data.json")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": w, "height": h})
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1500)

        # Before screenshot
        page.screenshot(path=before_path, full_page=True)
        before_height = page.evaluate("document.documentElement.scrollHeight")
        print(f"Before screenshot saved: {before_path}  (height: {before_height}px)")

        # Inject WCAG 1.4.12 spacing overrides
        page.add_style_tag(content=SPACING_CSS)
        page.wait_for_timeout(500)

        # After screenshot
        page.screenshot(path=after_path, full_page=True)
        after_height = page.evaluate("document.documentElement.scrollHeight")
        print(f"After screenshot saved:  {after_path}  (height: {after_height}px)")

        # Check for horizontal scroll
        has_horizontal_scroll = page.evaluate(
            "document.documentElement.scrollWidth > document.documentElement.clientWidth + 4"
        )

        # Detect overflowing elements
        overflowing_elements = page.evaluate("""
            (function() {
                var results = [];
                var all = document.querySelectorAll('*');
                for (var i = 0; i < all.length; i++) {
                    var el = all[i];
                    if (el.scrollWidth > el.clientWidth + 2) {
                        var s = window.getComputedStyle(el);
                        if (s.display === 'none' || s.visibility === 'hidden') continue;
                        if (el.clientWidth === 0) continue;
                        results.push({
                            tag: el.tagName.toLowerCase(),
                            id: el.id || '',
                            className: (el.className && typeof el.className === 'string')
                                       ? el.className.trim().replace(/\\s+/g, ' ').slice(0, 80)
                                       : '',
                            scrollWidth: el.scrollWidth,
                            clientWidth: el.clientWidth
                        });
                    }
                }
                return results.slice(0, 50);
            })()
        """)

        browser.close()

    height_increase_px = after_height - before_height
    height_increase_pct = round((height_increase_px / before_height * 100), 1) if before_height else 0

    data = {
        "viewport": viewport,
        "width": width_label,
        "before_height": before_height,
        "after_height": after_height,
        "height_increase_px": height_increase_px,
        "height_increase_pct": height_increase_pct,
        "has_horizontal_scroll": has_horizontal_scroll,
        "overflowing_elements": overflowing_elements,
    }

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Data saved: {data_path}")
    print(f"Height increase: {height_increase_px}px ({height_increase_pct}%)")
    print(f"Horizontal scroll: {has_horizontal_scroll}")
    print(f"Overflowing elements: {len(overflowing_elements)}")

    return data


def main():
    parser = argparse.ArgumentParser(
        description="Capture before/after screenshots applying WCAG 1.4.12 text-spacing overrides."
    )
    parser.add_argument("--url", required=True, help="URL to audit")
    parser.add_argument(
        "--viewport",
        default="desktop",
        choices=["desktop", "mobile"],
        help="Viewport size: desktop (1280px) or mobile (390px)",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to save before.png, after.png, and spacing_data.json",
    )
    args = parser.parse_args()
    capture(args.url, args.viewport, args.output_dir)


if __name__ == "__main__":
    main()
